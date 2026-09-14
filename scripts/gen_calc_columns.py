# -*- coding: utf-8 -*-
"""Port FRM10-12's remaining calculated columns onto `Order Items`.

    python gen_calc_columns.py

Emits `scripts/n9_create_calc_columns.js` -- eight columns created over REST (seven
calculated, plus the `Calc Refreshed` timestamp the nightly touch writes) -- from the
formulas read out of the workbook package rather than from any prose.

WHAT CHANGED, AND WHY THIS IS NOW POSSIBLE
------------------------------------------
`calculated-columns-plan.md` opens with "none of the 7 columns below can be a plain
SharePoint calculated column", on two walls:

    1. no cross-list lookups        <- THIS WALL IS GONE
    2. no volatile functions, no Hyperlink output

N3 fanned 48 parent columns down onto `Order Items`, so every input Price CAD/USD needs
is now on the same item: `Price`, `Province/State`, `Initial Promised Date`. `BO` is on
the list too, which retires that doc's "needs a BO field created first -- it exists on
neither list today". The two Excel lookup tables never needed to be lists: 13 province
codes that have not changed since 1999, and six rows of FX rate, both inlined below.

Wall 2 stands, and it turns out to settle three of the six by deletion rather than by
porting them:

    Price, Navigation Order, Navigation Model   -- all three are HYPERLINK(). DROPPED.
    Price CAD, Price USD                        -- money. Real calculated columns.

DROPPED, decided by the user 2026-09-14: the two navigation columns ARE the lookup
columns. `Order Items` already carries `Order Number` and `Model Revision` as real
lookups, whose own UI navigates to the parent -- so a column whose entire content is a
link to the parent is a second copy of a control SharePoint already renders.

An earlier pass here argued they were not redundant, because Excel's hyperlink opens a
FILTERED VIEW of every row for that order while a lookup opens the single parent item.
That distinction is real but it is not worth a column: this is now a list, and filtering
`Order Items` by order is what the list view does natively. Recorded so the argument is
not re-derived and re-lost.

`Price` goes with them. Excel's version existed only to make the number clickable --
`HYPERLINK(order url, [Price Value])` -- and `Order - Price` is already on the list as
real, sortable, summable currency. There is nothing left for it to add once the
click-through is redundant.

`Archived` is excluded: the user says it is deprecated, and the workbook has no formula
left for it anyway (confirmed by scanning the package -- 6 of the 7 flagged columns carry
a calculatedColumnFormula, `Archived` does not).

🔴 THE DEPENDENCY THAT FORCES A DECISION MADE EARLIER TODAY
-----------------------------------------------------------
Price CAD and Price USD both read `Estimated Delivery Date` -- they take `YEAR()` of it
to pick an FX rate. A calculated column can only reference a STORED field.

So: **Price CAD/USD as calculated columns require Estimated Delivery Date to be a stored
column.** Column formatting alone does not satisfy them -- it renders a string into the
page and stores nothing for a formula to read. This closes the open question in
`estimated-delivery-date-today.md` by dependency rather than by preference.

It also rules out storing the UNFLOORED estimate (the zero-daily-write idea): for a unit
whose milestone is in the past, the floored and unfloored values can fall in different
calendar years, which picks a different FX rate and so a different price. Fidelity to the
workbook needs the floored value, which needs the daily pass over the stalled rows.

`n9_create_calc_columns.js` CREATES it, at the head of the chain, and aborts if it
already exists -- a stored version built separately would be hand-editable, which is the
whole reason this chain is calculated.

WHERE THE PRICE AND PROVINCE ACTUALLY LIVE -- corrected 2026-09-14
------------------------------------------------------------------
A first pass at this assumed `Order Items` carried BOTH a native `Price` / `Province/
State` / `Initial Promised Date` and an N3-fanned `Ord*` copy, and made choosing between
them a parameter. That was wrong, and `column-reference.md` says so if you read it by
SECTION rather than grepping the whole file: those three columns are on the **`Order`**
list. `Order Items` has exactly one copy of each, the `Ord*` one N3 puts there.

So there is no choice to make -- and the reason the port is possible at all is precisely
that N3 fanned them down. Before that, these were the cross-list lookups that disqualified
the columns. The check at the bottom of this file is now section-aware, because a
whole-document grep is what produced the wrong answer.

THE PROVINCE RULE, decided by the user 2026-09-14
-------------------------------------------------
**A recognised Canadian province code prices in CAD. Everything else -- blank, a US
state, an unrecognised code -- prices in USD.** No exceptions and no data cleanup first.

This is what the ported formula already did, since `OR()` over the 13 codes is false for
a blank and false for anything unrecognised. What changes is that it is now a decision
rather than the two open questions `calculated-columns-plan.md` carried (30 of 441 orders
with no `Province/State`, and 1 holding `NO`). Both are answered: USD, deliberately.

`LOWER(TRIM())` is applied on both sides, because the rule says "is one of the Canadian
provinces" and a trailing space or a lowercase `qc` would otherwise quietly flip an
order's currency.

A first pass here applied only `TRIM` and asserted that SharePoint's `=` is
case-insensitive so `LOWER` was unnecessary. Do not take that back out. Excel's `=` is
case-insensitive; the SharePoint calculated-column engine is Excel-LIKE and documents no
such guarantee, and this repo has already paid for assuming a comparison was
case-forgiving -- the whole P3 `toLower` pass exists because unguarded uppercase-only
tests were a live bug class, and `flow_version.py`'s manifest still carries `toLower` and
`'EC'` as columns to watch it. Different engine, same cheap guard.
"""
import json, io, os, re, argparse

