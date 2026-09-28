#!/usr/bin/env python3
"""Static checks for the viewer-free `Archive FRM10-12` query set (power-query/Archive-active/).

    python scripts/check_frm1012_map.py                 # map + joins + catalog + viewer + vocab
    python scripts/check_frm1012_map.py --base <xlsx>   # also: archived values fit the map Types
    python scripts/check_frm1012_map.py --no-base       # skip the value check

The single source is ArchiveFrm1012Map.pq itself (no sidecar CSV): this script parses its
records with a strict one-record-per-line regex and refuses a line it cannot parse, so the
file cannot quietly hold a row the checks never saw. Joins are parsed from
ArchiveFrm1012Joined.pq the same way.

What must hold (each failure aborts with SystemExit, see test_check_frm1012_map.py):
  shape    exactly the 111 pinned names, in order (the 93 of TableArchiveFRM10_12 as of
           2026-09-27 23:56, then TableArchiveBO's 18 BO detail names); positions 1..111
  source   every SourceField / Arg ref / join key exists for its list in the LIVE mirror catalog
           (sharepoint-lists/mirror/live/Columns.csv); none is a sync copy (syncedFromList) or a
           *_TextField mirror; nothing on Order Items is an Ord*/Rev*/Mdl*/Cli* copy; each join's
           child key is a lookup INTO its parent list
  viewer   Basis "viewer" rows agree with FRM10-12/viewer/power-query/ColumnMap.pq (entity + the
           display name resolved to the internal name) and ValueConversions.pq (rule + arg); every
           ValueConversions row for a pinned column is carried by the map
  vocab    LocationCodes.pq / StatusStampCodes.pq here are byte-for-byte the viewer's files
           under their two header lines
  --base   every value in the archive's TableArchiveFRM10_12 (and TableArchiveBO for `bo`
           rows) converts under the map Type, for the real types (text/datetext/numtext accept
           anything); and the workbook's 93 headers equal the pinned 93
"""
import argparse
import csv
import datetime
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CLIENT = os.path.dirname(ROOT)
PQ = os.path.join(ROOT, "power-query", "Archive-active")
MAP_PQ = os.path.join(PQ, "ArchiveFrm1012Map.pq")
JOINED_PQ = os.path.join(PQ, "ArchiveFrm1012Joined.pq")
COLUMNS = os.path.join(ROOT, "sharepoint-lists", "mirror", "live", "Columns.csv")
VIEWER = os.path.join(CLIENT, "FRM10-12", "viewer", "power-query")
VOCABS = ("LocationCodes", "StatusStampCodes")
DEFAULT_BASE = os.path.join(ROOT, "workbooks", "Archive active 2026-09-27 2356.xlsx")

PINNED_93 = [
    "Order", "Client", "KVA and KV", "Primary Voltage", "Secondary Voltage", "Phases", "JS #",
    "Description", "Type", "PO", "Order Date", "Lead Time", "Ing. Due Date", "Qty", "PO Item #",
    "Family", "Duplicate", "Engineering Required", "Duplicate Order", "Price", "Province/State",
    "WET-WETP", "Indexing", "LDs", "Initial Promised Date", "Trimestrial Customer",
    "Client Date Status", "Info+", "Protector Status", "Protector & Switchgear PO",
    "Protector & Switchgear Item #", "Sales Notes", "Technical Notes", "Location", "Status",
    "Witness/Other", "Temperature Rise", "Impulse", "DB", "Partial D", "Oil Analysis", "SFRA", "CSA",
    "Core", "Core Status", "Oil Type", "Oil Amount", "Production Line", "Configuration",
    "Section Qty", "Cable", "Coil Winder", "Form", "Copper (LV)", "Wire (HV)", "Overcoil", "Winder",
    "Time (days)", "Tank", "Tank Delivery Date", "Frame", "ISO Stack", "ISO Coil", "Lead Assembly",
    "Coiling Date", "Stacking Date", "Assembly Date", "Drying Date", "Tanking Date", "Testing Date",
    "Finishing Date", "Delivery Date", "Original Tanking Date", "Estimated Delivery Date",
    "Tanking date change justification", "Manual Estimated Delivery Date", "BO", "Price Value",
    "Price CAD", "Price USD", "Navigation Order", "Navigation Model", "Archived", "Lot",
    "Tanking Date Status", "Planning Notes", "Production Complexity", "__PowerAppsId__",
    "Client Desired Date", "FI", "Stack", "Production Status", "Last Synchronisation Date",
]
BO_18 = ["BO%d %s" % (n, s) for n in (1, 2, 3)
         for s in ("Part Numbre", "Description", "PO Intern", "Date", "Fournisseur Interne", "OK")]
