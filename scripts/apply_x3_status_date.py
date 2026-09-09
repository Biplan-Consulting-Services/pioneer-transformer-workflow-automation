# -*- coding: utf-8 -*-
"""Author v002 of the Order Items trigger flow: X3 (strip 2c stage-stamping) plus the
Status Date auto-stamp.

    python apply_x3_status_date.py <v001 definition.json> [-o out.json]

Two changes, deliberately in ONE version because they touch the same actions and the
spec says the stamp must never be added to the flow as it stands -- 2c's stamping is
what put it at 131 actions and helped wedge it against the capacity cap.

X3 -- strip the stage-stamping
------------------------------
Deletes 54 of the 59 top-level actions: 23 InitializeVariable (every stage date/status
variable; vUpdateOrderItem survives) and 31 stamping blocks (Condition_1*, Condition_2,
Condition_4*, Condition_5*). Drops the 23 stage fields from Update_item, keeping the 4
TextField writes. Rewires Condition_3's runAfter from 9 predecessors down to 1.

Survivors: Initialize_variable -> Get_Client -> Get_Model -> Condition -> Condition_3
-> Update_item. Roughly 7 actions against 131.

THE STAMP -- "when a status is set, fill in the status date"
------------------------------------------------------------
A SharePoint trigger hands over the item's CURRENT state only. There is no previous
value and a trigger condition cannot see one, so "did Step Status change?" has to be
answered another way.

This flow already answers exactly that question for four other fields: `Condition`
compares `OrderNumber/Value` against `Order_Number_TextField`, and three more like it.
So the stamp uses the same idiom rather than a new mechanism -- a text mirror,
`StepStatusStamped`, created and pre-filled by scripts/n8_split_status.js.

  Initialize_vStatusDateValue          ''
  Condition_StatusDate                 Step Status is non-empty AND differs from its
                                       mirror -> set the date, set vUpdateOrderItem
  Update_item gains                    item/StatusDate, item/StepStatusStamped

Why this terminates instead of looping: the write modifies the item, which fires the
trigger again -- but on that pass Step Status equals its mirror, so vStatusDateValue
stays '', the TextFields also match, vUpdateOrderItem stays false, and Condition_3 is
false. The second pass writes NOTHING. The self-retrigger is bounded at one extra
evaluation, and it is bounded *because* of the change guard, not by luck.

Why the null on the unchanged path is safe: the connector does NOT clear a field passed
null (the R14 finding, proven by 844 stale Pending statuses surviving a full rewrite).
Here that behaviour is what we want -- an unchanged run leaves the existing Status Date
alone instead of blanking it.

DATE FORMAT -- the one place this deviates from the code already here
--------------------------------------------------------------------
2c wrote `@convertFromUtc(utcNow(), 'Eastern Standard Time')`, an unformatted local
datetime. This writes `formatDateTime(convertFromUtc(...), 'yyyy-MM-dd')` instead,
because a Date-Only column takes a bare date as site-local midnight (verified: 552 rows
at 04:00Z + 416 at 05:00Z, the DST split) while a fuller value depends on how the
connector reads a naive string. Both readings happen to land on the same Eastern day for
most of the clock, but NOT between midnight and 04:00 Eastern, where a naive string read
as UTC renders as the previous day -- R6's day-early bug, in a new place. The bare date
removes the question.

Refuses to run unless every expectation holds, and verifies afterwards that nothing
surviving still references a deleted action or variable -- which is the exact defect that
had to be caught by hand in v006.
"""
import json, io, os, re, sys, copy, argparse

KEEP_ACTIONS = {"Initialize_variable", "Get_Client", "Get_Model", "Condition", "Condition_3"}
KEEP_TEXTFIELDS = {"Client_ID_TextField", "Model_ID_TextField",
                   "Model_Revision_ID_TextField", "Order_Number_TextField"}
KEEP_VAR = "vUpdateOrderItem"
STAMP_VAR = "vStatusDateValue"

# Site-local calendar date, bare. See the DATE FORMAT note above.
LOCAL_DATE = ("@formatDateTime(convertFromUtc(utcNow(), 'Eastern Standard Time'), "
              "'yyyy-MM-dd')")


