# -*- coding: utf-8 -*-
"""Author v004 of the Order Items trigger flow: guard the two lookup gets, and take the
Status Date stamp out from behind them.

    python apply_v004_lookup_guards.py <v003 definition.json> [-o out.json]

WHY -- the flow is disabled in production
-----------------------------------------
Enabled 2026-09-11 07:1x, failed within minutes, turned off again:

    WorkflowOperationParametersRuntimeMissingValue
    'Get_Model' ... 'id' may not be null or empty

`Get_Client` and `Get_Model` read a lookup id straight off the trigger row with no
guard, and some units have no Client, Model or Model Revision. That population was
recorded as 203 of 1,189; measured directly on 2026-09-14 it is ~20 (16 with all three
empty, 4 with some). The 203 came from the `*_TextField` mirrors, whose sync has been off
since 2026-08-21 -- the trap x6_check_lookup_coverage.js exists to expose. The fix is
unchanged either way; only the blast radius was overstated.

Editing one of those units fails the flow at `Get_Client`, and because everything
downstream hangs off `Get_Model [Succeeded]`, the Status Date auto-stamp is skipped
with it. About 1.7% of units would silently stop stamping -- recorded at the time as
17%, on the same overstated population.

This predates v002. What changed is that the stamp came to depend on those two gets,
turning a dormant weakness into a user-visible one. The 2026-09-10 tests missed it
because they ran on units that have a model, which is most of them.

TWO CHANGES, AND THE SECOND IS THE REAL ONE
-------------------------------------------
1. GUARD BOTH GETS. Each moves inside an `If` that tests its own lookup id. A false
   condition still *succeeds* -- only the nested Get is skipped -- so every downstream
   `runAfter` stays plain `["Succeeded"]`. (The roadmap's sketch said downstream would
   need `Succeeded` AND `Skipped`; that is true of a bare `runAfter` guard, not of
   wrapping the action in a condition, which is why it is wrapped.)

   The guard tests two empty shapes, `''` and `0`, because the exact shape SharePoint
   sends for an empty lookup was never observed: the run died at the connector, which
   is downstream of the trigger body, so the failure told us the value was "null or
   empty" and nothing more precise. Testing both costs nothing and cannot be wrong.

2. DECOUPLE THE STAMP. `Condition_StatusDate` needs `Step Status` and
   `Step Status Stamped`, both of which are on the trigger row. It now runs directly
   off `Initialize_vStatusDateValue`, in parallel with the gets rather than downstream
   of them, so a unit with no model still gets its date. `Condition_3` already waits on
   both branches, so the graph becomes a diamond and needs no other rewiring.

   This is what makes the flow correct rather than merely not-failing. Change 1 alone
   would stop the error; a unit with no model would still take the stamping path only
   because nothing failed, not because the stamp has anything to do with its model.

COALESCE ON THE WRITE, NOT ONLY ON THE COMPARISON
-------------------------------------------------
Both `outputs('Get_Client')` expressions appear TWICE -- once in `Condition`'s change
guard and once in `Update_item`'s field map:

    Condition    @outputs('Get_Client')?['body/Client_ID']  ==  ...['Client_ID_TextField']
    Update_item  item/Client_ID_TextField = @outputs('Get_Client')?['body/Client_ID']

When a Get is skipped both evaluate to null. The comparison one is the bug the roadmap
names: null vs a populated mirror compares unequal, so `Condition` would report a
change that has not happened and rewrite the row on every poll -- an unbounded write
loop on those rows, because the write never makes the two sides agree.

The write one is milder than it looks and it is worth being exact about why, since the
reasoning is the same one v002 relies on: R14 established that this connector does NOT
clear a field passed null (844 stale Pending statuses survived a full rewrite), so the
mirrors would most likely be left alone rather than blanked. Both are coalesced anyway.
R14 is an observed connector behaviour, not a documented contract, and a field we
positively intend to leave unchanged should say so in the expression rather than lean
on a null being ignored. Coalescing costs one function call and removes the question:

    @coalesce(outputs('Get_Client')?['body/Client_ID'], triggerBody()?['Client_ID_TextField'])

Skipped -> the mirror's current value on both sides -> compares equal, writes itself.

WHAT IS DELIBERATELY NOT TOUCHED
--------------------------------
The trigger's `recurrence.interval` stays at 5. It was pasted as 1 and the designer
rewrote it on save; nobody chose 5 and nobody can find the field. Re-asserting 1 here
would make every future pull report FORKED on that one key forever.

`item/Model_Revision_ID_TextField` and `item/Order_Number_TextField` read the trigger
row directly, not an action output, so they are null on exactly the rows where their
mirror is also null and compare equal without help.

TERMINATION still holds, and now on the model-less rows as well. Pass 2 after a write: Step Status
equals its mirror so the stamp is false, and each coalesced lookup equals its own mirror
whether the Get ran or was skipped, so `Condition` is true, its `else` does not run,
`vUpdateOrderItem` stays false and `Condition_3` writes nothing.

BEFORE THIS GOES LIVE
---------------------
- Re-run the `StepStatusStamped = StepStatus` check. It was 262/262 at 05:55 and it is
  the gate that stops 246 historical dates being re-stamped to today.
- Test on a unit that HAS NO MODEL -- x10_trigger_flow_gate.js prints them. Testing the
  happy path is how the flow reached production broken.
"""
import json, io, os, argparse

