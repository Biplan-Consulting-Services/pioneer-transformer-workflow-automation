# -*- coding: utf-8 -*-
"""v005 -- populate the 18 `Order - X` parent columns during the one-time run.

The user's point: rather than create the parent columns and leave them empty for
the N3 sync flows to backfill later, populate them in the same run that is
already touching every row. For the Order group this is free -- the loop already
holds the full Order record.

WHY IT IS FREE
  Inside Apply_to_each, CheckOrderMatch runs a strictly serial chain:
      ResolvedOrderId -> GetResolvedOrder -> ClientIDToWrite -> Condition
                      -> Get_Order_items -> Switch -> {Create,Update}OrderItem
  GetResolvedOrder is a `Get item` on the Order list and completes before the
  write actions. So these 18 mappings add ZERO connector calls.

  Contrast the other two parent groups, deliberately NOT in this change:
    Models (5)          GetModels1 runs on a PARALLEL branch to the write path
                        (both hang off ItemStatus), so referencing it from the
                        writes is not guaranteed to have completed -- in Logic
                        Apps that yields null, silently. Needs the branches
                        serialised first.
    Model Revisions (24) the loop holds only the revision's ID, never the record.
                        Needs a new Get item per row: ~1,019 extra calls.

SOURCE NAMES ARE READ, NEVER TYPED
  Internal names come from the Order list's own export schema. Several are
  unguessable:
      Initial Promised Date   -> Initial_x0020_Promised_x0020_Dat   (truncated
                                 mid-word at 32 chars)
      New model to be created -> New_x0020_model_x0020_to_x0020_b   (truncated)
      Order Number            -> Order_x0020_Number1                (trailing 1)
      Order Type              -> Order_x0020_Type1                  (trailing 1)
      Province/State          -> Province_x002F_State  (Name has a capital F
                                 while StaticName has a lowercase f; the
                                 connector binds to Name)
"""
import json, io, sys, os, copy, argparse

G = "outputs('GetResolvedOrder')"

# (target internal, source internal on Order, source SharePoint type)
# Types verified from the Order export's field XML, not from a regex over
# attribute order -- `Indexing` reads Type="Choice" but carries
# FromBaseType="FALSE" first, which a naive scan mistakes for its type.
MAP = [
    ("OrdOrderNumber",         "Order_x0020_Number1",              "Text"),
    ("OrdQty",                 "Qty",                              "Number"),
    ("OrdOrderType",           "Order_x0020_Type1",                "Choice"),
    ("OrdOrderDate",           "Order_x0020_Date",                 "DateTime"),
    ("OrdInitialPromisedDate", "Initial_x0020_Promised_x0020_Dat", "DateTime"),
    ("OrdOrderStep",           "Order_x0020_Step",                 "Choice"),
    ("OrdNote",                "Note",                             "Note"),
    ("OrdPO",                  "PO",                               "Text"),
    ("OrdPrice",               "Price",                            "Currency"),
    ("OrdProvinceState",       "Province_x002F_State",             "Text"),
    ("OrdWETWETP",             "WET_x002d_WETP",                   "Choice"),
    ("OrdIndexing",            "Indexing",                         "Choice"),
    ("OrdNewmodeltobecreated", "New_x0020_model_x0020_to_x0020_b",  "Choice"),
    ("OrdEngineeringRequired", "EngineeringRequired",               "Boolean"),
    ("OrdLDs",                 "LDs",                               "Boolean"),
    ("OrdClientDateStatus",    "ClientDateStatus",                  "Choice"),
    ("OrdSalesNotes",          "SalesNotes",                        "Note"),
    ("OrdOrderStatus",         "OrderStatus",                       "Choice"),
]

# 🔴 DELIBERATELY EXCLUDED -- OrdOrderFolder / Order_x0020_Folder, type URL.
# A SharePoint hyperlink column is not a string on either side: reading gives an
# object and writing wants one. I could not establish the exact shape the
# connector expects from anything already in this repo, and a wrong shape on a
# write either fails the row -- surfacing as `Action 'Switch' failed`, across
# 1,019 rows -- or writes nothing at all. It is one folder link on a column no
# staff view shows, so guessing is not worth that. Confirm the shape from the D4
# smoke test's raw inputs, then add it. Roadmap item 38.

WRITES = (("No_Items_Found", "CreateOrderItem"), ("One_Item_Found", "UpdateOrderItem"))


def def_of(doc):
    return doc.get("properties", {}).get("definition", doc.get("definition", doc))


def locate(defn):
    sw = defn["actions"]["Apply_to_each"]["actions"]["CheckOrderMatch"]["actions"]["Switch"]
    return {act: sw["cases"][case]["actions"][act]["inputs"]["parameters"]
            for case, act in WRITES}


