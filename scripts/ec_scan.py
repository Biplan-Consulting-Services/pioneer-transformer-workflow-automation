# -*- coding: utf-8 -*-
"""Re-run D0's scan against the workbook the NEXT run will actually read.

D0 (2026-09-01) scanned the 08-31 snapshot and found 9 marker rows, 3 of them
lowercase `ec`, and said to expect the count to grow. This checks the 09-04
23:08 refresh -- the one the flow will read -- and reports which iterations will
throw if A5c is not applied first.
"""
import openpyxl, re, collections, io, os, datetime

# A real date cell is fine: the Excel connector hands the flow a serial number
# and addDays('1899-12-30', int(...)) is built for exactly that. Only a genuine
# *string* in a date column is a landmine.
NUMERICISH = (int, float, datetime.datetime, datetime.date, datetime.time)

WB = (r"C:\Users\solei\OneDrive\Documents\Biplan\claude\Clients\Pioneer Transformer"
      r"\FRM10-12\live-workbook-data\FRM10-12_2026-09-04_23h08m.xlsx")

# the six stages the flow maps; Tanking/Delivery are excluded per A5b
STAGES = ["Coiling Date", "Stacking Date", "Assembly Date", "Drying Date",
          "Testing Date", "Finishing Date"]
ALSO = ["Tanking Date", "Delivery Date", "Section Qty", "Time (days)",
        "Tank Delivery Date", "Original Tanking Date", "Manual Estimated Delivery Date"]

wb = openpyxl.load_workbook(WB, data_only=True)
ws = tbl = None
for s in wb.worksheets:
    for name, t in getattr(s, "tables", {}).items():
        if name == "TableOrders":
            ws, tbl = s, t
# openpyxl hands back either a Table object or a bare ref string depending on
# version, so take whichever this one gives.
ref = tbl if isinstance(tbl, str) else tbl.ref
print("TableOrders on sheet %r, ref %s" % (ws.title, ref))

a, b = ref.split(":")
c0, r0 = re.match(r"([A-Z]+)(\d+)", a).groups()
c1, r1 = re.match(r"([A-Z]+)(\d+)", b).groups()
from openpyxl.utils import column_index_from_string as ci
lo, hi, hdr = ci(c0), ci(c1), int(r0)

rows = list(ws.iter_rows(min_row=hdr, max_row=int(r1), min_col=lo, max_col=hi, values_only=True))
head = [str(h).strip() if h is not None else "" for h in rows[0]]
data = rows[1:]
print("header row %d, %d data rows, %d columns" % (hdr, len(data), len(head)))

idx = {h: i for i, h in enumerate(head)}
unit_i = idx.get("Order", 0)

print("\n=== non-numeric values in the six MAPPED stage columns ===")
found = collections.Counter()
detail = []
for n, row in enumerate(data, start=1):          # n = 1-based iteration order
    for st in STAGES:
        i = idx.get(st)
        if i is None:
            continue
        v = row[i]
        if v is None or isinstance(v, NUMERICISH):
            continue
        s = str(v).strip()
        if not s:
            continue
        found[(st, s)] += 1
        detail.append((n, str(row[unit_i]), st, s))

for (st, s), k in sorted(found.items(), key=lambda x: -x[1]):
    flag = "  <-- lowercase, THROWS on int()" if s != s.upper() else "  (uppercase, guarded today)"
    print("   %-16s %-10r x%-3d%s" % (st, s, k, flag))

throws = [d for d in detail if d[3] != d[3].upper()]
print("\n%d marker rows total; %d of them lowercase and will throw" % (len(detail), len(throws)))
if throws:
    print("\nrows that fail today, with their iteration number:")
    for n, unit, st, s in sorted(throws):
        print("   iteration ~%-5d %-14s %-16s %r" % (n, unit, st, s))
    ns = [t[0] for t in throws]
    print("\nfirst failing iteration ~%d  (Sep 1 run reported 497)" % min(ns))

print("\n=== the other int()-bound columns, for completeness ===")
for col in ALSO:
    i = idx.get(col)
    if i is None:
        print("   %-30s (not a TableOrders column)" % col); continue
    bad = collections.Counter()
    for row in data:
        v = row[i]
        if v is not None and not isinstance(v, NUMERICISH) and str(v).strip():
            bad[str(v).strip()] += 1
    print("   %-30s %s" % (col, dict(bad) if bad else "clean"))
