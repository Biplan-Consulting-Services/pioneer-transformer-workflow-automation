# -*- coding: utf-8 -*-
"""v006 -- the code-review fixes plus the fetch-once restructure, in one change.

Combines what the review recommended splitting, at the user's request. Every
change is asserted afterwards; the script refuses to emit a definition that does
not match what it intended.

WHAT IT DOES

  Critical fixes (review sections 1, 2, 3a)
    F1  null both model variables at the TOP of every iteration. They are
        run-scoped, and on the SAModelUnmatched path neither was set -- so the
        write used the PREVIOUS row's model. Deterministic, silent, wrong.
    F2  give CheckOrderMatch and CheckMatchCountModels an `else` that records
        the skipped unit, so "982 iterations" stops meaning "982 rows written".
    F3  delete GetResolvedOrder. Get_Orders already returned that row in full.

  Fetch-once restructure (review section 4, the user's proposal)
    R1  four upfront `Get items`, each with pagination 5000 -- Get items returns
        100 rows by DEFAULT, and all four lists exceed that.
    R2  replace the three unconditional per-row queries with Filter array.
    R3  KEEP GetModels live. It sits in the SA-only else branch (~42 rows/run),
        so caching it saves nothing -- and filtering it in memory would depend
        on how the connector shapes a lookup inside an array, which I have not
        observed. Not worth the uncertainty for 42 calls.

  New columns
    C1  5 `Mdl*` from the filtered Models record.
    C2  24 `Rev*` from a filtered Model Revisions record -- free now that the
        list is cached, where a per-row Get item would have cost ~1,019 calls.
    C3  repoint the 5 `Ord*` columns that UpdateOrder also writes so they use
        UpdateOrder's OWN expressions, read out of the definition rather than
        retyped. Those five are Excel-sourced (OrderStatus is the constant
        'Active'), so this removes the snapshot-staleness question entirely
        instead of choosing a side of it.
    C4  blank-guard Update_item's Family write. 385 of 1,019 source rows have a
        blank Family, and the write is unconditional, so it erases as well as
        fills (roadmap 35).

  Net: 9 connector calls per row -> 3, plus ~42 conditional. ~9,171 -> ~3,100.
"""
import json, io, sys, os, copy, argparse

SITE = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio"
LISTS = {
    "Order":           "6fe35dfe-2b7d-455a-abe3-056abb386733",
    "Models":          "b43a5140-0f9d-4ac1-9019-43b897074224",
    "Model Revisions": "e2ff8703-b590-4648-b181-9b47cf3883ba",
    "Order Items":     "d6468ec5-c7b5-44a3-8ce0-f81f059b671d",
}
FETCH = [("Get_All_Orders", "Order"), ("Get_All_Models", "Models"),
         ("Get_All_ModelRevisions", "Model Revisions"), ("Get_All_OrderItems", "Order Items")]

MDL = "first(body('Filter_Models'))"
REV = "first(body('Filter_ModelRevision'))"