CLIENT_ID = "triggerBody()?['Client/Id']"
MODEL_ID = "triggerBody()?['Model/Id']"

# (guard name, wrapped action, trigger lookup id)
GUARDS = [("Guard_Client", "Get_Client", CLIENT_ID),
          ("Guard_Model", "Get_Model", MODEL_ID)]

# (get action, its output path, the mirror it feeds)
LOOKUP_READS = [("Get_Client", "body/Client_ID", "Client_ID_TextField"),
                ("Get_Model", "body/ModelID", "Model_ID_TextField")]

STAMP = "Condition_StatusDate"
INIT_STAMP = "Initialize_vStatusDateValue"


def unwrap(doc):
    """Return (definition, setter). Handles both the export wrapper and a bare definition."""
    if "properties" in doc and "definition" in doc.get("properties", {}):
        return doc["properties"]["definition"], lambda d: doc["properties"].__setitem__("definition", d)
    if "definition" in doc:
        return doc["definition"], lambda d: doc.__setitem__("definition", d)
    return doc, lambda d: None


def nonempty(expr):
    """True when a SharePoint lookup id is really present.

    Two clauses because the empty shape was never observed -- see the module docstring.
    '' catches null/absent/empty-string, 0 catches a numeric zero id.
    """
    return {"and": [
        {"not": {"equals": ["@coalesce(%s, '')" % expr, ""]}},
        {"not": {"equals": ["@coalesce(%s, 0)" % expr, 0]}},
    ]}


def coalesced(action, path, mirror):
    return "@coalesce(outputs('%s')?['%s'], triggerBody()?['%s'])" % (action, path, mirror)


def count(d):
    n = 0
    for _, v in (d or {}).items():
        n += 1
        n += count(v.get("actions"))
        n += count((v.get("else") or {}).get("actions"))
        for c in (v.get("cases") or {}).values():
            n += count(c.get("actions"))
        n += count((v.get("default") or {}).get("actions"))
    return n