SITE = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio"
# Canadian province/territory codes, inlined from TableCanadianProvince (AL1:AM14).
# Static reference data -- a list would be ceremony around 13 strings.
PROVINCES = ["AB", "BC", "MB", "NB", "NL", "NT", "NS", "NU", "ON", "PE", "QC", "SK", "YT"]

# Table_USD_CAD_Conversion_Rate (AI1:AJ7). XLOOKUP match_mode -1 = exact or next SMALLER,
# so a year above the table takes the last rate; this reproduces that and ALSO clamps
# below the table, where Excel returns #N/A (Price CAD) or a string that then breaks the
# arithmetic (Price USD). Deliberate: a pre-2024 date should price at the oldest known
# rate rather than render an error in a money column.
FX = [(2024, 1.35), (2025, 1.44), (2026, 1.38), (2027, 1.39), (2028, 1.43), (2029, 1.47)]

# (display name, internal name) for Estimated Delivery Date's inputs. The two PLANNING
# columns are the field-mapping trap: workbook "Delivery Date" and "Tanking Date" are
# these, NOT DeliveryDate / TankingDate, which are the completion stamps and have no
# workbook column at all. Settled by the viewer's ColumnMap.pq, verified value-for-value
# at cutover. Mapping by name computes a different formula on all 1,189 rows and still
# looks plausible.
M_DELIVERY  = ("Planned Delivery Date", "Planned_x0020_Delivery_x0020_Dat")
M_MANUAL    = ("Manual Estimated Delivery Date", "ManualEstimatedDeliveryDate")
M_FINISHING = ("Finishing End Date", "FinishingDate")
M_TESTING   = ("Testing End Date", "TestingDate")
M_TANKING   = ("Planned Tanking Date", "Planned_x0020_Tanking_x0020_Date")
M_TANKDELIV = ("Tank Delivery Date", "TankDeliveryDate")
M_ORDERDATE = ("Order - Order Date", "OrdOrderDate")
M_LEADWEEKS = ("Client - Lead Time (weeks)", "CliLeadTimeWeeks")
M_BO        = ("BO", "BO")
COILING_RANGE = [("Coiling End Date", "CoilingDate"), ("Stacking End Date", "StackingDate"),
                 ("Assembly End Date", "AssemblyDate"), ("Drying End Date", "DryingDate")]

# Branch 7's fallback when a unit's client has no lead time. FRM13's GENERIC VALUE of
# 26 SEM, not the Excel formula's XLOOKUP default of 52 -- calculated-columns-plan.md
# settled that the 52 contradicts FRM13 itself and should be retired.
GENERIC_WEEKS = 26

