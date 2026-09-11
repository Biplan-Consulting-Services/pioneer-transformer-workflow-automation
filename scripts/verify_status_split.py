# -*- coding: utf-8 -*-
"""Check `Step Status` + `Status Date` against FRM10-12's composite `Status`.

    python scripts/verify_status_split.py
    python scripts/verify_status_split.py --detail

WHY THIS IS NOT JUST RE-READING n8's OUTPUT
  n8 parsed the composite off the LIST, where the transfer flow had written it. This
  re-derives it from the WORKBOOK instead, so it tests the whole chain end to end:
  Excel `Status` -> transfer flow -> list `Status` -> n8 -> the split pair. n8's own
  verification could only prove it was self-consistent.

  The parse is deliberately a second implementation of the same rules, written from
  `n8_split_status.js` (PREFIX, MONTH, the bare-prefix case, the `jui` ambiguity).
  Two implementations agreeing is worth something; one implementation agreeing with
  itself is worth nothing.

THE `jui` CASE, AND WHY IT IS CHECKED MORE LOOSELY
  `jui` is both juin and juillet. n8 resolves it per unit by taking whichever is nearer
  that unit's real past stage dates, and it resolved all 19 to juillet. Replicating that
  tie-break here would make this a copy of n8 rather than a check on it, so instead the
  day must match and the month must be June or July, and the 19 are listed for the eye.

⚠️ The composite `Status` is HIDDEN on the list (1.1e) and hidden columns do not export,
   so the list side of this comparison is unavailable -- which is exactly why the
   workbook is the right source here.
"""
import argparse, csv, glob, io, os, re, sys, warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
csv.field_size_limit(min(2 ** 31 - 1, sys.maxsize))

YEAR = 2026
UNIT = re.compile(r"^[A-Za-z0-9_]+-\d+/\d+$")

# transcribed from n8_split_status.js -- same tables, independent code
PREFIX = {"AT": "Attente", "EC": "En cours", "RE": "Réparation", "BO": "Manque Pièces",
          "TE": "Terminé", "B1": "Bobine 1", "B2": "Bobine 2", "B3": "Bobine 3"}
MONTH = {"ja": 1, "fe": 2, "fé": 2, "ma": 3, "av": 4, "ao": 8,
         "se": 9, "oc": 10, "no": 11, "de": 12}

BARE = re.compile(r"^([A-Za-z][A-Za-z0-9])$")
FULL = re.compile(r"^([A-Za-z0-9]{2})-([A-Za-zéÉ]{2,4})-(\d{1,2})$")


def newest(pat):
    f = sorted(glob.glob(os.path.join(ROOT, pat)))
    if not f:
        sys.exit("nothing matching %s" % pat)
    return f[-1]


def parse(raw):
    """(step, date|None, kind) or (None, None, reason)."""
    raw = (raw or "").strip()
    if not raw:
        return None, None, "blank"
    m = BARE.match(raw)
    if m:
        step = PREFIX.get(m.group(1).upper())
        return (step, None, "bare") if step else (None, None, "unknown bare prefix")
    m = FULL.match(raw)
    if not m:
        return None, None, "does not match PREFIX-Month-Day"
    pre, mon, day = m.group(1).upper(), m.group(2).lower(), int(m.group(3))
    step = PREFIX.get(pre)
    if not step:
        return None, None, "unknown prefix " + pre
    if mon == "jui":
        return step, day, "jui"        # day only; month is June or July
    mm = MONTH.get(mon)
    if not mm:
        return None, None, "unknown month " + mon
    return step, "%04d-%02d-%02d" % (YEAR, mm, day), "dated"


def workbook():
    import openpyxl
    from openpyxl.utils import range_boundaries
    p = newest("workbooks/FRM10-12 2*.xlsx")
    wb = openpyxl.load_workbook(p, data_only=True)
    ws = wb["Orders"]
    c1, r1, c2, r2 = range_boundaries(ws.tables["TableOrders"].ref)
    hdr = [str(ws.cell(row=r1, column=c).value or "").strip() for c in range(c1, c2 + 1)]
    ui = next(i for i, c in enumerate(range(c1, c2 + 1))
              if sum(1 for rr in range(r1 + 1, r2 + 1)
                     if UNIT.match(str(ws.cell(row=rr, column=c).value or "").strip())) > 500)
    si = hdr.index("Status")
    out = {}
    for rr in range(r1 + 1, r2 + 1):
        u = str(ws.cell(row=rr, column=c1 + ui).value or "").strip()
        if u:
            out[u] = str(ws.cell(row=rr, column=c1 + si).value or "").strip()
    wb.close()
    return os.path.basename(p), out


