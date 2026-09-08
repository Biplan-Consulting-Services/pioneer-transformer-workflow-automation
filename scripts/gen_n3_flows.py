# -*- coding: utf-8 -*-
"""Generate the three N3 parent-sync flow definitions as pasteable JSON.

    python scripts/gen_n3_flows.py

Writes workflow-data/n3-flows/<flow>.definition.json plus a MAPPING.md.

WHY A GENERATOR AND NOT HAND-WRITTEN JSON
  48 field mappings across three flows, each needing a target internal name, a
  source internal name and a read expression whose shape depends on the source
  column's type. Hand-typing that is how you get a silently-broken mapping --
  and this project has already lost 979 rows to exactly one such mistake (R22).

SOURCE INTERNAL NAMES WERE READ FROM THE PLATFORM on 2026-09-08 via
_api/v2.0/sites/root/lists/<id>/columns -- never guessed. Several are actively
misleading and would have broken the flow silently:

    Model Revisions          display                -> internal
      Client_Model_Code                             -> ModelName        (!)
      Model Description                             -> Description
      Model_Revion_ID                               -> ModelID          (!)
      Pioneer Model Code                            -> Model            (!)
      kVA                                           -> kVA_x0020_and_x0020_kV
    Models
      Latest Model Revision                         -> ModelRevision
      Model_ID                                      -> ModelID
      Model_Code                                    -> ModelName
    Order
      Order Number                                  -> Order_x0020_Number1  (trailing 1)
      Order Type                                    -> Order_x0020_Type1    (trailing 1)
      Initial Promised Date                         -> Initial_x0020_Promised_x0020_Dat  (truncated)
      New model to be created                       -> New_x0020_model_x0020_to_x0020_b  (truncated)

  NOTE THE CROSS-LIST COLLISIONS: `ModelID` is Model_ID on Models but
  Model_Revion_ID on Model Revisions. `Model` is a lookup on Order but the
  Pioneer Model Code on Model Revisions. `ModelName` is Model_Code on Models
  but Client_Model_Code on Model Revisions. Never reuse a name across lists.

READ SHAPES -- this is the R22 lesson encoded
  plain        triggerOutputs()?['body/F']
  choice/lookup triggerOutputs()?['body/F']?['Value']       <- WITHOUT ?['Value']
                                                               you store the raw
                                                               expanded reference,
                                                               which is what put
                                                               110 chars of JSON
                                                               into 979 rows
  multichoice  join(select(...,item()?['Value']), '; ')
"""
import json, io, os, collections

SITE = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio"
ORDER_ITEMS = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d"
LISTS = {
    "Order":           "6fe35dfe-2b7d-455a-abe3-056abb386733",
    "Models":          "b43a5140-0f9d-4ac1-9019-43b897074224",
    "Model Revisions": "e2ff8703-b590-4648-b181-9b47cf3883ba",
}
HOST = {"apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
        "operationId": None, "connectionName": "shared_sharepointonline"}

def host(op):
    h = dict(HOST); h["operationId"] = op; return h

# target internal name, source internal name, source kind
#   kind: plain | choice | lookup | multichoice
ORDER_MAP = [
    ("OrdClientDateStatus",   "ClientDateStatus",                  "choice"),
    ("OrdEngineeringRequired","EngineeringRequired",               "plain"),
    ("OrdIndexing",           "Indexing",                          "choice"),
    ("OrdInitialPromisedDate","Initial_x0020_Promised_x0020_Dat",   "plain"),
    ("OrdLDs",                "LDs",                               "plain"),
    ("OrdNewmodeltobecreated","New_x0020_model_x0020_to_x0020_b",   "choice"),
    ("OrdNote",               "Note",                              "plain"),
    ("OrdOrderDate",          "Order_x0020_Date",                  "plain"),
    ("OrdOrderNumber",        "Order_x0020_Number1",               "plain"),
    ("OrdOrderStatus",        "OrderStatus",                       "choice"),
    ("OrdOrderStep",          "Order_x0020_Step",                  "choice"),
    ("OrdOrderType",          "Order_x0020_Type1",                 "choice"),
    ("OrdPO",                 "PO",                                "plain"),
    ("OrdPrice",              "Price",                             "plain"),
    ("OrdProvinceState",      "Province_x002F_State",              "plain"),
    ("OrdQty",                "Qty",                               "plain"),
    ("OrdSalesNotes",         "SalesNotes",                        "plain"),
    ("OrdWETWETP",            "WET_x002d_WETP",                    "choice"),
]
# DELIBERATELY EXCLUDED: OrdOrderFolder (Order_x0020_Folder, a URL/hyperlink).
# Roadmap 38 is still an open decision -- a hyperlink column is an object on both
# read and write, the shape was never sourced, and a wrong one either fails every
# row or writes nothing. Left out rather than guessed. Add it once the shape is
# confirmed from one real trigger payload.

