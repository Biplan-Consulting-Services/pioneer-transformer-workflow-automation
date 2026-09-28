#!/usr/bin/env python3
"""Replay Nightly Sync v007's gate (stage C) and empty-row cleanup (stage D) offline.

    python scripts/replay_nightly_v007.py "<Archive active copy>.xlsx" [--oi <Order Items.csv>] [--now 2026-09-29T05:30:00Z]

"SharePoint" = the mirror's sharepoint-lists/mirror/live/Order Items.csv (raw REST shape: Location /
ItemStatus display text, Modified / Created ISO text, lookups as <Name>Id). "Archive" = the xlsx's
TableArchiveOrderItems, located through the zip's table/sheet parts and read with openpyxl read_only.
The rules are the flow's (gen_nightly_sync.py), restated here in Python:

  C1  unit Location = Livraison AND ItemStatus = Delivered
  C2  archive rows with Location = Livraison
  C4  confirmed = archive row, same Id, ItemStatus Delivered, Modified text EXACTLY equal, and the
      unit's Modified <= now - GraceDays
  D1  Title, OrderNumberId, ModelId, ClientId, ModelRevisionId, Location all empty, Created == Modified,
      Created <= now - 24 h;  cap EmptyRowCap
Read-only: never writes the workbook or the mirror.
"""
import argparse
import csv
import datetime as dt
import os
import posixpath
import re
import sys
import zipfile

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gen_nightly_sync as N  # noqa: E402  (the constants: table name, caps, grace)

OI_CSV = os.path.join(ROOT, "sharepoint-lists", "mirror", "live", "Order Items.csv")
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _rels(z, part):
    """{rId: target part path} for one part's .rels."""
    d, b = posixpath.split(part)
    rp = posixpath.join(d, "_rels", b + ".rels")
    if rp not in z.namelist():
        return {}
    x = z.read(rp).decode("utf-8", "ignore")
    out = {}
    for m in re.finditer(r"<Relationship\b[^>]*>", x):
        t = m.group(0)
        rid = re.search(r'\bId="([^"]+)"', t).group(1)
        tgt = re.search(r'\bTarget="([^"]+)"', t).group(1)
        out[rid] = posixpath.normpath(tgt.lstrip("/") if tgt.startswith("/") else posixpath.join(d, tgt))
    return out


def locate_table(path, name):
    """(sheet title, ref, [column names]) of the named table, from the zip parts."""
    z = zipfile.ZipFile(path)
    wb_rels = _rels(z, "xl/workbook.xml")
    wbx = z.read("xl/workbook.xml").decode("utf-8", "ignore")
    for m in re.finditer(r"<sheet\b[^>]*>", wbx):
        t = m.group(0)
        title = re.search(r'\bname="([^"]+)"', t).group(1)
        rid = re.search(r'\br:id="([^"]+)"', t) or re.search(r'\bid="([^"]+)"', t)
        sheet_part = wb_rels.get(rid.group(1))
        if not sheet_part:
            continue
        sx = z.read(sheet_part).decode("utf-8", "ignore")
        srels = _rels(z, sheet_part)
        for tp in re.finditer(r'<tablePart\b[^>]*\br:id="([^"]+)"', sx):
            tpart = srels.get(tp.group(1))
            if not tpart:
                continue
            tname, rows, cols = gdi_table_columns(z, tpart)
            if tname == name:
                ref = re.search(r'<table[^>]*\bref="([^"]+)"', z.read(tpart).decode("utf-8", "ignore")).group(1)
                return _unescape(title), ref, cols
    sys.exit("ABORT: no table %r in %s" % (name, path))


def _unescape(s):
    return s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")


def gdi_table_columns(z, name):
    import gen_data_inventory as GDI   # the repo's table-header parser (OOXML name decoding)
    return GDI.table_columns(z, name)


def read_table(path, name):
    title, ref, cols = locate_table(path, name)
    m = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)$", ref)
    c1, r1, c2, r2 = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
    ci = openpyxl.utils.column_index_from_string
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[title]
    rows = []
    for vals in ws.iter_rows(min_row=r1 + 1, max_row=r2, min_col=ci(c1), max_col=ci(c2), values_only=True):
        rows.append(dict(zip(cols, vals)))
    wb.close()
    return title, ref, cols, rows