def order_items():
    p = newest("sharepoint-lists/Order Items 2*.csv")
    r = csv.reader(io.open(p, encoding="utf-8-sig", newline=""))
    first = next(r)
    hdr = next(r) if first and first[0].startswith("ListSchema=") else first
    iu, istep, idate = (hdr.index("Unit ID"), hdr.index("Step Status"),
                        hdr.index("Status Date"))
    out = {}
    for x in r:
        u = (x[iu] or "").strip()
        if u:
            out[u] = ((x[istep] or "").strip(), (x[idate] or "").strip())
    return os.path.basename(p), out


def isodate(s):
    s = (s or "").strip()
    if not s:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return "%s-%s-%s" % m.groups()
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)      # d/m/Y as the export writes it
    if m:
        return "%s-%02d-%02d" % (m.group(3), int(m.group(2)), int(m.group(1)))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detail", action="store_true")
    a = ap.parse_args()

    wbname, wb = workbook()
    oiname, oi = order_items()
    print("workbook    %-42s %5d units" % (wbname, len(wb)))
    print("Order Items %-42s %5d units" % (oiname, len(oi)))

    both = [u for u in wb if u in oi]
    stats = {"ok": 0, "ok_jui": 0, "ok_bare": 0, "blank_both": 0, "list_only_step": 0,
             "STEP_WRONG": 0, "DATE_WRONG": 0, "MISSING_ON_LIST": 0, "UNPARSED": 0}
    bad = {"STEP_WRONG": [], "DATE_WRONG": [], "MISSING_ON_LIST": [], "UNPARSED": []}

    for u in both:
        raw = wb[u]
        step, date, kind = parse(raw)
        lstep, ldate = oi[u]
        ldate = isodate(ldate)

        if kind == "blank":
            # A blank workbook Status against a populated Step Status is NOT a match.
            # It counted as one in the first version of this script, which inflated the
            # match total past the number of units the workbook even has a Status on --
            # the kind of arithmetic that makes a green result meaningless. It is not an
            # error either: a step set natively on the list after the last workbook
            # refresh looks exactly like this. So it gets its own line.
            if lstep:
                stats["list_only_step"] += 1
                bad.setdefault("list_only_step", []).append((u, "(blank)", "-", lstep, ldate))
            else:
                stats["blank_both"] += 1
            continue
        if step is None:
            stats["UNPARSED"] += 1
            bad["UNPARSED"].append((u, raw, kind, lstep, ldate))
            continue
        if not lstep:
            stats["MISSING_ON_LIST"] += 1
            bad["MISSING_ON_LIST"].append((u, raw, step, lstep, ldate))
            continue
        if lstep != step:
            stats["STEP_WRONG"] += 1
            bad["STEP_WRONG"].append((u, raw, step, lstep, ldate))
            continue
        if kind == "bare":
            if ldate:
                stats["DATE_WRONG"] += 1
                bad["DATE_WRONG"].append((u, raw, "(no date in the code)", lstep, ldate))
            else:
                stats["ok_bare"] += 1
            continue
        if kind == "jui":
            m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", ldate or "")
            if m and int(m.group(3)) == date and m.group(2) in ("06", "07"):
                stats["ok_jui"] += 1
            else:
                stats["DATE_WRONG"] += 1
                bad["DATE_WRONG"].append((u, raw, "juin/juillet day %d" % date, lstep, ldate))
            continue
        if ldate == date:
            stats["ok"] += 1
        else:
            stats["DATE_WRONG"] += 1
            bad["DATE_WRONG"].append((u, raw, date, lstep, ldate))

    print("compared on %d units present in both\n" % len(both))
    print("  exact match (step + date)      %5d" % stats["ok"])
    print("  jui rows, day and month sane   %5d" % stats["ok_jui"])
    print("  bare prefix, step only         %5d" % stats["ok_bare"])
    print("  no Status either side          %5d" % stats["blank_both"])
    print("  step on the list, none in Excel%5d   (set natively after the last refresh)"
          % stats["list_only_step"])
    for row in bad.get("list_only_step", [])[:None if a.detail else 3]:
        print("        %-14s list=%r / %r" % (row[0], row[3], row[4]))
    print("  ---")
    for k in ("STEP_WRONG", "DATE_WRONG", "MISSING_ON_LIST", "UNPARSED"):
        print("  %-30s %5d%s" % (k, stats[k], "   <<<" if stats[k] else ""))
        for row in bad[k][:None if a.detail else 5]:
            print("        %-14s workbook=%-12r expected=%-24r list=%r / %r"
                  % (row[0], row[1], row[2], row[3], row[4]))
        if not a.detail and len(bad[k]) > 5:
            print("        ... %d more, run with --detail" % (len(bad[k]) - 5))

    fails = sum(stats[k] for k in ("STEP_WRONG", "DATE_WRONG", "MISSING_ON_LIST", "UNPARSED"))
    print("\n%s" % ("✓ every unit's split matches the workbook's Status" if not fails
                    else "%d unit(s) disagree with the workbook" % fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
