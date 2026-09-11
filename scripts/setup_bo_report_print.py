# -*- coding: utf-8 -*-
"""Make BO Report.xlsx printable on paper, respecting whatever filter is applied.

    python scripts/setup_bo_report_print.py            # dry run
    python scripts/setup_bo_report_print.py --apply

THE FILTER NEEDS NOTHING. Excel omits filtered-out (hidden) rows from a printout
already. What was missing is that the sheet had NO print setup at all - no page
setup, no print area, no repeating header - so a filtered print still sprawled
across three pages wide with the headers appearing only on page 1.

WHY NOT JUST "FIT TO ONE PAGE WIDE"
  The 24 columns total 421 char-widths. A landscape Letter page fits about 140 at
  full size, so fit-to-one-page would scale to ~33%: technically one page, and
  unreadable. The columns are three repeats of the same six fields, so the sheet
  wants to break BETWEEN part groups, not be crushed.

THE LAYOUT - measured, not guessed (widths read off the file 2026-09-11)

    page 1   A..I   Unit ID, Planned Tanking Date, BO, BO1 group   152 char-widths
    page 2   A + J..O   Unit ID repeated, BO2 group                122
    page 3   A + P..V   Unit ID repeated, BO3 group, Unit #        127

  Column A repeats on every page as a print title, so page 2 and 3 are not
  anonymous columns of part numbers - every row still says which unit it belongs to.
  That is the whole reason for the manual column breaks rather than letting Excel
  split wherever it runs out of room, which would cut a part group in half.

  Page 1 is 152 against ~140 usable, hence scale 90. The other two have headroom.

W AND X ARE EXCLUDED FROM THE PRINT AREA
  `Item Type` and `Path` are SharePoint export metadata - the list's own plumbing,
  51 char-widths of it, meaningless on paper. They stay in the sheet (a refresh
  would put them back anyway); they are simply outside Print_Area. `Unit #` is kept.

🔴 XML SURGERY, NOT openpyxl - same reasoning as apply_bo_report_formatting.py.
  This workbook is a SharePoint "Export to Excel" web query: xl/connections.xml
  holds an OLEDB list connection (`Microsoft.Office.List.OLEDB.2.0`) pointing at the
  Order Items list and ONE view GUID, plus a queryTable and a table part. openpyxl
  models none of that and would drop it, turning a refreshable report into a dead
  snapshot. Every part other than sheet1.xml and workbook.xml is copied verbatim.

  Element order inside CT_Worksheet is fixed by the schema and Excel rejects a file
  that gets it wrong, so each fragment below is inserted at a named anchor rather
  than appended: sheetPr first, printOptions before pageMargins, pageSetup after it,
  then headerFooter, then colBreaks.
"""
import argparse
import os
import re
import shutil
import zipfile

WB = os.path.join("workbooks", "BO Report.xlsx")
SHEET = "xl/worksheets/sheet1.xml"
BOOK = "xl/workbook.xml"

SHEET_NAME = "query (20)"
LAST_ROW = 1092
PRINT_LAST_COL = "V"          # keep Unit #, drop Item Type + Path
COL_BREAKS = [9, 15]          # after I (BO1) and after O (BO2)
SCALE = 90


