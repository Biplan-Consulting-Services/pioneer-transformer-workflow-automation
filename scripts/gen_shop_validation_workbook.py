# -*- coding: utf-8 -*-
"""Build the Excel workbook the shop fills in, with real dropdowns.

User, 2026-09-09: "the shop sheet is a bit hard for a human to use. it should be a table
and maybe have drope down lists for the sections where they choose the right value" and
"the 72 wrong and the 52 blank should be in a second page ... as a nice to have backlog".

So: an .xlsx, not a CSV. Excel data-validation dropdowns on every cell the shop fills, a
frozen header, real column widths, and the vocabulary on its own sheet so the lists are
one edit away from being changed. Works in desktop Excel, Excel Online and SharePoint --
which matters more than anything I could build in a browser, because the shop already
lives in Excel.

TWO SHEETS, and the split is the point
--------------------------------------
  1. "Validate"  -- nobody knows the answer. A value that is not in the vocabulary and
                    cannot be resolved from the data. This is the ask.
  2. "Backlog"   -- we DO know the answer, it is just deferred. Two kinds:
                      * a Description value sitting in Model Type. The right target is
                        named; the row keeps its value until someone moves it.
                      * Model Type blank on a revision that was never ordered.
                    Nice-to-have, per the user. Nothing depends on it.

Sheet 1 is a request. Sheet 2 is a to-do list. Mixing them would bury the 25 rows that
actually block the strict-Choice conversion in a hundred that do not.

Reads the newest export, the archive (context only) and the worklist CSV. Writes one
.xlsx. No network calls; touches no SharePoint list.
"""
import io, os, re, csv, glob, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lib  # noqa: E402
from gen_choice_cleanup_worklist import (MODEL_TYPES, DESCRIPTIONS, canon, multi,
                                         schema, GOOD_PHASES)  # noqa: E402

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

HDR_FILL = PatternFill("solid", fgColor="1F3864")
ASK_FILL = PatternFill("solid", fgColor="FFF2CC")     # cells the shop fills
CTX_FILL = PatternFill("solid", fgColor="F2F2F2")
HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def sheet(wb, title, columns, rows, ask_from, validations):
    ws = wb.create_sheet(title)
    ws.append([c[0] for c in columns])
    for i, (name, width) in enumerate(columns, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
        c = ws.cell(row=1, column=i)
        c.fill = HDR_FILL
        c.font = HDR_FONT
        c.alignment = Alignment(vertical="center", wrap_text=True)
        c.border = BORDER
    ws.row_dimensions[1].height = 32
    for r in rows:
        ws.append(r)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=len(columns)):
        for c in row:
            c.border = BORDER
            c.alignment = Alignment(vertical="top", wrap_text=(c.column < ask_from))
            c.fill = ASK_FILL if c.column >= ask_from else CTX_FILL
    ws.freeze_panes = ws.cell(row=2, column=1)
    ws.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(columns)), ws.max_row)
    last = max(ws.max_row, 2)
    for col, source in validations:
        dv = DataValidation(type="list", formula1=source, allow_blank=True,
                            showDropDown=False)   # False = SHOW the dropdown arrow
        dv.error = "Pick a value from the list."
        dv.promptTitle = "Choose"
        dv.prompt = "Pick from the dropdown."
        ws.add_data_validation(dv)
        dv.add("%s2:%s%d" % (col, col, last))
    return ws


