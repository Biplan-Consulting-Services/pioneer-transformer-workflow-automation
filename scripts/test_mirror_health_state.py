#!/usr/bin/env python3
"""E12 tests: the ported state checks (x25 parent drift, x16 lookup mirrors, x17 revision ids)
on the CURRENT live mirror CSVs, with planted defects.

    python scripts/test_mirror_health_state.py

Today's counts are printed, not asserted (the live data moves). What is asserted: each planted
defect appears as exactly one more finding in the right check, and a matching known rule turns
a planted parent drift from red into known. Nothing under sharepoint-lists/ is written.
"""
import copy
import csv
import gzip
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mirror_lib as M        # noqa: E402
import mirror_health as H     # noqa: E402

fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def write_snap(folder, tables):
    os.makedirs(folder)
    for name, rows in tables.items():
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader(); w.writerows(rows)
        with gzip.open(os.path.join(folder, name + ".csv.gz"), "wt", encoding="utf-8", newline="") as f:
            f.write(buf.getvalue())
    with open(os.path.join(folder, "snapshot.json"), "w") as f:
        json.dump({"asOf": "2026-09-25T05:00Z"}, f)
    return M.Snapshot(folder)


def rows_of(res, check, level=None, field=None):
    return sum(r["rows"] or 0 for r in res if r["check"] == check
               and (level is None or r["level"] == level) and (field is None or r["field"] == field))


def main():
    base = {t: M.read_table(os.path.join(M.LIVE, t + ".csv")) for t in M.LISTS + [M.CATALOG]}
    if "csvColumn" not in base[M.CATALOG][0]:
        sys.exit("ABORT: live/Columns.csv predates E8c - refresh the mirror first")
    known = H.load_known()
    tmp = tempfile.mkdtemp(prefix="e12-")
    try:
        s0 = write_snap(os.path.join(tmp, "base"), base)
        r0 = H.state_checks(s0, "2026-09-25T02:25Z", known)
        print("baseline (live, informational):")
        for r in r0:
            print("  %-13s %-6s %-28s %4s" % (r["check"], r["level"], r["field"], r["rows"]))
        base_red_drift = rows_of(r0, "parent drift", "red")

        # 1. parent drift: a unit whose OrdPO no longer matches its Order
        t = copy.deepcopy(base)
        u = next(x for x in t["Order Items"] if M.norm(x.get("OrderNumberId")) and M.norm(x.get("OrdPO")))
        u["OrdPO"] = "PLANTED-STALE-PO"
        r1 = H.state_checks(write_snap(os.path.join(tmp, "p1"), t), "2026-09-25T02:25Z", known)
        check(rows_of(r1, "parent drift", "red", "OrdPO") == rows_of(r0, "parent drift", "red", "OrdPO") + 1,
              "planted stale OrdPO on %s -> one more RED parent drift on OrdPO" % u["Title"])
        # ... and a known rule for exactly that unit turns it into 'known'
        r1k = H.state_checks(M.Snapshot(os.path.join(tmp, "p1")), "2026-09-25T02:25Z",
                             known + [{"check": "parent drift", "units": [u["Title"]], "reason": "test"}])
        check(rows_of(r1k, "parent drift", "red") == base_red_drift, "a matching known rule turns it from red to known")

        # 2. x16: a unit's Client_ID_TextField disagrees with its Client lookup
        t = copy.deepcopy(base)
        u = next(x for x in t["Order Items"] if M.norm(x.get("ClientId")) and M.norm(x.get("Client_ID_TextField")))
        u["Client_ID_TextField"] = "PLANTED-WRONG-CLIENT"
        r2 = H.state_checks(write_snap(os.path.join(tmp, "p2"), t), None, known)
        check(rows_of(r2, "lookup mirror", "red", "Client_ID_TextField") == rows_of(r0, "lookup mirror", "red", "Client_ID_TextField") + 1,
              "planted wrong Client_ID_TextField on %s -> one more RED lookup-mirror finding" % u["Title"])

        # 3. x17: a revision whose ModelID holds its MODEL's code (the corruption signature)
        t = copy.deepcopy(base)
        mods = {M.key(m): M.norm(m.get("ModelID")).strip() for m in t["Models"]}
        idcol = M.Catalog(s0).id_column("Model Revisions", "Model")
        rv = next(x for x in t["Model Revisions"] if M.norm(x.get(idcol)) in mods
                  and M.norm(x.get("ModelID")).upper().startswith("MR"))
        rv["ModelID"] = mods[M.norm(rv[idcol])]
        r3 = H.state_checks(write_snap(os.path.join(tmp, "p3"), t), None, known)
        check(rows_of(r3, "revision id", "red", "ModelID") == rows_of(r0, "revision id", "red", "ModelID") + 1
              and any("equals its MODEL code" in r["detail"] for r in r3 if r["check"] == "revision id"),
              "planted MODEL code in revision %s's ModelID -> one more RED, 'equals its MODEL code'" % M.key(rv))

        # 4. x17: a revision that loses its Model link (read through idColumn = ModelId2)
        t = copy.deepcopy(base)
        rv = next(x for x in t["Model Revisions"] if M.norm(x.get(idcol)))
        rv[idcol] = ""
        r4 = H.state_checks(write_snap(os.path.join(tmp, "p4"), t), None, known)
        check(rows_of(r4, "revision id", "red", idcol) == rows_of(r0, "revision id", "red", idcol) + 1,
              "revision %s with no %s -> one more RED 'no Model link'" % (M.key(rv), idcol))

        # 5. whitespace in an id is reported apart, never as drift
        check(all(r["level"] == "amber" for r in r0 if r["check"] == "id whitespace"), "id whitespace is amber, not red")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not fails else "%d FAILED" % len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
