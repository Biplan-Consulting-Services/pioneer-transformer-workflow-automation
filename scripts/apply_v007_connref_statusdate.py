# -*- coding: utf-8 -*-
"""Author v007 of the Order Items trigger flow: one connection reference, and a Status Date
that survives being typed in the same edit as a step change.

    python scripts/apply_v007_connref_statusdate.py [-o out.json]

Reads the newest pulled version (v006, the user's 2026-09-24 edit) and this flow's
2026-09-09 editor-wrapper drop, the last copy that carried the solution connection
reference. Writes an EDITOR WRAPPER -- {$schema, connectionReferences, definition} --
because that is the only shape the extension accepts without unbinding the actions.

WHAT v006 IS
------------
The user's own edit, pulled 2026-09-24. It already fixes the Status Date erase that
`apply_v006_status_date_preserve.py` was written for (that script never ran and is now
moot): `vStatusDateValue` initialises from the row instead of from ''. It also adds the
Location stamp (`LocationStamped`) and the Livraison auto-complete (`CompletOrder`).

THE FOUR CHANGES
----------------
C1  CONNECTION REFERENCE. After the 2026-09 password reset the user reconnected in the
    designer, which moved the TRIGGER alone onto a new plain connection,
    `shared_sharepointonline_1`, while the three actions stayed on `shared_sharepointonline`.
    The designer then warns "uses a connection instead of a connection reference". The
    2026-09-09 drop shows `shared_sharepointonline` bound to the solution reference
    `new_sharedsharepointonline_89e9a` -- the same one all four N3 flows use -- so: point
    the trigger back at it and emit a wrapper holding that one reference and nothing else.

C2  NULL-SAFE INIT. v006 initialises a String variable from `StatusDate`, which is null on
    most units (911 of 1,085 in the 09-16 export). Power Automate is expected to reject
    that. `apply_v008_variable_nulls.py` records InitializeVariable accepting a null, but
    for an Integer in the other flow, so it does not settle String. Normalise instead:
    '' when empty, else `yyyy-MM-dd`. Normalising also removes the round-trip question the
    v006 note flagged -- whatever shape the trigger reports, what gets compared and
    written back is a plain date.

C3  A DATE TYPED IN THE SAME EDIT IS KEPT. The user's case: staff change Step Status AND
    type a Status Date in one save. The flow sees the step change and overwrites their
    date with today. The trigger cannot see the previous values, so add a stamp, like
    the other two: `StatusDateStamped` (Text, yyyy-MM-dd) = the date as the flow last left it.
        step/location changed, date == stamp  -> nobody touched the date: stamp today
        step/location changed, date != stamp  -> staff typed it in this edit: keep it
    Update_item writes the stamp every time it writes.

C4  A DATE EDITED ON ITS OWN RE-SYNCS THE STAMP. Without this C3 breaks on the NEXT edit:
    staff fix a date alone, no step change, nothing writes, and the stamp lags -- so the
    next real step change sees date != stamp, decides staff typed it, and does not stamp
    today. So Condition_2's empty true branch (no step/location change) gets one If:
    date != stamp -> vUpdateOrderItem. That costs one self-triggered write, after which
    date == stamp and the next run writes nothing.

    Every unsure case falls on the SAFE side: an unbackfilled stamp (blank) against a set
    date reads as "staff typed it", so the date is kept, never overwritten.

NOT CHANGED, ON PURPOSE
-----------------------
The Livraison auto-complete, the Location stamp and the connection id itself. Livraison
is pending a question to the user (it tests current Location, not a move into it).

PREREQUISITES -- none of this is live until they hold
-----------------------------------------------------
`StatusDateStamped` must exist, and all three stamps must be backfilled with the flow OFF:
`scripts/x24_backfill_stamps.js`. If the column is missing, the paste still saves, but
every Update_item fails.
"""
import json, io, os, glob, argparse, copy

HERE = os.path.dirname(os.path.abspath(__file__))
FLOW = os.path.join(HERE, "..", "workflow-data", "Order Items - Create or Update Trigger flow")
SRC_GLOB = "v006__*__pulled__*.json"
WRAPPER_DROP = os.path.join(FLOW, "_inbox", "_archive",
                            "2026-09-09T00-34__OrderItems-CreateorUpdateTrigger.json")

REF_KEY = "shared_sharepointonline"
REF_LOGICAL = "new_sharedsharepointonline_89e9a"
STRAY = "shared_sharepointonline_1"

SD = "triggerOutputs()?['body/StatusDate']"
STAMP = "coalesce(triggerOutputs()?['body/StatusDateStamped'], '')"
# `if` is written as if both branches evaluate (the repo's recorded assumption, see
# apply_v007_revmodeldescription.py): formatDateTime never sees a null.
ND = ("if(empty(%s), '', formatDateTime(coalesce(%s, '1900-01-01'), 'yyyy-MM-dd'))" % (SD, SD))
TODAY = "formatDateTime(convertFromUtc(utcNow(), 'Eastern Standard Time'), 'yyyy-MM-dd')"

INIT_OLD = "@triggerOutputs()?['body/StatusDate']"
INIT_NEW = "@" + ND
STAMP_TODAY_OLD = "@" + TODAY
STAMP_TODAY_NEW = "@if(equals(%s, %s), %s, %s)" % (ND, STAMP, TODAY, ND)
WRITE_STAMP = "@variables('vStatusDateValue')"