# (display name, internal name). These are the N3 "Parent Sync" copies, and they are the
# ONLY copies on Order Items -- the originals are on the Order list. See the docstring.
SRC = {"price":    ("Order - Price", "OrdPrice"),
       "province": ("Order - Province/State", "OrdProvinceState"),
       "promised": ("Order - Initial Promised Date", "OrdInitialPromisedDate")}

EDD = ("Estimated Delivery Date", "EstimatedDeliveryDate")
LOOKUPS = {"OrderNumber", "Client", "Model", "ModelRevision"}

GROUP = "Calculated"


def xesc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def fx_rate_formula(year_col):
    """Nested IF over the FX table, referencing a helper column rather than re-deriving
    the year. Inlining the date cascade instead would repeat a ~100-char expression once
    per rate and push the formula toward SharePoint's length limit for no benefit."""
    expr = str(FX[-1][1])
    for yr, rate in reversed(FX[1:-1]):
        expr = 'IF([%s]=%d,%s,%s)' % (year_col, yr, rate, expr)
    expr = 'IF([%s]<=%d,%s,%s)' % (year_col, FX[0][0], FX[0][1], expr)
    return 'IF([%s]=0,0,%s)' % (year_col, expr)


def calc_fields():
    pd, _ = SRC["price"]
    vd, vi = SRC["province"]
    md, mi = SRC["promised"]
    _, pi = SRC["price"]
    ed, ei = EDD

    date_cascade = 'IF(ISBLANK([%s]),[%s],[%s])' % (ed, md, ed)

    # MAX() over TODAY and the milestone(s); SharePoint takes multiple arguments, so the
    # 2^n nesting the column-formatting version needed does not arise here.
    def milestone(terms, buffer_days):
        return "MAX(TODAY(),%s)+%d+[Bo Penalty]" % (
            ",".join("[%s]" % d for d, _ in terms), buffer_days)

    any_coiling = "OR(%s)" % ",".join("NOT(ISBLANK([%s]))" % d for d, _ in COILING_RANGE)
    weeks = "IF(ISBLANK([%s]),%d,[%s])" % (M_LEADWEEKS[0], GENERIC_WEEKS, M_LEADWEEKS[0])

    edd = (
        '=IF(NOT(ISBLANK([{dlv}])),[{dlv}],'
        'IF(NOT(ISBLANK([{man}])),[{man}],'
        'IF(NOT(ISBLANK([{fin}])),{b_fin},'
        'IF(NOT(ISBLANK([{tst}])),{b_tst},'
        'IF(NOT(ISBLANK([{tnk}])),{b_tnk},'
        'IF({any_coil},{b_coil},'
        'IF(NOT(ISBLANK([{ord}])),[{ord}]+90+({wk})*7,'
        '"")))))))'
    ).format(dlv=M_DELIVERY[0], man=M_MANUAL[0], fin=M_FINISHING[0], tst=M_TESTING[0],
             tnk=M_TANKING[0], ord=M_ORDERDATE[0], wk=weeks, any_coil=any_coiling,
             b_fin=milestone([M_FINISHING], 7), b_tst=milestone([M_TESTING], 10),
             b_tnk=milestone([M_TANKING], 14),
             b_coil=milestone(COILING_RANGE + [M_TANKDELIV], 21))

    return [
        # The only NON-calculated column here, and the only one anything writes to.
        dict(disp="Calc Refreshed", name="CalcRefreshed", rtype="DateTime", plain=True,
             refs=[],
             formula="",
             why="What the nightly touch writes. A calculated column re-evaluates when the "
                 "ITEM is written, so keeping TODAY() honest on a stalled unit means "
                 "writing something to that row -- and 'write any field back' is the kind "
                 "of clever-but-opaque trick that later reads as a bug. A dedicated, "
                 "flow-owned timestamp says outright why the row has a version every "
                 "night, and gives you a way to check the pass actually ran. Nothing else "
                 "reads it."),

        dict(disp="Bo Penalty", name="BoPenalty", rtype="Number", dec=0, refs=[M_BO[1]],
             formula='=IF(OR(LOWER(TRIM([%s]))="ok",TRIM([%s])=""),0,30)' % (M_BO[0], M_BO[0]),
             why="The 30-day back-order penalty, split out because it appears in all four "
                 "milestone branches and inlining it four times costs ~200 characters "
                 "against a 1024 limit. LOWER+TRIM for the same reason as Is Canadian: BO "
                 "is a Choice, so the vocabulary is controlled, but this repo's P3 pass "
                 "exists because an uppercase-only test was assumed safe once already."),

        dict(disp=EDD[0], name=EDD[1], rtype="DateTime", refs=[
                 M_DELIVERY[1], M_MANUAL[1], M_FINISHING[1], M_TESTING[1], M_TANKING[1],
                 M_TANKDELIV[1], M_ORDERDATE[1], M_LEADWEEKS[1], "BoPenalty"]
                 + [i for _, i in COILING_RANGE],
             formula=edd,
             why="The eight-branch formula, ported from TableOrders' own "
                 "calculatedColumnFormula. A CALCULATED column rather than a stored one "
                 "(user, 2026-09-14): it cannot be hand-edited, it recomputes on save "
                 "rather than after a 5-minute poll, it works while the trigger flow is "
                 "off, and the whole chain below is then one mechanism. TODAY() freezes at "
                 "last write, so the nightly touch keeps the ~21 stalled rows honest."),

        # Split out so each piece is independently readable and checkable in a view.
        dict(disp="Is Canadian", name="IsCanadian", rtype="Boolean", refs=[vi],
             formula="=" + "OR(%s)" % ",".join(
                 'LOWER(TRIM([%s]))="%s"' % (vd, p.lower()) for p in PROVINCES),
             why="TableCanadianProvince, inlined. A recognised code prices in CAD; blank, "
                 "a US state and an unrecognised code all fall through to USD, which is "
                 "the rule the user settled 2026-09-14 rather than an accident of OR(). "
                 "LOWER+TRIM on both sides -- see the docstring, do not simplify."),

        dict(disp="Fx Year", name="FxYear", rtype="Number", dec=0, refs=[ei, mi],
             formula="=IF(AND(ISBLANK([%s]),ISBLANK([%s])),0,YEAR(%s))" % (ed, md, date_cascade),
             why="Excel's two-deep cascade: Estimated Delivery Date, else Initial Promised "
                 "Date. 0 means neither is set -- Excel yields the string 'Invalid date for "
                 "conversion' here and then errors on YEAR(); 0 is the same condition, "
                 "testable."),

        dict(disp="Fx Rate", name="FxRate", rtype="Number", dec=4, refs=["FxYear"],
             formula="=" + fx_rate_formula("Fx Year"),
             why="THE ONE PLACE TO EDIT WHEN A NEW YEAR'S RATE IS AGREED. Update FX in "
                 "gen_calc_columns.py and re-run; do not hand-edit the column."),

        dict(disp="Price CAD", name="PriceCAD", rtype="Currency", dec=2,
             refs=["IsCanadian", pi, "FxRate"],
             formula='=IF([Is Canadian],[%s],IF([Fx Rate]=0,"",[%s]*[Fx Rate]))' % (pd, pd),
             why="Canadian order: the price is already CAD. Otherwise it is USD, converted."),

        dict(disp="Price USD", name="PriceUSD", rtype="Currency", dec=2,
             refs=["IsCanadian", pi, "FxRate"],
             formula='=IF([Is Canadian],IF([Fx Rate]=0,"",[%s]/[Fx Rate]),[%s])' % (pd, pd),
             why="The mirror image. Excel multiplies by (1/rate); dividing is the same "
                 "value without the intermediate rounding."),
    ]


