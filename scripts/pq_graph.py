# -*- coding: utf-8 -*-
"""Builds the cross-workbook data-source graph from the tracked .pq files.

Every Pioneer workbook resolves its external sources through the same helper --
ImportFromIndex(<Index list title>, <table name>) -- so the whole inter-workbook
dependency graph is recoverable by scanning for that one call, plus the direct
SharePoint.* / Web.Contents / Excel.CurrentWorkbook sources.

Run after scripts/Export-PowerQuery.ps1 has populated power-query/<workbook>/.
"""
import os, re, glob, collections

WA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(WA, "power-query")

RE_IMPORT   = re.compile(r'ImportFromIndex\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"', re.S)
RE_IMPORTV  = re.compile(r'ImportFromIndex\s*\(\s*([A-Za-z_#][^,()]*),\s*("?[^,()"]*"?)\s*\)')
RE_DEFVAL   = re.compile(r'ImportDefinedValueFromIndex\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"', re.S)
RE_SPSITE   = re.compile(r'SharePoint\.(?:Tables|Lists|Files|Contents)\s*\(\s*"([^"]+)"')
RE_WEB      = re.compile(r'Web\.Contents\s*\(\s*"([^"]+)"')
RE_LOCAL    = re.compile(r'Excel\.CurrentWorkbook\(\)\{\[Name="([^"]+)"\]\}')
RE_QNAME    = re.compile(r'^//\s*Query:\s*(.+)$')


def read_queries(folder):
    out = {}
    for f in sorted(glob.glob(os.path.join(folder, "*.pq"))):
        text = open(f, encoding="utf-8").read()
        first, _, body = text.partition("\n")
        m = RE_QNAME.match(first.strip())
        name = m.group(1).strip() if m else os.path.splitext(os.path.basename(f))[0]
        out[name] = body
    return out


def main():
    books = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)))
    if not books:
        raise SystemExit("no exported workbooks under power-query/ -- run Export-PowerQuery.ps1 first")

    edges = collections.defaultdict(set)   # workbook -> {(index title, table)}
    sites = collections.defaultdict(set)
    locals_ = collections.defaultdict(set)
    webs = collections.defaultdict(set)
    dynamic = collections.defaultdict(set)
    counts = {}

    for b in books:
        qs = read_queries(os.path.join(ROOT, b))
        counts[b] = len(qs)
        for qname, body in qs.items():
            for sheet, table in RE_IMPORT.findall(body):
                edges[b].add((sheet, table, qname))
            for sheet, table in RE_DEFVAL.findall(body):
                edges[b].add((sheet, table + "  (defined value)", qname))
            for site in RE_SPSITE.findall(body):
                sites[b].add((site, qname))
            for t in RE_LOCAL.findall(body):
                locals_[b].add(t)
            for u in RE_WEB.findall(body):
                if "://" in u:
                    webs[b].add((u, qname))
            # ImportFromIndex called with a variable rather than a literal
            for a, _t in RE_IMPORTV.findall(body):
                a = a.strip()
                if not a.startswith('"'):
                    dynamic[b].add((a, qname))

    print("=" * 78)
    print("Pioneer workbooks -- Power Query source graph")
    print("=" * 78)
    for b in books:
        print("\n### %s   (%d queries)" % (b, counts[b]))
        if sites[b]:
            for site, q in sorted(sites[b]):
                print("    SharePoint site   %s        [%s]" % (site, q))
        if edges[b]:
            print("    reads via Index:")
            for sheet, table, q in sorted(edges[b]):
                print("      %-26s %-28s [%s]" % (sheet, table, q))
        if dynamic[b]:
            print("    reads via Index, target computed at runtime:")
            for expr, q in sorted(dynamic[b]):
                print("      %-40s [%s]" % (expr[:40], q))
        if webs[b]:
            for u, q in sorted(webs[b]):
                print("    direct URL        %s   [%s]" % (u[:70], q))
        if locals_[b]:
            print("    own sheet tables: %s" % ", ".join(sorted(locals_[b])))

    print("\n" + "=" * 78)
    print("Who reads what, by Index title")
    print("=" * 78)
    by_target = collections.defaultdict(set)
    for b in books:
        for sheet, table, _q in edges[b]:
            by_target[sheet].add((b, table))
    for sheet in sorted(by_target):
        readers = collections.defaultdict(set)
        for b, table in by_target[sheet]:
            readers[b].add(table)
        print("\n  %s" % sheet)
        for b in sorted(readers):
            print("      <- %-16s %s" % (b, ", ".join(sorted(readers[b]))))


if __name__ == "__main__":
    main()