def as_connector_text(v):
    """What the Excel connector would hand the flow: text. Numbers print without a trailing .0."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def norm_id(v):
    # the flow: first(split(replace(replace(string(x), ',', ''), ' ', ''), '.'))
    return as_connector_text(v).replace(",", "").replace(" ", "").split(".")[0]


def ts(s):
    return dt.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--oi", default=OI_CSV)
    ap.add_argument("--now", default=None, help="UTC ISO instant the flow runs at (default: now)")
    a = ap.parse_args()
    now = ts(a.now) if a.now else dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    grace, cap, ecap = N.GRACE_DAYS, N.CAP, N.EMPTY_ROW_CAP

    with open(a.oi, encoding="utf-8-sig", newline="") as f:
        units = list(csv.DictReader(f))
    title, ref, cols, arch = read_table(a.xlsx, N.EXCEL_TABLE_NAME)
    print("SharePoint: %s  (%d units)" % (os.path.relpath(a.oi, ROOT), len(units)))
    print("Archive   : %s  %s!%s  (%d rows, %d cols)" % (os.path.basename(a.xlsx), title, ref, len(arch), len(cols)))
    print("now (UTC) : %s   grace %d d -> unit Modified <= %s" % (now.isoformat(), grace, (now - dt.timedelta(days=grace)).isoformat()))
    for c in ("Id", "Location", "ItemStatus", "Modified", "Created", "Title"):
        if c not in cols:
            sys.exit("ABORT: TableArchiveOrderItems has no column %r" % c)
    # cell types matter: the flow compares TEXT. A real date in Modified would come off the connector
    # as a serial or reformatted, and would never equal SharePoint's ISO text (fails safe, blocks all).
    for c in ("Id", "Modified", "ItemStatus", "Location"):
        types = {}
        for r in arch:
            types[type(r[c]).__name__] = types.get(type(r[c]).__name__, 0) + 1
        print("  archive %-10s cell types: %s" % (c, types))

    # ---- stage C
    c1 = [u for u in units if u["Location"] == "Livraison" and u["ItemStatus"] == "Delivered"]
    c2 = [r for r in arch if as_connector_text(r["Location"]) == "Livraison"]
    ids = {norm_id(r["Id"]) for r in c2}
    status_keys = {"%s|%s" % (norm_id(r["Id"]), as_connector_text(r["ItemStatus"])) for r in c2}
    state_keys = {"%s|%s|%s" % (norm_id(r["Id"]), as_connector_text(r["ItemStatus"]), as_connector_text(r["Modified"])) for r in c2}
    by_id = {}
    for r in c2:
        by_id.setdefault(norm_id(r["Id"]), r)
    limit = now - dt.timedelta(days=grace)
    confirmed, held = [], []
    for u in c1:
        i = u["Id"]
        ok_row = i in ids
        ok_del = ("%s|Delivered" % i) in status_keys
        ok_cur = ("%s|Delivered|%s" % (i, u["Modified"])) in state_keys
        ok_grace = ts(u["Modified"]) <= limit
        if ok_del and ok_cur and ok_grace:
            confirmed.append(u)
        else:
            reason = ("no archive row at Livraison" if not ok_row else
                      "archive not Delivered" if not ok_del else
                      "archive older than the unit (Modified differs)" if not ok_cur else
                      "edited within %d days" % grace)
            held.append((u, reason))
    over = len(confirmed) > cap
    print("\nSTAGE C  candidates (Livraison + Delivered on SharePoint): %d" % len(c1))
    print("  archive rows at Livraison: %d" % len(c2))
    print("  CONFIRMED: %d%s" % (len(confirmed), "  -> CAP EXCEEDED (> %d), nothing would be deleted" % cap if over else ""))
    for u in sorted(confirmed, key=lambda u: u["Title"]):
        print("    %-6s %-16s Modified %s" % (u["Id"], u["Title"], u["Modified"]))
    print("  HELD BACK: %d" % len(held))
    tally = {}
    for u, why in held:
        tally[why] = tally.get(why, 0) + 1
    for why, n in sorted(tally.items(), key=lambda t: -t[1]):
        print("    %3d  %s" % (n, why))
    for u, why in sorted(held, key=lambda t: (t[1], t[0]["Title"])):
        extra = ""
        r = by_id.get(u["Id"])
        if r is not None and why.startswith("archive older"):
            extra = "  archive Modified %s" % as_connector_text(r["Modified"])
        elif r is not None and why == "archive not Delivered":
            extra = "  archive ItemStatus %s" % as_connector_text(r["ItemStatus"])
        print("    %-6s %-16s unit Modified %s  %s%s" % (u["Id"], u["Title"], u["Modified"], why, extra))

    sp_ids = {u["Id"] for u in units}
    sp_by_id = {u["Id"]: u for u in units}
    disagree = [sp_by_id[i] for i in sorted({k.split("|")[0] for k in status_keys if k.endswith("|Delivered")} & sp_ids, key=int)
                if not (sp_by_id[i]["Location"] == "Livraison" and sp_by_id[i]["ItemStatus"] == "Delivered")]
    gone = [r for r in c2 if as_connector_text(r["ItemStatus"]) == "Delivered" and norm_id(r["Id"]) not in sp_ids]
    print("  C4c archive Livraison+Delivered, SharePoint disagrees: %d" % len(disagree))
    for u in disagree:
        print("    %-6s %-16s SharePoint: %s / %s" % (u["Id"], u["Title"], u["Location"] or "(empty)", u["ItemStatus"]))
    print("  C4d archive Livraison+Delivered, unit already gone: %d" % len(gone))

    # ---- stage D
    day = now - dt.timedelta(hours=24)
    empty = lambda s: (s or "") == ""
    cand, near = [], []
    for u in units:
        blank = (empty(u["Title"]) and all(empty(u[k]) for k in ("OrderNumberId", "ModelId", "ClientId", "ModelRevisionId"))
                 and empty(u["Location"]))
        if not blank:
            continue
        if u["Created"] == u["Modified"] and ts(u["Created"]) <= day:
            cand.append(u)
        else:
            near.append(u)
    print("\nSTAGE D  empty-row candidates: %d%s" % (len(cand), "  -> CAP EXCEEDED (> %d), nothing would be recycled" % ecap
                                                       if len(cand) > ecap else ""))
    for u in cand:
        print("    would recycle %s  (Created %s)" % (u["Id"], u["Created"]))
    if near:
        print("  blank rows NOT taken (edited since creation, or younger than 24 h): %d" % len(near))
        for u in near:
            print("    %-6s Created %s  Modified %s" % (u["Id"], u["Created"], u["Modified"]))
    untitled = [u for u in units if empty(u["Title"])]
    print("  units with an empty Title at all: %d%s" % (len(untitled), "" if not untitled else " (" + ", ".join(u["Id"] for u in untitled) + ")"))


if __name__ == "__main__":
    main()
