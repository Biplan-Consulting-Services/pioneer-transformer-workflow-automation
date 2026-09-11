# -*- coding: utf-8 -*-
"""Stamp fresh exports and workbook copies, and archive the ones they supersede.

    python scripts/stamp_exports.py            # dry run, shows every move
    python scripts/stamp_exports.py --apply

A browser download lands as `Order Items (10).csv` or `FRM10-12 (21).xlsx`. The repo
convention is `{Name} {YYYY-MM-DD} {HHMM}.ext`, stamped from the file's own mtime so the
name records when the snapshot was *taken*, and whatever it replaces moves to that
folder's `Archive/` rather than being deleted (2026-08-13 convention, see CLAUDE.md).

Two folders, same rule:

    sharepoint-lists/   list exports            .csv
    workbooks/          workbook copies         .xlsx .xlsm

WHY THIS COUNTS ROWS AND COLUMNS BEFORE MOVING ANYTHING
  An *Export to CSV* follows the **currently selected view**, not the list. A view-shaped
  export looks completely real until you count it: the first `Order Items` export of
  2026-09-05 was the BO Tracking view, 3 rows and 23 columns, and read as a real export.
  That risk is live in a new way now that `FRM10-12 Layout` is becoming the default view,
  since it yields 24 columns, active units only.

  The cutover's only data rollback is four of these files. A rollback missing the
  delivered units is not a rollback, so the counts are printed against the file being
  superseded and a large drop is called out rather than mentioned. Judgement stays with
  the reader: this refuses nothing, it just makes the number impossible to miss.

  Counting means parsing, and parsing means the two traps in CLAUDE.md: the giant
  `ListSchema={...}` record comes FIRST and contains newlines, so it is one csv *record*
  to skip, not one line; and a column count from the header is the columns in the export,
  not the columns on the list (lookups are absent entirely, hidden columns drop out).

  Workbooks are stamped on their name and size alone. Counting anything inside one means
  Excel COM, and COM on FRM10-12 is how you lose the six native formula columns.
"""
import argparse, csv, io, os, re, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TARGETS = [("sharepoint-lists", (".csv",)),
           ("workbooks", (".xlsx", ".xlsm"))]

STAMPED = re.compile(r"^(?P<name>.+?) (?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{4})"
                     r"\.(?P<ext>[A-Za-z]+)$")
# "Order Items (10).csv", "FRM10-12 (21).xlsx", "Order Items.csv"
FRESH = re.compile(r"^(?P<name>.+?)(?: \(\d+\))*\.(?P<ext>[A-Za-z]+)$")
# Checked separately, to keep this off files already carrying a date in some other shape.
# `Models dedup worklist 2026-09-05.csv` is a one-off worklist, not a list export, and
# stamping it produces `Models dedup worklist 2026-09-05 2026-09-05 1639.csv`.
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


def mb(path):
    return os.path.getsize(path) / 1048576.0


def scan(folder, exts):
    """(moves, lines) for one folder. Nothing is touched here."""
    d = os.path.join(ROOT, folder)
    arch = os.path.join(d, "Archive")
    out, moves = [], []

    known = {}
    for f in os.listdir(d):
        m = STAMPED.match(f)
        if m and ("." + m.group("ext").lower()) in exts:
            known.setdefault(m.group("name"), []).append(f)

    for f in sorted(os.listdir(d)):
        if os.path.splitext(f)[1].lower() not in exts:
            continue
        if STAMPED.match(f) or DATED.search(f):
            continue
        m = FRESH.match(f)
        if not m:
            continue
        name, ext = m.group("name"), m.group("ext")
        src = os.path.join(d, f)
        t = time.localtime(os.path.getmtime(src))
        new = "%s %s.%s" % (name, time.strftime("%Y-%m-%d %H%M", t), ext)

        out.append("")
        out.append("%s/%s" % (folder, f))
        out.append("   -> %s" % new)

        prev = sorted(known.get(name, []))
        if ext.lower() == "csv":
            rows, cols = shape(src)
            if rows is not None:
                line = "      %d rows x %d columns" % (rows, cols)
                if prev:
                    pr, pc = shape(os.path.join(d, prev[-1]))
                    out.append(line + "   (was %d x %d in %s)" % (pr, pc, prev[-1]))
                    if rows < pr * 0.9 or cols < pc * 0.9:
                        out.append("      \U0001F534 MUCH smaller than the file it "
                                   "replaces. A SharePoint export follows the SELECTED "
                                   "VIEW, not the list. Re-export from All Items before "
                                   "trusting this as a rollback.")
                else:
                    out.append(line + "   (nothing earlier of this name)")
        else:
            was = "   (was %.1f MB)" % mb(os.path.join(d, prev[-1])) if prev else ""
            out.append("      %.1f MB%s" % (mb(src), was))
        for p in prev:
            out.append("      archive %s" % p)
        moves.append((src, os.path.join(d, new), arch,
                      [os.path.join(d, p) for p in prev]))
    return moves, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    moves = []
    for folder, exts in TARGETS:
        m, lines = scan(folder, exts)
        moves += m
        for l in lines:
            print(l)

    if not moves:
        print("Nothing unstamped in %s." % " or ".join(f for f, _ in TARGETS))
        return 0
    if not a.apply:
        print("\nDRY RUN, nothing moved. Re-run with --apply.")
        return 0

    for src, dst, arch, prevs in moves:
        if prevs and not os.path.isdir(arch):
            os.makedirs(arch)
        for p in prevs:
            shutil.move(p, os.path.join(arch, os.path.basename(p)))
        os.rename(src, dst)
    print("\n%d file(s) stamped, %d archived."
          % (len(moves), sum(len(p) for _, _, _, p in moves)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
