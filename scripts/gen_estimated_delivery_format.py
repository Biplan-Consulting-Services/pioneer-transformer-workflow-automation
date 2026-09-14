# -*- coding: utf-8 -*-
"""Generate the SharePoint column-formatting JSON for Estimated Delivery Date.

    python gen_estimated_delivery_format.py [-o out.json]

WHY COLUMN FORMATTING AND NOT A CALCULATED COLUMN OR A FLOW
-----------------------------------------------------------
`TODAY()` in a SharePoint calculated column is a snapshot: it is evaluated when the
item is written and never again, so the value freezes at last-save and drifts a day
further out of date every day after. `calculated-columns-plan.md` settled on a nightly
flow that touches rows to force re-evaluation; the 2026-09-11 nightly-cleanup build
measured that at 915 of 1,189 rows a night -- ~334,000 versions a year and ~1,830
Power Automate actions against a 2,000/day allowance, which would starve the five
event-triggered flows. That approach is dead.

Column formatting's `@now` is evaluated in the browser at render time. It is never
stale, costs nothing, writes nothing, and creates no versions.

WHAT IT CANNOT DO, AND THIS IS THE WHOLE TRADE
----------------------------------------------
Column formatting DISPLAYS a value; it does not STORE one. The column stays empty, so
the estimate cannot be sorted, filtered, grouped, exported to Excel, read by Power
Query, or picked up by the BO Report (which is a view-bound Export-to-Excel web query,
so it exports the stored value -- nothing).

For the workbook side the answer is not a flow either: the viewer already rebuilds
`TableOrders` in Power Query, so it can compute this same formula in M against
`DateTime.LocalNow()` and get a live value at every refresh, also for free. See
`docs/estimated-delivery-date-today.md`.

THE SOURCE FORMULA
------------------
Ported from `TableOrders`' `Estimated Delivery Date` calculatedColumnFormula, read out
of `xl/tables/table4.xml` in the archived staff workbook -- not from any prose summary
of it. Eight branches, tested in this order:

    1  Delivery Date set                -> it
    2  Manual Estimated Delivery Date   -> it
    3  Finishing Date set               -> MAX(TODAY, Finishing)          + 7  + pen
    4  Testing Date set                 -> MAX(TODAY, Testing)            + 10 + pen
    5  Tanking Date set                 -> MAX(TODAY, Tanking)            + 14 + pen
    6  any of Coiling..Drying set       -> MAX(TODAY, Coiling..Drying,
                                               Tank Delivery Date)        + 21 + pen
    7  Order Date set                   -> Order Date + 90 + LeadTime*7
    8  otherwise                        -> "no order" / "defaut formule"

    pen = 0 when BO is "OK" or blank, else 30.

TWO FIELD-MAPPING TRAPS -- the reason this is generated rather than hand-typed
------------------------------------------------------------------------------
The workbook column names do NOT map to the same-sounding SharePoint columns. Both of
these are settled by the viewer's `ColumnMap.pq`, which was verified value-for-value at
cutover (18,946 values, 3 differences, all understood):

    workbook "Delivery Date"  ->  Planned_x0020_Delivery_x0020_Dat   NOT DeliveryDate
    workbook "Tanking Date"   ->  Planned_x0020_Tanking_x0020_Date   NOT TankingDate

`DeliveryDate` ("Delivery End Date") and `TankingDate` ("Tanking End Date") are the
COMPLETION stamps and have no workbook column at all. The columns staff have always
typed into are the planning dates. Mapping by name would silently produce a different
formula on ~1,189 rows and still look plausible.

⚠️ `calculated-columns-plan.md`'s 2026-08-31 impact table labels its rows
"Delivery End Date" and "Tanking End Date". If it counted the End Date columns, its
21-rows-where-TODAY-matters figure is measuring different columns than the formula
reads. Raised, not silently corrected -- re-measure before relying on that number.

ONE DELIBERATE BEHAVIOUR CHANGE
-------------------------------
Branch 7's Excel form is `XLOOKUP(Client, ClientLeadTimes, ..., 52)` -- a 52-week
default for a client missing from the table. `calculated-columns-plan.md` settled that
this contradicts FRM13's own `GENERIC VALUE` of 26 SEM and should be retired. The lead
time is already synced onto `Order Items` as `CliLeadTimeWeeks`, so this uses that
column and falls back to GENERIC_WEEKS below, not 52. Change the constant, not the
emitted JSON.

A QUIRK PRESERVED ON PURPOSE
----------------------------
Branch 6's CONDITION tests only Coiling..Drying, but its VALUE also maxes in
`Tank Delivery Date`. So a unit with a Tank Delivery Date and no other milestone falls
through to branch 7 and never sees it. That is what the workbook does. Preserved
deliberately; if it is wrong it is wrong in Excel too and should be fixed in both.
"""
import json, io, argparse

# Lead-time weeks for a row with no CliLeadTimeWeeks. FRM13's GENERIC VALUE, not the
# Excel formula's 52 -- see the module docstring.
GENERIC_WEEKS = 26

# SharePoint internal name -> what it is in the workbook. Order matters for nothing
# here; this exists so the traps above are visible in one place.
F_DELIVERY   = "Planned_x0020_Delivery_x0020_Dat"   # workbook "Delivery Date"
F_MANUAL     = "ManualEstimatedDeliveryDate"
F_FINISHING  = "FinishingDate"
F_TESTING    = "TestingDate"
F_TANKING    = "Planned_x0020_Tanking_x0020_Date"   # workbook "Tanking Date"
F_COILING    = "CoilingDate"
F_STACKING   = "StackingDate"
F_ASSEMBLY   = "AssemblyDate"
F_DRYING     = "DryingDate"
F_TANKDELIV  = "TankDeliveryDate"
F_ORDERDATE  = "OrdOrderDate"
F_LEADWEEKS  = "CliLeadTimeWeeks"
F_BO         = "BO"
F_ORDER      = "Order_Number_TextField"