PINNED = PINNED_93 + BO_18

SOURCE_LISTS = ("Order Items", "Order", "Model Revisions", "Clients", "Models")
RULES_SOURCED = {"copy", "multichoice", "marker", "yn", "loccode", "ec", "default", "bo"}
RULES_COMPUTED = {"status", "ingdue", "navorder", "navmodel"}
RULES_REF = {"ec"} | RULES_COMPUTED          # rules whose Arg holds field refs
TYPES = {"text", "number", "date", "logical", "datetext", "numtext"}
STRICT_TYPES = {"number", "date", "logical"}
VIEWER_ENTITY = {"Orders": "Order", "Model Revisions": "Model Revisions", "Order Items": "Order Items"}
COPY_PREFIX = re.compile(r"^(Ord|Rev|Mdl|Cli)[A-Z]")

S = r'"((?:[^"]|"")*)"'
MAP_ROW = re.compile(
    r'^\s*\[Position = (\d+), TargetColumn = ' + S + r', SourceList = ' + S + r', SourceField = ' + S
    + r', Rule = ' + S + r', Arg = (null|' + S + r'), Type = ' + S + r', Basis = ' + S + r'\],?\s*$')
JOIN_ROW = re.compile(r'\[Child = ' + S + r',\s*ChildKey = ' + S + r',\s*Parent = ' + S + r',\s*ParentKey = ' + S + r'\]')
VCM_ROW = re.compile(r'\[Entity = ' + S + r', SourceField = ' + S + r', WorkbookField = ' + S + r', Type = ' + S)
VVC_ROW = re.compile(r'\[Entity = ' + S + r',\s*WorkbookField = ' + S + r',\s*Convert = ' + S + r',\s*Arg = (null|' + S + r')\]')


def fail(msg):
    raise SystemExit("check_frm1012_map: " + msg)


def unq(s):
    return None if s is None else s.replace('""', '"')


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- loaders
def parse_map(text):
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        if not line.lstrip().startswith("[Position"):
            continue
        m = MAP_ROW.match(line)
        if not m:
            fail("ArchiveFrm1012Map.pq line %d is a map record the checker cannot parse "
                 "(keep one record per line, fields in the documented order): %s" % (i, line.strip()[:120]))
        g = m.groups()
        rows.append({"Position": int(g[0]), "TargetColumn": unq(g[1]), "SourceList": unq(g[2]),
                     "SourceField": unq(g[3]), "Rule": unq(g[4]),
                     "Arg": None if g[5] == "null" else unq(g[6]),
                     "Type": unq(g[7]), "Basis": unq(g[8]), "line": i})
    return rows


def parse_joins(text):
    return [{"Child": unq(a), "ChildKey": unq(b), "Parent": unq(c), "ParentKey": unq(d)}
            for a, b, c, d in JOIN_ROW.findall(text)]


def load_columns(path=COLUMNS):
    if not os.path.exists(path):
        fail("%s missing - refresh the mirror (scripts/Refresh-SharePointMirror.ps1)" % path)
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_viewer():
    cm = [dict(zip(("Entity", "SourceField", "WorkbookField", "Type"), map(unq, r)))
          for r in VCM_ROW.findall(read(os.path.join(VIEWER, "ColumnMap.pq")))]
    vc = [{"Entity": unq(a), "WorkbookField": unq(b), "Convert": unq(c), "Arg": None if d == "null" else unq(e)}
          for a, b, c, d, e in VVC_ROW.findall(read(os.path.join(VIEWER, "ValueConversions.pq")))]
    if len(cm) < 40 or len(vc) < 13:
        fail("viewer ColumnMap/ValueConversions parsed to %d/%d rows - the regex no longer fits the files" % (len(cm), len(vc)))
    return cm, vc


def load_vocabs():
    """{name: (archive copy text, viewer text)}"""
    return {q: (read(os.path.join(PQ, q + ".pq")), read(os.path.join(VIEWER, q + ".pq"))) for q in VOCABS}


