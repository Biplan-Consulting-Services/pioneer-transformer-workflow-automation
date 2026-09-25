"""Shared helpers for the SharePoint mirror's change tracking (E10, docs/change-tracking-design-2026-09-24.md).

One place for the rules every step uses:
  - where things live (D3 layout)
  - how a snapshot is read (new gz folders, or the pre-D3 flat timestamped CSVs)
  - rows are keyed by list + Id, NEVER by Title
  - which columns change without anyone editing (excluded) and which the mirror DERIVES
    (lookup display values, *_Email, calculated columns - tagged, never restored)
"""
import csv
import datetime as dt
import glob
import gzip
import io
import json
import os
import re

def _eastern_offset_hours(local):
    """UTC offset of a naive Eastern local time: -4 in DST, -5 otherwise. US/Canada rule:
    DST from 02:00 on the 2nd Sunday of March to 02:00 on the 1st Sunday of November.
    Hand-rolled because Windows Python ships no tz database (no tzdata dependency)."""
    y = local.year

    def nth_sunday(month, n):
        d = dt.datetime(y, month, 1)
        first = d + dt.timedelta(days=(6 - d.weekday()) % 7)
        return first + dt.timedelta(weeks=n - 1)
    start = nth_sunday(3, 2).replace(hour=2)
    end = nth_sunday(11, 1).replace(hour=2)
    return -4 if start <= local < end else -5

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIRROR = os.path.join(ROOT, "sharepoint-lists", "mirror")
LIVE = os.path.join(MIRROR, "live")
SNAPSHOTS = os.path.join(MIRROR, "snapshots")
JOURNAL = os.path.join(MIRROR, "journal")
HEALTH = os.path.join(MIRROR, "health")

# The real lists. `Columns` is the schema catalog; diagnostics (Order via SharePointTables,
# Lists, VersionCounts, VersionProbe) are never journaled.
LISTS = ["Order Items", "Order", "Models", "Model Revisions", "Clients", "Index", "Models SA"]
CATALOG = "Columns"

# Change without anyone editing the row's data. Never journaled.
VOLATILE = {"Modified", "EditorId", "Editor_Email", "OData__UIVersionString", "odata.etag",
            "GUID", "ContentVersion", "SMLastModifiedDate", "SMTotalSize"}

csv.field_size_limit(10_000_000)