def schema_xml(f):
    if f.get("plain"):
        return ('<Field Type="%s" DisplayName="%s" Name="%s" StaticName="%s" '
                'Required="FALSE" Group="%s" Format="DateOnly" />'
                % (f["rtype"], f["disp"], f["name"], f["name"], GROUP))
    extra = ""
    if f["rtype"] in ("Number", "Currency"):
        extra += ' Decimals="%d"' % f.get("dec", 2)
    if f["rtype"] == "Currency":
        extra += ' LCID="1033"'
    refs = "".join('<FieldRef Name="%s" />' % r for r in f["refs"])
    return ('<Field Type="Calculated" DisplayName="%s" Name="%s" StaticName="%s" '
            'Required="FALSE" Group="%s" ResultType="%s"%s>'
            '<Formula>%s</Formula><FieldRefs>%s</FieldRefs></Field>'
            % (f["disp"], f["name"], f["name"], GROUP, f["rtype"], extra,
               xesc(f["formula"]), refs))



CREATOR_HEAD = """/* N9 -- create the five calculated columns ported from FRM10-12.
   GENERATED by scripts/gen_calc_columns.py -- regenerate, do not hand-edit.

   Paste into the browser console on the SharePoint site.

   DRY RUN by default: it creates nothing until APPLY = true.

   It creates EIGHT columns, Estimated Delivery Date included, in dependency order.
   Nothing has to exist first -- but the whole chain is calculated, so each row is only
   as fresh as its last write. TODAY() freezes at last save, which is exactly what the
   nightly touch stage in the cleanup flow exists to fix for the stalled rows.
   See docs/calc-columns-port.md.
*/
(async () => {
  const APPLY = false;
  const base = "%(site)s";
  const LIST = "Order Items";
  const EDD_INTERNAL = "%(edd)s";

  const J = async u => (await fetch(u, {credentials:"include",
              headers:{Accept:"application/json;odata=nometadata"}})).json();

  const FIELDS = %(fields)s;

  // ---------------------------------------------------------------- preflight
  const f = await J(base + "/_api/web/lists/getbytitle('" + LIST + "')/fields"
              + "?$select=InternalName,TypeAsString&$top=500");
  if (!f.value || !f.value.length) { console.error("ABORT: read 0 fields."); return; }
  const have = new Map(f.value.map(x => [x.InternalName, x.TypeAsString]));

  const edd = have.get(EDD_INTERNAL);
  if (edd) {
    console.error("ABORT: '" + EDD_INTERNAL + "' already exists (type " + edd + ").");
    console.error("  This script CREATES it. If a stored version was built first, decide");
    console.error("  which one wins before running -- do not end up with both, and note");
    console.error("  that a stored one can be hand-edited, which is the whole reason this");
    console.error("  chain is calculated. See docs/calc-columns-port.md.");
    return;
  }

  const dup = FIELDS.filter(x => have.has(x.name));
  if (dup.length) {
    console.error("ABORT: already present: " + dup.map(d => d.name).join(", "));
    console.error("  Delete them first, or this creates duplicates with a 0 suffix --");
    console.error("  the x9 cleanup exists because that already happened once.");
    return;
  }
  for (const x of FIELDS)
    for (const r of x.refs)
      if (!have.has(r) && !FIELDS.some(y => y.name === r))
        { console.error("ABORT: " + x.name + " references missing field " + r); return; }

  console.table(FIELDS.map(x => ({ field: x.name, type: x.rtype, formula: x.formula })));
  if (!APPLY) { console.log("\\nDRY RUN -- nothing created. Set APPLY = true."); return; }
"""

