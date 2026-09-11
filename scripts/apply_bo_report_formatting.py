# -*- coding: utf-8 -*-
"""Give BO Report.xlsx the same conditional formatting as BO Manager.xlsx.

    python scripts/apply_bo_report_formatting.py            # dry run
    python scripts/apply_bo_report_formatting.py --apply

WHAT BO MANAGER ACTUALLY DOES -- three logical rules, read off the file 2026-09-11
  1. roll-up = "BO"  -> fill  (dxf theme 5, tint 0.4)
  2. roll-up = "OK"  -> fill  (dxf theme 9, tint 0.4)
  3. a part group's OK checkbox is TRUE -> STRIKETHROUGH across that group's five
     data columns (NOT the checkbox column itself)

  The strikethrough is what the user calls "the dashed lines when the checkbox is
  checked". Rule 3 exists once per part group, so three times.

WHY BO REPORT LOOKED UNFORMATTED
  It already had all three rules AND the right dxf formats. The problem was the
  RANGES: every conditionalFormatting block was anchored at rows 1024-1037 -- 14
  rows out of 1,091. Everything above row 1024 had no formatting at all. So this is
  a re-anchor, not a new design, and it reuses the workbook's existing dxf indices
  rather than inventing colours.

  Both files show the same decay: BO Manager's three rules have fragmented into 83
  distinct formulas across 130 blocks, because Excel splits a CF range and re-anchors
  its relative formula every time rows are inserted or deleted. BO Report had started
  down the same path. Collapsing back to one block per rule is the fix in both cases.

COLOURS ARE THEME REFERENCES, NOT RGB -- deliberately
  The dxfs say `theme=5 tint=0.4` / `theme=9 tint=0.4`, which resolve through
  theme1.xml. An earlier pass on this estate resolved them to #F4B183 / #A9D18E and
  wrote the RGB down; hardcoding those here would silently diverge the day the theme
  changes. Reusing the existing dxf index keeps the two workbooks tied to one source.

🔴 XML SURGERY, NOT openpyxl
  openpyxl rewrites the whole package and drops what it does not model. BO Report
  carries `xl/connections.xml` and two table parts; BO Manager additionally carries a
  DataMashup blob (the Power Query store). Losing a query binding on a query-backed
  table is exactly the 2026-08-28 corruption mechanism in FRM10-12/CLAUDE.md. So this
  edits ONE string inside sheet1.xml and copies every other part through byte for
  byte.

  The new blocks are written at the exact offset the old ones occupied, so the
  CT_Worksheet element order (… mergeCells, conditionalFormatting, dataValidations,
  hyperlinks, pageMargins …) is preserved without having to reason about it.
"""
import argparse
import os
import re
import shutil
import zipfile

WB = os.path.join("workbooks", "BO Report.xlsx")
SHEET = "xl/worksheets/sheet1.xml"

FIRST_DATA_ROW = 2
LAST_DATA_ROW = 1092

# 🔴 DXF INDICES ARE RESOLVED BY CONTENT, NEVER HARDCODED.
# They were hardcoded (15/16/0) in the first version of this script, and they went
# stale the same afternoon: the moment Excel opened and re-saved the workbook it
# garbage-collected unused dxfs, 41 -> 29, and renumbered the survivors to 4/3/0.
# A re-run against the hardcoded numbers would have pointed the BO and OK rules at
# two blank formats - the fills would have silently disappeared, with the rules still
# present and apparently fine. So: find them by what they ARE.
STRIKE_MARK = '<strike'
BO_FILL_THEME = '5'   # theme 5 tint 0.4 - the orange, per BO Manager
OK_FILL_THEME = '9'   # theme 9 tint 0.4 - the green


def resolve_dxfs(styles_xml):
    """-> (bo, ok, strike) dxf indices, by inspecting each dxf rather than trusting
    a position. Raises rather than guessing: a wrong index here is invisible."""
    dxfs = re.findall(r'<dxf>(.*?)</dxf>', styles_xml, re.S)
    bo = ok = strike = None
    for i, d in enumerate(dxfs):
        if strike is None and STRIKE_MARK in d:
            strike = i
            continue
        th = re.search(r'<bgColor theme="(\d+)"', d)
        if th and bo is None and th.group(1) == BO_FILL_THEME:
            bo = i
        elif th and ok is None and th.group(1) == OK_FILL_THEME:
            ok = i
    missing = [n for n, v in (("BO fill", bo), ("OK fill", ok), ("strike", strike))
               if v is None]
    if missing:
        raise SystemExit(
            "could not find the %s dxf in styles.xml. Refusing to write conditional "
            "formatting that points at the wrong format - that failure is invisible in "
            "Excel. Check the workbook still carries BO Manager's formats."
            % " and ".join(missing))
    return bo, ok, strike

ROLLUP_COL = "C"

