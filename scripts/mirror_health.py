#!/usr/bin/env python3
"""E10 Layer C1 - is something wrong? Checks the latest journal batch + snapshot, writes
sharepoint-lists/mirror/health/latest.md, exits 1 if anything is RED.

    python scripts/mirror_health.py                 # latest journal batch vs latest snapshot
    python scripts/mirror_health.py --as-of 2026-09-25T03:11Z

Checks (docs/change-tracking-design-2026-09-24.md, Layer C1, build step 3):
  bulk change    > BULK (25, D5) real changes on one field in one batch -> red, unless
                   - acknowledged (health/acknowledged.jsonl), or
                   - a probable PARENT FAN-OUT (D5): every changed field of those units is a
                     synced-from column, and every unit's parent changed the copied field in the
                     same batch -> 'expected'. Units moving on their own is exactly the drift we
                     want to see, so nothing is suppressed when a parent did not change.
  value erased   non-blank -> blank: >= 5 rows on one field = red (bulk erasure), fewer = amber
  rows deleted   any deleted row -> red (recycle bin keeps them 93 days)
  schema change  any Columns change -> red
  Index changed  any change on the Index list -> red (infrastructure, no history of its own)
  broken lookup  a <Lookup>Id pointing at no row of its target list -> red

Acknowledge a planned run by appending one line to health/acknowledged.jsonl:
  {"from":"2026-09-25T02:25Z","to":"2026-09-25T03:11Z","list":"Order Items","field":"*",
   "check":"bulk change","reason":"RUN2 x22 OVERWRITE (748 fields)"}
(field / check may be "*"; the batch's asOf must fall inside [from, to].)
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mirror_lib as M  # noqa: E402

BULK = 25
ERASE_RED = 5


def load_acks():
    p = os.path.join(M.HEALTH, "acknowledged.jsonl")
    out = []
    if os.path.exists(p):
        with open(p, encoding="utf-8-sig") as f:
            for line in f:
                if line.strip():
                    out.append(json.loads(line))
    return out


def acked(acks, check, lst, field, as_of):
    for a in acks:
        if a.get("check", "*") not in ("*", check):
            continue
        if a.get("list", "*") not in ("*", lst):
            continue
        if a.get("field", "*") not in ("*", field):
            continue
        if a.get("from", "") <= as_of <= a.get("to", "9999"):
            return a
    return None


def evaluate(events, snap, acknowledged=None):
    acks = acknowledged if acknowledged is not None else load_acks()
    cat = M.Catalog(snap)
    out = []
    as_of = events[0]["asOf"] if events else snap.as_of

    def add(check, level, detail, lst=None, field=None, rows=None):
        if level == "red":
            a = acked(acks, check, lst or "*", field or "*", as_of)
            if a:
                level, detail = "acknowledged", detail + " - acknowledged: " + a.get("reason", "")
        out.append({"check": check, "level": level, "list": lst, "field": field, "detail": detail, "rows": rows})

    real = [e for e in events if e["kind"] == "change" and not e.get("derived")]
    by_field = collections.defaultdict(list)
    for e in real:
        by_field[(e["list"], e["field"])].append(e)
    changed_fields_of = collections.defaultdict(set)      # (list, id) -> fields changed this batch
    for e in real:
        changed_fields_of[(e["list"], e["id"])].add(e["field"])
    parent_changed = {(e["list"], e["id"], e["field"]) for e in real}

    # ---- bulk change (+ fan-out classifier)
    for (lst, field), evs in sorted(by_field.items()):
        if len(evs) <= BULK:
            continue
        s = cat.synced(lst, field)
        fanout = None
        if s is not None:
            rows = snap.by_id(lst)
            parents, ok = collections.Counter(), True
            for e in evs:
                fields = changed_fields_of[(lst, e["id"])]
                if not all(cat.synced(lst, f) for f in fields):
                    ok = False; break                                        # (a) only synced fields moved
                pid = M.norm((rows.get(str(e["id"])) or {}).get(s["fk"]))
                if not pid or (s["list"], int(float(pid)), s["field"]) not in parent_changed:
                    ok = False; break                                        # (c) that parent changed that field
                parents[pid] += 1
            if ok:
                fanout = parents
        if fanout:
            ids = ", ".join("%s (%d units)" % (p, n) for p, n in fanout.most_common(5))
            add("bulk change", "expected", "%d rows - probable fan-out of %s %s via %s"
                % (len(evs), s["list"], ids, s["flow"]), lst, field, len(evs))
        else:
            add("bulk change", "red", "%d rows changed %s in one batch (threshold %d); e.g. ids %s"
                % (len(evs), field, BULK, ", ".join(str(e["id"]) for e in evs[:8])), lst, field, len(evs))

    # ---- value erased
    er = collections.defaultdict(list)
    for e in real:
        if e.get("old", "") != "" and e.get("new", "") == "":
            er[(e["list"], e["field"])].append(e)
    for (lst, field), evs in sorted(er.items()):
        lvl = "red" if len(evs) >= ERASE_RED else "amber"
        add("value erased", lvl, "%d rows lost their %s, e.g. %s" % (len(evs), field,
            "; ".join("%s %r" % (e["id"], e["old"][:30]) for e in evs[:5])), lst, field, len(evs))

    # ---- deleted / schema / Index
    dl = [e for e in events if e["kind"] == "deleted"]
    for lst, evs in sorted(collections.Counter(e["list"] for e in dl).items()):
        add("rows deleted", "red", "%d rows gone from %s (ids %s). Restore from the recycle bin (93 days) - not by rollback."
            % (evs, lst, ", ".join(str(e["id"]) for e in dl if e["list"] == lst)[:200]), lst, None, evs)
    for e in [e for e in events if e["kind"] == "schema"]:
        add("schema change", "red", "%s.%s: %s%s" % (e["list"], e["field"], e["what"],
            (" (%r -> %r)" % (e.get("old"), e.get("new"))) if "old" in e else ""), e["list"], e["field"])
    ix = [e for e in events if e["list"] == "Index" and e["kind"] in ("change", "added", "deleted") and not e.get("derived")]
    if ix:
        add("Index changed", "red", "%d change(s) to the Index list: %s" % (len(ix), "; ".join(
            "%s %s %s" % (e["kind"], e["id"], e.get("field", "")) for e in ix[:6])), "Index", None, len(ix))

    # ---- broken lookups (state, not change: checked on the snapshot itself)
    titles = {}
    for r in cat.rows:
        if r.get("type", "").startswith("lookup") and r.get("lookupList") and r["list"] in M.LISTS:
            tgt = r["lookupList"]
            if tgt not in M.LISTS or not snap.has(tgt) or not snap.has(r["list"]):
                continue
            if tgt not in titles:
                titles[tgt] = set(snap.by_id(tgt))
            idcol = r["internalName"] + "Id"
            bad = []
            for row in snap.table(r["list"]):
                v = (row.get(idcol) or "").strip()
                if not v:
                    continue
                ids = json.loads(v) if v.startswith("[") else [v]
                for i in ids:
                    if M.norm(i) not in titles[tgt]:
                        bad.append((M.key(row), i))
            if bad:
                add("broken lookup", "red", "%d %s rows point %s at a %s row that does not exist: %s"
                    % (len(bad), r["list"], idcol, tgt, ", ".join("%s->%s" % b for b in bad[:8])), r["list"], idcol, len(bad))
    return out


def report_md(findings, as_of, prev_as_of, n_events):
    reds = [f for f in findings if f["level"] == "red"]
    amb = [f for f in findings if f["level"] == "amber"]
    ok = [f for f in findings if f["level"] in ("expected", "acknowledged")]
    lines = ["# Mirror health - %s" % as_of, "",
             "Batch %s -> %s, %d journal events. Generated by `scripts/mirror_health.py`." % (prev_as_of, as_of, n_events), ""]
    if not findings:
        lines += ["**All clear.** Nothing matched a check.", ""]
    for title, group in (("RED - needs a look", reds), ("Amber", amb), ("Expected / acknowledged", ok)):
        if group:
            lines += ["## %s (%d)" % (title, len(group)), ""]
            lines += ["- **%s** - %s%s" % (f["check"], (f["list"] + ": ") if f["list"] else "", f["detail"]) for f in group]
            lines += [""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", help="journal batch asOf (default: the newest)")
    ap.add_argument("--snapshot", help="snapshot folder (default: the newest)")
    args = ap.parse_args()
    j = M.read_journal()
    runs = [e for e in j if e["kind"] == "run"]
    if not runs:
        sys.exit("ABORT: journal is empty - run mirror_journal.py first")
    as_of = args.as_of or runs[-1]["asOf"]
    run = [r for r in runs if r["asOf"] == as_of]
    if not run:
        sys.exit("ABORT: no journal batch with asOf %s" % as_of)
    events = [e for e in j if e["kind"] != "run" and e["asOf"] == as_of]
    snaps = M.snapshots_sorted()
    folder = args.snapshot or next((s for s in reversed(snaps) if M.Snapshot(s).as_of == as_of), snaps[-1] if snaps else None)
    if not folder:
        sys.exit("ABORT: no snapshot to check against")
    snap = M.Snapshot(folder)
    findings = evaluate(events, snap)
    md = report_md(findings, as_of, run[-1]["prevAsOf"], len(events))
    os.makedirs(M.HEALTH, exist_ok=True)
    with open(os.path.join(M.HEALTH, "latest.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md + "\n")
    print(md)
    red = sum(1 for f in findings if f["level"] == "red")
    print("health: %d red, %d amber, %d expected/acknowledged -> health/latest.md" % (
        red, sum(1 for f in findings if f["level"] == "amber"), sum(1 for f in findings if f["level"] in ("expected", "acknowledged"))))
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
