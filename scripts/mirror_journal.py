#!/usr/bin/env python3
"""E10 Layer B - append what changed between two mirror snapshots to journal/YYYY-MM.jsonl.

    python scripts/mirror_journal.py                       # the two newest snapshots
    python scripts/mirror_journal.py --prev SPEC --cur SPEC [--dry]
      SPEC = a snapshot folder, or 'legacy:2026-09-24 2222' for the pre-D3 flat CSVs

One JSON object per change (docs/change-tracking-design-2026-09-24.md, Layer B):
  {"asOf","prevAsOf","list","id","title","kind","field","old","new","modified","editor","derived"}
  kind: change | added | deleted | schema
Rows are keyed by list + Id, never Title. Volatile columns (Modified, Editor, versions) are
not journaled. Mirror-derived columns (lookup display values, *_Email, calculated) ARE
journaled but tagged derived:true, so they never read as edits and are never restored.

Idempotent: a (prevAsOf, asOf) pair already in the journal is refused, not appended twice.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mirror_lib as M  # noqa: E402


def diff(prev, cur, lists=None):
    events = []
    cat = M.Catalog(cur)
    for lst in (lists or M.LISTS):
        if not (prev.has(lst) and cur.has(lst)):
            print("  skip %-16s (not in both snapshots)" % lst)
            continue
        a, b = prev.by_id(lst), cur.by_id(lst)
        base = {"asOf": cur.as_of, "prevAsOf": prev.as_of, "list": lst}
        n0 = len(events)
        for i in sorted(set(a) | set(b), key=int):
            ra, rb = a.get(i), b.get(i)
            row = rb or ra
            meta = dict(base, id=int(i), title=row.get("Title", ""),
                        modified=(rb or {}).get("Modified", ""), editor=(rb or {}).get("Editor_Email", ""))
            if ra is None:
                events.append(dict(meta, kind="added"))
                continue
            if rb is None:
                events.append(dict(meta, kind="deleted"))
                continue
            for f in sorted(set(ra) | set(rb)):
                if f in M.VOLATILE or f == "Id":
                    continue
                o, n = M.norm(ra.get(f)), M.norm(rb.get(f))
                if o != n:
                    e = dict(meta, kind="change", field=f, old=o, new=n)
                    if cat.kind(lst, f) == "derived":
                        e["derived"] = True
                    events.append(e)
        print("  %-16s %5d rows prev, %5d rows cur -> %d events" % (lst, len(a), len(b), len(events) - n0))

    # schema: the Columns catalog itself, keyed by (list, internalName)
    if prev.has(M.CATALOG) and cur.has(M.CATALOG):
        ka = {(r["list"], r["internalName"]): r for r in prev.table(M.CATALOG)}
        kb = {(r["list"], r["internalName"]): r for r in cur.table(M.CATALOG)}
        n0 = len(events)
        for k in sorted(set(ka) | set(kb)):
            ra, rb = ka.get(k), kb.get(k)
            what = ("column added" if ra is None else "column removed" if rb is None else None)
            if what is None:
                for f in ("displayName", "type", "choices", "lookupList", "lookupShowField", "required", "hidden"):
                    if M.norm(ra.get(f)) != M.norm(rb.get(f)):
                        events.append({"asOf": cur.as_of, "prevAsOf": prev.as_of, "list": k[0], "kind": "schema",
                                       "field": k[1], "what": f + " changed", "old": M.norm(ra.get(f)), "new": M.norm(rb.get(f))})
            else:
                events.append({"asOf": cur.as_of, "prevAsOf": prev.as_of, "list": k[0], "kind": "schema",
                               "field": k[1], "what": what})
        print("  %-16s -> %d schema events" % (M.CATALOG, len(events) - n0))
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev")
    ap.add_argument("--cur")
    ap.add_argument("--dry", action="store_true", help="print the summary, append nothing")
    args = ap.parse_args()

    if args.prev and args.cur:
        prev, cur = M.Snapshot(args.prev), M.Snapshot(args.cur)
    else:
        snaps = M.snapshots_sorted()
        if len(snaps) < 2:
            sys.exit("ABORT: need two snapshots in %s (have %d); or pass --prev/--cur" % (M.SNAPSHOTS, len(snaps)))
        prev, cur = M.Snapshot(snaps[-2]), M.Snapshot(snaps[-1])
    print("journal %s -> %s" % (prev.as_of, cur.as_of))
    if prev.as_of >= cur.as_of:
        sys.exit("ABORT: prev (%s) is not older than cur (%s)" % (prev.as_of, cur.as_of))

    done = {(e["prevAsOf"], e["asOf"]) for e in M.read_journal(cur.as_of[:7])}
    if (prev.as_of, cur.as_of) in done and not args.dry:
        sys.exit("ABORT: %s -> %s is already in the journal; refusing to append it twice" % (prev.as_of, cur.as_of))

    events = diff(prev, cur)
    kinds = {}
    for e in events:
        k = e["kind"] + ("/derived" if e.get("derived") else "")
        kinds[k] = kinds.get(k, 0) + 1
    print("events: %d  %s" % (len(events), kinds))
    if args.dry:
        print("DRY - nothing appended.")
        return events
    os.makedirs(M.JOURNAL, exist_ok=True)
    path = M.month_file(cur.as_of)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        # one marker line per run, so an empty diff is still a recorded fact
        f.write(json.dumps({"asOf": cur.as_of, "prevAsOf": prev.as_of, "kind": "run", "events": len(events)},
                           ensure_ascii=False) + "\n")
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print("appended %d events to %s" % (len(events), os.path.relpath(path, M.ROOT)))
    return events


if __name__ == "__main__":
    main()
