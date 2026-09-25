# -*- coding: utf-8 -*-
# SUPERSEDED 2026-09-24, NEVER RUN: fixed by the user's own (pulled) v006 by another route, then Status Date made manual in v008 -- this file's "v006" is unrelated to the pulled v006. Kept for its R14 finding below.
"""Author v006 of the Order Items trigger flow: stop `Update_item` erasing `Status Date`.

    python apply_v006_status_date_preserve.py <v004 definition.json> [-o out.json]

WHY -- the flow ERASES a hand-entered date
------------------------------------------
Found 2026-09-15 00:1x, after v004 had passed every test in the evening runbook.

    item/StatusDate = @if(equals(variables('vStatusDateValue'), ''), null, variables(...))

`vStatusDateValue` initialises to `''` and is set to today ONLY inside
`Condition_StatusDate`, which requires `StepStatus <> StepStatusStamped` -- i.e. the step
actually changed. So when the step has NOT changed the expression writes **null**.

But `Update_item` does not only run on step changes. It runs whenever `Condition` (the
four `_TextField` mirror comparison) fails, via `Set_variable_16` -> `vUpdateOrderItem` ->
`Condition_3`. The two are independent. Hence:

    a mirror needs refreshing  AND  the step did not change
      -> Update_item fires to fix the mirror
      -> Condition_StatusDate is false
      -> Status Date is written as null and ERASED

Measured on `21408-1/1` (id 4): v37.0 at 03:38:53Z emptied a real 2026-07-16 date, moments
after x18 repaired its Model Revision and made its mirror stale.

⚠️ The design relied on **R14 -- "the connector ignores a null rather than clearing"**.
For this DateTime column that is FALSE. Anywhere else R14 was relied on needs re-checking;
it is recorded in x10_trigger_flow_gate.js's Gate B notes.

This predates v004 -- the identical expression is in v003 and v005 -- so it was live during
the 2026-09-11 enable attempt too. v004 did not cause it and does not contain the fix.

THE CHANGE -- ONE EXPRESSION
----------------------------
Write back the value the row already holds instead of null:

    - @if(equals(variables('vStatusDateValue'), ''), null, variables('vStatusDateValue'))
    + @if(equals(variables('vStatusDateValue'), ''), triggerBody()?['StatusDate'], variables('vStatusDateValue'))

Same shape the other three mirrors already use: when we have nothing new to say, restate
what is there rather than asserting emptiness.

⚠️ ASSUMPTION, NOT A FINDING: `triggerBody()?['StatusDate']` returns the date as the
trigger read it -- a full ISO timestamp, not the `yyyy-MM-dd` string the true branch
writes. Writing it back to a DateTime column should be a no-op because it is the value
already stored, but that has NOT been observed. The no-step-change test below is what
settles it. If it misbehaves, the fallback is to drop `item/StatusDate` from the write
entirely when there is no drift.

HOW TO TEST IT -- NOT THE HAPPY PATH
------------------------------------
A step change proves nothing: that path already worked, and passed steps 8 and 9 of the
evening runbook while this bug was live. The test is:

  1. a unit whose `Step Status` does NOT change
  2. whose `_TextField` mirror DOES disagree (any unit pointing at one of the 29 revisions
     x18 repaired qualifies)
  3. edit some other field to fire the trigger
  4. `Status Date` must be UNCHANGED, and the mirror must have been refreshed

Only after that passes should the ~724 stale mirrors be backfilled -- doing it first would
fire this bug on every row it touches.
"""
import json, io, os, argparse, sys

OLD = "@if(equals(variables('vStatusDateValue'), ''), null, variables('vStatusDateValue'))"
NEW = ("@if(equals(variables('vStatusDateValue'), ''), "
       "triggerBody()?['StatusDate'], variables('vStatusDateValue'))")

KEY = "item/StatusDate"
WRITE = "Update_item"