def patch_sheet(xml):
    changed = []

    # fitToPage="0": the manual column breaks above are the layout. Turning fit-to-page
    # on would override them and crush all 24 columns onto one sheet.
    if "<sheetPr" not in xml:
        xml = re.sub(r"(<worksheet[^>]*>)",
                     r'\1<sheetPr><pageSetUpPr fitToPage="0"/></sheetPr>', xml, count=1)
        changed.append("sheetPr")

    if "<printOptions" not in xml:
        xml = xml.replace("<pageMargins", '<printOptions gridLines="1"/><pageMargins', 1)
        changed.append("printOptions gridLines")

    xml = re.sub(r'<pageMargins[^>]*/>',
                 '<pageMargins left="0.25" right="0.25" top="0.5" bottom="0.5"'
                 ' header="0.3" footer="0.3"/>', xml, count=1)
    changed.append("margins narrowed")

    if "<pageSetup" not in xml:
        xml = re.sub(r'(<pageMargins[^>]*/>)',
                     r'\1<pageSetup paperSize="1" scale="%d" orientation="landscape"'
                     r' fitToWidth="0" fitToHeight="0"/>' % SCALE, xml, count=1)
        changed.append("pageSetup landscape scale %d" % SCALE)

    if "<headerFooter" not in xml:
        xml = re.sub(r'(<pageSetup[^>]*/>)',
                     r'\1<headerFooter><oddFooter>&amp;LBO Report&amp;CPage &amp;P of &amp;N'
                     r'&amp;R&amp;D</oddFooter></headerFooter>', xml, count=1)
        changed.append("footer")

    if "<colBreaks" not in xml:
        brks = "".join('<brk id="%d" max="1048575" man="1"/>' % c for c in COL_BREAKS)
        frag = '<colBreaks count="%d" manualBreakCount="%d">%s</colBreaks>' % (
            len(COL_BREAKS), len(COL_BREAKS), brks)
        if "<headerFooter" in xml:
            xml = re.sub(r'(</headerFooter>)', r'\1' + frag, xml, count=1)
        else:
            xml = re.sub(r'(<pageSetup[^>]*/>)', r'\1' + frag, xml, count=1)
        changed.append("column breaks after %s" % ", ".join(
            chr(64 + c) for c in COL_BREAKS))
    return xml, changed


def patch_book(xml):
    q = "'%s'" % SHEET_NAME          # the name has a space and parens - must be quoted
    area = "%s!$A$1:$%s$%d" % (q, PRINT_LAST_COL, LAST_ROW)
    titles = "%s!$A:$A,%s!$1:$1" % (q, q)
    defs = ('<definedName name="_xlnm.Print_Area" localSheetId="0">%s</definedName>'
            '<definedName name="_xlnm.Print_Titles" localSheetId="0">%s</definedName>'
            % (area, titles))
    if "_xlnm.Print_Area" in xml or "_xlnm.Print_Titles" in xml:
        return xml, []
    if "<definedNames>" in xml:
        xml = xml.replace("<definedNames>", "<definedNames>" + defs, 1)
    else:
        # definedNames sits between <sheets> and <calcPr> in CT_Workbook
        xml = xml.replace("</sheets>", "</sheets><definedNames>%s</definedNames>" % defs, 1)
    return xml, ["Print_Area %s" % area, "Print_Titles row 1 + column A"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    lock = os.path.join(os.path.dirname(WB), "~$" + os.path.basename(WB))
    if os.path.exists(lock):
        raise SystemExit("REFUSING: %s exists - the workbook is open in Excel." % lock)

    with zipfile.ZipFile(WB) as z:
        order = z.namelist()
        parts = {n: z.read(n) for n in order}

    sheet_xml, c1 = patch_sheet(parts[SHEET].decode("utf-8"))
    book_xml, c2 = patch_book(parts[BOOK].decode("utf-8"))

    print(WB)
    for c in c1 + c2:
        print("  +", c)
    print("\n  page 1  A..I   Unit ID + BO1")
    print("  page 2  A + J..O   Unit ID repeated + BO2")
    print("  page 3  A + P..V   Unit ID repeated + BO3 + Unit #")
    print("  filtered-out rows are omitted by Excel automatically - nothing to configure")

    if not args.apply:
        print("\nDRY RUN - nothing written. Re-run with --apply.")
        return

    bak = WB + ".printsetup.bak"
    if not os.path.exists(bak):
        shutil.copy2(WB, bak)
        print("\nbackup: %s" % bak)

    parts[SHEET] = sheet_xml.encode("utf-8")
    parts[BOOK] = book_xml.encode("utf-8")
    tmp = WB + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in order:
            z.writestr(n, parts[n])
    os.replace(tmp, WB)
    print("written.")


if __name__ == "__main__":
    main()