# (group data columns, the OK checkbox column driving the strikethrough)
GROUPS = [
    (("D", "H"), "I"),   # BO1 Part Numbre .. Fournisseur Interne, OK in I
    (("J", "N"), "O"),   # BO2
    (("P", "T"), "U"),   # BO3
]


def build_cf(dxf_bo, dxf_ok, dxf_strike):
    """The five blocks, one per logical rule. Priority ascending; the strikethrough
    rules sit on disjoint column ranges so they never compete with each other, and
    they never overlap the roll-up column, so priority order is not load-bearing -
    but it is written explicitly rather than left to chance."""
    out = []
    p = 1
    for value, dxf in (("BO", dxf_bo), ("OK", dxf_ok)):
        out.append(
            '<conditionalFormatting sqref="{c}{a}:{c}{b}">'
            '<cfRule type="expression" dxfId="{d}" priority="{p}">'
            '<formula>{c}{a}="{v}"</formula>'
            '</cfRule></conditionalFormatting>'.format(
                c=ROLLUP_COL, a=FIRST_DATA_ROW, b=LAST_DATA_ROW, d=dxf, p=p, v=value)
        )
        p += 1
    for (c1, c2), ok in GROUPS:
        # $OK<firstrow> - column absolute, row RELATIVE. Excel offsets the row per
        # cell from the range's top-left, so one block covers every row. Anchoring
        # it at anything other than FIRST_DATA_ROW is how these drift.
        out.append(
            '<conditionalFormatting sqref="{c1}{a}:{c2}{b}">'
            '<cfRule type="expression" dxfId="{d}" priority="{p}">'
            '<formula>${ok}{a}=TRUE</formula>'
            '</cfRule></conditionalFormatting>'.format(
                c1=c1, c2=c2, a=FIRST_DATA_ROW, b=LAST_DATA_ROW,
                d=dxf_strike, p=p, ok=ok)
        )
        p += 1
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write the file (default is a dry run)")
    args = ap.parse_args()

    if not os.path.exists(WB):
        raise SystemExit("not found: %s" % WB)
    lock = os.path.join(os.path.dirname(WB), "~$" + os.path.basename(WB))
    if os.path.exists(lock):
        raise SystemExit(
            "REFUSING: %s exists, so the workbook is open in Excel. Close it first - "
            "writing underneath an open Excel loses whatever Excel saves next." % lock)

    with zipfile.ZipFile(WB) as z:
        parts = {n: z.read(n) for n in z.namelist()}
        order = z.namelist()

    xml = parts[SHEET].decode("utf-8")
    blocks = re.findall(r"<conditionalFormatting.*?</conditionalFormatting>", xml, re.S)
    if not blocks:
        raise SystemExit("no conditionalFormatting found in %s - aborting rather than "
                         "guessing where to insert it" % SHEET)

    start = xml.index(blocks[0])
    end = xml.rindex(blocks[-1]) + len(blocks[-1])
    between = xml[start:end]
    stray = re.sub(r"<conditionalFormatting.*?</conditionalFormatting>", "", between, flags=re.S)
    if stray.strip():
        raise SystemExit("unexpected markup between the CF blocks, refusing to "
                         "clobber it: %r" % stray[:200])

    dxf_bo, dxf_ok, dxf_strike = resolve_dxfs(parts['xl/styles.xml'].decode('utf-8'))
    cf = build_cf(dxf_bo, dxf_ok, dxf_strike)
    new_xml = xml[:start] + cf + xml[end:]

    print("%s" % WB)
    print("  existing CF blocks : %d  (ranges anchored at rows %s)" % (
        len(blocks),
        "/".join(sorted({m for b in blocks
                         for m in re.findall(r"[A-Z]+(\d+)", b)})[:4]) or "?"))
    print("  replacement blocks : %d" % len(re.findall(r"<conditionalFormatting", cf)))
    print("  resolved dxfs      : BO=%d OK=%d strike=%d" % (dxf_bo, dxf_ok, dxf_strike))
    for (c1, c2), ok in GROUPS:
        print("    strike %s%d:%s%d  when  $%s<row>=TRUE" % (
            c1, FIRST_DATA_ROW, c2, LAST_DATA_ROW, ok))
    print("    fill   %s%d:%s%d  when  =\"BO\" (dxf %d) / =\"OK\" (dxf %d)" % (
        ROLLUP_COL, FIRST_DATA_ROW, ROLLUP_COL, LAST_DATA_ROW, dxf_bo, dxf_ok))

    if not args.apply:
        print("\nDRY RUN - nothing written. Re-run with --apply.")
        return

    bak = WB + ".bak"
    if not os.path.exists(bak):
        shutil.copy2(WB, bak)
        print("\nbackup: %s" % bak)

    parts[SHEET] = new_xml.encode("utf-8")
    tmp = WB + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in order:                      # original order, every other part verbatim
            z.writestr(n, parts[n])
    os.replace(tmp, WB)
    print("written.")


if __name__ == "__main__":
    main()