# ---------------------------------------------------------------- reading tables
def _read_csv_text(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    return rows


def read_table(path):
    """A mirror CSV (.csv or .csv.gz) -> list of dicts. Zero rows is a failed read."""
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as f:
            rows = _read_csv_text(f.read())
    else:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = _read_csv_text(f.read())
    if not rows:
        raise SystemExit("ABORT: read 0 rows from %s. A zero-row read is a failed read." % path)
    return rows


def _as_utc(local_stamp):
    """'2026-09-24 2222' (Eastern, as the refresh names files) -> '2026-09-25T02:22Z'."""
    t = dt.datetime.strptime(local_stamp, "%Y-%m-%d %H%M")
    return (t - dt.timedelta(hours=_eastern_offset_hours(t))).strftime("%Y-%m-%dT%H:%MZ")


class Snapshot:
    """A set of mirror tables taken by one refresh.

    spec is either
      - a snapshot folder (D3):  sharepoint-lists/mirror/snapshots/2026-09-25_0130/  (+ snapshot.json)
      - 'legacy:2026-09-24 2222' : the pre-D3 flat files "<Table> 2026-09-24 2222.csv", found in
        mirror/ or mirror/Archive/
    """

    def __init__(self, spec):
        self.spec = spec
        self.files = {}
        if spec.startswith("legacy:"):
            stamp = spec[len("legacy:"):]
            self.as_of = _as_utc(stamp)
            for d in (MIRROR, os.path.join(MIRROR, "Archive")):
                for p in glob.glob(os.path.join(d, "* %s.csv" % stamp)):
                    name = os.path.basename(p)[: -len(" %s.csv" % stamp)]
                    self.files.setdefault(name, p)
        else:
            folder = spec
            meta = os.path.join(folder, "snapshot.json")
            if not os.path.exists(meta):
                raise SystemExit("ABORT: %s has no snapshot.json" % folder)
            with open(meta, encoding="utf-8-sig") as f:   # PS 5.1 writes a BOM
                self.meta = json.load(f)
            self.as_of = self.meta["asOf"]
            for p in glob.glob(os.path.join(folder, "*.csv.gz")):
                self.files[os.path.basename(p)[: -len(".csv.gz")]] = p
        if not self.files:
            raise SystemExit("ABORT: snapshot %r holds no tables" % spec)
        self._cache = {}

    def has(self, table):
        return table in self.files

    def table(self, table):
        if table not in self._cache:
            if table not in self.files:
                raise SystemExit("ABORT: snapshot %r has no %r table" % (self.spec, table))
            self._cache[table] = read_table(self.files[table])
        return self._cache[table]

    def by_id(self, table):
        out = {}
        for r in self.table(table):
            k = key(r)
            if k is None:
                raise SystemExit("ABORT: a %s row has no Id - cannot key it (never key by Title)" % table)
            if k in out:
                raise SystemExit("ABORT: duplicate Id %s in %s" % (k, table))
            out[k] = r
        return out


def snapshots_sorted():
    """D3 snapshot folders, oldest first."""
    if not os.path.isdir(SNAPSHOTS):
        return []
    dirs = [os.path.join(SNAPSHOTS, d) for d in os.listdir(SNAPSHOTS)
            if re.match(r"^\d{4}-\d{2}-\d{2}_\d{4}$", d) and os.path.exists(os.path.join(SNAPSHOTS, d, "snapshot.json"))]
    return sorted(dirs)


def key(row):
    """Id as an int string. Excel hands numbers back as '126' or '126.0'."""
    v = (row.get("Id") or "").strip()
    if not v:
        return None
    try:
        return str(int(float(v)))
    except ValueError:
        return v


def norm(v):
    """Compare values the way they are stored: '' == missing, '28' == '28.0'."""
    if v is None:
        return ""
    s = str(v)
    if re.fullmatch(r"-?\d+\.0", s):
        s = s[:-2]
    return s


# ---------------------------------------------------------------- the catalog
class Catalog:
    """What each column IS, from the Columns table of a snapshot."""

    def __init__(self, snap):
        self.rows = snap.table(CATALOG) if snap.has(CATALOG) else []
        self.by = {(r["list"], r["internalName"]): r for r in self.rows}
        # E8c: the CSV column that holds each field. Usually the internal name; for a lookup its
        # id column, which Excel may have renamed (Model Revisions: REST `ModelId` -> CSV `ModelId2`,
        # because `ModelID` exists and Excel names are case-insensitive).
        self.by_csv = {}
        for r in self.rows:
            csvc = (r.get("csvColumn") or "").strip()
            if csvc:
                self.by_csv[(r["list"], csvc)] = (r.get("restField") or r["internalName"]).strip()

    def col(self, lst, name):
        return self.by.get((lst, name))

    def rest_field(self, lst, csv_col):
        """The name REST / flows / x27 use for a mirror CSV column (ModelId2 -> ModelId)."""
        return self.by_csv.get((lst, csv_col), csv_col)

    def id_column(self, lst, lookup_name):
        """The mirror CSV column holding a lookup's id (Model -> ModelId2 on Model Revisions)."""
        c = self.col(lst, lookup_name)
        v = ((c or {}).get("idColumn") or "").strip()
        return v or lookup_name + "Id"

    def kind(self, lst, name):
        """'real' (journal + restorable), 'derived' (journal, tagged, never restored)."""
        if (lst, name) in self.by_csv and self.by_csv[(lst, name)] != name:
            return "real"             # a renamed id column (ModelId2): the writable lookup id
        c = self.col(lst, name)
        if name.endswith("_Email") and self.col(lst, name[: -len("_Email")]) is not None:
            return "derived"          # mirror-added: <Person>_Email
        if c is not None:
            t = c.get("type", "")
            if t.startswith("lookup") or t.startswith("personOrGroup"):
                return "derived"      # mirror-added display value; the real field is <name>Id
            if t.startswith("calculated"):
                return "derived"      # recomputed by SharePoint, not edited
            return "real"
        if name.endswith("Id") and self.col(lst, name[:-2]) is not None:
            return "real"             # <Lookup>Id / <Person>Id - the writable id
        return "real"

    def synced(self, lst, name):
        c = self.col(lst, name)
        if c and (c.get("syncedByFlow") or "").strip():
            return {"list": c["syncedFromList"], "field": c["syncedFromField"],
                    "fk": c["viaLookup"], "flow": c["syncedByFlow"]}
        return None

    def type(self, lst, name):
        rest = self.rest_field(lst, name)
        if rest != name and rest.endswith("Id"):
            return "lookupId"
        c = self.col(lst, name)
        if c is None and name.endswith("Id") and self.col(lst, name[:-2]) is not None:
            return "lookupId"
        return (c or {}).get("type", "")


def month_file(as_of):
    return os.path.join(JOURNAL, as_of[:7] + ".jsonl")


def read_journal(month=None):
    files = sorted(glob.glob(os.path.join(JOURNAL, "*.jsonl")))
    if month:
        files = [f for f in files if os.path.basename(f).startswith(month)]
    out = []
    for f in files:
        with open(f, encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    return out
