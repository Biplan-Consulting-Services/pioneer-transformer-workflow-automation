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

        # PS 5.1 writes snapshot.json with a UTF-8 BOM (first real refresh, 2026-09-25 00:55)
        bom = os.path.join(tmp, "bom")
        write_snap(bom, "2026-09-25T04:55Z", {"Index": tables["Index"]})
        with open(os.path.join(bom, "snapshot.json"), "w", encoding="utf-8-sig") as f:
            json.dump({"asOf": "2026-09-25T04:55Z", "tables": {"Index": len(tables["Index"])}}, f)
        check(M.Snapshot(bom).as_of == "2026-09-25T04:55Z", "snapshot.json with a BOM reads")

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

            # fan-out classifier (D5): the busiest Model Revision, its Cable -> every unit's RevCable
            import collections as C
            cnt = C.Counter(M.norm(u.get("ModelRevisionId")) for u in tables["Order Items"] if M.norm(u.get("ModelRevisionId")))
            rev_id, n_units = cnt.most_common(1)[0]
            check(n_units > H.BULK, "fan-out fixture: revision %s has %d units (> %d)" % (rev_id, n_units, H.BULK))
            for with_parent in (True, False):
                t3 = copy.deepcopy(tables)
                if with_parent:
                    rv = next(r for r in t3["Model Revisions"] if M.key(r) == rev_id)
                    rv["Cable"] = "PLANTED-CABLE"
                for u in t3["Order Items"]:
                    if M.norm(u.get("ModelRevisionId")) == rev_id:
                        u["RevCable"] = "PLANTED-CABLE"
                c = os.path.join(tmp, "fan-%s" % with_parent)
                write_snap(c, "2026-09-25T09:00Z", t3)
                ev3 = J.diff(M.Snapshot(a), M.Snapshot(c))
                rep3 = H.evaluate(ev3, M.Snapshot(c), acknowledged=[])
                bulk = [r for r in rep3 if r["check"] == "bulk change" and r["field"] == "RevCable"]
                if with_parent:
                    check(len(bulk) == 1 and bulk[0]["level"] == "expected" and rev_id in bulk[0]["detail"],
                          "fan-out: parent changed too -> 'expected, fan-out of Model Revisions %s' (got %s)"
                          % (rev_id, [b["level"] for b in bulk]))
                else:
                    check(len(bulk) == 1 and bulk[0]["level"] == "red",
                          "no parent change -> the same bulk stays RED (got %s)" % [b["level"] for b in bulk])
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
        # E8c: renamed id column (Model Revisions: REST ModelId -> CSV ModelId2), with the LIVE catalog
        live_cols = os.path.join(M.LIVE, M.CATALOG + ".csv")
        if os.path.exists(live_cols) and "csvColumn" in M.read_table(live_cols)[0]:
            print("\nE8c: ModelId2 with the live catalog")
            t4 = copy.deepcopy(tables)
            t4[M.CATALOG] = M.read_table(live_cols)
            a4 = os.path.join(tmp, "e8c-a"); write_snap(a4, "2026-09-25T10:00Z", t4)
            t5 = copy.deepcopy(t4)
            rv = next(r for r in t5["Model Revisions"] if M.norm(r.get("ModelId2")))
            rv_id, old_mid = M.key(rv), M.norm(rv["ModelId2"])
            rv["ModelId2"] = "999999"                                   # dangling lookup id
            b4 = os.path.join(tmp, "e8c-b"); write_snap(b4, "2026-09-25T11:00Z", t5)
            ev4 = J.diff(M.Snapshot(a4), M.Snapshot(b4))
            e = [x for x in ev4 if x.get("field") == "ModelId2"]
            check(len(e) == 1 and not e[0].get("derived"), "ModelId2 change journaled as a REAL change")
            cat4 = M.Catalog(M.Snapshot(b4))
            check(cat4.rest_field("Model Revisions", "ModelId2") == "ModelId", "catalog maps CSV ModelId2 -> REST ModelId")
            check(cat4.id_column("Model Revisions", "Model") == "ModelId2", "catalog: Model's id column is ModelId2")
            import plan_rollback as R
            p4 = R.build_plan(ev4, cat4, lists=["Model Revisions"])["entries"]
            check(len(p4) == 1 and p4[0]["field"] == "ModelId" and p4[0]["csvColumn"] == "ModelId2"
                  and p4[0]["restore"] == int(old_mid) and p4[0]["expect"] == 999999,
                  "rollback targets REST ModelId, typed int (got %s)" % p4)
            import mirror_health as H
            bl = [r for r in H.evaluate(ev4, M.Snapshot(b4), acknowledged=[]) if r["check"] == "broken lookup"
                  and r["list"] == "Model Revisions"]
            check(bl and bl[0]["field"] == "ModelId2" and ("%s->999999" % rv_id) in bl[0]["detail"],
                  "health: dangling ModelId2 caught as a broken lookup")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not fails else "%d FAILED" % len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