def main():
    path, sch = schema("Model Revisions")
    rows = lib.load(path)
    TD, DD = sch["Model_x0020_Type"]["disp"], sch["Description"]["disp"]
    CMC, MRID = sch["ModelName"]["disp"], sch["ModelID"]["disp"]
    byid = {str(r.get("Id") or r.get("ID") or ""): r for r in rows}

    wbk = sorted(glob.glob(os.path.join(ROOT, "workbooks", "Archive active *.xlsx")))[-1]
    _, arch = lib.xl_table(wbk, "TableArchiveFRM10_12")
    nrm = lambda s: re.sub(r'\s+', '', str(s or '').strip().upper())
    by_item = defaultdict(list)
    for a in arch:
        k = nrm(a.get("PO Item #"))
        if k:
            by_item[k].append(a)

    wl = os.path.join(ROOT, "reports", "Model Revisions choice cleanup 2026-09-08.csv")
    if not os.path.exists(wl):
        raise SystemExit("run scripts/gen_choice_cleanup_worklist.py first")
    keep = defaultdict(list)
    with io.open(wl, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["tier"] == "KEEP":
                keep[str(row["row_id"])].append(row)

    DESC_CANON = {canon(d) for d in DESCRIPTIONS}

    def ctx(r):
        c = by_item.get(nrm(r.get(CMC)), [])
        return ("; ".join(sorted({str(a.get("Client") or "").strip() for a in c if a.get("Client")})[:2]),
                "; ".join(sorted({str(a.get("Order") or "").strip() for a in c if a.get("Order")})[:5])
                or "never ordered",
                "; ".join(sorted({str(a.get("KVA and KV") or "").strip() for a in c if a.get("KVA and KV")})[:2]))

    validate, backlog = [], []
    for rid, items in keep.items():
        r = byid.get(rid)
        if not r:
            continue
        tv = str(r.get(TD) or "").strip()
        dv = multi(r.get(DD))
        ph = str(r.get("Phases") or "").strip()
        client, orders, kva = ctx(r)
        base = [r.get(MRID) or "", r.get(CMC) or "", client, orders, kva,
                ph or "(blank)", tv or "(blank)", "; ".join(dv)]
        # deferred-but-known: the value is a real Description sitting in Model Type
        known = [i for i in items
                 if i["column"] == "Model Type" and canon(i["current_value"]) in DESC_CANON]
        if known and len(known) == len(items):
            tgt = next(d for d in DESCRIPTIONS if canon(d) == canon(known[0]["current_value"]))
            backlog.append(base + ["Model Type holds %r, which is really a Description"
                                   % known[0]["current_value"],
                                   "move it to Model Description as %r" % tgt, "", ""])
        else:
            why = "; ".join(sorted({i["why"] for i in items}))
            if ph not in GOOD_PHASES:
                why += " | Phases is %s, so 1PH/3PH cannot be confirmed from data" % (ph or "blank")
            validate.append(base + [why[:300], "", "", "", "", ""])

    # Model Type blank and never ordered -> backlog
    for r in rows:
        if str(r.get(TD) or "").strip():
            continue
        client, orders, kva = ctx(r)
        if orders != "never ordered":
            continue
        backlog.append([r.get(MRID) or "", r.get(CMC) or "", client, orders, kva,
                        str(r.get("Phases") or "").strip() or "(blank)", "(blank)",
                        "; ".join(multi(r.get(DD))),
                        "Model Type is blank and the model was never ordered",
                        "assign a type if this model is still live", "", ""])

    wb = Workbook()
    wb.remove(wb.active)

    lst = wb.create_sheet("Lists")
    lst["A1"] = "Model Types"; lst["A1"].font = Font(bold=True)
    for i, v in enumerate(MODEL_TYPES, start=2):
        lst.cell(row=i, column=1, value=v)
    lst["B1"] = "Model Descriptions"; lst["B1"].font = Font(bold=True)
    for i, v in enumerate(DESCRIPTIONS, start=2):
        lst.cell(row=i, column=2, value=v)
    lst["C1"] = "Phases"; lst["C1"].font = Font(bold=True)
    lst["C2"], lst["C3"] = 1, 3
    lst.column_dimensions["A"].width = 24
    lst.column_dimensions["B"].width = 24
    T = "Lists!$A$2:$A$%d" % (len(MODEL_TYPES) + 1)
    D = "Lists!$B$2:$B$%d" % (len(DESCRIPTIONS) + 1)
    P = "Lists!$C$2:$C$3"

    CTXCOLS = [("Model Revision ID", 16), ("Client Model Code", 18), ("Client", 20),
               ("Orders (from archive)", 26), ("kVA", 10), ("Phases now", 10),
               ("Model Type now", 20), ("Descriptions now", 26)]

    sheet(wb, "Validate",
          CTXCOLS + [("What needs confirming", 46),
                     ("✔ Model Type", 20), ("✔ Description 1", 18),
                     ("✔ Description 2", 18), ("✔ Description 3", 18),
                     ("✔ Phases", 10), ("Shop notes", 26)],
          validate, ask_from=10,
          validations=[("J", T), ("K", D), ("L", D), ("M", D), ("N", P)])

    # Columns: A-H context, I "What is wrong", J "What it should become" (pre-filled by
    # us, not a dropdown), K "Done?", L notes. Only K needs validation -- putting the
    # description list on K is what the first build did, and K is the Done column.
    sheet(wb, "Backlog",
          CTXCOLS + [("What is wrong", 44), ("What it should become", 34),
                     ("✔ Done?", 10), ("Shop notes", 26)],
          backlog, ask_from=11,
          validations=[("K", "\"yes,no\"")])

    outp = os.path.join(ROOT, "reports", "Model validation for shop 2026-09-09.xlsx")
    wb.save(outp)
    print("wrote %s" % outp)
    print("   Validate : %3d rows  (nobody knows the answer -- this is the ask)" % len(validate))
    print("   Backlog  : %3d rows  (answer known, just deferred)" % len(backlog))
    print("   Lists    : %d model types, %d descriptions" % (len(MODEL_TYPES), len(DESCRIPTIONS)))
    print("\n   dropdowns: Validate!J (types), K/L/M (descriptions), N (phases);"
          " Backlog!K (descriptions), L (yes/no)")


if __name__ == "__main__":
    main()