MODELS_MAP = [
    ("MdlEstimatedEffort",    "Estimated_x0020_Effort",            "plain"),
    ("MdlLatestModelRevision","ModelRevision",                     "lookup"),
    ("MdlModelID",            "ModelID",                           "plain"),
    ("MdlModificationStatus", "ModificationStatus",                "choice"),
    ("MdlParentModel",        "ParentModel",                       "lookup"),
]
REV_MAP = [
    ("RevCable",              "Cable",                             "plain"),
    ("RevClientModelCode",    "ModelName",                         "plain"),
    ("RevCopperLV",           "Copper_x0028_LV_x0029_",            "plain"),
    ("RevCoreType",           "Core_x0020_Type",                   "choice"),
    ("RevDuplicateOrder",     "DuplicateOrder",                    "lookup"),
    ("RevFamily",             "Family",                            "choice"),
    ("RevForm",               "Form",                              "plain"),
    ("RevJS",                 "JS_x0020__x0023_",                  "plain"),
    ("RevModelDescription",   "Description",                       "multichoice"),
    ("RevModelType",          "Model_x0020_Type",                  "choice"),
    ("RevModelRevionID",      "ModelID",                           "plain"),
    ("RevNotes",              "Notes",                             "plain"),
    ("RevOilAmount",          "OilAmount",                         "plain"),
    ("RevOilType",            "Oil_x0020_Type",                    "choice"),
    ("RevOvercoil",           "Overcoil",                          "plain"),
    ("RevPhases",             "Phases",                            "plain"),
    ("RevPioneerModelCode",   "Model",                             "lookup"),
    ("RevPrimaryVoltage",     "PrimaryVoltage",                    "plain"),
    ("RevSecondaryVoltage",   "SecondaryVoltage",                  "plain"),
    ("RevSpecDate",           "Spec_Date",                         "plain"),
    ("RevSpecID",             "SpecID",                            "plain"),
    ("RevSpecRevision",       "Spec_Revision",                     "plain"),
    ("RevWireHV",             "Wire_x0028_HV_x0029_",              "plain"),
    ("RevkVA",                "kVA_x0020_and_x0020_kV",            "plain"),
]

FLOWS = [
    ("Order Items - sync from Order",           "Order",           "OrderNumberId",   ORDER_MAP),
    ("Order Items - sync from Models",          "Models",          "ModelId",         MODELS_MAP),
    ("Order Items - sync from Model Revisions", "Model Revisions", "ModelRevisionId", REV_MAP),
]

def read_expr(src, kind):
    """The source-side expression, shaped by the source column's type."""
    b = "triggerOutputs()?['body/%s']" % src
    if kind in ("choice", "lookup"):
        return "%s?['Value']" % b
    if kind == "multichoice":
        # keep only the Values and join them -- never store the raw array
        return ("if(empty(coalesce(%s, json('[]'))), null, "
                "join(select(%s, item()?['Value']), '; '))" % (b, b))
    return b

