# -*- coding: utf-8 -*-
"""Author the Save Conflict retry on the four N3 sync flows (Punch List p-n3-retry).

    python scripts/apply_n3_retry.py                    # all four, from each flow's newest live version
    python scripts/apply_n3_retry.py --flow "Order Items - sync from Order"
    python scripts/apply_n3_retry.py --src some.definition.json -o out.json   # offline check, no history

Built from the newest pulled/applied version in each flow's history.json. Intake the live
flows first (the extension's JSON, not a zip: only it carries the connection references).

WHY
---
A parent edit fans out to its units; two N3 flows (or a flow and a person) writing the same unit
at the same moment get `400 Save Conflict`. Logic Apps' default retry covers 408/429/5xx only
and a retryPolicy cannot select status codes, so the 400 is lost for good: the run fails and the
unit keeps stale parent columns (docs/n3-fanout-race-2026-09-21.md, "Fixing this one" 1).

THE CHANGE (two actions added, nothing edited)
----------------------------------------------
Beside Update_unit, in the same container:
    Wait_before_retry   runAfter Update_unit: [Failed, TimedOut]   Wait 15 s
    Update_unit_retry   runAfter Wait_before_retry: [Succeeded]    an exact copy of Update_unit
Update_unit succeeds -> both skipped, behaviour unchanged. It fails -> one more attempt with the
same values (the write is idempotent: it copies the parent's current values). The retry failing
too fails the run exactly as today, so nothing is swallowed.
"""
import argparse, copy, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from apply_v007_connref_statusdate import REF_KEY, REF_LOGICAL, load, flatten  # noqa: E402


def unwrap(doc):
    """Any shape: export wrapper, {definition: ...}, or the bare definition the extension hands over."""
    return doc.get("properties", {}).get("definition", doc.get("definition", doc))

ROOT = os.path.join(HERE, "..", "workflow-data")
FLOWS = ["Order Items - sync from Order", "Order Items - sync from Models",
         "Order Items - sync from Model Revisions", "Order Items - sync from Clients"]
TARGET, WAIT, RETRY = "Update_unit", "Wait_before_retry", "Update_unit_retry"


def container_of(node, name):
    """The `actions` dict that holds action `name` (N3: Only_if_something_changed's)."""
    if isinstance(node, dict):
        acts = node.get("actions")
        if isinstance(acts, dict) and name in acts and isinstance(acts[name], dict) and "type" in acts[name]:
            return acts
        for v in node.values():
            got = container_of(v, name)
            if got is not None:
                return got
    elif isinstance(node, list):
        for v in node:
            got = container_of(v, name)
            if got is not None:
                return got
    return None


def author(defn):
    acts = container_of(defn, TARGET)
    assert acts is not None, "no %s action" % TARGET
    assert WAIT not in acts and RETRY not in acts, "retry already present -- nothing to author"
    upd = acts[TARGET]
    assert upd["type"] == "OpenApiConnection" and upd["inputs"]["host"]["operationId"] == "PatchItem", "Update_unit is not a PatchItem"
    assert not any(TARGET in (a.get("runAfter") or {}) for a in acts.values()), "something already runs after Update_unit"
    before = flatten(defn)
    retry = copy.deepcopy(upd)
    retry["runAfter"] = {WAIT: ["Succeeded"]}
    acts[WAIT] = {"runAfter": {TARGET: ["Failed", "TimedOut"]}, "type": "Wait",
                  "inputs": {"interval": {"count": 15, "unit": "Second"}}}
    acts[RETRY] = retry
    after = flatten(defn)
    assert all(after.get(k) == v for k, v in before.items()), "an existing leaf changed"
    added = sorted(k for k in after if k not in before)
    assert added and all(("/" + WAIT + "/") in k or ("/" + RETRY + "/") in k for k in added), added
    # the retry writes exactly what Update_unit writes
    assert {k: v for k, v in retry["inputs"]["parameters"].items()} == upd["inputs"]["parameters"]
    return len(upd["inputs"]["parameters"]), len(added)


def build(doc, check_refs=True):
    defn = copy.deepcopy(unwrap(doc))
    n_params, n_added = author(defn)
    names = set(re.findall(r'"connectionName": "([^"]+)"', json.dumps(defn)))
    refs = doc.get("connectionReferences") or {}
    if check_refs:
        for n in names:
            assert refs.get(n, {}).get("connectionReferenceLogicalName"), \
                "%s has no solution connection reference -- intake the extension's JSON, not a zip" % n
        assert refs.get(REF_KEY, {}).get("connectionReferenceLogicalName") == REF_LOGICAL, "SharePoint reference is not " + REF_LOGICAL
    out = {"$schema": doc.get("$schema"), "connectionReferences": {n: refs[n] for n in names if n in refs}, "definition": defn}
    return out, n_params, n_added


def newest_live(flow):
    fold = os.path.join(ROOT, flow)
    h = load(os.path.join(fold, "history.json"))
    live = [v for v in h["versions"] if v["state"] in ("pulled", "applied")]
    assert live, "%s: no pulled version -- intake the live flow first" % flow
    return live[-1], os.path.join(fold, live[-1]["files"]["definition"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flow", choices=FLOWS)
    ap.add_argument("--src", help="offline: a definition file, no history and no reference check")
    ap.add_argument("-o", "--out", help="output file (--src / one --flow) or folder (all)")
    a = ap.parse_args()
    if a.src:
        out, n, k = build(load(a.src), check_refs=False)
        dst = a.out or os.path.join(os.environ.get("TEMP", "."), "n3-retry-check.json")
        io.open(dst, "w", encoding="utf-8").write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        print("offline %s: Update_unit writes %d fields; added %d leaves (Wait + retry) -> %s" % (os.path.basename(a.src), n, k, dst))
        return 0
    for flow in [a.flow] if a.flow else FLOWS:
        live, src = newest_live(flow)
        out, n, k = build(load(src))
        dst = a.out if (a.out and a.flow) else os.path.join(a.out or os.environ.get("TEMP", "."), flow + " - retry.json")
        io.open(dst, "w", encoding="utf-8").write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        print("%s: from v%03d (%s); Update_unit writes %d fields; added %d leaves -> %s" % (flow, live["v"], live["state"], n, k, dst))
    return 0


if __name__ == "__main__":
    sys.exit(main())