def unwrap(doc):
    """Accept either a bare definition or an editor/export wrapper."""
    if isinstance(doc, dict) and "definition" in doc and isinstance(doc["definition"], dict):
        return doc, doc["definition"]
    if isinstance(doc, dict) and "properties" in doc \
            and isinstance(doc["properties"], dict) and "definition" in doc["properties"]:
        return doc, doc["properties"]["definition"]
    return doc, doc


def find(node, name):
    """Locate an action by name anywhere in the graph, including inside scopes."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == name and isinstance(v, dict) and "inputs" in v:
                return v
            got = find(v, name)
            if got is not None:
                return got
    elif isinstance(node, list):
        for v in node:
            got = find(v, name)
            if got is not None:
                return got
    return None


def flatten(node, path="", out=None):
    """Every leaf as path -> value, so the diff can be counted exactly."""
    if out is None:
        out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            flatten(v, path + "/" + str(k), out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            flatten(v, path + "/[%d]" % i, out)
    else:
        out[path] = node
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    doc = json.load(io.open(a.src, encoding="utf-8"))
    doc, defn = unwrap(doc)
    before = flatten(defn)

    upd = find(defn, WRITE)
    assert upd is not None, "no %s action found" % WRITE
    params = upd["inputs"]["parameters"]

    assert KEY in params, "%s has no %s -- wrong flow or already restructured" % (WRITE, KEY)
    assert params[KEY] != NEW, "already patched -- has this run already?"
    assert params[KEY] == OLD, (
        "unexpected %s expression; refusing to patch blind.\n  found: %s\n  want : %s"
        % (KEY, params[KEY], OLD))

    # The bug only exists because these two are independent. If that ever stops being
    # true the reasoning above needs revisiting, so assert it rather than assume it.
    cond = find(defn, "Condition_StatusDate")
    assert cond is not None, "Condition_StatusDate missing"
    assert "StepStatusStamped" in json.dumps(cond["expression"], ensure_ascii=False), \
        "Condition_StatusDate no longer compares against StepStatusStamped"
    c3 = find(defn, "Condition_3")
    assert c3 is not None and "vUpdateOrderItem" in json.dumps(c3["expression"], ensure_ascii=False), \
        "Condition_3 no longer gates on vUpdateOrderItem"

    params[KEY] = NEW

    # ---- exactly one leaf may have changed -----------------------------------
    after = flatten(defn)
    changed = [k for k in set(before) | set(after) if before.get(k) != after.get(k)]
    assert len(changed) == 1, "expected exactly 1 changed leaf, got %d:\n  %s" % (
        len(changed), "\n  ".join(sorted(changed)))
    assert changed[0].endswith(KEY.replace("/", "~")) or KEY.split("/")[-1] in changed[0], \
        "the single change is not %s but %s" % (KEY, changed[0])

    # things that must not have moved, stated explicitly
    assert defn["triggers"]["When_an_item_is_created_or_modified"]["recurrence"]["interval"] == 5, \
        "recurrence interval is no longer 5"
    blob = json.dumps(defn, ensure_ascii=False)
    assert blob.count("coalesce(outputs('Get_Client')") >= 1, "the Get_Client coalesce vanished"
    assert blob.count("coalesce(outputs('Get_Model')") >= 1, "the Get_Model coalesce vanished"
    assert "Guard_Client" in blob and "Guard_Model" in blob, "a v004 guard vanished"

    out = a.out or os.path.splitext(a.src)[0] + ".v006.json"
    io.open(out, "w", encoding="utf-8").write(json.dumps(doc, indent=2, ensure_ascii=False))

    print("wrote %s" % out)
    print("  changed leaves : %d  (%s)" % (len(changed), changed[0]))
    print("  %s" % KEY)
    print("    - %s" % OLD)
    print("    + %s" % NEW)
    print("\n  assertions passed: recurrence still 5, both v004 guards intact, both")
    print("  lookup coalesces intact, and exactly one leaf in the whole definition moved.")
    print("\n  NOT YET PROVEN: that triggerBody()?['StatusDate'] round-trips cleanly into")
    print("  a DateTime column. Test on a row whose step does NOT change.")


if __name__ == "__main__":
    main()