def build(flow_name, parent, lookup_id_field, mapping):
    trig = "When_an_item_is_created_or_modified"
    loop = "Apply_to_each_unit"
    # 4a -- the change guard. coalesce BOTH sides to '' : null != '' in Power
    # Automate, so without it every row with a blank looks changed and the guard
    # never fires.
    cmps = ["not(equals(coalesce(items('%s')?['%s'], ''), coalesce(%s, '')))"
            % (loop, tgt, read_expr(src, kind)) for tgt, src, kind in mapping]
    guard = "@or(\n  " + ",\n  ".join(cmps) + "\n)"
    patch_params = {"dataset": SITE, "table": ORDER_ITEMS,
                    "id": "@items('%s')?['ID']" % loop}
    for tgt, src, kind in mapping:
        patch_params["item/%s" % tgt] = "@" + read_expr(src, kind)
    return {
        "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {"$authentication": {"defaultValue": {}, "type": "SecureObject"},
                       "$connections":    {"defaultValue": {}, "type": "Object"}},
        "triggers": {
            trig: {
                "type": "OpenApiConnectionWebhook",
                "inputs": {"parameters": {"dataset": SITE, "table": LISTS[parent]},
                           "host": host("GetOnUpdatedItems")},
                "splitOn": "@triggerOutputs()?['body/value']",
                # A trigger condition belongs on the ORDER ITEMS flow, not here:
                # writing to Order Items cannot re-trigger this flow, which reads
                # a different list. See the spec, block 2.
            }
        },
        "actions": {
            "Get_units_of_this_parent": {
                "runAfter": {},
                "type": "OpenApiConnection",
                "inputs": {
                    "parameters": {
                        "dataset": SITE, "table": ORDER_ITEMS,
                        # filter on the lookup's Id, never on a _TextField mirror:
                        # the mirrors are stale (their sync flows are off since
                        # Aug 21) so filtering on them silently misses rows
                        "$filter": "%s eq @{triggerOutputs()?['body/ID']}" % lookup_id_field,
                        "$top": 5000},
                    "host": host("GetItems")},
                "runtimeConfiguration": {"paginationPolicy": {"minimumItemCount": 5000}}
            },
            loop: {
                "foreach": "@outputs('Get_units_of_this_parent')?['body/value']",
                "runAfter": {"Get_units_of_this_parent": ["Succeeded"]},
                "type": "Foreach",
                "actions": {
                    "needsUpdate": {"runAfter": {}, "type": "Compose", "inputs": guard},
                    "Only_if_something_changed": {
                        "runAfter": {"needsUpdate": ["Succeeded"]},
                        "type": "If",
                        "expression": {"equals": ["@outputs('needsUpdate')", True]},
                        "actions": {
                            "Update_unit": {
                                "runAfter": {}, "type": "OpenApiConnection",
                                "inputs": {"parameters": patch_params, "host": host("PatchItem")}
                            }
                        }
                    }
                }
            }
        }
    }

def main():
    outdir = os.path.join("workflow-data", "n3-flows")
    os.makedirs(outdir, exist_ok=True)
    md = ["# N3 flow definitions — generated\n",
          "`python scripts/gen_n3_flows.py`. Source internal names read from the platform "
          "2026-09-08; read shapes follow the R22 lesson (`?['Value']` on every Choice and "
          "Lookup source).\n"]
    for name, parent, lookup, mapping in FLOWS:
        d = build(name, parent, lookup, mapping)
        fn = name.replace(" ", "_").replace("-", "") + ".definition.json"
        p = os.path.join(outdir, fn)
        io.open(p, "w", encoding="utf-8", newline="\n").write(
            json.dumps(d, indent=2, ensure_ascii=False))
        kinds = collections.Counter(k for _, _, k in mapping)
        print("wrote %-58s %2d fields  %s" % (p, len(mapping), dict(kinds)))
        md.append("\n## `%s`\n" % name)
        md.append("Trigger list **%s** · fan-out filter `%s` · **%d** fields\n" % (parent, lookup, len(mapping)))
        md.append("| → `Order Items` | ← source internal | source kind | read expression |")
        md.append("|---|---|---|---|")
        for tgt, src, kind in mapping:
            md.append("| `%s` | `%s` | %s | `%s` |" % (tgt, src, kind, read_expr(src, kind)))
    md.append("\n## Deliberately excluded\n")
    md.append("`OrdOrderFolder` (`Order_x0020_Folder`, URL). Roadmap 38 is an open decision — a "
              "hyperlink is an object on both read and write, the shape was never sourced, and a "
              "wrong one either fails every row or writes nothing. Confirm the shape from one "
              "real trigger payload, then add it.\n")
    io.open(os.path.join(outdir, "MAPPING.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md))
    print("wrote %s" % os.path.join(outdir, "MAPPING.md"))

if __name__ == "__main__":
    main()
