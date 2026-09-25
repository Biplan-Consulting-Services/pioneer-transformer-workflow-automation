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


def load_known():
    p = os.path.join(M.HEALTH, "known.jsonl")
    out = []
    if os.path.exists(p):
        with open(p, encoding="utf-8-sig") as f:
            for line in f:
                if line.strip():
                    out.append(json.loads(line))
    return out


def _flat(v):
    """x25's normalisation, on a mirror CSV value: JSON arrays joined '; ' (MultiChoice),
    URL objects -> Url, everything trimmed; '' for missing."""
    s = M.norm(v).strip()
    if s[:1] == "[":
        try:
            arr = json.loads(s)
            return "; ".join(str(x.get("Value", x)) if isinstance(x, dict) else str(x) for x in arr)
        except ValueError:
            return s
    if s[:1] == "{":
        try:
            o = json.loads(s)
            return str(o.get("Url", o.get("Value", s)))
        except ValueError:
            return s
    return s


def _is_known(known, check, row):
    for k in known:
        if k.get("check") != check:
            continue
        if "fields" in k and row.get("field") not in k["fields"]:
            continue
        if "units" in k and row.get("unit") not in k["units"]:
            continue
        if "orders" in k and row.get("order") not in k["orders"]:
            continue
        if k.get("parentBlank") and row.get("parentV", "") != "":
            continue
        return k
    return None


def state_checks(snap, prev_as_of, known):
    """E12: x25 / x16 / x17 ported from the console to the snapshot on disk. State, not change:
    they report what IS wrong in this snapshot, every refresh. Known cases (health/known.jsonl,
    pending a user decision) report as 'known'; anything else is red."""
    cat = M.Catalog(snap)
    out = []
    if not (snap.has("Order Items") and snap.has(M.CATALOG)):
        return out
    units = snap.table("Order Items")

    # ---- parent drift (x25): every synced-from column vs its parent, through the unit's lookup
    groups = collections.OrderedDict()
    for r in cat.rows:
        if r["list"] == "Order Items" and (r.get("syncedByFlow") or "").strip():
            groups.setdefault((r["syncedFromList"], r["viaLookup"]), []).append((r["internalName"], r["syncedFromField"]))
    drift = []
    for (plist, fk), pairs in groups.items():
        if not snap.has(plist):
            continue
        parents = snap.by_id(plist)
        fkcol = next((c for (l, c), rest in cat.by_csv.items() if l == "Order Items" and rest == fk), fk)
        for u in units:
            pid = M.norm(u.get(fkcol))
            if not pid:
                continue
            par = parents.get(pid)
            if par is None:
                drift.append({"unit": u.get("Title"), "field": "(parent %s %s missing)" % (plist, pid), "list": plist})
                continue
            for tgt, src in pairs:
                a, b = _flat(u.get(tgt)), _flat(par.get(src))
                if a != b:
                    drift.append({"unit": u.get("Title"), "order": u.get("OrderNumber") or u.get("Order_Number_TextField"),
                                  "list": plist, "parentId": pid, "field": tgt, "unitV": a[:40], "parentV": b[:40],
                                  "recent": bool(prev_as_of) and (par.get("Modified") or "") >= prev_as_of})
    kn = collections.Counter()
    red = collections.defaultdict(list)
    for d in drift:
        k = _is_known(known, "parent drift", d)
        if k:
            kn[k.get("reason", "known")] += 1
        else:
            red[d["field"]].append(d)
    for reason, n in kn.items():
        out.append({"check": "parent drift", "level": "known", "list": "Order Items", "field": None, "rows": n,
                    "detail": "%d unit-fields known: %s" % (n, reason)})
    for field, ds in sorted(red.items(), key=lambda kv: -len(kv[1])):
        rec = sum(1 for d in ds if d.get("recent"))
        out.append({"check": "parent drift", "level": "red", "list": "Order Items", "field": field, "rows": len(ds),
                    "detail": "%d units differ from their %s on %s (%d parent changed since %s, %d older); e.g. %s"
                    % (len(ds), ds[0]["list"], field, rec, prev_as_of or "?", len(ds) - rec,
                       "; ".join("%s %r vs %r" % (d["unit"], d.get("unitV", ""), d.get("parentV", "")) for d in ds[:4]))})

    # ---- lookup mirrors (x16): *_TextField vs the id its lookup really points at
    # Ids compare TRIMMED. A stray newline inside an id (Models 'M-FIEN-0004\n', found 2026-09-25)
    # is its own defect - reported below as amber - not a stale mirror or a wrong revision id.
    def ids(lst, field):
        return {k: M.norm(r.get(field)).strip() for k, r in snap.by_id(lst).items()} if snap.has(lst) else None
    MOD, REV, CLI = ids("Models", "ModelID"), ids("Model Revisions", "ModelID"), ids("Clients", "Client_ID")
    for lst, field in (("Models", "ModelID"), ("Model Revisions", "ModelID"), ("Clients", "Client_ID")):
        if snap.has(lst):
            ws = ["%s %r" % (k, M.norm(r.get(field))) for k, r in snap.by_id(lst).items()
                  if M.norm(r.get(field)) != M.norm(r.get(field)).strip()]
            if ws:
                out.append({"check": "id whitespace", "level": "amber", "list": lst, "field": field, "rows": len(ws),
                            "detail": "%d %s ids carry leading/trailing whitespace (compared trimmed; fix at source): %s"
                            % (len(ws), lst, "; ".join(ws[:6]))})
    cases = [("Client", "ClientId", "Client_ID_TextField", CLI), ("Model", "ModelId", "Model_ID_TextField", MOD),
             ("Model Revision", "ModelRevisionId", "Model_Revision_ID_TextField", REV)]
    for name, lk, mir, truth_map in cases:
        if truth_map is None or not units or mir not in units[0]:
            continue
        stale, empty = [], []
        for u in units:
            lid = M.norm(u.get(lk))
            if not lid:
                continue
            truth, mv = truth_map.get(lid), M.norm(u.get(mir)).strip()
            if mv == "":
                empty.append(u.get("Title"))
            elif truth is None or mv != truth:
                corrupt = name == "Model Revision" and MOD and mv == MOD.get(M.norm(u.get("ModelId")))
                stale.append("%s %r (lookup says %r)%s" % (u.get("Title"), mv, truth, " MODEL id - corruption signature" if corrupt else ""))
        if stale:
            out.append({"check": "lookup mirror", "level": "red", "list": "Order Items", "field": mir, "rows": len(stale),
                        "detail": "%d units' %s disagrees with its lookup: %s" % (len(stale), mir, "; ".join(stale[:6]))})
        if empty:
            out.append({"check": "lookup mirror", "level": "amber", "list": "Order Items", "field": mir, "rows": len(empty),
                        "detail": "%d units have an EMPTY %s (self-heals on the unit's next edit): %s"
                        % (len(empty), mir, ", ".join(empty[:8]))})

    # ---- revision ids (x17): ModelID = 'MR' + <linked model's code minus its M> + '-V<n>'
    if snap.has("Model Revisions") and MOD is not None:
        idcol = cat.id_column("Model Revisions", "Model")          # ModelId2 on disk (E8c)
        revs = snap.table("Model Revisions")
        if idcol not in revs[0]:
            # A pre-E8c snapshot's catalog has no idColumn, and the guessed `ModelId` does not exist in
            # the CSV (it is ModelId2) - every revision would read as unlinked. Say so; never guess.
            out.append({"check": "revision id", "level": "amber", "list": "Model Revisions", "field": idcol, "rows": None,
                        "detail": "cannot check: the Model lookup's id column %r is not in this snapshot (catalog predates "
                                  "E8c idColumn) - refresh the mirror" % idcol})
            return out
        bad, unlinked = [], []
        for k, r in snap.by_id("Model Revisions").items():
            link = M.norm(r.get(idcol))
            rid = M.norm(r.get("ModelID")).strip()
            if not link:
                unlinked.append("%s %r" % (k, rid))
                continue
            code = MOD.get(link, "")
            want = ("MR" + code[1:]).upper() if code else ""
            if not want or not rid.upper().startswith(want + "-V"):
                why = "empty" if not rid else ("equals its MODEL code" if rid == code else "expected %s-V<n>" % want)
                bad.append("%s %r (%s)" % (k, rid, why))
        if bad:
            out.append({"check": "revision id", "level": "red", "list": "Model Revisions", "field": "ModelID", "rows": len(bad),
                        "detail": "%d revisions' ModelID does not match their model: %s" % (len(bad), "; ".join(bad[:8]))})
        if unlinked:
            out.append({"check": "revision id", "level": "red", "list": "Model Revisions", "field": idcol, "rows": len(unlinked),
                        "detail": "%d revisions have NO Model link: %s" % (len(unlinked), "; ".join(unlinked[:10]))})
    return out