def load_all():
    return {"map": parse_map(read(MAP_PQ)), "joins": parse_joins(read(JOINED_PQ)),
            "cols": load_columns(), "viewer": load_viewer(), "vocabs": load_vocabs()}


# ---------------------------------------------------------------- checks
def catalog(cols):
    """{list: {name: row}} keyed by BOTH internalName and restField (lookups: <Name>Id)."""
    out = {}
    for r in cols:
        d = out.setdefault(r["list"], {})
        d[r["internalName"]] = r
        if r.get("restField"):
            d.setdefault(r["restField"], r)
    return out


def check_field(cat, lst, field, where):
    if lst not in cat:
        fail("%s: list %r is not in the mirror catalog" % (where, lst))
    if field == "Id":                     # ArchiveTyped's item id (catalog: ID)
        return
    r = cat[lst].get(field)
    if r is None:
        fail("%s: %s.%s does not exist in the live catalog (Columns.csv)" % (where, lst, field))
    if r.get("syncedFromList"):
        fail("%s: %s.%s is a sync COPY of %s.%s - read the parent list instead"
             % (where, lst, field, r["syncedFromList"], r.get("syncedFromField") or "?"))
    if "_TextFiel" in field or "_TextFiel" in r["internalName"]:
        fail("%s: %s.%s is a *_TextField mirror (stale by design) - read the lookup's own list" % (where, lst, field))
    if lst == "Order Items" and COPY_PREFIX.match(r["internalName"]):
        fail("%s: Order Items.%s is an Ord*/Rev*/Mdl*/Cli* copy column - read the parent list instead" % (where, field))


def check_vocab(vocabs):
    for q, (mine, theirs) in vocabs.items():
        lines = mine.replace("\r\n", "\n").split("\n")
        if not lines[0].startswith("// Query: " + q):
            fail("%s.pq: first line must be '// Query: %s'" % (q, q))
        body = "\n".join(lines[2:])
        if body != theirs.replace("\r\n", "\n"):
            fail("%s.pq has DRIFTED from FRM10-12/viewer/power-query/%s.pq - re-copy it verbatim" % (q, q))


