# -*- coding: utf-8 -*-
"""Apply D1/D2 -- the six missing column mappings -- to an exported flow definition.

Authored locally on purpose. Typing JSON into a live editor risks a structural
mistake reaching production; doing it here means the result is diffable and the
change is provably confined to six keys on two actions.

Adds nothing else, reorders nothing, and refuses to run if any target key already
exists or if either write action cannot be found.

    python apply_d1d2.py <exported definition.json> [-o <out.json>]

Writes the patched definition plus a `<out>.parameters.json` holding just the two
`inputs/parameters` objects, for an editor that only wants the action bodies.
"""
import json, io, sys, os, copy, argparse

# Target internal name -> expression. Both read out of the export / SharePoint
# /fields, never retyped: `Protector_x0020__x0026__x0020_Sw` is escaped and then
# TRUNCATED at 32 characters, and its Excel key is `..._x0023_`, not `#`.
MAPPINGS = {
    "item/Info_x002b_":
        "@item()?['Info+']",
    "item/Technical_x0020_Notes":
        "@item()?['Technical Notes']",
    "item/Protector_x0020__x0026__x0020_Sw":
        "@item()?['Protector & Switchgear Item _x0023_']",
    # 9 rows hold an Excel *time* value; without the 00:00:00 guard those write
    # "00:00:00" into a Text column, and Text does not reject anything.
    "item/Configuration":
        "@if(or(equals(trim(string(item()?['Configuration'])), ''), "
        "equals(trim(string(item()?['Configuration'])), '00:00:00')), null, "
        "item()?['Configuration'])",
    # int('') throws, and the throw surfaces as Action 'Switch' failed -- the same
    # signature as the EC bug, so the blank guard is load-bearing.
    "item/Section_x0020_Qty":
        "@if(equals(trim(string(item()?['Section Qty'])), ''), null, "
        "int(item()?['Section Qty']))",
    # Not from Excel -- reuses the Compose the flow already computes.
    "item/Order_Number_TextField":
        "@outputs('OrderNumberText')",
}

WRITES = (("No_Items_Found", "CreateOrderItem"), ("One_Item_Found", "UpdateOrderItem"))


def def_of(doc):
    """The `definition` object, whatever shape was handed in.

    The user copies the bare definition out of the designer's JSON editor, while
    an exported package wraps it in properties. Both must work, or the authoring
    step breaks depending on where the input came from."""
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
    out = a.out or src.replace(".json", " +d1d2.json")

    doc = json.load(io.open(src, encoding="utf-8"))
    defn = def_of(doc)
    before = copy.deepcopy(doc)

    params = locate(defn)
    if set(params) != {"CreateOrderItem", "UpdateOrderItem"}:
        raise SystemExit("could not find both write actions -- aborting")

    for act, P in params.items():
        clash = [k for k in MAPPINGS if k in P]
        if clash:
            raise SystemExit("%s already has %s -- aborting rather than overwrite"
                             % (act, clash))

    for act, P in params.items():
        for k, v in MAPPINGS.items():
            P[k] = v

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
        changed = [k for k in set(pa[act]) & set(pb[act]) if pa[act][k] != pb[act][k]]
        # Count item/* only, so this agrees with flow_version.py's fingerprint.
        # Counting every parameter would include dataset/table (and id on Update)
        # and report 52/61 where the other tool reports 50/58.
        nb = len([k for k in pb[act] if k.startswith("item/")])
        na = len([k for k in pa[act] if k.startswith("item/")])
        print("%-16s %d -> %d item/* fields   +%d  -%d  ~%d"
              % (act, nb, na, len(added), len(removed), len(changed)))
        if sorted(added) != sorted(MAPPINGS) or removed or changed:
            ok = False
            print("   UNEXPECTED  added=%s removed=%s changed=%s" % (added, removed, changed))

    # everything outside those two parameter objects must be byte-identical
    def blank(doc):
        c = copy.deepcopy(doc)
        for act, P in locate(def_of(c)).items():
            P.clear()
        return json.dumps(c, sort_keys=True)
    same = blank(before) == blank(after)
    print()
    print("rest of the definition unchanged: %s" % same)
    print("toLower( count: %d (expect 28)" % json.dumps(def_of(after)).count("toLower("))
    print("'EC' count    : %d (expect 0)" % json.dumps(def_of(after)).count("'EC'"))
    print()
    print("RESULT: %s" % ("OK -- exactly the 6 mappings, on both actions, nothing else touched"
                          if (ok and same) else "PROBLEM -- do not paste this"))
    return 0 if (ok and same) else 1


if __name__ == "__main__":
    sys.exit(main())