def evaluate(events, snap, acknowledged=None, prev_as_of=None, known=None, state=True):
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
            idcol = cat.id_column(r["list"], r["internalName"])   # E8c: ModelId2, not a guessed ModelId
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
    if state:
        out.extend(state_checks(snap, prev_as_of, known if known is not None else load_known()))
    return out


def report_md(findings, as_of, prev_as_of, n_events):
    reds = [f for f in findings if f["level"] == "red"]
    amb = [f for f in findings if f["level"] == "amber"]
    ok = [f for f in findings if f["level"] in ("expected", "acknowledged", "known")]
    lines = ["# Mirror health - %s" % as_of, "",
             "Batch %s -> %s, %d journal events. Generated by `scripts/mirror_health.py`." % (prev_as_of, as_of, n_events), ""]
    if not findings:
        lines += ["**All clear.** Nothing matched a check.", ""]
    for title, group in (("RED - needs a look", reds), ("Amber", amb), ("Expected / acknowledged / known", ok)):
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
    findings = evaluate(events, snap, prev_as_of=run[-1]["prevAsOf"])
    md = report_md(findings, as_of, run[-1]["prevAsOf"], len(events))
    os.makedirs(M.HEALTH, exist_ok=True)
    with open(os.path.join(M.HEALTH, "latest.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md + "\n")
    print(md)
    red = sum(1 for f in findings if f["level"] == "red")
    print("health: %d red, %d amber, %d expected/acknowledged/known -> health/latest.md" % (
        red, sum(1 for f in findings if f["level"] == "amber"), sum(1 for f in findings if f["level"] in ("expected", "acknowledged", "known"))))
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
