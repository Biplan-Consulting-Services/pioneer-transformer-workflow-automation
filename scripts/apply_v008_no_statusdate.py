# -*- coding: utf-8 -*-
"""Author v008 of the Order Items trigger flow: the flow stops touching `Status Date`.

    python scripts/apply_v008_no_statusdate.py [-o out.json]

Built from v006 (the user's 2026-09-24 edit, the newest pulled), NOT from v007. v007 was
never pasted and is superseded by this.

WHY
---
Decided by the user 2026-09-24: "just not update the status date, leave it manual, I'll
come back to it if it's needed." Every version that wrote the date had a way to destroy
one -- v003-v005 erased it on a mirror refresh, v006 overwrote a date typed in the same
save as a step change, and v007's fix needed a third stamp column and a drift branch to
get right. Staff have typed the date by hand since the cutover; that stays the rule.

With no write, none of those cases can occur: PatchItem leaves an omitted field alone.

THE CHANGES (all against v006)
------------------------------
C1  Connection reference -- identical to v007's C1. The trigger goes back from the stray
    `shared_sharepointonline_1` (the 2026-09 password reset) to `shared_sharepointonline`,
    and the wrapper carries only the solution reference `new_sharedsharepointonline_89e9a`.
C2  `item/StatusDate` removed from Update_item.
C3  `Set_vStatusDateValue` removed from Condition_2's else branch; the setter after it
    now runs first in that branch.
C4  `Initialize_vStatusDateValue` removed -- nothing reads the variable any more, and it
    was the action expected to fail on a blank date. `Initialize_variable_2` now runs
    after `Initialize_variable`.

KEPT, UNCHANGED
---------------
The step/location stamps and Condition_2 that compares them, because the Livraison
auto-complete (`CompletOrder`) and the stamp writes still hang off it. Condition_2's else
branch still sets vUpdateOrderItem, so a step or location change still writes the stamps.
If you come back to automating the date, `apply_v007_connref_statusdate.py` has the
worked design (StatusDateStamped, keep-a-typed-date, drift re-sync).
"""
import json, io, os, glob, argparse, copy, re

from apply_v007_connref_statusdate import (FLOW, WRAPPER_DROP, REF_KEY, REF_LOGICAL, STRAY,
                                           load, unwrap, find, flatten)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    srcs = glob.glob(os.path.join(FLOW, "v006__*__pulled__*.json"))
    assert len(srcs) == 1, "expected exactly one pulled v006, found %d" % len(srcs)
    defn = copy.deepcopy(unwrap(load(srcs[0])))
    wrapper = load(WRAPPER_DROP)
    before = flatten(defn)

    # ---- C1 connection reference -------------------------------------------
    trig = defn["triggers"]["When_an_item_is_created_or_modified"]
    assert trig["inputs"]["host"]["connectionName"] == STRAY, "re-pull before authoring"
    trig["inputs"]["host"]["connectionName"] = REF_KEY
    ref = copy.deepcopy(wrapper["connectionReferences"][REF_KEY])
    assert ref.get("connectionReferenceLogicalName") == REF_LOGICAL

    # ---- C2 no Status Date write --------------------------------------------
    params = find(defn, "Update_item")["inputs"]["parameters"]
    assert "item/StatusDate" in params
    del params["item/StatusDate"]

    # ---- C3 no date setter in the step-change branch ------------------------
    branch = find(defn, "Condition_2")["else"]["actions"]
    assert "Set_vStatusDateValue" in branch
    del branch["Set_vStatusDateValue"]
    nxt = branch["Set_vUpdateOrderItem_StatusDate_3"]
    assert nxt["runAfter"] == {"Set_vStatusDateValue": ["Succeeded"]}, nxt["runAfter"]
    nxt["runAfter"] = {}

    # ---- C4 no variable ------------------------------------------------------
    assert "Initialize_vStatusDateValue" in defn["actions"]
    del defn["actions"]["Initialize_vStatusDateValue"]
    iv2 = defn["actions"]["Initialize_variable_2"]
    assert iv2["runAfter"] == {"Initialize_vStatusDateValue": ["Succeeded"]}, iv2["runAfter"]
    iv2["runAfter"] = {"Initialize_variable": ["Succeeded"]}

    # ---- nothing left that reads or writes the date --------------------------
    blob = json.dumps(defn, ensure_ascii=False)
    for gone in ("vStatusDateValue", "body/StatusDate", "item/StatusDate", "['StatusDate']", STRAY):
        assert gone not in blob, "%s is still in the definition" % gone
    assert set(re.findall(r'"connectionName": "([^"]+)"', json.dumps(defn))) == {REF_KEY}
    assert trig["recurrence"]["interval"] == 5, "recurrence moved"
    for must in ("Guard_Client", "Guard_Model", "CompletOrder", "LocationStamped",
                 "StepStatusStamped", "coalesce(outputs('Get_Client')", "coalesce(outputs('Get_Model')"):
        assert must in blob, "%s vanished" % must

    # every action's runAfter must name an action that still exists in its scope
    def check_scope(acts):
        for n, act in acts.items():
            for dep in act.get("runAfter", {}):
                assert dep in acts, "%s runs after missing %s" % (n, dep)
            for sub in ("actions",):
                if sub in act: check_scope(act[sub])
            if "else" in act: check_scope(act["else"]["actions"])
    check_scope(defn["actions"])

    after = flatten(defn)
    removed = sorted(k for k in before if k not in after)
    changed = sorted(k for k in before if k in after and before[k] != after[k])
    added = sorted(k for k in after if k not in before)
    assert changed == ["/triggers/When_an_item_is_created_or_modified/inputs/host/connectionName"], changed
    assert added == ["/actions/Initialize_variable_2/runAfter/Initialize_variable/[0]"], added
    assert all(("StatusDate" in k) for k in removed), [k for k in removed if "StatusDate" not in k]

    out_doc = {"$schema": wrapper["$schema"], "connectionReferences": {REF_KEY: ref}, "definition": defn}
    out = a.out or os.path.join(os.environ.get("TEMP", "."), "trigger-v008.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(out_doc, indent=2, ensure_ascii=False) + "\n")
    print("wrote %s" % out)
    print("  C1 trigger back on %s (%s)" % (REF_KEY, REF_LOGICAL))
    print("  removed %d leaves, all Status Date:" % len(removed))
    for k in removed:
        print("    - " + k)
    print("  runAfter rewired: Set_vUpdateOrderItem_StatusDate_3 -> {}, Initialize_variable_2 -> Initialize_variable")


if __name__ == "__main__":
    main()
