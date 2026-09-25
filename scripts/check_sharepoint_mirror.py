#!/usr/bin/env python3
"""Acceptance checks for the SharePoint mirror CSVs (board E8, 2026-09-24).

Reads the NEWEST file per table in sharepoint-lists/mirror/ and checks:
  1. row counts (pass expected counts with --expect Table=N ...; defaults are 2026-09-24's)
  2. dates come back RAW - the E7 pair: unit 22157-1/10 OrdOrderDate vs Order 22157's
     Order_x0020_Date, and what SharePoint.Tables made of the same Order date
  3. lookup ids present on Order Items (and their display columns)
  4. the Cli* fill: CliLeadTimeWeeks on HYDRO QUEBEC's units

    python scripts/check_sharepoint_mirror.py
"""
import collections
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import load_exports as L  # noqa: E402

MIRROR = os.path.join(os.path.dirname(HERE), "sharepoint-lists", "mirror")
EXPECT = {"Order Items": 1127, "Order": 470, "Models": 394, "Model Revisions": 395, "Clients": 99}
fails = []


def newest(table):
    pat = re.compile(r"^" + re.escape(table) + r" \d{4}-\d{2}-\d{2} \d{4}\.csv$")
    files = sorted(f for f in os.listdir(MIRROR) if pat.match(f))
    if not files:
        sys.exit("ABORT: no mirror CSV for %r in %s" % (table, MIRROR))
    return L.load(os.path.join(MIRROR, files[-1])), files[-1]


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


for arg in sys.argv[1:]:
    if arg.startswith("--expect"):
        continue
    if "=" in arg:
        k, v = arg.split("=", 1)
        EXPECT[k] = int(v)

T = {}
print("1. row counts")
for t in ["Order Items", "Order", "Models", "Model Revisions", "Clients", "Index", "Models SA", "Columns",
          "Order via SharePointTables"]:
    rows, f = newest(t)
    T[t] = rows
    exp = EXPECT.get(t)
    check(len(rows) > 0 and (exp is None or len(rows) == exp),
          "%-27s %5d rows%s   (%s)" % (t, len(rows), "" if exp is None else " (expect %d)" % exp, f))

print("\n2. dates are raw (E7 pair)")
unit = next((r for r in T["Order Items"] if r.get("Title") == "22157-1/10"), None)
order = next((r for r in T["Order"] if (r.get("Order_x0020_Number1") or "").strip() == "22157"), None)
check(unit is not None, "unit 22157-1/10 found")
check(order is not None, "Order 22157 found (id %s)" % (order or {}).get("Id"))
if unit and order:
    uv, ov = unit.get("OrdOrderDate"), order.get("Order_x0020_Date")
    check(uv == "2026-08-31T04:00:00Z", "unit OrdOrderDate      = %r (x25 saw '2026-08-31T04:00:00Z')" % uv)
    check(ov == "2026-09-01T00:00:00Z", "Order Order_x0020_Date = %r (x25 saw '2026-09-01T00:00:00Z')" % ov)
    spt = next((r for r in T["Order via SharePointTables"] if str(r.get("ID")).split(".")[0] == str(order.get("Id")).split(".")[0]), None)
    if spt:
        print("  info SharePoint.Tables, same Order: Order Date = %r  [M type: %s]"
              % (spt.get("Order Date"), spt.get("Order Date [M type]")))
    else:
        print("  info SharePoint.Tables row for Order id %s not found" % order.get("Id"))

print("\n3. lookup ids on Order Items")
oi = T["Order Items"]
for fk, disp in [("OrderNumberId", "OrderNumber"), ("ModelId", "Model"), ("ModelRevisionId", "ModelRevision"), ("ClientId", "Client")]:
    has = fk in oi[0]
    n = sum(1 for r in oi if (r.get(fk) or "").strip()) if has else 0
    d = sum(1 for r in oi if (r.get(disp) or "").strip()) if disp in oi[0] else None
    check(has and n > 0, "%-16s present, %4d of %d set;  display column %-14s %s"
          % (fk, n, len(oi), disp, "missing" if d is None else "%d set" % d))

print("\n4. Cli* fill")
hq = [c for c in T["Clients"] if "HYDRO" in (c.get("Title") or "").upper() and "QUEBEC" in (c.get("Title") or "").upper()]
check(len(hq) == 1, "HYDRO QUEBEC client row: %s" % [(c.get("Id"), c.get("Title"), c.get("CliLeadTimeWeeks")) for c in hq])
if hq:
    hid = str(hq[0]["Id"]).split(".")[0]
    units = [r for r in oi if str(r.get("ClientId") or "").split(".")[0] == hid]
    dist = collections.Counter(r.get("CliLeadTimeWeeks") or "<blank>" for r in units)
    print("  info %d HYDRO QUEBEC units, CliLeadTimeWeeks: %s" % (len(units), dict(dist)))
    check(units and all((r.get("CliLeadTimeWeeks") or "").split(".")[0] == str(hq[0].get("CliLeadTimeWeeks")).split(".")[0] for r in units),
          "every HYDRO QUEBEC unit carries the client's lead time")

cols = T["Columns"]
synced = [c for c in cols if (c.get("syncedByFlow") or "").strip()]
print("\n5. Columns table: %d rows, %d marked synced-from (x22 map has 47)" % (len(cols), len(synced)))
check(len(synced) == 47, "synced-from rows = 47")

print("\n%s" % ("ALL CHECKS PASS" if not fails else "%d CHECK(S) FAILED" % len(fails)))
sys.exit(1 if fails else 0)