def load(p):
    return json.load(io.open(p, encoding="utf-8-sig"))


def unwrap(doc):
    if "definition" in doc:
        return doc["definition"]
    return doc["properties"]["definition"]


def find(node, name):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == name and isinstance(v, dict) and "type" in v:
                return v
            got = find(v, name)
            if got is not None:
                return got
    return None


def flatten(node, path="", out=None):
    out = {} if out is None else out
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
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    srcs = glob.glob(os.path.join(FLOW, SRC_GLOB))
    assert len(srcs) == 1, "expected exactly one pulled v006, found %d" % len(srcs)
    defn = copy.deepcopy(unwrap(load(srcs[0])))
    wrapper = load(WRAPPER_DROP)
    before = flatten(defn)

    # ---- C1 connection reference -------------------------------------------
    trig = defn["triggers"]["When_an_item_is_created_or_modified"]
    assert trig["inputs"]["host"]["connectionName"] == STRAY, \
        "trigger is not on %s any more -- re-pull before authoring" % STRAY
    trig["inputs"]["host"]["connectionName"] = REF_KEY
    ref = copy.deepcopy(wrapper["connectionReferences"][REF_KEY])
    assert ref.get("connectionReferenceLogicalName") == REF_LOGICAL, \
        "the 09-09 drop no longer names %s" % REF_LOGICAL

    # ---- C2 null-safe init --------------------------------------------------
    init = find(defn, "Initialize_vStatusDateValue")
    var = init["inputs"]["variables"][0]
    assert var["name"] == "vStatusDateValue" and var["value"] == INIT_OLD, var
    var["value"] = INIT_NEW

    # ---- C3 keep a date typed in the same edit ------------------------------
    c2 = find(defn, "Condition_2")
    setd = c2["else"]["actions"]["Set_vStatusDateValue"]
    assert setd["inputs"]["value"] == STAMP_TODAY_OLD, setd["inputs"]["value"]
    setd["inputs"]["value"] = STAMP_TODAY_NEW

    upd = find(defn, "Update_item")
    params = upd["inputs"]["parameters"]
    assert "item/StatusDateStamped" not in params, "already patched?"
    params["item/StatusDateStamped"] = WRITE_STAMP

    # ---- C4 a lone date edit re-syncs the stamp -----------------------------
    assert c2["actions"] == {}, "Condition_2's true branch is no longer empty"
    c2["actions"]["Condition_StatusDate_Drift"] = {
        "type": "If",
        "runAfter": {},
        "expression": {"not": {"equals": ["@" + ND, "@" + STAMP]}},
        "actions": {
            "Set_vUpdateOrderItem_StatusDate_Drift": {
                "type": "SetVariable", "runAfter": {},
                "inputs": {"name": "vUpdateOrderItem", "value": True},
            }
        },
        "else": {"actions": {}},
    }

    # ---- exactly these leaves moved, nothing else ---------------------------
    after = flatten(defn)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    expect_changed = {
        "/triggers/When_an_item_is_created_or_modified/inputs/host/connectionName",
        "/actions/Initialize_vStatusDateValue/inputs/variables/[0]/value",
        "/actions/Condition_2/else/actions/Set_vStatusDateValue/inputs/value",
        "/actions/Condition_3/actions/Update_item/inputs/parameters/item/StatusDateStamped",
    }
    drift = [k for k in changed if not k.startswith("/actions/Condition_2/actions/Condition_StatusDate_Drift/")]
    assert set(drift) == expect_changed, "unexpected changes:\n  " + "\n  ".join(sorted(set(drift) ^ expect_changed))

    blob = json.dumps(defn, ensure_ascii=False)
    assert STRAY not in blob, "%s is still referenced somewhere" % STRAY
    import re
    names = set(re.findall(r'"connectionName": "([^"]+)"', json.dumps(defn)))
    assert names == {REF_KEY}, "connection names in use: %s" % names
    assert trig["recurrence"]["interval"] == 5, "recurrence moved"
    for must in ("Guard_Client", "Guard_Model", "CompletOrder", "LocationStamped",
                 "coalesce(outputs('Get_Client')", "coalesce(outputs('Get_Model')"):
        assert must in blob, "%s vanished" % must

    out_doc = {"$schema": wrapper["$schema"],
               "connectionReferences": {REF_KEY: ref},
               "definition": defn}
    out = a.out or os.path.join(os.environ.get("TEMP", "."), "trigger-v007.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(out_doc, indent=2, ensure_ascii=False) + "\n")

    print("wrote %s" % out)
    print("  C1 trigger %s -> %s ; wrapper carries only %s (%s)" % (STRAY, REF_KEY, REF_KEY, REF_LOGICAL))
    print("  C2 init    : %s" % INIT_NEW)
    print("  C3 stamp   : %s" % STAMP_TODAY_NEW)
    print("     write   : item/StatusDateStamped = %s" % WRITE_STAMP)
    print("  C4 drift   : Condition_2 true branch -> Condition_StatusDate_Drift")
    print("  changed leaves: %d, all expected" % len(changed))


if __name__ == "__main__":
    main()