def checks(data):
    rows, joins, cols = data["map"], data["joins"], data["cols"]
    vcm, vvc = data["viewer"]
    cat = catalog(cols)

    # ---- shape
    names = [r["TargetColumn"] for r in rows]
    if len(names) != len(set(names)):
        fail("duplicate TargetColumn(s): %s" % sorted({n for n in names if names.count(n) > 1}))
    if names != PINNED:
        missing = [n for n in PINNED if n not in names]
        extra = [n for n in names if n not in PINNED]
        if missing or extra:
            fail("map is not the pinned list: missing %s, extra %s" % (missing, extra))
        first = next(i for i, (a, b) in enumerate(zip(names, PINNED)) if a != b)
        fail("map columns are REORDERED: position %d is %r, pinned has %r" % (first + 1, names[first], PINNED[first]))
    if [r["Position"] for r in rows] != list(range(1, len(PINNED) + 1)):
        fail("Position must run 1..%d in file order" % len(PINNED))

    by_target = {r["TargetColumn"]: r for r in rows}
    for r in rows:
        where = "map row %d (%s)" % (r["Position"], r["TargetColumn"])
        rule, lst, typ = r["Rule"], r["SourceList"], r["Type"]
        if typ not in TYPES:
            fail("%s: unknown Type %r" % (where, typ))
        if rule in RULES_SOURCED:
            if lst not in SOURCE_LISTS:
                fail("%s: rule %s needs a real SourceList, got %r" % (where, rule, lst))
            check_field(cat, lst, r["SourceField"], where)
        elif rule in RULES_COMPUTED:
            if (lst, r["SourceField"]) != ("computed", "computed"):
                fail("%s: computed rule %s must have SourceList/SourceField 'computed'" % (where, rule))
        elif rule in ("legacy", "archive"):
            if (lst, r["SourceField"]) != (rule, rule):
                fail("%s: rule %s must have SourceList/SourceField %r" % (where, rule, rule))
        else:
            fail("%s: unknown Rule %r" % (where, rule))
        if rule == "marker" and (r["Arg"] is None or len(r["Arg"]) != 1):
            fail("%s: marker needs a one-letter Arg" % where)
        if rule == "default":
            try:
                float(r["Arg"])
            except (TypeError, ValueError):
                fail("%s: default needs a numeric Arg, got %r" % (where, r["Arg"]))
        if rule in RULES_REF:
            if not r["Arg"]:
                fail("%s: rule %s needs field refs in Arg" % (where, rule))
            for tok in r["Arg"].split(";"):
                src = next((l for l in SOURCE_LISTS if tok.startswith(l + ".")), None)
                if src:
                    check_field(cat, src, tok[len(src) + 1:], where + " Arg")
                elif tok not in by_target:
                    fail("%s: Arg ref %r is neither <List>.<field> nor a TargetColumn" % (where, tok))
                elif by_target[tok]["Rule"] in RULES_COMPUTED:
                    fail("%s: Arg ref %r is itself computed (phase 2 cannot read phase 2)" % (where, tok))
                if rule == "ec" and not src:
                    fail("%s: ec Arg must be the stage's status field" % where)
    bo_targets = {r["TargetColumn"] for r in rows if r["Rule"] == "bo"}
    if bo_targets != set(BO_18) | {"BO"}:
        fail("rule 'bo' must cover exactly BO + the 18 BO detail columns; got %s" % sorted(bo_targets ^ (set(BO_18) | {"BO"})))

    # ---- joins
    if not joins:
        fail("no Joins parsed from ArchiveFrm1012Joined.pq")
    for j in joins:
        where = "join %s.%s -> %s.%s" % (j["Child"], j["ChildKey"], j["Parent"], j["ParentKey"])
        check_field(cat, j["Child"], j["ChildKey"], where)
        if j["ParentKey"] != "Id":
            fail("%s: parent key must be the item Id" % where)
        ck = cat[j["Child"]][j["ChildKey"]]
        if ck.get("type") != "lookup" or ck.get("lookupList") != j["Parent"]:
            fail("%s: %s is not a lookup into %s (catalog: type %s, lookupList %r)"
                 % (where, j["ChildKey"], j["Parent"], ck.get("type"), ck.get("lookupList")))
    reached = {"Order Items"} | {j["Parent"] for j in joins}
    for r in rows:
        if r["SourceList"] in SOURCE_LISTS and r["SourceList"] not in reached:
            fail("map row %d reads %s, which no join reaches" % (r["Position"], r["SourceList"]))

    # ---- viewer agreement
    for r in rows:
        if r["Basis"] != "viewer":
            continue
        where = "map row %d (%s, Basis viewer)" % (r["Position"], r["TargetColumn"])
        hits = [v for v in vcm if v["WorkbookField"] == r["TargetColumn"] and v["Entity"] in VIEWER_ENTITY]
        if len(hits) != 1:
            fail("%s: viewer ColumnMap has %d rows for this column" % (where, len(hits)))
        v = hits[0]
        if VIEWER_ENTITY[v["Entity"]] != r["SourceList"]:
            fail("%s: viewer reads it from %s, map from %s" % (where, v["Entity"], r["SourceList"]))
        internals = {c["internalName"] for c in cols if c["list"] == r["SourceList"] and c["displayName"] == v["SourceField"]}
        if r["SourceField"] not in internals:
            fail("%s: viewer's %r resolves to %s in the catalog, map says %r"
                 % (where, v["SourceField"], sorted(internals) or "nothing", r["SourceField"]))
    conv_rules = {"marker", "yn", "loccode"}
    for r in rows:
        vc = [c for c in vvc if c["WorkbookField"] == r["TargetColumn"]]
        if r["Rule"] in conv_rules and not vc:
            fail("map row %d (%s): rule %s has no ValueConversions row in the viewer" % (r["Position"], r["TargetColumn"], r["Rule"]))
    for c in vvc:
        r = by_target.get(c["WorkbookField"])
        if r is None:
            continue
        if (r["Rule"], r["Arg"] if r["Rule"] == "marker" else None) != (c["Convert"], c["Arg"]):
            fail("map row %d (%s): viewer ValueConversions says %s/%r, map says %s/%r"
                 % (r["Position"], r["TargetColumn"], c["Convert"], c["Arg"], r["Rule"], r["Arg"]))

    # ---- vocab copies
    check_vocab(data["vocabs"])
    return rows


