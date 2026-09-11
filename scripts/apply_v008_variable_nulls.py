# -*- coding: utf-8 -*-
"""v008 — stop the integer variables ever holding null.

    python scripts/apply_v008_variable_nulls.py

THE FAILURE
    BadRequest
    The variable 'ModelIDToWrite' of type 'Integer' cannot be set to null or empty value.

`ResetModelID` is the SECOND action inside `Apply_to_each`, before every filter and both
writes, and it sets a literal `null` on an integer variable. So every iteration dies at
action two and nothing downstream runs -- no `UpdateOrder`, no `Update_item`, no writes at
all. That is why it failed on every item, and also why the cancelled run cost nothing.

`InitializeVariable` accepts a null; `SetVariable` does not. That asymmetry is the whole
bug: the flow initialises cleanly and then dies in the loop.

THE FIX, AND WHY NOT THE OBVIOUS ONE
  The obvious fix is to delete the two Reset actions. Don't: they exist so a unit with no
  model does not inherit the previous iteration's model id, and silently writing the wrong
  model onto a unit is far worse than a loud failure.

  The second-obvious fix is to retype the variables as string and reset to ''. Don't do
  that either: the only readers are `item/Model/Id` and `item/ModelRevision/Id`, which are
  lookup ids, and handing a lookup an empty string is a new guess about connector shapes.
  Tonight has already cost one run to a shape guess.

  So: keep them integer, reset to **-1** as the sentinel, and translate -1 back to null at
  the write. The variable is always a valid integer; the field still receives a real null.

  ⚠️ Per R14/R22, null does NOT clear an existing value through this connector -- a unit
  whose model cannot be resolved keeps whatever it already had. That is exactly the
  `null`-on-empty idiom the other 121 mappings use, so this is consistent rather than a
  new behaviour. It is NOT a way to blank a lookup.

ALL SIX SETTERS ARE GUARDED, not just the two that fail today
  `Set_variable`/`_1` read `?['Model/Id']` off a filtered `Get items` result. v006 changed
  that read from `Get item` to a cached `Get items` filtered in memory, and runbook 2.2
  flags the flattened `Name/Value` key form as the thing to confirm. If those keys are
  absent the expression yields null and hits the same error -- so coalesce them now rather
  than discover it on the next run.

  `Set_variable_3` is worse: `['ModelRevision/Id']` with **no `?`**. That is a hard index,
  not a safe navigation, and it throws outright when the key is missing rather than
  yielding null. Same family as the `?['Url']` failure earlier tonight.
"""
import io, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FLOW = os.path.join(ROOT, "workflow-data", "Order Items - excel transfer flow")

# -1, not 0. This is the user's own choice, and it is the one that has actually run: they
# hit this same BadRequest under v006, fixed it live with a -1 sentinel, and that flow
# completed. -1 is also SharePoint's conventional "no value" id -- the fill-in choice blob
# in the 09-08 export carries "Id":-1 -- whereas 0 is merely unused.
SENTINEL = -1

# action name -> (expected current value, new value)
SETTERS = {
    "ResetModelID": (None, SENTINEL),
    "ResetModelRevisionID": (None, SENTINEL),
    "Set_variable": (
        "@first(body('Filter_Orders'))?['Model/Id']",
        "@coalesce(first(body('Filter_Orders'))?['Model/Id'], -1)"),
    "Set_variable_1": (
        "@first(body('Filter_Orders'))?['ModelRevision/Id']",
        "@coalesce(first(body('Filter_Orders'))?['ModelRevision/Id'], -1)"),
    "Set_variable_2": (
        "@first(outputs('GetModels')?['body/value'])?['ID']",
        "@coalesce(first(outputs('GetModels')?['body/value'])?['ID'], -1)"),
    "Set_variable_3": (
        "@first(outputs('GetModels')?['body/value'])['ModelRevision/Id']",
        "@coalesce(first(outputs('GetModels')?['body/value'])?['ModelRevision/Id'], -1)"),
}

WRITES = {
    "item/Model/Id": ("@variables('ModelIDToWrite')",
                      "@if(equals(variables('ModelIDToWrite'), -1), null, "
                      "variables('ModelIDToWrite'))"),
    "item/ModelRevision/Id": ("@variables('ModelRevisionIDToWrite')",
                              "@if(equals(variables('ModelRevisionIDToWrite'), -1), null, "
                              "variables('ModelRevisionIDToWrite'))"),
}


