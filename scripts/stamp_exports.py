# -*- coding: utf-8 -*-
"""Stamp fresh SharePoint exports and archive the ones they supersede.

    python scripts/stamp_exports.py            # dry run, shows every move
    python scripts/stamp_exports.py --apply

A browser download lands as `Order Items (10).csv`. The repo convention is
`{List Name} {YYYY-MM-DD} {HHMM}.csv`, stamped from the file's own mtime so the name
records when the snapshot was *taken*, and the export it replaces moves to
`sharepoint-lists/Archive/` rather than being deleted (2026-08-13 convention, see
CLAUDE.md).

WHY THIS COUNTS ROWS AND COLUMNS BEFORE MOVING ANYTHING
  An *Export to CSV* follows the **currently selected view**, not the list. A view-shaped
  export looks completely real until you count it: the first `Order Items` export of
  2026-09-05 was the BO Tracking view, 3 rows and 23 columns, and read as a real export.
  Tonight that risk is live in a new way, because `FRM10-12 Layout` is about to become the
  default view and yields 24 columns, active units only.

  These four files are the cutover's only data rollback. A rollback missing the delivered
  units is not a rollback, so the counts are printed against the export being superseded
  and a large drop is called out rather than mentioned. Judgement stays with the reader:
  this refuses nothing, it just makes the number impossible to miss.

  Counting means parsing, and parsing means the two traps in CLAUDE.md: the giant
  `ListSchema={...}` record comes FIRST and contains newlines, so it is one csv *record*
  to skip, not one line; and a column count from the header is the columns in the export,
  not the columns on the list (lookups are absent entirely, hidden columns drop out).
"""
import argparse, csv, io, os, re, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LISTS = os.path.join(ROOT, "sharepoint-lists")
ARCHIVE = os.path.join(LISTS, "Archive")

STAMPED = re.compile(r"^(?P<name>.+?) (?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{4})\.csv$")
# "Order Items (10).csv" / "Order Items.csv" / "Order Items (10) (1).csv".
# DATED is checked separately to keep this off files that already carry a date in some
# other shape -- `Models dedup worklist 2026-09-05.csv` is a one-off worklist, not a list
# export, and stamping it produces `... 2026-09-05 2026-09-05 1639.csv`.
FRESH = re.compile(r"^(?P<name>.+?)(?: \(\d+\))*\.csv$")
DATED = re.compile(r"\d{4}-\d{2}-\d{2}")

csv.field_size_limit(min(2 ** 31 - 1, sys.maxsize))


def shape(path):
    """(rows, columns) of a SharePoint export, or (None, None) if it will not parse."""
    try:
        r = csv.reader(io.open(path, encoding="utf-8-sig", newline=""))
        first = next(r)
        # the ListSchema record is one field on its own record, before the real header
        hdr = next(r) if first and first[0].startswith("ListSchema=") else first
        return sum(1 for _ in r), len(hdr)
    except Exception as e:
        print("   ! could not parse: %s" % e)
        return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    known = {}
    for f in os.listdir(LISTS):
        m = STAMPED.match(f)
        if m:
            known.setdefault(m.group("name"), []).append(f)

    fresh = []
    for f in sorted(os.listdir(LISTS)):
        if not f.lower().endswith(".csv") or STAMPED.match(f) or DATED.search(f):
            continue
        m = FRESH.match(f)
        if m:
            fresh.append((f, m.group("name")))

    if not fresh:
        print("Nothing unstamped in sharepoint-lists/.")
        return 0

    moves = []
    for f, name in fresh:
        src = os.path.join(LISTS, f)
        t = time.localtime(os.path.getmtime(src))
        new = "%s %s.csv" % (name, time.strftime("%Y-%m-%d %H%M", t))
        rows, cols = shape(src)

        prev = sorted(known.get(name, []))
        pr, pc = (None, None)
        if prev:
            pr, pc = shape(os.path.join(LISTS, prev[-1]))

        print("\n%s" % f)
        print("   -> %s" % new)
        if rows is not None:
            print("      %d rows x %d columns" % (rows, cols), end="")
            if pr is not None:
                print("   (was %d x %d in %s)" % (pr, pc, prev[-1]))
                if rows < pr * 0.9 or cols < pc * 0.9:
                    print("      \U0001F534 MUCH smaller than the export it replaces. A "
                          "SharePoint export follows the SELECTED VIEW, not the list. "
                          "Re-export from All Items before trusting this as a rollback.")
            else:
                print("   (no earlier export of this list)")
        for p in prev:
            print("      archive %s" % p)
        moves.append((src, os.path.join(LISTS, new),
                      [os.path.join(LISTS, p) for p in prev]))

    if not a.apply:
        print("\nDRY RUN, nothing moved. Re-run with --apply.")
        return 0

    if not os.path.isdir(ARCHIVE):
        os.makedirs(ARCHIVE)
    for src, dst, prevs in moves:
        for p in prevs:
            shutil.move(p, os.path.join(ARCHIVE, os.path.basename(p)))
        os.rename(src, dst)
    print("\n%d export(s) stamped, %d archived."
          % (len(moves), sum(len(p) for _, _, p in moves)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
