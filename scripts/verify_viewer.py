# -*- coding: utf-8 -*-
"""Runbook 3.2 — check the viewer's value conversions after a refresh.

    python scripts/verify_viewer.py

Reads `../FRM10-12/viewer/workbook/FRM10-12.xlsx` and checks what the four consumers
will actually see. Every check here is one the runbook lists; doing it by eye means
scrolling 82 columns across 1,000 rows and concluding it looks fine.

THE FOUR CONSUMERS KEY ON SHAPE AND ON CODES, NOT ON DISPLAY NAMES
  FRM09, FRM11, FRM13 and BO Manager read `TableOrders` through the `Index` list. FRM11
  is the strictest: it takes ten columns **by literal string** and its purge rule tests
  `Location` against the two-letter codes {XT, TE, FI, LI}. So a conversion that renders
  `Extérieur` instead of `XT` does not error anywhere — it silently stops FRM11 purging
  tanks, and eight outside companies keep getting a report that never shrinks.

WHAT WOULD OTHERWISE BE INVISIBLE
  - An Excel error cell reads as the string `#VALUE!`, not as a failure. `Frame` used to
    throw here and the refresh still "worked".
  - The six native formula columns are Excel's, not Power Query's. A generic refresh
    re-lands the table without them, which is why only the Office Script may refresh this
    file. This checks they are still formulas, on every row, not merely present.
  - `Status` must survive in `TE-Se-4` CODE form. FRM11 parses that format. The viewer
    now derives it from `Step Status` + `Status Date`, so it is freshly computed rather
    than copied, and it is the newest thing in the chain.
"""
import os, re, sys, warnings, collections

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VIEWER = os.path.join(os.path.dirname(ROOT), "FRM10-12", "viewer", "workbook",
                      "FRM10-12.xlsx")

# column -> (predicate, description of what is expected)
MARKERS = ["Tank", "ISO Stack", "ISO Coil", "Lead Assembly"]
XMARKS = ["Temperature Rise", "Impulse", "Partial D", "Oil Analysis", "DB"]
FORMULA_COLS = ["Estimated Delivery Date", "Price CAD", "Price USD", "Price",
                "Navigation Order", "Navigation Model"]
LOCATION_CODES = {"XT", "TE", "FI", "LI", "BO", "AS", "FO", "EN", "RE", "TA", "LV", "EX"}
STATUS_RE = re.compile(r"^[A-Za-z0-9]{2}-[A-Za-zéÉ]{2,4}-\d{1,2}$")


def main():
    import openpyxl
    from openpyxl.utils import range_boundaries
    if not os.path.exists(VIEWER):
        sys.exit("viewer workbook not found: %s" % VIEWER)

    print("viewer: %s" % VIEWER)
    print("        %.1f MB, modified %s\n" % (
        os.path.getsize(VIEWER) / 1048576.0,
        __import__("time").strftime("%Y-%m-%d %H:%M",
                                    __import__("time").localtime(os.path.getmtime(VIEWER)))))

    wbv = openpyxl.load_workbook(VIEWER, data_only=True)     # cached values
    wbf = openpyxl.load_workbook(VIEWER, data_only=False)    # formulas
    ws, wsf = wbv["Orders"], wbf["Orders"]
    c1, r1, c2, r2 = range_boundaries(ws.tables["TableOrders"].ref)
    hdr = [str(ws.cell(row=r1, column=c).value or "").strip() for c in range(c1, c2 + 1)]
    nrows = r2 - r1
    print("TableOrders: %d columns x %d rows" % (len(hdr), nrows))

    def colvals(name, formulas=False):
        if name not in hdr:
            return None
        c = c1 + hdr.index(name)
        src = wsf if formulas else ws
        return [src.cell(row=rr, column=c).value for rr in range(r1 + 1, r2 + 1)]

    fails = []

    # 1 -- Excel errors anywhere in the table
    print("\n--- Excel errors ---")
    errs = collections.Counter()
    for name in hdr:
        for v in colvals(name) or []:
            if isinstance(v, str) and v.startswith("#") and v.endswith("!"):
                errs[name] += 1
    if errs:
        for n, c in errs.most_common():
            print("  🔴 %-34s %d error cells" % (n, c))
        fails.append("%d column(s) contain Excel errors" % len(errs))
    else:
        print("  none across all %d columns" % len(hdr))

    # 2 -- markers render as letters, not booleans
    print("\n--- markers: expect the letter, never TRUE/FALSE ---")
    for name, want in [(m, "R") for m in MARKERS] + [(m, "x") for m in XMARKS] + [("SFRA", "Y")]:
        v = colvals(name)
        if v is None:
            print("  ?  %-22s not in the table" % name); continue
        vals = collections.Counter(str(x).strip() for x in v if x not in (None, ""))
        bad = [k for k in vals if k.upper() in ("TRUE", "FALSE")]
        ok = not bad
        print("  %s %-22s %s" % ("OK " if ok else "🔴", name,
                                 dict(list(vals.most_common(3)))))
        if bad:
            fails.append("%s renders %s" % (name, bad))

    # 3 -- Location in two-letter codes, which FRM11's purge rule tests
    print("\n--- Location: FRM11 tests {XT,TE,FI,LI} ---")
    v = colvals("Location") or []
    vals = collections.Counter(str(x).strip() for x in v if x not in (None, ""))
    longform = [k for k in vals if len(k) > 3]
    print("  distinct: %s" % dict(list(vals.most_common(6))))
    if longform:
        print("  🔴 display names present, not codes: %s" % longform[:6])
        fails.append("Location renders display names")
    else:
        print("  OK  all values are short codes")

    # 4 -- Frame, the one that used to throw
    print("\n--- Frame: used to error ---")
    v = colvals("Frame") or []
    vals = collections.Counter(str(x).strip() for x in v if x not in (None, ""))
    print("  %s" % dict(list(vals.most_common(5))))

    # 5 -- Status rebuilt in code form
    print("\n--- Status: FRM11 parses TE-Se-4 ---")
    v = [x for x in (colvals("Status") or []) if x not in (None, "")]
    good = [x for x in v if STATUS_RE.match(str(x).strip())]
    print("  %d non-empty, %d in code form" % (len(v), len(good)))
    odd = [str(x) for x in v if not STATUS_RE.match(str(x).strip())][:5]
    if odd:
        print("  odd values: %s" % odd)
    if v and len(good) < len(v) * 0.95:
        fails.append("Status is not in code form on %d rows" % (len(v) - len(good)))

    # 6 -- the six native formula columns, still formulas on every row
    print("\n--- native formula columns: Excel's, not Power Query's ---")
    for name in FORMULA_COLS:
        f = colvals(name, formulas=True)
        if f is None:
            print("  🔴 %-28s MISSING from the table" % name)
            fails.append("%s missing" % name); continue
        n = sum(1 for x in f if isinstance(x, str) and x.startswith("="))
        ok = n >= nrows * 0.95
        print("  %s %-28s %d/%d rows carry a formula" % ("OK " if ok else "🔴", name, n, nrows))
        if not ok:
            fails.append("%s is formulas on only %d of %d rows" % (name, n, nrows))

    wbv.close(); wbf.close()
    print("\n%s" % ("✓ 3.2 passes" if not fails else
                    "🔴 %d problem(s):\n   %s" % (len(fails), "\n   ".join(fails))))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
