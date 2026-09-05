# -*- coding: utf-8 -*-
"""SharePoint 'Export to CSV' puts a huge ListSchema=... line first, then the
real header, then data. Skip line 1 and parse from line 2."""
import csv, io, os, sys

BASE = r"C:\Users\solei\OneDrive\Documents\Biplan\claude\Clients\Pioneer Transformer\Workflow-Automation\sharepoint-lists"
csv.field_size_limit(10_000_000)

def load(name):
    p = name if os.path.isabs(name) else os.path.join(BASE, name)
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            raw = io.open(p, encoding=enc, newline="").read()
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit("cannot decode " + name)
    # drop the leading ListSchema=... record if present
    if raw.lstrip().startswith("ListSchema="):
        rdr = csv.reader(io.StringIO(raw))
        rows = list(rdr)
        rows = rows[1:]                      # first *record*, not first line
        if not rows:
            return []
        hdr = rows[0]
        return [dict(zip(hdr, r)) for r in rows[1:] if any(c.strip() for c in r)]
    return list(csv.DictReader(io.StringIO(raw)))

if __name__ == "__main__":
    for f in sys.argv[1:]:
        d = load(f)
        print("=== %s -> %d rows" % (f, len(d)))
        if d:
            print("   cols:", list(d[0].keys()))