CREATOR_TAIL = """
  const dg = await (await fetch(base + "/_api/contextinfo", { method:"POST",
    credentials:"include", headers:{Accept:"application/json;odata=nometadata"} })).json();

  const results = [];
  // Sequential on purpose: Fx Rate references Fx Year and the price columns reference
  // both, and SharePoint rejects a FieldRef to a field that does not exist yet.
  for (const x of FIELDS) {
    try {
      const r = await fetch(base + "/_api/web/lists/getbytitle('" + LIST
        + "')/fields/createfieldasxml", {
        method:"POST", credentials:"include",
        headers:{ Accept:"application/json;odata=nometadata",
                  "Content-Type":"application/json;odata=verbose",
                  "X-RequestDigest": dg.FormDigestValue },
        body: JSON.stringify({ parameters: {
          __metadata:{ type:"SP.XmlSchemaFieldCreationInformation" },
          SchemaXml: x.xml, Options: 8 } })
      });
      results.push({ field:x.name, ok:r.ok, status:r.status,
                     error: r.ok ? "" : (await r.text()).slice(0,300) });
      if (!r.ok) break;   // a later field references this one; stop rather than cascade
    } catch (e) { results.push({ field:x.name, ok:false, status:0, error:String(e) }); break; }
  }
  console.table(results);

  // Read back. A 200 is not proof SharePoint stored the ResultType you asked for --
  // it silently accepts and downgrades some combinations.
  const after = await J(base + "/_api/web/lists/getbytitle('" + LIST + "')/fields"
                  + "?$select=InternalName,TypeAsString,OutputType&$top=500");
  const made = (after.value||[]).filter(x => FIELDS.some(y => y.name === x.InternalName));
  console.log("\\n--- read back (trust this, not the POST results) ---");
  console.table(made.map(x => ({ field:x.InternalName, type:x.TypeAsString, output:x.OutputType })));
})();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default="docs/column-reference.md")
    ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    fields = calc_fields()
    for f in fields:
        f["xml"] = schema_xml(f)

    # ------------------------------------------------------------------ verify
    # Section-aware on purpose: column-reference.md documents five lists, and a
    # whole-file grep happily "finds" an Order-list column and calls it an Order Items
    # one. That is exactly the mistake this file's docstring records.
    known, sec = set(), None
    for ln in io.open("docs/column-reference.md", encoding="utf-8"):
        h = re.match(r"^## (.+)$", ln)
        if h:
            sec = h.group(1).strip()
            continue
        m = re.match(r"^\|\s*`([^`]+)`\s*\|", ln)
        if m and sec == "Order Items":
            known.add(m.group(1))
    known |= LOOKUPS      # real columns, absent from the doc by its own admission
    made = {f["name"] for f in fields}
    for f in fields:
        for r in f["refs"]:
            assert r in known or r in made, \
                "%s references %s, which is neither on the list nor created here" % (f["name"], r)

    # The creator posts these in list order, and SharePoint rejects a FieldRef naming a
    # field that does not exist yet -- so a field may only reference one appearing EARLIER
    # in the chain. Asserted rather than assumed, because the failure is a bare 400.
    seen = set()
    for f in fields:
        for r in f["refs"]:
            assert r in known or r in seen, \
                "%s references %s, which this chain creates LATER -- reorder" % (f["name"], r)
        seen.add(f["name"])
        assert f["name"] not in known, "%s already exists on the list" % f["name"]
    for k in ("price", "province", "promised"):
        assert SRC[k][1] in known, "source column %s not on the list" % SRC[k][1]

    # SharePoint caps a calculated column's Formula at 1024 characters and does not say
    # so when you exceed it -- createfieldasxml returns an unhelpful 400. `Is Canadian`
    # is the one at risk: LOWER(TRIM([Order - Province/State])) is 38 characters and it
    # appears once per province, so adding codes or renaming that column moves it fast.
    for f in fields:
        assert len(f["formula"]) <= 1024, \
            "%s formula is %d chars, over SharePoint's 1024 limit" % (f["disp"], len(f["formula"]))
    assert EDD[1] not in known, \
        "Estimated Delivery Date already exists -- re-check the chain before creating it"

    js = (CREATOR_HEAD % {"site": SITE, "edd": EDD[1],
                          "fields": json.dumps(
                              [{"name": f["name"], "rtype": f["rtype"], "refs": f["refs"],
                                "formula": f["formula"], "xml": f["xml"]} for f in fields],
                              indent=4)}) + CREATOR_TAIL
    io.open("scripts/n9_create_calc_columns.js", "w", encoding="utf-8").write(js)

    print("source columns    : %s" % ", ".join(v[1] for v in SRC.values()))
    print("\nwrote scripts/n9_create_calc_columns.js")
    for f in fields:
        print("  %-14s %-9s %s" % (f["disp"], f["rtype"], f["formula"][:88]))
    print("\n  every FieldRef resolves, no column collides with an existing one,")
    print("  and Estimated Delivery Date is confirmed absent (the creator gates on it).")


if __name__ == "__main__":
    main()
