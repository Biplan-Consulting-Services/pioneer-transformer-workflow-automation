#!/usr/bin/env python3
"""ONE-OFF (2026-09-24, design D3): move the pre-D3 flat mirror files into the D3 layout.

    python scripts/migrate_mirror_d3.py            # dry: prints the plan
    python scripts/migrate_mirror_d3.py --apply

  mirror/<Table> <yyyy-mm-dd HHMM>.csv  and  mirror/Archive/...
      -> mirror/snapshots/<yyyy-mm-dd_HHMM>/<Table>.csv.gz  (+ snapshot.json, asOf in UTC)
  the newest set -> mirror/live/<Table>.csv  (stable names)

Snapshots hold the real lists + Columns only (design Layer A); diagnostics (Lists,
VersionCounts, VersionProbe, Order via SharePointTables) go to live/ only.
Every snapshot is READ BACK and compared row-for-row before any flat file is deleted.
The workbook move (workbooks/ -> mirror/live/) is a `git mv`, done separately.
"""
import argparse
import collections
import glob
import gzip
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mirror_lib as M  # noqa: E402

SNAP_TABLES = set(M.LISTS) | {M.CATALOG}
PAT = re.compile(r"^(?P<table>.+) (?P<stamp>\d{4}-\d{2}-\d{2} \d{4})\.csv$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    sets = collections.defaultdict(dict)   # stamp -> table -> path
    for d in (M.MIRROR, os.path.join(M.MIRROR, "Archive")):
        for p in glob.glob(os.path.join(d, "*.csv")):
            m = PAT.match(os.path.basename(p))
            if m:
                sets[m["stamp"]].setdefault(m["table"], p)
    if not sets:
        sys.exit("ABORT: no flat mirror CSVs found - already migrated?")
    stamps = sorted(sets)
    newest = stamps[-1]
    print("found sets:", {s: len(t) for s, t in sets.items()}, " newest:", newest)

    plan = []
    for s in stamps:
        folder = os.path.join(M.SNAPSHOTS, s.replace(" ", "_"))
        tables = {t: p for t, p in sets[s].items() if t in SNAP_TABLES}
        if not tables:
            # a -Tables diagnostic-only refresh: nothing to snapshot. Its files are older
            # copies of tables the newest set carries, so they are superseded, not lost.
            sup = [t for t in sets[s] if t in sets[newest]]
            if len(sup) != len(sets[s]):
                sys.exit("ABORT: set %s has tables the newest set lacks: %s" % (s, sorted(set(sets[s]) - set(sup))))
            print("  skip     %-16s diagnostic-only (%s) - superseded by %s" % (s, ", ".join(sets[s]), newest))
            continue
        plan.append((s, folder, tables))
        print("  snapshot %-16s <- %d tables%s" % (os.path.basename(folder), len(tables),
              "   (EXISTS - will refuse)" if os.path.exists(folder) else ""))
    print("  live/ <- the %s set: %s" % (newest, sorted(sets[newest])))
    if not args.apply:
        print("DRY - nothing written. --apply to do it.")
        return

    # 1. snapshots, each read back before going on
    for s, folder, tables in plan:
        if os.path.exists(folder):
            sys.exit("ABORT: %s exists" % folder)
        os.makedirs(folder)
        counts = {}
        for t, p in tables.items():
            src_rows = M.read_table(p)
            with open(p, "rb") as fi, gzip.open(os.path.join(folder, t + ".csv.gz"), "wb") as fo:
                shutil.copyfileobj(fi, fo)
            counts[t] = len(src_rows)
        with open(os.path.join(folder, "snapshot.json"), "w", encoding="utf-8") as f:
            json.dump({"asOf": M._as_utc(s), "localStamp": s, "tables": counts,
                       "source": "migrated from flat files by migrate_mirror_d3.py"}, f, indent=1)
        snap = M.Snapshot(folder)
        for t, n in counts.items():
            got = snap.table(t)
            if len(got) != n or got != M.read_table(tables[t]):
                sys.exit("ABORT: snapshot %s/%s does not read back identical - flat files kept" % (folder, t))
        print("  wrote + verified %s (%d tables, asOf %s)" % (os.path.relpath(folder, M.ROOT), len(counts), snap.as_of))

    # 2. live/ with stable names
    os.makedirs(M.LIVE, exist_ok=True)
    for t, p in sets[newest].items():
        shutil.copyfile(p, os.path.join(M.LIVE, t + ".csv"))
    print("  live/: %d tables from %s" % (len(sets[newest]), newest))

    # 3. only now remove the flat files (all are inside a verified snapshot, or in live/)
    n = 0
    for s in stamps:
        for t, p in sets[s].items():
            os.remove(p)
            n += 1
    arch = os.path.join(M.MIRROR, "Archive")
    if os.path.isdir(arch) and not os.listdir(arch):
        os.rmdir(arch)
    print("  removed %d flat files%s" % (n, "" if os.path.isdir(arch) else " and the empty Archive/"))


if __name__ == "__main__":
    main()