def expr(src, sptype):
    """The expression to read one Order field.

    Choice returns an object, so it needs the /Value leg -- reading `body/X` on a
    Choice writes the object's stringification, which is garbage that no column
    type rejects.

    DateTime -> DateOnly is reformatted rather than copied. Copying an ISO
    instant into a Date-Only column is exactly the UTC-midnight mechanism the
    whole backfill exists to undo; formatDateTime to a bare date lands as
    site-local midnight. Guarded because formatDateTime(null) throws.
    """
    if sptype == "Choice":
        return "@%s?['body/%s/Value']" % (G, src)
    if sptype == "DateTime":
        return ("@if(empty(%s?['body/%s']), null, formatDateTime(%s?['body/%s'], 'yyyy-MM-dd'))"
                % (G, src, G, src))
    return "@%s?['body/%s']" % (G, src)


MAPPINGS = {"item/%s" % tgt: expr(src, t) for tgt, src, t in MAP}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("-o", "--out")
    a = ap.parse_args()
    out = a.out or a.src.replace(".json", " +v005.json")

    doc = json.load(io.open(a.src, encoding="utf-8"))
    before = copy.deepcopy(doc)
    defn = def_of(doc)

    # The mappings reference GetResolvedOrder, so it must exist and must precede
    # the writes. Assert both rather than assume the graph is what I last read.
    co = defn["actions"]["Apply_to_each"]["actions"]["CheckOrderMatch"]["actions"]
    if "GetResolvedOrder" not in co:
        raise SystemExit("GetResolvedOrder is missing -- the mappings would read null")
    chain, cur, seen = [], "Switch", set()
    while cur and cur not in seen:
        seen.add(cur); chain.append(cur)
        after = list(co.get(cur, {}).get("runAfter", {}).keys())
        cur = after[0] if after else None
    if "GetResolvedOrder" not in chain:
        raise SystemExit("Switch does not run after GetResolvedOrder (chain: %s) -- "
                         "the reads could yield null silently" % " <- ".join(chain))

    for act, P in locate(defn).items():
        clash = [k for k in MAPPINGS if k in P]
        if clash:
            raise SystemExit("%s already has %s -- aborting" % (act, clash))
    for act, P in locate(defn).items():
        P.update(MAPPINGS)

    io.open(out, "w", encoding="utf-8").write(json.dumps(doc, indent=2, ensure_ascii=False))

    # ----------------------------------------------------------- verify -----
    after_doc = json.load(io.open(out, encoding="utf-8"))
    pa, pb = locate(def_of(after_doc)), locate(def_of(before))
    ok = True
    print("wrote %s\n" % os.path.basename(out))
    print("chain into Switch: %s\n" % " <- ".join(chain))
    for act in pa:
        add = sorted(set(pa[act]) - set(pb[act]))
        rm = sorted(set(pb[act]) - set(pa[act]))
        ch = [k for k in set(pa[act]) & set(pb[act]) if pa[act][k] != pb[act][k]]
        nb = len([k for k in pb[act] if k.startswith("item/")])
        na = len([k for k in pa[act] if k.startswith("item/")])
        print("%-16s %d -> %d item/*   +%d  -%d  ~%d" % (act, nb, na, len(add), len(rm), len(ch)))
        if sorted(add) != sorted(MAPPINGS) or rm or ch:
            ok = False; print("   UNEXPECTED +%s -%s ~%s" % (add, rm, ch))

    def strip(d):
        c = copy.deepcopy(def_of(d))
        sw = c["actions"]["Apply_to_each"]["actions"]["CheckOrderMatch"]["actions"]["Switch"]
        for case, act in WRITES:
            sw["cases"][case]["actions"][act]["inputs"]["parameters"].clear()
        return json.dumps(c, sort_keys=True)
    rest = strip(after_doc) == strip(before)
    print("\nrest of the definition untouched : %s" % rest)

    s = json.dumps(def_of(after_doc))
    checks = {
        "Choice mappings use the /Value leg":
            s.count("/Value']") >= 2 * sum(1 for _, _, t in MAP if t == "Choice"),
        "DateTime mappings reformat to yyyy-MM-dd":
            s.count("'yyyy-MM-dd'") == 2 * sum(1 for _, _, t in MAP if t == "DateTime"),
        "no reference to the parallel GetModels1": "GetModels1'" not in json.dumps(MAPPINGS),
        "OrdOrderFolder deliberately absent": "item/OrdOrderFolder" not in s,
        "toLower count unchanged (34)": s.count("toLower(") == 34,
    }
    for k, v in checks.items():
        print("  %-42s %s" % (k, "PASS" if v else "**FAIL**"))
        ok = ok and v

    print("\nRESULT: %s" % ("OK -- 18 Order mappings on both actions, 0 extra connector calls"
                            if (ok and rest) else "PROBLEM -- do not paste this"))
    return 0 if (ok and rest) else 1


if __name__ == "__main__":
    sys.exit(main())
