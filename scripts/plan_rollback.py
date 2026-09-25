#!/usr/bin/env python3
"""E10 Layer C2 - turn journal events into a RESTORE PLAN for x27_restore.js. Writes nothing to SharePoint.

    python scripts/plan_rollback.py --as-of 2026-09-25T03:11Z --list "Order Items" --field MdlLatestModelRevision
    python scripts/plan_rollback.py --from 2026-09-25T02:00Z --to 2026-09-25T04:00Z --list Order --editor someone@x
    python scripts/plan_rollback.py --list "Order Items" --ids 126,127 --field Location --out plan.json

Each entry: {list, id, title, field, expect, restore, type}
  expect  = what the journal says the row holds NOW (the value being undone)
  restore = the value BEFORE
x27 is compare-and-set: it writes `restore` only where the row still holds `expect`, so a later
legitimate edit is reported and left alone.

Rules:
  - only kind=change on REAL columns; derived (lookup display, *_Email, calculated) never
  - a field changed several times in the window restores to the OLDEST 'old' and expects the NEWEST 'new'
  - values are typed from the Columns catalog (number / boolean / lookup id / text); nested values
    (URL, MultiChoice, multi-lookup: JSON text) are marked unsupported - x27 will not guess their shape
  - deleted rows are NOT recreated here: restore them from the recycle bin (keeps Id and history)
"""
import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mirror_lib as M  # noqa: E402

PARENT_LISTS = {"Order", "Models", "Model Revisions", "Clients"}


def typed(value, ctype):
    """A journal string -> the JSON value REST expects, or raise ValueError if unsupported."""
    if value == "" or value is None:
        return None
    if value[:1] in "[{":
        raise ValueError("nested value (URL / MultiChoice / multi-lookup)")
    if ctype.startswith(("number", "currency")) or ctype == "lookupId":
        f = float(value)
        return int(f) if f.is_integer() else f
    if ctype.startswith("boolean"):
        if value.lower() in ("true", "1"):
            return True
        if value.lower() in ("false", "0"):
            return False
        raise ValueError("boolean %r" % value)
    return value


def build_plan(events, catalog, lists=None, fields=None, ids=None, editors=None, frm=None, to=None, as_of=None):
    sel = []
    for e in events:
        if e.get("kind") != "change" or e.get("derived"):
            continue
        if lists and e["list"] not in lists:
            continue
        if fields and e["field"] not in fields:
            continue
        if ids and e["id"] not in ids:
            continue
        if editors and e.get("editor") not in editors:
            continue
        if as_of and e["asOf"] != as_of:
            continue
        if frm and e["asOf"] < frm:
            continue
        if to and e["asOf"] > to:
            continue
        if catalog.kind(e["list"], e["field"]) == "derived":
            continue
        sel.append(e)
    chain = {}
    for e in sorted(sel, key=lambda e: e["asOf"]):
        k = (e["list"], e["id"], e["field"])
        if k not in chain:
            chain[k] = {"first": e, "last": e}
        else:
            chain[k]["last"] = e
    entries, unsupported = [], []
    for (lst, i, f), c in sorted(chain.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        ctype = catalog.type(lst, f)
        rest = catalog.rest_field(lst, f)       # the journal holds CSV names; x27 writes REST names
        ent = {"list": lst, "id": i, "title": c["last"].get("title", ""), "field": rest, "type": ctype or "text",
               "fromAsOf": c["first"]["prevAsOf"], "toAsOf": c["last"]["asOf"]}
        if rest != f:
            ent["csvColumn"] = f
        try:
            ent["expect"] = typed(c["last"]["new"], ctype)
            ent["restore"] = typed(c["first"]["old"], ctype)
        except ValueError as ex:
            ent.update(expect=c["last"]["new"], restore=c["first"]["old"], unsupported=str(ex))
            unsupported.append(ent)
            continue
        entries.append(ent)
    touched = sorted({e["list"] for e in entries})
    warnings = []
    if set(touched) & PARENT_LISTS:
        warnings.append("Restoring %s rows FIRES the N3 sync flows, which push the restored values to their units. "
                        "Usually what you want - but it is more writes than this plan lists." % ", ".join(sorted(set(touched) & PARENT_LISTS)))
    if "Order Items" in touched:
        warnings.append("Restoring Order Items rows fires the Order Items trigger flow if it is ON.")
    deleted = [e for e in events if e.get("kind") == "deleted" and (not lists or e["list"] in lists)]
    if deleted:
        warnings.append("%d deleted row(s) in the window are NOT restored by this plan - use the recycle bin: %s"
                        % (len(deleted), ", ".join("%s %s" % (e["list"], e["id"]) for e in deleted[:10])))
    return {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "selection": {"lists": lists, "fields": fields, "ids": ids, "editors": editors, "from": frm, "to": to, "asOf": as_of},
            "counts": {"entries": len(entries), "rows": len({(e["list"], e["id"]) for e in entries}), "unsupported": len(unsupported)},
            "warnings": warnings, "entries": entries, "unsupported": unsupported}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to")
    ap.add_argument("--list", action="append", dest="lists")
    ap.add_argument("--field", action="append", dest="fields")
    ap.add_argument("--ids", help="comma-separated Ids")
    ap.add_argument("--editor", action="append", dest="editors")
    ap.add_argument("--out", help="plan file (default: sharepoint-lists/mirror/rollback-plans/plan-<now>.json)")
    args = ap.parse_args()
    if not any([args.as_of, args.frm, args.to, args.lists, args.fields, args.ids, args.editors]):
        sys.exit("ABORT: give at least one selector (--as-of/--from/--to/--list/--field/--ids/--editor); "
                 "a plan that restores everything is never what you want.")
    events = M.read_journal()
    snaps = M.snapshots_sorted()
    if not snaps:
        sys.exit("ABORT: no snapshot - the catalog comes from the newest one")
    cat = M.Catalog(M.Snapshot(snaps[-1]))
    ids = [int(x) for x in args.ids.split(",")] if args.ids else None
    plan = build_plan(events, cat, args.lists, args.fields, ids, args.editors, args.frm, args.to, args.as_of)
    if not plan["entries"]:
        sys.exit("ABORT: the selection matches 0 restorable changes. A zero-row plan is a failed selection.")
    out = args.out or os.path.join(M.MIRROR, "rollback-plans", "plan-%s.json" % plan["generated"].replace(":", ""))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    print("plan: %d entries on %d rows (%d unsupported) -> %s" % (
        plan["counts"]["entries"], plan["counts"]["rows"], plan["counts"]["unsupported"], os.path.relpath(out, M.ROOT)))
    for w in plan["warnings"]:
        print("  ⚠️ " + w)
    for e in plan["entries"][:10]:
        print("  %s %s %-28s expect %r -> restore %r" % (e["list"], e["id"], e["field"], e["expect"], e["restore"]))
    if len(plan["entries"]) > 10:
        print("  ... %d more" % (len(plan["entries"]) - 10))
    print("Next: paste the plan into x27_restore.js (PLAN = ...), DRY first.")


if __name__ == "__main__":
    main()