# (target, source internal, kind).  kind: text | num | choice | lookup | date | multi
MDL_MAP = [
    ("MdlModelID",             "ModelID",                "text"),
    ("MdlModificationStatus",  "ModificationStatus",     "choice"),
    ("MdlEstimatedEffort",     "Estimated_x0020_Effort", "num"),
    ("MdlLatestModelRevision", "ModelRevision",          "lookup"),
    ("MdlParentModel",         "ParentModel",            "lookup"),
]
REV_MAP = [
    ("RevModelRevionID",    "ModelID",                 "text"),
    ("RevSpecID",           "SpecID",                  "text"),
    ("RevClientModelCode",  "ModelName",               "text"),
    ("RevNotes",            "Notes",                   "text"),
    ("RevkVA",              "kVA_x0020_and_x0020_kV",  "num"),
    ("RevModelType",        "Model_x0020_Type",        "choice"),
    ("RevOilType",          "Oil_x0020_Type",          "choice"),
    ("RevCoreType",         "Core_x0020_Type",         "choice"),
    ("RevPhases",           "Phases",                  "num"),
    ("RevOilAmount",        "OilAmount",               "num"),
    ("RevCable",            "Cable",                   "text"),
    ("RevForm",             "Form",                    "text"),
    ("RevCopperLV",         "Copper_x0028_LV_x0029_",  "text"),
    ("RevWireHV",           "Wire_x0028_HV_x0029_",    "text"),
    ("RevOvercoil",         "Overcoil",                "num"),
    ("RevModelDescription", "Description",             "multi"),
    ("RevJS",               "JS_x0020__x0023_",        "text"),
    ("RevSpecRevision",     "Spec_Revision",           "text"),
    ("RevSpecDate",         "Spec_Date",               "date"),
    ("RevPrimaryVoltage",   "PrimaryVoltage",          "num"),
    ("RevSecondaryVoltage", "SecondaryVoltage",        "num"),
    ("RevPioneerModelCode", "Model",                   "lookup"),
    ("RevDuplicateOrder",   "DuplicateOrder",          "lookup"),
    ("RevFamily",           "Family",                  "choice"),
]
# The 5 Ord* columns UpdateOrder also writes -> reuse ITS expression (C3).
ORD_FROM_UPDATEORDER = {
    "OrdClientDateStatus":    "item/ClientDateStatus/Value",
    "OrdEngineeringRequired": "item/EngineeringRequired",
    "OrdLDs":                 "item/LDs",
    "OrdOrderStatus":         "item/OrderStatus/Value",
    "OrdSalesNotes":          "item/SalesNotes",
}
WRITES = (("No_Items_Found", "CreateOrderItem"), ("One_Item_Found", "UpdateOrderItem"))


def def_of(doc):
    return doc.get("properties", {}).get("definition", doc.get("definition", doc))


def mapping(src_expr, field, kind):
    """One read off a cached record.

    The lookup/choice legs use the connector's own flattened `Name/Value` key
    form -- the same accessor the working code already uses for
    `?['ModelRevision/Id']`, rather than a nested `?['X']?['Value']` guess.
    """
    base = "%s?['%s']" % (src_expr, field)
    if kind == "choice" or kind == "lookup":
        return "@%s?['%s/Value']" % (src_expr, field)
    if kind == "date":
        return ("@if(empty(%s), null, formatDateTime(%s, 'yyyy-MM-dd'))" % (base, base))
    if kind == "multi":
        # A multi-choice arrives as an array. string() never throws whatever the
        # element shape is, and the target is a Note column, so this is lossless
        # if occasionally ugly. Switch to join() once the shape is observed.
        return "@if(empty(%s), null, string(%s))" % (base, base)
    return "@" + base


