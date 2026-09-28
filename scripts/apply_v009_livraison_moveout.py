# -*- coding: utf-8 -*-
"""Author v009 of the Order Items trigger flow: moving a unit OUT of Livraison makes it Active again.

    python scripts/apply_v009_livraison_moveout.py [-o out.json]

Built from the newest live version in history.json (v008 as of 2026-09-28). Re-export and
intake the live flow before running it; the asserts below refuse if the live expressions
differ from what this change was written against.

WHY
---
Decided by the user 2026-09-28 (option C of the Livraison lock review). In v008, a step or
location change at Livraison forces Terminé + Delivered (CompletOrder). That lock stays.
But a unit moved back out of Livraison (a mistake, or a return to production) kept
ItemStatus = Delivered forever: no branch ever set it back. Views filtered on Active lost
it, and the archive and completed-order rules would count it as done.

THE CHANGE (one expression)
---------------------------
Update_item's `item/ItemStatus/Value`:
    CompletOrder                                         -> 'Delivered'   (unchanged)
    was at Livraison (LocationStamped), is not any more,
    and ItemStatus is Delivered                          -> 'Active'      (new)
    otherwise                                            -> keep the value (unchanged)

Cancelled / Regrouped are never touched (only Delivered flips). Step Status is NOT changed
on the way out: the user decided it stays as the person set it ("the step status is only
edited by a person for now").

No new loop: the move-out makes Location differ from LocationStamped, so Condition_2's else
branch already sets vUpdateOrderItem and Update_item already runs and re-stamps Location.
The follow-up run then sees Location == LocationStamped and writes nothing.
"""
import json, io, os, argparse, copy, re

from apply_v007_connref_statusdate import FLOW, REF_KEY, REF_LOGICAL, load, unwrap, find, flatten

ITEM_STATUS = "item/ItemStatus/Value"
OLD = "@if(variables('CompletOrder'), 'Delivered', triggerOutputs()?['body/ItemStatus/Value'])"
MOVED_OUT = ("and(equals(coalesce(triggerOutputs()?['body/LocationStamped'], ''), 'Livraison'), "
             "not(equals(coalesce(triggerOutputs()?['body/Location/Value'], ''), 'Livraison')), "
             "equals(coalesce(triggerOutputs()?['body/ItemStatus/Value'], ''), 'Delivered'))")
NEW = ("@if(variables('CompletOrder'), 'Delivered', if(%s, 'Active', triggerOutputs()?['body/ItemStatus/Value']))"
       % MOVED_OUT)


def newest_live():
    h = load(os.path.join(FLOW, "history.json"))
    live = [v for v in h["versions"] if v["state"] in ("pulled", "applied")][-1]
    return live, os.path.join(FLOW, live["files"]["definition"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    live, src = newest_live()
    doc = load(src)
    defn = copy.deepcopy(unwrap(doc))
    before = flatten(defn)

    params = find(defn, "Update_item")["inputs"]["parameters"]
    assert params[ITEM_STATUS] == OLD, "ItemStatus expression changed since v008 -- re-read before authoring:\n" + params[ITEM_STATUS]
    assert params["item/LocationStamped"] == "@triggerOutputs()?['body/Location/Value']", "LocationStamped write changed"
    cond2 = json.dumps(find(defn, "Condition_2")["expression"])
    assert "body/LocationStamped" in cond2 and "body/Location/Value" in cond2, "Condition_2 no longer compares the Location stamp"
    params[ITEM_STATUS] = NEW

    # Step Status and its stamp are untouched (user decision)
    assert params["item/StepStatus/Value"] == "@if(variables('CompletOrder'), 'Terminé', triggerOutputs()?['body/StepStatus/Value'])"

    after = flatten(defn)
    changed = sorted(k for k in before if k in after and before[k] != after[k])
    assert changed == ["/actions/Condition_3/actions/Update_item/inputs/parameters/" + ITEM_STATUS], changed
    assert set(before) == set(after), "leaves added or removed"
    assert set(re.findall(r'"connectionName": "([^"]+)"', json.dumps(defn))) == {REF_KEY}

    refs = doc.get("connectionReferences") or {}
    assert refs.get(REF_KEY, {}).get("connectionReferenceLogicalName") == REF_LOGICAL, \
        "source carries no solution connection reference -- intake the extension's JSON, not a zip"
    out_doc = {"$schema": doc.get("$schema"), "connectionReferences": {REF_KEY: refs[REF_KEY]}, "definition": defn}
    out = a.out or os.path.join(os.environ.get("TEMP", "."), "trigger-v009.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(out_doc, indent=2, ensure_ascii=False) + "\n")
    print("built from v%03d (%s)" % (live["v"], live["state"]))
    print("wrote %s" % out)
    print("  changed 1 leaf: Update_item %s" % ITEM_STATUS)
    print("  new: " + NEW)


if __name__ == "__main__":
    main()