def walk(d):
    """Yield (name, action, its container) for every action at every nesting level."""
    for n, v in (d or {}).items():
        yield n, v, d
        for sub in (v.get("actions"), (v.get("else") or {}).get("actions")):
            for x in walk(sub):
                yield x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    doc = json.load(io.open(a.src, encoding="utf-8"))
    defn, _ = unwrap(doc)
    A = defn["actions"]
    before_top = len(A)
    before_total = count(A)

    # ---------------------------------------------------------------- preflight
    for g, get, _ in GUARDS:
        assert g not in A, "%s already present -- has this run already?" % g
        assert get in A, "expected a top-level %s to wrap" % get
        assert A[get]["inputs"]["host"]["operationId"] == "GetItem", "%s is not a GetItem" % get
    assert A["Get_Client"]["inputs"]["parameters"]["id"] == "@" + CLIENT_ID, \
        "Get_Client reads an id this script does not recognise"
    assert A["Get_Model"]["inputs"]["parameters"]["id"] == "@" + MODEL_ID, \
        "Get_Model reads an id this script does not recognise"
    assert A[STAMP]["runAfter"] == {"Condition": ["Succeeded"]}, \
        "%s is not where v003 leaves it (behind Condition)" % STAMP
    assert A["Condition"]["runAfter"] == {"Get_Model": ["Succeeded"]}, \
        "Condition is not where v003 leaves it (behind Get_Model)"
    assert A["Condition_3"]["runAfter"] == {"Condition": ["Succeeded"], STAMP: ["Succeeded"]}, \
        "Condition_3 does not already wait on both branches"
    params = A["Condition_3"]["actions"]["Update_item"]["inputs"]["parameters"]
    assert "coalesce(outputs(" not in json.dumps(defn), "lookup reads are already coalesced"

    # ------------------------------------------------- 1. wrap the gets in guards
    # An If that evaluates false still SUCCEEDS, so every downstream runAfter below
    # stays ["Succeeded"] and only the nested Get is skipped.
    for g, get, lookup in GUARDS:
        inner = A.pop(get)
        outer_runafter = inner["runAfter"]
        inner["runAfter"] = {}
        A[g] = {
            "type": "If",
            "runAfter": outer_runafter,
            "expression": nonempty(lookup),
            "actions": {get: inner},
        }
    # Guard_Model inherited Get_Client's old runAfter, which names an action that is no
    # longer a top-level sibling; repoint it at the guard standing in its place.
    A["Guard_Model"]["runAfter"] = {"Guard_Client": ["Succeeded"]}
    A["Condition"]["runAfter"] = {"Guard_Model": ["Succeeded"]}

    # --------------------------------------------- 2. take the stamp off the gets
    A[STAMP]["runAfter"] = {INIT_STAMP: ["Succeeded"]}

    # ------------------------------------- coalesce: comparison AND write, both
    patched_cmp = 0
    for clause in A["Condition"]["expression"]["and"]:
        lhs = clause.get("equals", [None])[0]
        for get, path, mirror in LOOKUP_READS:
            if lhs == "@outputs('%s')?['%s']" % (get, path):
                clause["equals"][0] = coalesced(get, path, mirror)
                patched_cmp += 1
    assert patched_cmp == 2, "expected 2 lookup comparisons in Condition, patched %d" % patched_cmp

    patched_write = 0
    for get, path, mirror in LOOKUP_READS:
        key = "item/%s" % mirror
        assert params[key] == "@outputs('%s')?['%s']" % (get, path), \
            "%s is not the bare read this script expects" % key
        params[key] = coalesced(get, path, mirror)
        patched_write += 1
    assert patched_write == 2, "expected 2 lookup writes, patched %d" % patched_write

    # ---------------------------------------------------------------- verify
    for n, act, container in walk(A):
        for dep in (act.get("runAfter") or {}):
            # a runAfter may only name a sibling in the SAME container
            assert dep in container, "%s runAfter names %s, which is not its sibling" % (n, dep)
    for g, get, _ in GUARDS:
        assert get not in A, "%s is still top-level" % get
        assert get in A[g]["actions"], "%s did not land inside %s" % (get, g)
        assert A[g]["actions"][get]["runAfter"] == {}, "%s must start its guard" % get

    blob = json.dumps(defn)
    for get, path, _ in LOOKUP_READS:
        assert '"@outputs(\'%s\')?[\'%s\']"' % (get, path) not in blob, \
            "an uncoalesced %s read survives" % get
    assert defn["triggers"]["When_an_item_is_created_or_modified"]["recurrence"]["interval"] == 5, \
        "the polling interval moved -- see the docstring, it must stay at 5"
    # the stamp must no longer reach either get, directly or transitively
    assert A[STAMP]["runAfter"] == {INIT_STAMP: ["Succeeded"]}
    assert set((A[INIT_STAMP].get("runAfter") or {})) <= {"Initialize_variable"}, \
        "the stamp's new parent is not itself independent of the gets"

    out = a.out or os.path.splitext(a.src)[0] + ".v004.json"
    io.open(out, "w", encoding="utf-8").write(json.dumps(doc, indent=2, ensure_ascii=False))

    print("wrote %s" % out)
    print("  top-level actions : %d -> %d   (2 gets moved into 2 guards)" % (before_top, len(A)))
    print("  total actions     : %d -> %d   (+2 guards)" % (before_total, count(A)))
    print("  guarded           : %s" % ", ".join("%s{%s}" % (g, get) for g, get, _ in GUARDS))
    print("  stamp runAfter    : Condition -> %s" % INIT_STAMP)
    print("  coalesced         : %d comparisons, %d writes" % (patched_cmp, patched_write))
    print("  graph:")
    for n in A:
        print("    %-22s <- %s" % (n, ", ".join(A[n].get("runAfter") or {}) or "(trigger)"))
    print("\n  all assertions passed: no runAfter crosses a scope, no uncoalesced lookup")
    print("  read survives, the stamp no longer descends from either get, interval still 5.")


if __name__ == "__main__":
    main()