def sp_get_items(name, list_key, host_template, runafter):
    node = copy.deepcopy(host_template)
    node["runAfter"] = runafter
    node["runtimeConfiguration"] = {"paginationPolicy": {"minimumItemCount": 5000}}
    node["inputs"]["parameters"] = {"dataset": SITE, "table": LISTS[list_key]}
    node["inputs"].pop("metadata", None)
    return node


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("-o", "--out")
    a = ap.parse_args()
    out = a.out or a.src.replace(".json", " +v006.json")

    doc = json.load(io.open(a.src, encoding="utf-8"))
    before = copy.deepcopy(doc)
    defn = def_of(doc)
    top = defn["actions"]
    loop = top["Apply_to_each"]["actions"]
    co = loop["CheckOrderMatch"]["actions"]
    sw = co["Switch"]

    # a clean SharePoint GetItems node to clone the host/auth from
    tmpl = copy.deepcopy(co["Get_Order_items"])
    tmpl.pop("runtimeConfiguration", None)

    # ---- C3: capture UpdateOrder's own expressions BEFORE anything moves ----
    uo = co["UpdateOrder"]["inputs"]["parameters"]
    ord_reuse = {}
    for tgt, key in ORD_FROM_UPDATEORDER.items():
        if key not in uo:
            raise SystemExit("UpdateOrder has no %s -- cannot reuse its expression" % key)
        ord_reuse[tgt] = uo[key]

    # ---------------------------------------------------------- R1: fetches --
    prev = {"List_rows_present_in_a_table_BO": ["Succeeded"]}
    for name, key in FETCH:
        if name in top:
            raise SystemExit("%s already exists -- v006 looks already applied" % name)
        top[name] = sp_get_items(name, key, tmpl, prev)
        prev = {name: ["Succeeded"]}
    top["Filter_array"]["runAfter"] = prev

    # ---- F2: an array to record skipped rows -------------------------------
    top["InitSkippedUnits"] = {
        "type": "InitializeVariable",
        "runAfter": {"InitializeModelRevisionIDToWrite": ["Succeeded"]},
        "inputs": {"variables": [{"name": "SkippedUnits", "type": "array"}]},
    }
    top["Apply_to_each"]["runAfter"] = {"InitSkippedUnits": ["Succeeded"]}

    # ---------------------------------------------- F1 + R2: the loop chain --
    loop["ResetModelID"] = {
        "type": "SetVariable", "runAfter": {"RawOrder": ["Succeeded"]},
        "inputs": {"name": "ModelIDToWrite", "value": None}}
    loop["ResetModelRevisionID"] = {
        "type": "SetVariable", "runAfter": {"ResetModelID": ["Succeeded"]},
        "inputs": {"name": "ModelRevisionIDToWrite", "value": None}}
    loop["Filter_BO"]["runAfter"] = {"ResetModelRevisionID": ["Succeeded"]}

    loop["PoItemNumber"] = {
        "type": "Compose", "runAfter": {"ItemStatus": ["Succeeded"]},
        "inputs": "@trim(string(coalesce(item()?['PO Item _x0023_'], '')))"}

    def q(name, source, where, after):
        loop[name] = {"type": "Query", "runAfter": {after: ["Succeeded"]},
                      "inputs": {"from": "@outputs('%s')?['body/value']" % source,
                                 "where": where}}

    q("Filter_Orders", "Get_All_Orders",
      "@equals(trim(string(coalesce(item()?['Order_x0020_Number1'], ''))), outputs('OrderNumberText'))",
      "PoItemNumber")
    q("Filter_Models", "Get_All_Models",
      "@equals(trim(string(coalesce(item()?['ModelName'], ''))), outputs('PoItemNumber'))",
      "Filter_Orders")
    # null revision id -> equals(ID, null) is false for every row -> empty. Safe.
    q("Filter_ModelRevision", "Get_All_ModelRevisions",
      "@equals(item()?['ID'], %s?['ModelRevision/Id'])" % MDL, "Filter_Models")
    q("Filter_OrderItems", "Get_All_OrderItems",
      "@equals(trim(string(coalesce(item()?['Title'], ''))), outputs('RawOrder'))",
      "Filter_ModelRevision")

    loop["CheckOrderMatch"]["runAfter"] = {"Filter_OrderItems": ["Succeeded"]}
    loop["CheckMatchCountModels"]["runAfter"] = {"CheckOrderMatch": ["Succeeded"]}
    loop["CheckMatchCountModels"]["expression"] = {
        "and": [{"equals": ["@length(body('Filter_Models'))", 1]}]}
    loop["CheckOrderMatch"]["expression"] = {
        "and": [{"equals": ["@length(body('Filter_Orders'))", 1]}]}

    for dead in ("Get_Orders", "GetModels1"):
        if dead not in loop:
            raise SystemExit("expected %s in the loop" % dead)
        del loop[dead]
    for dead in ("Get_Order_items", "GetResolvedOrder"):   # F3
        if dead not in co:
            raise SystemExit("expected %s in CheckOrderMatch" % dead)
        del co[dead]

    co["ResolvedOrderId"]["inputs"] = "@first(body('Filter_Orders'))?['ID']"
    co["ClientIDToWrite"]["runAfter"] = {"ResolvedOrderId": ["Succeeded"]}
    sw["runAfter"] = {"Condition": ["Succeeded"]}
    sw["expression"] = "@length(body('Filter_OrderItems'))"

    # Every read of a deleted action must be repointed. Doing this as a single
    # text pass over the whole document is what catches the ones that are easy
    # to forget -- UpdateOrderItem's `id` came from Get_Order_items, and
    # ResolvedModelCode / ResolvedModelRevisionID came from GetModels1. Missing
    # either would have failed every update, or resolved every revision to null.
    blob = json.dumps(doc)
    for a, b in (
        # collection reads: outputs('X')?['body/value']  ->  body('Filter_Y')
        ("outputs('Get_Order_items')?['body/value']", "body('Filter_OrderItems')"),
        ("outputs('GetModels1')?['body/value']",      "body('Filter_Models')"),
        ("outputs('Get_Orders')?['body/value']",      "body('Filter_Orders')"),
        # single-item reads: outputs('GetResolvedOrder')?['body/X']  ->  first(...)?['X']
        ("outputs('GetResolvedOrder')?['body/",       "first(body('Filter_Orders'))?['"),
    ):
        blob = blob.replace(a, b)
    doc = json.loads(blob)
    defn = def_of(doc); top = defn["actions"]; loop = top["Apply_to_each"]["actions"]
    co = loop["CheckOrderMatch"]["actions"]; sw = co["Switch"]

    # ---- F2: the else branches --------------------------------------------
    loop["CheckOrderMatch"]["else"] = {"actions": {"RecordSkippedOrder": {
        "type": "AppendToArrayVariable", "runAfter": {},
        "inputs": {"name": "SkippedUnits",
                   "value": "@concat(outputs('RawOrder'), ' | order not resolved: ',"
                            " string(length(body('Filter_Orders'))), ' matches for \"',"
                            " outputs('OrderNumberText'), '\"')"}}}}
    loop["CheckMatchCountModels"]["else"] = {"actions": {"RecordSkippedModel": {
        "type": "AppendToArrayVariable", "runAfter": {},
        "inputs": {"name": "SkippedUnits",
                   "value": "@concat(outputs('RawOrder'), ' | model not resolved: ',"
                            " string(length(body('Filter_Models'))), ' matches for \"',"
                            " outputs('PoItemNumber'), '\" (Model Revisions not updated)')"}}}}

    # ---- C4: blank-guard the Family write ---------------------------------
    up = loop["CheckMatchCountModels"]["actions"]["Update_item"]["inputs"]["parameters"]
    up["item/Family/Value"] = ("@if(empty(trim(string(coalesce(item()?['Family'], '')))), "
                               "null, item()?['Family'])")

    # ---- C1 + C2 + C3: the mappings ---------------------------------------
    new = {}
    for tgt, src, kind in MDL_MAP:
        new["item/" + tgt] = mapping(MDL, src, kind)
    for tgt, src, kind in REV_MAP:
        new["item/" + tgt] = mapping(REV, src, kind)
    for tgt, expr in ord_reuse.items():
        new["item/" + tgt] = expr

    for case, act in WRITES:
        P = sw["cases"][case]["actions"][act]["inputs"]["parameters"]
        P.update(new)

    io.open(out, "w", encoding="utf-8").write(json.dumps(doc, indent=2, ensure_ascii=False))

    # =================================================================== verify
    after = json.load(io.open(out, encoding="utf-8"))
    da = def_of(after); ta = da["actions"]; la = ta["Apply_to_each"]["actions"]
    ca = la["CheckOrderMatch"]["actions"]; sa = ca["Switch"]
    blob = json.dumps(da)
    ok = True

    def chk(label, cond):
        nonlocal ok
        print("  %-56s %s" % (label, "PASS" if cond else "**FAIL**"))
        ok = ok and cond

    print("wrote %s\n" % os.path.basename(out))
    print("STRUCTURE")
    chk("4 upfront Get items added", all(n in ta for n, _ in FETCH))
    chk("all 4 paginate at 5000",
        all(ta[n].get("runtimeConfiguration", {}).get("paginationPolicy", {})
            .get("minimumItemCount") == 5000 for n, _ in FETCH))
    chk("Get_Orders / GetModels1 removed",
        "Get_Orders" not in la and "GetModels1" not in la)
    chk("Get_Order_items / GetResolvedOrder removed",
        "Get_Order_items" not in ca and "GetResolvedOrder" not in ca)
    DELETED = ("GetResolvedOrder", "Get_Orders", "GetModels1", "Get_Order_items")
    dangling = [n for n in DELETED if ("'%s'" % n) in blob]
    chk("no reference to any deleted action %s" % (dangling or ""), not dangling)
    chk("GetModels kept live (SA-only branch)",
        "GetModels" in ca["Condition"]["else"]["actions"])
    chk("4 Filter array actions added",
        all(n in la for n in ("Filter_Orders", "Filter_Models",
                              "Filter_ModelRevision", "Filter_OrderItems")))

    print("\nCONNECTOR CALLS")
    def count(actions, in_loop=False, d=0):
        n = 0
        for _, node in actions.items():
            if node.get("type") == "OpenApiConnection" and in_loop:
                n += 1
            for k in ("actions",):
                if node.get(k):
                    n += count(node[k], in_loop or node.get("type") == "Foreach")
            if node.get("else", {}).get("actions"):
                n += count(node["else"]["actions"], in_loop or node.get("type") == "Foreach")
            for c in node.get("cases", {}).values():
                if c.get("actions"):
                    n += count(c["actions"], in_loop or node.get("type") == "Foreach")
        return n
    per_row = count(ta)
    # The two Switch cases are MUTUALLY EXCLUSIVE -- exactly one runs per row --
    # and GetModels only runs for SA units. So the honest per-row figure is
    # unconditional writes + one write, not the raw action count.
    exclusive = 1        # CreateOrderItem xor UpdateOrderItem
    conditional = 1      # GetModels, SA-only (~42 of 1019 rows)
    effective = per_row - exclusive - conditional
    print("  connector actions inside the loop : %d  (was 9)" % per_row)
    print("  every row                         : %d  (2 writes + 1 of Create/Update)" % effective)
    print("  plus SA-only GetModels            : ~42 of 1019 rows")
    chk("every-row calls down to 3", effective == 3)

    print("\nCRITICAL FIXES")
    chk("F1 both model variables reset per iteration",
        la.get("ResetModelID", {}).get("type") == "SetVariable"
        and la.get("ResetModelRevisionID", {}).get("type") == "SetVariable")
    def chain_into(scope, start):
        out, cur = [], start
        while cur:
            out.append(cur)
            ra = list(scope.get(cur, {}).get("runAfter", {}).keys())
            cur = ra[0] if ra else None
        return out
    into_com = chain_into(la, "CheckOrderMatch")
    chk("F1 both resets precede CheckOrderMatch (so precede Condition)",
        "ResetModelID" in into_com and "ResetModelRevisionID" in into_com)
    chk("F1 both reset to null",
        la["ResetModelID"]["inputs"]["value"] is None
        and la["ResetModelRevisionID"]["inputs"]["value"] is None)
    chk("F2 CheckOrderMatch has an else", bool(la["CheckOrderMatch"].get("else", {}).get("actions")))
    chk("F2 CheckMatchCountModels has an else",
        bool(la["CheckMatchCountModels"].get("else", {}).get("actions")))
    chk("F2 SkippedUnits array initialised", "InitSkippedUnits" in ta)

    print("\nMAPPINGS")
    for case, act in WRITES:
        P = sa["cases"][case]["actions"][act]["inputs"]["parameters"]
        keys = [k for k in P if k.startswith("item/")]
        mdl = [k for k in keys if k.startswith("item/Mdl")]
        rev = [k for k in keys if k.startswith("item/Rev")]
        print("  %-16s %d item/*   Mdl* %d   Rev* %d" % (act, len(keys), len(mdl), len(rev)))
        chk("  %s has 5 Mdl*" % act, len(mdl) == 5)
        chk("  %s has 24 Rev*" % act, len(rev) == 24)
        for tgt, expr in ord_reuse.items():
            chk("  %s %s reuses UpdateOrder's expression" % (act, tgt),
                P.get("item/" + tgt) == expr)

    print("\nGUARDS")
    chk("C4 Family write is blank-guarded",
        "empty(trim(string(coalesce(item()?['Family']" in
        la["CheckMatchCountModels"]["actions"]["Update_item"]["inputs"]["parameters"]["item/Family/Value"])
    chk("toLower count still 34", blob.count("toLower(") == 34)
    chk("no unguarded 'EC' returned", blob.count("'EC'") == 0)
    chk("date reads reformat to yyyy-MM-dd", blob.count("'yyyy-MM-dd'") >= 6)

    print("\nRESULT: %s" % ("OK" if ok else "PROBLEM -- do not paste this"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
