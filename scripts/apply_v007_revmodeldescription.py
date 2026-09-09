# -*- coding: utf-8 -*-
"""Apply v007 -- the R22 `RevModelDescription` mapping correction -- to a flow definition.

This is the *only* change v007 carries, and it is urgent rather than tidy: the final
transfer-flow run rewrites `RevModelDescription` on ~1,000 rows, and the mapping live in
v006 re-installs the 110-character JSON blob on the 979 rows the repair script already
fixed. Left alone, the last act of the flow before it is deleted would be to undo R22.

Why the expression is shaped the way it is -- all three points from
`docs/r22-mapping-correction-2026-09-08.md`, read out of the platform, not retyped:

  * the internal name is `Description`; `Model Description` is the display name;
  * `Description` is `MultiChoice` -- the only multi-value field across `Order`, `Models`
    and `Model Revisions` -- so the value arriving is an **array**, and the bug is
    `string()` serialising it;
  * `?['Value']` is the single-Choice shape and yields nothing on an array, which is why
    the fix every other doc prescribed would have "succeeded" and changed nothing.

`coalesce` appears twice on purpose: Power Automate's `if()` evaluates both branches
rather than short-circuiting, so a bare `select(null, ...)` can throw even when the guard
is true.

Refuses to run if either write action is missing, if the key is absent, or if what is
there is not the exact defective expression this script was written to replace.

    python apply_v007_revmodeldescription.py <v006 definition.json> [-o <out.json>]
"""
import json, io, sys, os, copy, argparse

KEY = "item/RevModelDescription"

# What v006 has, verbatim. Matched exactly -- if the designer was hand-edited since,
# this script must stop rather than silently overwrite someone else's change.
EXPECTED_BEFORE = (
    "@if(empty(first(body('Filter_ModelRevision'))?['Description']), null, "
    "string(first(body('Filter_ModelRevision'))?['Description']))"
)

AFTER = (
    "@if(empty(coalesce(first(body('Filter_ModelRevision'))?['Description'], json('[]'))), null, "
    "join(select(coalesce(first(body('Filter_ModelRevision'))?['Description'], json('[]')), "
    "item()?['Value']), '; '))"
)

WRITES = (("No_Items_Found", "CreateOrderItem"), ("One_Item_Found", "UpdateOrderItem"))


def def_of(doc):
    """The `definition` object, whatever shape was handed in -- bare from the designer's
    JSON editor, wrapped in properties from an exported package."""
    return doc.get("properties", {}).get("definition", doc.get("definition", doc))


def locate(defn):
    sw = defn["actions"]["Apply_to_each"]["actions"]["CheckOrderMatch"]["actions"]["Switch"]
    out = {}
    for case, act in WRITES:
        out[act] = sw["cases"][case]["actions"][act]["inputs"]["parameters"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    src = a.src
    out = a.out or src.replace(".json", " +v007.json")

    doc = json.load(io.open(src, encoding="utf-8"))
    defn = def_of(doc)
    before = copy.deepcopy(doc)

    params = locate(defn)
    if set(params) != {"CreateOrderItem", "UpdateOrderItem"}:
        raise SystemExit("could not find both write actions -- aborting")

    for act, P in params.items():
        if KEY not in P:
            raise SystemExit("%s has no %s -- aborting" % (act, KEY))
        if P[KEY] == AFTER:
            raise SystemExit("%s is already corrected -- nothing to do" % act)
        if P[KEY] != EXPECTED_BEFORE:
            raise SystemExit(
                "%s holds an expression this script did not expect -- aborting rather "
                "than overwrite a hand edit.\n  found: %s" % (act, P[KEY]))

    for act, P in params.items():
        P[KEY] = AFTER

    io.open(out, "w", encoding="utf-8").write(json.dumps(doc, indent=2, ensure_ascii=False))

    pout = out.replace(".json", ".parameters.json")
    io.open(pout, "w", encoding="utf-8").write(json.dumps(
        {act: params[act] for act in ("CreateOrderItem", "UpdateOrderItem")},
        indent=2, ensure_ascii=False))

    # --- prove the change is confined ---
    after = json.load(io.open(out, encoding="utf-8"))
    pb, pa = locate(def_of(before)), locate(def_of(after))
    print("wrote %s" % os.path.basename(out))
    print("wrote %s  (the two parameter objects only)" % os.path.basename(pout))
    print()
    ok = True
    for act in pa:
        added = sorted(set(pa[act]) - set(pb[act]))
        removed = sorted(set(pb[act]) - set(pa[act]))
        changed = sorted(k for k in set(pa[act]) & set(pb[act]) if pa[act][k] != pb[act][k])
        nb = len([k for k in pb[act] if k.startswith("item/")])
        na = len([k for k in pa[act] if k.startswith("item/")])
        print("%-16s %d -> %d item/* fields   +%d  -%d  ~%d"
              % (act, nb, na, len(added), len(removed), len(changed)))
        if added or removed or changed != [KEY] or nb != na:
            ok = False
            print("   UNEXPECTED  added=%s removed=%s changed=%s" % (added, removed, changed))

    def blank(d):
        c = copy.deepcopy(d)
        for act, P in locate(def_of(c)).items():
            P.clear()
        return json.dumps(c, sort_keys=True)
    same = blank(before) == blank(after)
    txt = json.dumps(def_of(after))
    print()
    print("rest of the definition unchanged: %s" % same)
    print("toLower( count : %d (expect 34)" % txt.count("toLower("))
    print("'EC' count     : %d (expect 0)" % txt.count("'EC'"))
    print("string(...Description) left: %d (expect 0)"
          % txt.count("string(first(body('Filter_ModelRevision'))?['Description'])"))
    print()
    print("RESULT: %s" % ("OK -- exactly %s, on both actions, nothing else touched" % KEY
                          if (ok and same) else "PROBLEM -- do not paste this"))
    return 0 if (ok and same) else 1


if __name__ == "__main__":
    sys.exit(main())