# ---------------------------------------------------------------- --base: archived values fit the Types
ISO = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}([T ].*)?$")
US = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}( .*)?$")
NUM = re.compile(r"^-?\d+([.,]\d+)?$")


def converts(v, typ):
    """Mirror of the M normalisers in `Archive FRM10-12` for the real types."""
    if v is None or (isinstance(v, str) and v.strip() == "") or typ not in STRICT_TYPES:
        return True
    if typ == "date":
        return isinstance(v, (datetime.date, datetime.datetime)) or (
            isinstance(v, (int, float)) and not isinstance(v, bool)) or (
            isinstance(v, str) and bool(ISO.match(v.strip()) or US.match(v.strip())))
    if typ == "number":
        return (isinstance(v, (int, float)) and not isinstance(v, bool)) or (isinstance(v, str) and bool(NUM.match(v.strip())))
    if typ == "logical":
        return isinstance(v, bool) or (isinstance(v, str) and v.strip().upper() in ("TRUE", "FALSE"))
    return True


def table_header(z, table):
    for n in z.namelist():
        if re.match(r"xl/tables/table\d+\.xml$", n):
            x = z.read(n).decode("utf-8", "ignore")
            if re.search(r'<table[^>]*\bname="%s"' % table, x):
                return [c.replace("&amp;", "&") for c in re.findall(r'<tableColumn[^>]*\bname="([^"]*)"', x)]
    return None


def sheet_values(wb, header_first):
    for ws in wb.worksheets:
        it = ws.iter_rows(values_only=True)
        first = next(it, None)
        if first and first[0] == header_first[0] and list(first[:len(header_first)]) == header_first:
            return first, list(it)
    return None, None


def base_values(path):
    """{table: (header, rows)} for the two tables the value check reads."""
    import openpyxl
    z = zipfile.ZipFile(path)
    wb = openpyxl.load_workbook(path, read_only=True)
    out = {}
    for t in ("TableArchiveFRM10_12", "TableArchiveBO"):
        h = table_header(z, t)
        if h is None:
            out[t] = (None, [])
            continue
        _, rows = sheet_values(wb, h)
        out[t] = (h, rows or [])
    return out


def check_base(rows, base):
    h, data = base["TableArchiveFRM10_12"]
    if h is None:
        fail("--base: no TableArchiveFRM10_12 in the workbook")
    if h[:93] != PINNED_93:
        fail("--base: the workbook's TableArchiveFRM10_12 headers differ from the pinned 93")
    bad = []
    tables = [("TableArchiveFRM10_12",) + base["TableArchiveFRM10_12"]]
    if base["TableArchiveBO"][0]:
        tables.append(("TableArchiveBO",) + base["TableArchiveBO"])
    for r in rows:
        if r["Type"] not in STRICT_TYPES:
            continue
        for tname, hdr, vals in tables:
            if r["TargetColumn"] not in hdr or (tname == "TableArchiveBO" and r["Rule"] != "bo"):
                continue
            i = hdr.index(r["TargetColumn"])
            wrong = [v for v in (row[i] for row in vals) if not converts(v, r["Type"])]
            if wrong:
                bad.append("%s.%s as %s: %d value(s) e.g. %r" % (tname, r["TargetColumn"], r["Type"], len(wrong), wrong[:3]))
    if bad:
        fail("--base: archived values that the map Type would turn into errors - make the column "
             "datetext/numtext/text instead:\n  " + "\n  ".join(bad))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--no-base", action="store_true")
    a = ap.parse_args()
    data = load_all()
    rows = checks(data)
    by = {}
    for r in rows:
        by.setdefault(r["SourceList"], 0)
        by[r["SourceList"]] += 1
    print("map: %d pinned columns OK; sources %s; %d joins OK; viewer ColumnMap/ValueConversions agree; vocab copies identical"
          % (len(rows), ", ".join("%s %d" % kv for kv in sorted(by.items())), len(data["joins"])))
    if not a.no_base:
        if not os.path.exists(a.base):
            fail("--base %s not found (pass --no-base to skip the value check)" % a.base)
        check_base(rows, base_values(a.base))
        print("base: every archived value fits its map Type (%s)" % os.path.basename(a.base))
    print("ALL CHECKS PASS")


if __name__ == "__main__":
    main()
