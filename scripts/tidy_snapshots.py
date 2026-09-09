# -*- coding: utf-8 -*-
"""Timestamp new snapshot drops and archive the superseded ones.

Two folders follow the same convention and both had drifted:

    sharepoint-lists/     {List Name} {YYYY-MM-DD} {HHMM}.csv
    workbooks/            {Workbook Name} {YYYY-MM-DD} {HHMM}.xlsx

A browser download arrives as `Order Items (9).csv` or `FRM10-12 (20).xlsx`, which
says nothing about when the snapshot was taken -- and the whole point of the
convention is that a re-export must not silently overwrite the record of when the
previous one happened. So: rename from the file's own mtime, which is when it
arrived.

Superseded snapshots move to `Archive/` rather than being deleted. Nothing is lost;
a diff against an older generation just reads from Archive/.

    python scripts/tidy_snapshots.py           # dry run
    python scripts/tidy_snapshots.py --apply

⚠️ Only files matching the two shapes are touched. Anything else in these folders --
worklists, build sheets, field-definition JSON -- is left alone, because it is not a
snapshot and has no generation.
"""
import os, re, sys, datetime, shutil, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FOLDERS = [
    (os.path.join(ROOT, "sharepoint-lists"), ".csv"),
    (os.path.join(ROOT, "workbooks"), ".xlsx"),
]

# `Name (3).csv` or `Name.csv` -- a fresh drop with no timestamp
UNSTAMPED = re.compile(r"^(?P<name>.+?)(?: \((?P<n>\d+)\))?$")
# `Name 2026-09-09 1758.csv` -- already conventional
STAMPED = re.compile(r"^(?P<name>.+) (?P<d>\d{4}-\d{2}-\d{2}) (?P<t>\d{4})$")

# Not snapshots: no generation, so no archiving and no renaming.
SKIP = re.compile(r"worklist|build list|field definitions|dedup", re.I)

apply = "--apply" in sys.argv
plan_rename, plan_archive = [], []

for folder, ext in FOLDERS:
    if not os.path.isdir(folder):
        continue
    archive = os.path.join(folder, "Archive")
    names = [f for f in os.listdir(folder)
             if f.lower().endswith(ext) and os.path.isfile(os.path.join(folder, f))]

    # --- 1. rename anything without a timestamp, using its own mtime ------------
    for f in sorted(names):
        stem = f[: -len(ext)]
        if SKIP.search(stem) or STAMPED.match(stem):
            continue
        m = UNSTAMPED.match(stem)
        base = m.group("name").strip()
        ts = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(folder, f)))
        new = "%s %s %s%s" % (base, ts.strftime("%Y-%m-%d"), ts.strftime("%H%M"), ext)
        if new != f:
            plan_rename.append((folder, f, new))

    # --- 2. archive every superseded generation --------------------------------
    # Applied to the post-rename names, so a drop renamed above is considered too.
    after = [n for (_, o, n) in plan_rename if _ == folder]
    after += [f for f in names if not any(o == f for (_, o, _n) in plan_rename)]
    gens = collections.defaultdict(list)
    for f in after:
        stem = f[: -len(ext)]
        if SKIP.search(stem):
            continue
        m = STAMPED.match(stem)
        if not m:
            continue
        gens[m.group("name")].append((m.group("d") + " " + m.group("t"), f))
    for base, items in gens.items():
        items.sort()                       # oldest first
        for _stamp, f in items[:-1]:       # keep only the newest
            plan_archive.append((folder, archive, f))

def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")

print("RENAME (%d)" % len(plan_rename))
for folder, old, new in plan_rename:
    print("   %-18s %-52s -> %s" % (rel(folder), old, new))
print()
print("ARCHIVE (%d)" % len(plan_archive))
by = collections.Counter(rel(f) for f, _a, _n in plan_archive)
for folder, n in by.items():
    print("   %-18s %d file(s)" % (folder, n))
for folder, _a, f in plan_archive:
    print("      %s" % f)

if not apply:
    print()
    print("DRY RUN -- nothing moved. Re-run with --apply.")
    sys.exit(0)

for folder, old, new in plan_rename:
    dst = os.path.join(folder, new)
    if os.path.exists(dst):
        print("SKIP rename, target exists: %s" % new)
        continue
    os.rename(os.path.join(folder, old), dst)
for folder, archive, f in plan_archive:
    os.makedirs(archive, exist_ok=True)
    dst = os.path.join(archive, f)
    if os.path.exists(dst):
        print("SKIP archive, already there: %s" % f)
        continue
    shutil.move(os.path.join(folder, f), dst)

print()
print("done: %d renamed, %d archived" % (len(plan_rename), len(plan_archive)))