COILING_RANGE = [F_COILING, F_STACKING, F_ASSEMBLY, F_DRYING]


def fld(name):
    return "[$%s]" % name


def num(expr):
    return "Number(%s)" % expr


def if_(cond, a, b):
    return "if(%s, %s, %s)" % (cond, a, b)


def mx(terms):
    """MAX over date expressions, returning the winning DATE (not a number).

    Balanced rather than left-folded: there are no variables in a column-formatting
    expression, so every fold step re-inlines its accumulator and a left fold over n
    terms costs 2^n - 1 comparisons. Pairing them costs far fewer for the six-term
    branch 6 and is otherwise identical.
    """
    if len(terms) == 1:
        return terms[0]
    mid = len(terms) // 2
    a, b = mx(terms[:mid]), mx(terms[mid:])
    return if_("%s > %s" % (num(a), num(b)), a, b)


def nonblank(name):
    return "%s != ''" % fld(name)


def shown(date_expr):
    return "toLocaleDateString(%s)" % date_expr


def milestone(terms, buffer_days):
    """MAX(TODAY(), <terms>) + buffer + BO penalty, rendered as a date string.

    The penalty folds into addDays' day count rather than a second addDays: the BO
    test is the same in all four milestone branches and this keeps it to one call.
    """
    pen = if_("%s == 'OK' || %s == ''" % (fld(F_BO), fld(F_BO)),
              str(buffer_days), str(buffer_days + 30))
    return shown("addDays(%s, %s)" % (mx(["@now"] + [fld(t) for t in terms]), pen))


def build_expression():
    # Branch 7 -- Order Date + 90 + LeadTime*7, with GENERIC_WEEKS for a blank lead time.
    weeks = if_("%s == ''" % fld(F_LEADWEEKS), str(GENERIC_WEEKS), num(fld(F_LEADWEEKS)))
    branch7 = shown("addDays(%s, 90 + (%s) * 7)" % (fld(F_ORDERDATE), weeks))

    # Branch 8 -- the two Excel error strings, kept verbatim so a row reading one of
    # these means the same thing it means in the workbook.
    branch8 = if_("%s == ''" % fld(F_ORDER), "'no order'", "'defaut formule'")

    # Built inside-out, so this reads in the reverse of the branch order above.
    expr = if_(nonblank(F_ORDERDATE), branch7, branch8)
    expr = if_(" || ".join(nonblank(f) for f in COILING_RANGE),
               milestone(COILING_RANGE + [F_TANKDELIV], 21), expr)
    expr = if_(nonblank(F_TANKING), milestone([F_TANKING], 14), expr)
    expr = if_(nonblank(F_TESTING), milestone([F_TESTING], 10), expr)
    expr = if_(nonblank(F_FINISHING), milestone([F_FINISHING], 7), expr)
    expr = if_(nonblank(F_MANUAL), shown(fld(F_MANUAL)), expr)
    expr = if_(nonblank(F_DELIVERY), shown(fld(F_DELIVERY)), expr)
    return expr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out",
                    default="sharepoint-lists/formatting/EstimatedDeliveryDate.format.json")
    a = ap.parse_args()

    expr = build_expression()

    doc = {
        "$schema": "https://developer.microsoft.com/json-schemas/sp/v2/column-formatting.schema.json",
        "elmType": "div",
        "style": {"white-space": "nowrap"},
        "txtContent": "=" + expr,
    }

    # ------------------------------------------------------------------ verify
    # Every field the expression reads must be one this script declares. A typo in an
    # internal name does not error in SharePoint -- it renders blank, which reads as
    # "this unit has no estimate" rather than as a broken column.
    import re
    used = set(re.findall(r"\[\$([A-Za-z0-9_]+)\]", expr))
    declared = {F_DELIVERY, F_MANUAL, F_FINISHING, F_TESTING, F_TANKING, F_TANKDELIV,
                F_ORDERDATE, F_LEADWEEKS, F_BO, F_ORDER} | set(COILING_RANGE)
    assert used <= declared, "expression reads undeclared field(s): %s" % (used - declared)
    assert F_DELIVERY in used and F_TANKING in used, "a planning-date trap field went missing"
    assert "DeliveryDate" not in used, "DeliveryDate is the completion stamp -- see the docstring"
    assert "TankingDate" not in used, "TankingDate is the completion stamp -- see the docstring"
    # Parens balance, checked by walking rather than by counting call sites -- the
    # first attempt at this counted `if(`/`Number(`/... against `)` and was simply
    # wrong (it missed the `(weeks) * 7` grouping), which is a good argument for
    # checking the property you mean instead of a proxy for it.
    depth = 0
    for ch in expr:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            assert depth >= 0, "expression closes a paren it never opened"
    assert depth == 0, "expression leaves %d paren(s) open" % depth

    import os
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(doc, indent=2) + "\n")

    print("wrote %s" % a.out)
    print("  expression length : %d chars" % len(expr))
    print("  if() branches     : %d" % expr.count("if("))
    print("  fields read       : %d  (%s)" % (len(used), ", ".join(sorted(used))))
    print("  lead-time default : %d weeks (FRM13 GENERIC VALUE, not the workbook's 52)" % GENERIC_WEEKS)
    print("  planning-date traps honoured: %s, %s" % (F_DELIVERY, F_TANKING))


if __name__ == "__main__":
    main()
