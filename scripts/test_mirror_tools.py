#!/usr/bin/env python3
"""Tests for the E10 mirror tools, on REAL mirror data with known, planted edits.

    python scripts/test_mirror_tools.py [--base <snapshot folder>]

Builds two D3-layout snapshot folders (gz + snapshot.json) in a temp dir from a real
snapshot, plants edits in the second, and checks journal, health and rollback planning
see exactly those. Nothing under sharepoint-lists/ is written.
"""
import argparse
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
import mirror_lib as M  # noqa: E402
import mirror_journal as J  # noqa: E402

fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def write_snap(folder, as_of, tables):
    os.makedirs(folder)
    for name, rows in tables.items():
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)
        with gzip.open(os.path.join(folder, name + ".csv.gz"), "wt", encoding="utf-8", newline="") as f:
            f.write(buf.getvalue())
    with open(os.path.join(folder, "snapshot.json"), "w", encoding="utf-8") as f:
        json.dump({"asOf": as_of, "tables": {k: len(v) for k, v in tables.items()}}, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.path.join(M.SNAPSHOTS, "2026-09-24_2225"))
    args = ap.parse_args()
    base = M.Snapshot(args.base)
    tables = {t: base.table(t) for t in M.LISTS + [M.CATALOG] if base.has(t)}
    tmp = tempfile.mkdtemp(prefix="mirror-test-")
    try:
        a = os.path.join(tmp, "2026-09-25_0100")
        b = os.path.join(tmp, "2026-09-25_0300")
        write_snap(a, "2026-09-25T05:00Z", tables)

        t2 = copy.deepcopy(tables)
        oi = t2["Order Items"]
        u0, u1 = oi[0], oi[1]
        u0_id, u1_id = M.key(u0), M.key(u1)
        old_loc = u0.get("Location", "")
        u0["Location"] = "PLANTED-LOCATION"                  # real change
        u0["Modified"] = "2030-01-01T00:00:00Z"              # volatile: must NOT journal
        u0["Editor_Email"] = "someone@else"                  # volatile: must NOT journal
        if "Model" in u0:
            u0["Model"] = "PLANTED-DISPLAY"                  # derived (lookup display)
        deleted = oi.pop(5)
        added = dict(oi[2]); added["Id"] = "999999"; added["Title"] = "PLANTED-NEW"
        oi.append(added)
        u1["Location"] = ""                                  # an erasure
        cols = t2[M.CATALOG]
        cols[0] = dict(cols[0]); cols[0]["displayName"] = "PLANTED-RENAME"
        write_snap(b, "2026-09-25T07:00Z", t2)

        print("journal diff on planted edits")
        ev = J.diff(M.Snapshot(a), M.Snapshot(b))
        ch = [e for e in ev if e["kind"] == "change"]
        check(any(e["id"] == int(u0_id) and e["field"] == "Location" and e["new"] == "PLANTED-LOCATION"
                  and e["old"] == M.norm(old_loc) and not e.get("derived") for e in ch), "real change seen, with old value")
        check(not any(e.get("field") in ("Modified", "Editor_Email") for e in ev), "volatile columns not journaled")
        if "Model" in u0:
            check(any(e["field"] == "Model" and e.get("derived") for e in ch), "lookup display change tagged derived")
        check(any(e["kind"] == "deleted" and e["id"] == int(M.key(deleted)) for e in ev), "deleted row seen")
        check(any(e["kind"] == "added" and e["id"] == 999999 for e in ev), "added row seen")
        check(any(e["kind"] == "schema" and e["what"] == "displayName changed" for e in ev), "schema rename seen")
        check(any(e["id"] == int(u1_id) and e["field"] == "Location" and e["new"] == "" for e in ch), "erasure seen")
        expected = 2 + (1 if "Model" in u0 else 0)
        check(len(ch) == expected, "exactly the planted changes: %d change events (expect %d)" % (len(ch), expected))
        check(all(e["prevAsOf"] == "2026-09-25T05:00Z" and e["asOf"] == "2026-09-25T07:00Z" for e in ev), "asOf stamps from snapshot.json")

        # health + rollback, if present
        try:
            import mirror_health as H
            print("\nhealth on the planted events")
            rep = H.evaluate(ev, M.Snapshot(b), acknowledged=[])
            reds = [r for r in rep if r["level"] == "red"]
            check(any(r["check"] == "rows deleted" for r in reds), "health: deletion is red")
            check(any(r["check"] == "schema change" for r in reds), "health: schema change is red")
            check(not any(r["check"] == "bulk change" for r in reds), "health: 2 changes is not a bulk change")
        except ImportError:
            print("  (mirror_health not built yet)")
        try:
            import plan_rollback as R
            print("\nrollback plan on the planted events")
            plan = R.build_plan(ev, M.Catalog(M.Snapshot(b)), lists=["Order Items"], fields=["Location", "Model"])
            ents = plan["entries"]
            check(any(p["id"] == int(u0_id) and p["field"] == "Location" and p["expect"] == "PLANTED-LOCATION"
                      and p["restore"] == M.norm(old_loc) for p in ents), "rollback: restore old Location, expect planted value")
            check(not any(p["field"] == "Model" for p in ents), "rollback: derived display column never restored")
        except ImportError:
            print("  (plan_rollback not built yet)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not fails else "%d FAILED" % len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