def unwrap(doc):
    """Return (definition, setter). Handles both the export wrapper and a bare definition."""
    if "properties" in doc and "definition" in doc.get("properties", {}):
        return doc["properties"]["definition"], lambda d: doc["properties"].__setitem__("definition", d)
    if "definition" in doc:
        return doc["definition"], lambda d: doc.__setitem__("definition", d)
    return doc, lambda d: None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    doc = json.load(io.open(a.src, encoding="utf-8"))
    defn, _ = unwrap(doc)
    A = defn["actions"]
    before_actions = len(A)

    # ---------------------------------------------------------------- preflight
    assert set(KEEP_ACTIONS) <= set(A), "missing expected survivors: %s" % (KEEP_ACTIONS - set(A))
    upd = A["Condition_3"]["actions"]["Update_item"]
    assert upd["inputs"]["host"]["operationId"] == "PatchItem", "Condition_3 does not hold a PatchItem"
    params = upd["inputs"]["parameters"]
    for k in ("StatusDate", "StepStatusStamped"):
        assert "item/%s" % k not in params, "item/%s already mapped -- has this run already?" % k
    assert STAMP_VAR not in json.dumps(defn), "%s already present" % STAMP_VAR
    inits = {n: v["inputs"]["variables"][0]["name"]
             for n, v in A.items() if v.get("type") == "InitializeVariable"}
    assert list(inits.values()).count(KEEP_VAR) == 1, "expected exactly one %s init" % KEEP_VAR

    # ------------------------------------------------------------------- X3
    doomed = {n for n, v in inits.items() if v != KEEP_VAR}
    doomed |= {n for n in A if re.fullmatch(r'Condition_(1|2|4|5)(_\d+)*', n)}
    assert not (doomed & KEEP_ACTIONS), "about to delete a survivor: %s" % (doomed & KEEP_ACTIONS)
    assert len(doomed) == 54, "expected to delete 54 actions, got %d" % len(doomed)
    for n in doomed:
        del A[n]

    dropped = [k for k in list(params)
               if k.startswith("item/") and k.split("/", 1)[1].split("/")[0] not in KEEP_TEXTFIELDS]
    assert len(dropped) == 23, "expected 23 stage fields to drop, got %d" % len(dropped)
    for k in dropped:
        del params[k]

    # Condition_3 waited on all eight Condition_5* plus Condition; now only the guards.
    A["Condition_3"]["runAfter"] = {"Condition": ["Succeeded"],
                                    "Condition_StatusDate": ["Succeeded"]}

    # ---------------------------------------------------------------- the stamp
    A["Initialize_%s" % STAMP_VAR] = {
        "type": "InitializeVariable",
        "runAfter": {"Initialize_variable": ["Succeeded"]},
        "inputs": {"variables": [{"name": STAMP_VAR, "type": "string", "value": ""}]},
    }
    # Get_Client waited on Initialize_variable; keep it after the new init so the two
    # variables are always both in scope before anything reads them.
    A["Get_Client"]["runAfter"] = {"Initialize_%s" % STAMP_VAR: ["Succeeded"]}

    A["Condition_StatusDate"] = {
        "type": "If",
        "runAfter": {"Condition": ["Succeeded"]},
        "expression": {"and": [
            {"not": {"equals": ["@triggerBody()?['StepStatus/Value']", "@null"]}},
            {"not": {"equals": ["@triggerBody()?['StepStatus/Value']", ""]}},
            {"not": {"equals": ["@coalesce(triggerBody()?['StepStatus/Value'], '')",
                                "@coalesce(triggerBody()?['StepStatusStamped'], '')"]}},
        ]},
        "actions": {
            "Set_vStatusDateValue": {
                "type": "SetVariable",
                "runAfter": {},
                "inputs": {"name": STAMP_VAR, "value": LOCAL_DATE},
            },
            "Set_vUpdateOrderItem_StatusDate": {
                "type": "SetVariable",
                "runAfter": {"Set_vStatusDateValue": ["Succeeded"]},
                "inputs": {"name": KEEP_VAR, "value": True},
            },
        },
    }

    params["item/StatusDate"] = ("@if(equals(variables('%s'), ''), null, variables('%s'))"
                                 % (STAMP_VAR, STAMP_VAR))
    params["item/StepStatusStamped"] = "@triggerBody()?['StepStatus/Value']"

    # ---------------------------------------------------------------- verify
    blob = json.dumps(defn)
    live_actions = set(A) | {k for n in A for k in (A[n].get("actions") or {})} \
                          | {k for n in A for k in ((A[n].get("else") or {}).get("actions") or {})}
    for n in sorted(doomed):
        for pat in ("actions('%s')" % n, "outputs('%s')" % n, "body('%s')" % n):
            assert pat not in blob, "a survivor still references deleted action %s" % n
        assert '"%s"' % n not in blob, "deleted action %s still named somewhere (runAfter?)" % n
    dead_vars = {v for n, v in inits.items() if v != KEEP_VAR}
    for v in sorted(dead_vars):
        assert "variables('%s')" % v not in blob, "still references deleted variable %s" % v
    # every runAfter target must exist
    for n, act in A.items():
        for dep in (act.get("runAfter") or {}):
            assert dep in A, "%s runAfter names a missing action %s" % (n, dep)

    out = a.out or os.path.splitext(a.src)[0] + ".v002.json"
    io.open(out, "w", encoding="utf-8").write(json.dumps(doc, indent=2, ensure_ascii=False))

    def count(d):
        n = 0
        for k, v in (d or {}).items():
            n += 1
            n += count(v.get("actions"))
            n += count((v.get("else") or {}).get("actions"))
            for c in (v.get("cases") or {}).values():
                n += count(c.get("actions"))
            n += count((v.get("default") or {}).get("actions"))
        return n

    print("wrote %s" % out)
    print("  top-level actions : %d -> %d   (deleted %d)" % (before_actions, len(A), len(doomed)))
    print("  total actions     : %d" % count(A))
    print("  Update_item writes: %d  (%s + StatusDate + StepStatusStamped)"
          % (len([k for k in params if k.startswith("item/")]), len(KEEP_TEXTFIELDS)))
    print("  dropped from write: %s" % ", ".join(sorted(k.replace("item/", "") for k in dropped)[:6]) + " ...")
    print("  survivors         : %s" % ", ".join(sorted(A)))
    print("\n  all assertions passed: no dangling action or variable references,")
    print("  every runAfter target exists, and nothing was mapped twice.")


if __name__ == "__main__":
    main()