def newest_local():
    """The newest stored definition, whatever its version. Authoring refuses to run off
    anything but the newest known-live version -- see the repo's flow versioning rule."""
    out = subprocess.check_output(
        [sys.executable, os.path.join(HERE, "flow_version.py"), "status"],
        cwd=ROOT).decode("utf-8", "replace")
    return out


def patch(o, counts, parent_key=None):
    if isinstance(o, dict):
        # a SetVariable action
        t, ins = o.get("type"), o.get("inputs")
        if t == "SetVariable" and isinstance(ins, dict):
            pass  # handled by name at the caller, names are the dict keys
        for k, v in list(o.items()):
            if k in WRITES and isinstance(v, str):
                want, new = WRITES[k]
                if v == want:
                    o[k] = new
                    counts[k] = counts.get(k, 0) + 1
                elif v != new:
                    sys.exit("unexpected value on %s:\n   %s" % (k, v))
            else:
                patch(v, counts, k)
    elif isinstance(o, list):
        for x in o:
            patch(x, counts, parent_key)


def patch_setters(acts, counts):
    for n, a in (acts or {}).items():
        if not isinstance(a, dict):
            continue
        if a.get("type") == "SetVariable" and n in SETTERS:
            want, new = SETTERS[n]
            cur = (a.get("inputs") or {}).get("value")
            if cur == want:
                a["inputs"]["value"] = new
                counts[n] = counts.get(n, 0) + 1
            elif cur != new:
                sys.exit("unexpected value on %s:\n   want %r\n   got  %r" % (n, want, cur))
        for key in ("actions",):
            if isinstance(a.get(key), dict):
                patch_setters(a[key], counts)
        e = a.get("else")
        if isinstance(e, dict) and isinstance(e.get("actions"), dict):
            patch_setters(e["actions"], counts)
        for c in (a.get("cases") or {}).values():
            if isinstance(c, dict) and isinstance(c.get("actions"), dict):
                patch_setters(c["actions"], counts)
        dflt = a.get("default")
        if isinstance(dflt, dict) and isinstance(dflt.get("actions"), dict):
            patch_setters(dflt["actions"], counts)


def main():
    import glob
    src = sorted(glob.glob(os.path.join(FLOW, "*v007*.json")))
    if not src:
        sys.exit("v007 not found")
    src = src[0]
    j = json.loads(io.open(src, encoding="utf-8").read())
    d = j.get("definition") or j.get("properties", {}).get("definition")
    if d is None:
        sys.exit("no definition in %s" % src)

    counts = {}
    patch_setters(d.get("actions", {}), counts)
    patch(d, counts)

    # also drop the null out of the two initialisers, for one less null in the file
    for n in ("InitialiseModelIDToWrite", "InitializeModelRevisionIDToWrite"):
        a = d["actions"].get(n)
        if a:
            for v in a["inputs"]["variables"]:
                if v.get("value") in ("@null", None):
                    v["value"] = SENTINEL
                    counts[n] = counts.get(n, 0) + 1

    print("changes:")
    for k in sorted(counts):
        print("   %-28s x%d" % (k, counts[k]))

    expect = {"ResetModelID": 1, "ResetModelRevisionID": 1, "Set_variable": 1,
              "Set_variable_1": 1, "Set_variable_2": 1, "Set_variable_3": 1,
              "item/Model/Id": 2, "item/ModelRevision/Id": 2,
              "InitialiseModelIDToWrite": 1, "InitializeModelRevisionIDToWrite": 1}
    if counts != expect:
        print("\nEXPECTED:")
        for k in sorted(expect):
            print("   %-28s x%d" % (k, expect[k]))
        sys.exit("\ndiff is not exactly what was intended -- nothing written")

    # no null may remain on any SetVariable
    s = json.dumps(d)
    left = s.count('"value": null')
    if left:
        sys.exit("still %d null-valued setter(s)" % left)

    out = os.path.join(FLOW, "_v008-candidate.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        json.dumps(j, indent=1, ensure_ascii=False))
    print("\nwrote %s" % os.path.relpath(out, ROOT))
    print("next: flow_version.py snapshot that file --local "
          "--note 'v008 integer variables never null'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
