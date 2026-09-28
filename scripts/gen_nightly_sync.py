#!/usr/bin/env python3
"""Generate Order Items - Nightly Sync v007 (board E11; spec docs/nightly-sync-review-2026-09-25.md §5-6f,
gate: docs/archive-all-lists-design-2026-09-27.md §5).

    python scripts/gen_nightly_sync.py            # -> workflow-data/_generated/Order_Items_Nightly_Sync_v007.json

History: v001 (user, hand-built) deleted on the Excel archive alone, sequentially, uncapped. v003 added
the double confirmation, cap 50 and the dry run. v005 put both connections on solution references.
v006 read TableArchiveFRM10_12 by name. v007 (2026-09-28) moves the gate to the new per-list archive
table and adds stage D:

  B  RECALC  - gen_nightly_cleanup.py's stage B, reused by import (not copied). Unchanged.
  C  ARCHIVE DELETE - a unit from C1 (Order Items: Location = Livraison AND ItemStatus = Delivered) is
     deleted only when ALL of these hold (archive design §5):
       a. TableArchiveOrderItems has a row with the same Id, at Livraison, with ItemStatus = Delivered;
       b. that row's Modified text equals the unit's Modified EXACTLY (the archive holds the unit's
          latest state - an edit after the last archive refresh blocks the delete);
       c. the unit's Modified is at least GraceDays (7) ago, as a timestamp (ticks), no date truncation.
     C2 reads TableArchiveOrderItems BY NAME, filtered Location eq 'Livraison' (the archive table
     holds display text and raw ISO text, so v006's Excel-serial parsing is gone). Cap 50,
     DeleteEnabled = false (dry run), no variables, delete loop at concurrency 10.
  D  EMPTY-ROW CLEANUP (user, 2026-09-28: grid-view accidents like Ids 1256/1257) - from C1b, no extra
     read: Title, OrderNumber, Model, Client, ModelRevision and Location all empty, never edited
     (Created == Modified), created at least 24 h ago. Cap EmptyRowCap = 10 (over it: recycle nothing,
     report). Same DeleteEnabled switch: dry run composes "would recycle <Id>".
  Trigger: daily 01:30 "Eastern Standard Time" - no UTC startTime (DST-proof). Unchanged.

C7_Summary fields, v006 -> v007:
  deleteEnabled, cap, B_touched, C_candidates_OrderItems, C_capExceeded, C_deletedOrWouldDelete   unchanged
  C_confirmed_by_Excel                -> C_confirmed_by_archive   (now gate a+b+c, not Excel LI + date)
  C_heldBack_notConfirmedByExcel      -> C_heldBack               (count)
  C_heldBackTitles                    -> C_heldBack_units         ([{Id, Title, Modified, reason}])
  C_excelDone_listDisagrees(_units)   -> C_archiveDone_listDisagrees(_units)
                                         archive row at Livraison+Delivered, unit still on SharePoint
                                         but NOT Livraison+Delivered there
  C_excelDone_noUnitRow_alreadyGone   -> C_archiveDone_noUnitRow_alreadyGone
                                         archive row at Livraison+Delivered whose unit is gone (normal)
  new: graceDays, emptyRowCap, D_emptyRowCandidates, D_emptyRowIds, D_capExceeded, D_recycledOrWouldRecycle
  Held-back reasons, first failing wins: "no archive row at Livraison" / "archive not Delivered" /
  "archive older than the unit (Modified differs)" / "edited within 7 days".

The Excel action keeps v001's source / drive / file ids, its metadata (minus tableId) and host.
The output is the editor wrapper {connectionReferences, definition}; every connection is a solution
connection reference. Hand the output path to the planning session: it snapshots it --local and stages
it (parent v006). This script never writes into workflow-data/<flow>/.
"""
import copy
import csv
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gen_nightly_cleanup as G   # noqa: E402  (stage B + helpers; its main() is not run)

FLOW_DIR = os.path.join(ROOT, "workflow-data", "Order Items - Nightly Sync")
COLUMNS = os.path.join(ROOT, "sharepoint-lists", "mirror", "live", "Columns.csv")
OI_CSV = os.path.join(ROOT, "sharepoint-lists", "mirror", "live", "Order Items.csv")

OUT = os.path.join(ROOT, "workflow-data", "_generated", "Order_Items_Nightly_Sync_v007.json")
EXCEL_TABLE_NAME = "TableArchiveOrderItems"   # v007: per-list archive, SharePoint internal column names
EXCEL_FILTER = "Location eq 'Livraison'"      # the archive holds display text, not v006's 'LI' code

# 🔴 This flow lives in a SOLUTION: every connection must name its solution connection reference.
CONNREF_NAMES = {"shared_sharepointonline": "new_sharedsharepointonline_89e9a",
                 "shared_excelonlinebusiness": "new_sharedexcelonlinebusiness_452b5"}

CAP = 50            # N2: at most this many deletions in one night; more = delete nothing, report
EMPTY_ROW_CAP = 10  # stage D: at most this many empty rows recycled in one night
DELETE_ENABLED = False
GRACE_DAYS = 7      # the unit untouched for at least 7 days (archive design §5.4)
TZ = G.TZ           # "Eastern Standard Time" (Windows zone name; covers EST/EDT)

LOOKUPS = ("OrderNumber", "Model", "Client", "ModelRevision")   # internal names (REST: <name>Id)

# ---- expression pieces, pinned once so checks() can assert them verbatim
# The Excel connector returns every cell as TEXT: an Id may come back "1130", "1130.0" or, with a
# thousands format, "1,130". Normalise to the integer's digits. SharePoint's ID is a number: string() it.
def xl_id(x="item()"):
    return "first(split(replace(replace(string(coalesce(%s?['Id'],'')),',',''),' ',''),'.'))" % x

SP_ID = "string(item()?['ID'])"
XL_STATUS_KEY = "concat(%s, '|', string(coalesce(item()?['ItemStatus'],'')))" % xl_id()
XL_STATE_KEY = ("concat(%s, '|', string(coalesce(item()?['ItemStatus'],'')), '|', string(coalesce(item()?['Modified'],'')))"
                % xl_id())
SP_STATUS_KEY = "concat(%s, '|', 'Delivered')" % SP_ID
SP_STATE_KEY = "concat(%s, '|', 'Delivered', '|', string(item()?['Modified']))" % SP_ID
GRACE = "lessOrEquals(ticks(item()?['Modified']), ticks(addDays(utcNow(), mul(-1, outputs('Settings')?['GraceDays']))))"

HAS_ROW = "contains(body('C3_Archive_ids'), %s)" % SP_ID
ARCH_DELIVERED = "contains(body('C3b_Archive_status_keys'), %s)" % SP_STATUS_KEY
ARCH_CURRENT = "contains(body('C3c_Archive_state_keys'), %s)" % SP_STATE_KEY

SP_AT_LI_DELIVERED = ("and(equals(item()?['Location']?['Value'], 'Livraison'), "
                      "equals(item()?['ItemStatus']?['Value'], 'Delivered'))")

# Stage D. A lookup comes off the connector as an object {Id, Value} and also as '<name>#Id'; take
# whichever is there, so an empty test never passes just because one spelling is absent.
def lookup_empty(n):
    return "empty(string(coalesce(item()?['%s']?['Id'], item()?['%s#Id'], '')))" % (n, n)

D_TITLE_EMPTY = "empty(string(coalesce(item()?['Title'], '')))"
D_LOCATION_EMPTY = "empty(string(coalesce(item()?['Location']?['Value'], '')))"
D_NEVER_EDITED = "equals(string(item()?['Created']), string(item()?['Modified']))"
D_OLDER_24H = "lessOrEquals(ticks(item()?['Created']), ticks(addHours(utcNow(), -24)))"
D_CLAUSES = [D_TITLE_EMPTY] + [lookup_empty(n) for n in LOOKUPS] + [D_LOCATION_EMPTY, D_NEVER_EDITED, D_OLDER_24H]


def fail(msg):
    sys.exit("ABORT: " + msg)


def load_v001():
    files = sorted(glob.glob(os.path.join(FLOW_DIR, "v001__*.json")))
    if not files:
        fail("no v001 in %s" % FLOW_DIR)
    with open(files[0], encoding="utf-8-sig") as f:
        d = json.load(f)
    props = d.get("properties", d)
    return props["definition"], props.get("connectionReferences"), os.path.basename(files[0])


def load_columns():
    if not os.path.exists(COLUMNS):
        fail("%s missing - refresh the mirror (scripts/Refresh-SharePointMirror.ps1)" % COLUMNS)
    with open(COLUMNS, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["internalName"]: r for r in rows if r["list"] == "Order Items"}


def load_archive_header():
    """TableArchiveOrderItems' columns ARE the mirror's Order Items.csv headers (same REST reader)."""
    if not os.path.exists(OI_CSV):
        fail("%s missing - refresh the mirror" % OI_CSV)
    with open(OI_CSV, encoding="utf-8-sig", newline="") as f:
        return set(next(csv.reader(f)))


def where(expr):
    return "@" + expr


def build():
    v1, connrefs, v1name = load_v001()
    cols = load_columns()

    need = ["Title", "ItemStatus", "Location", "Planned_x0020_Delivery_x0020_Dat", "Created", "Modified",
            "ManualEstimatedDeliveryDate", "CalcRefreshed", "FinishingDate", "TestingDate",
            "Planned_x0020_Tanking_x0020_Date", "TankDeliveryDate"] + G.COILING + list(LOOKUPS)
    missing = [n for n in need if n not in cols]
    if missing:
        fail("Order Items has no column(s) %s (live/Columns.csv)" % missing)
    for n in LOOKUPS:
        if cols[n]["type"] != "lookup":
            fail("%s is not a lookup column (%s)" % (n, cols[n]["type"]))
    choices = lambda n: [c.strip() for c in (cols[n].get("choices") or "").split("|")]
    if "Livraison" not in choices("Location"):
        fail("'Livraison' is not a Location choice: %s" % choices("Location"))
    for v in ("Active", "Delivered"):
        if v not in choices("ItemStatus"):
            fail("'%s' is not an ItemStatus choice: %s" % (v, choices("ItemStatus")))

    # ---- v001's Excel read: same file/source/drive/host/metadata, new table by name, new filter
    xl1 = v1["actions"].get("List_rows_present_in_a_table")
    if not xl1:
        fail("v001 has no List_rows_present_in_a_table action")
    excel = copy.deepcopy(xl1)
    excel["inputs"]["parameters"]["table"] = EXCEL_TABLE_NAME
    excel["inputs"]["parameters"]["$filter"] = EXCEL_FILTER
    (excel.get("metadata") or {}).pop("tableId", None)
    excel["runtimeConfiguration"] = {"paginationPolicy": {"minimumItemCount": 5000}}

    d = {
        "$schema": v1["$schema"],
        "contentVersion": v1.get("contentVersion", "1.0.0.0"),
        "parameters": copy.deepcopy(v1["parameters"]),
        "triggers": {
            "Every_night_at_01_30_Eastern": {
                "type": "Recurrence",
                "recurrence": {"frequency": "Day", "interval": 1, "timeZone": TZ,
                               "schedule": {"hours": ["1"], "minutes": [30]}},
            }
        },
        "actions": {},
    }
    A = d["actions"]
    after = lambda *names, st=("Succeeded",): {n: list(st) for n in names}
    ANY = ("Succeeded", "Failed", "Skipped")

    A["Settings"] = {"runAfter": {}, "type": "Compose",
                     "inputs": {"DeleteEnabled": DELETE_ENABLED, "Cap": CAP, "GraceDays": GRACE_DAYS,
                                "EmptyRowCap": EMPTY_ROW_CAP,
                                "note": "DeleteEnabled=false is a DRY RUN: C6 composes 'would delete <Title>', D3 "
                                        "'would recycle <Id>'. Flip to true after one night's report has been "
                                        "checked against the mirror."}}

    # ---- stage B, reused from gen_nightly_cleanup.py
    for k in ("B1_Get_stall_candidates", "B2_Where_TODAY_is_the_answer", "B3_Touch_each_stalled_unit"):
        A[k] = copy.deepcopy(G.A[k])
    A["B1_Get_stall_candidates"]["runAfter"] = after("Settings")
    A["B3_Touch_each_stalled_unit"]["runtimeConfiguration"] = {"concurrency": {"repetitions": 10}}

    # ---- stage C
    A["C1_Get_Livraison_candidates"] = G.get_items("Location eq 'Livraison' and ItemStatus eq 'Delivered'")
    A["C1_Get_Livraison_candidates"]["runAfter"] = after("B3_Touch_each_stalled_unit", st=ANY)
    # C1b: every unit, ONE paged read - feeds the disagreement report (C4c) and stage D.
    A["C1b_Get_all_units"] = G.sp("GetItems", {"dataset": G.SITE, "table": G.ORDER_ITEMS, "$top": 5000})
    A["C1b_Get_all_units"]["runtimeConfiguration"] = {"paginationPolicy": {"minimumItemCount": 5000}}
    A["C1b_Get_all_units"]["runAfter"] = after("C1_Get_Livraison_candidates")
    A["C1c_All_ids"] = {"runAfter": after("C1b_Get_all_units"), "type": "Select",
                        "inputs": {"from": "@outputs('C1b_Get_all_units')?['body/value']", "select": "@" + SP_ID}}

    A["C2_Get_archive_Livraison_rows"] = excel
    A["C2_Get_archive_Livraison_rows"]["runAfter"] = after("C1c_All_ids")
    arch = "@outputs('C2_Get_archive_Livraison_rows')?['body/value']"
    # C3*: three key lists over the archive rows - Id / Id|ItemStatus / Id|ItemStatus|Modified.
    # One Select each, then plain contains() per candidate: no per-unit rescan, no variables.
    A["C3_Archive_ids"] = {"runAfter": after("C2_Get_archive_Livraison_rows"), "type": "Select",
                           "inputs": {"from": arch, "select": "@" + xl_id()}}
    A["C3b_Archive_status_keys"] = {"runAfter": after("C3_Archive_ids"), "type": "Select",
                                    "inputs": {"from": arch, "select": "@" + XL_STATUS_KEY}}
    A["C3c_Archive_state_keys"] = {"runAfter": after("C3b_Archive_status_keys"), "type": "Select",
                                   "inputs": {"from": arch, "select": "@" + XL_STATE_KEY}}
    # C4: the gate - a (archive Delivered) + b (Modified equal) are both inside ARCH_CURRENT's key,
    # c is the grace. ARCH_DELIVERED is implied by ARCH_CURRENT and kept explicit for the reader.
    A["C4_Confirmed_by_archive"] = {
        "runAfter": after("C3c_Archive_state_keys"), "type": "Query",
        "inputs": {"from": "@outputs('C1_Get_Livraison_candidates')?['body/value']",
                   "where": where("and(%s, %s, %s)" % (ARCH_DELIVERED, ARCH_CURRENT, GRACE))}}
    A["C4b_Held_back"] = {
        "runAfter": after("C4_Confirmed_by_archive"), "type": "Query",
        "inputs": {"from": "@outputs('C1_Get_Livraison_candidates')?['body/value']",
                   "where": where("not(and(%s, %s, %s))" % (ARCH_DELIVERED, ARCH_CURRENT, GRACE))}}
    # C4c (REPORT ONLY): the archive says Livraison + Delivered, the unit on SharePoint does not.
    # Location / ItemStatus are CHOICE columns on the connector: compare ?['Value'].
    A["C4c_Archive_done_list_disagrees"] = {
        "runAfter": after("C4b_Held_back"), "type": "Query",
        "inputs": {"from": "@outputs('C1b_Get_all_units')?['body/value']",
                   "where": where("and(%s, not(%s))" % (ARCH_DELIVERED, SP_AT_LI_DELIVERED))}}
    # C4d (REPORT ONLY): archived at Livraison + Delivered, unit already gone from SharePoint - normal.
    A["C4d_Archive_done_no_unit_row"] = {
        "runAfter": after("C4c_Archive_done_list_disagrees"), "type": "Query",
        "inputs": {"from": arch,
                   "where": where("and(equals(string(coalesce(item()?['ItemStatus'],'')), 'Delivered'), "
                                  "not(contains(body('C1c_All_ids'), %s)))" % xl_id())}}

    # C5: the cap. Over it -> delete NOTHING tonight, say so.
    A["C5_Cap_guard"] = {
        "runAfter": after("C4d_Archive_done_no_unit_row"), "type": "If",
        "expression": {"greater": ["@length(body('C4_Confirmed_by_archive'))", "@outputs('Settings')?['Cap']"]},
        "actions": {
            "C5a_Cap_exceeded_nothing_deleted": {"runAfter": {}, "type": "Compose",
                "inputs": "@concat('CAP EXCEEDED: ', string(length(body('C4_Confirmed_by_archive'))), ' candidates > cap ', "
                          "string(outputs('Settings')?['Cap']), ' - nothing deleted tonight. Check the archive read and the mirror.')"}},
        "else": {"actions": {
            "C6_For_each_confirmed": {
                "runAfter": {}, "type": "Foreach", "foreach": "@body('C4_Confirmed_by_archive')",
                "runtimeConfiguration": {"concurrency": {"repetitions": 10}},
                "actions": {
                    "C6a_Delete_enabled": {
                        "runAfter": {}, "type": "If",
                        "expression": {"equals": ["@outputs('Settings')?['DeleteEnabled']", True]},
                        "actions": {"C6b_Delete_item": dict(G.sp("DeleteItem", {
                            "dataset": G.SITE, "table": G.ORDER_ITEMS,
                            "id": "@items('C6_For_each_confirmed')?['ID']"}), runAfter={})},
                        "else": {"actions": {"C6c_Would_delete": {"runAfter": {}, "type": "Compose",
                            "inputs": "@concat('would delete ', items('C6_For_each_confirmed')?['Title'])"}}},
                    }
                },
            }
        }},
    }

    # ---- stage D: empty-row cleanup, from C1b (already read)
    A["D1_Empty_row_candidates"] = {
        "runAfter": after("C5_Cap_guard", st=ANY), "type": "Query",
        "inputs": {"from": "@outputs('C1b_Get_all_units')?['body/value']",
                   "where": where("and(%s)" % ", ".join(D_CLAUSES))}}
    A["D2_Empty_row_cap_guard"] = {
        "runAfter": after("D1_Empty_row_candidates"), "type": "If",
        "expression": {"greater": ["@length(body('D1_Empty_row_candidates'))", "@outputs('Settings')?['EmptyRowCap']"]},
        "actions": {
            "D2a_Cap_exceeded_nothing_recycled": {"runAfter": {}, "type": "Compose",
                "inputs": "@concat('EMPTY-ROW CAP EXCEEDED: ', string(length(body('D1_Empty_row_candidates'))), ' rows > cap ', "
                          "string(outputs('Settings')?['EmptyRowCap']), ' - nothing recycled tonight. Check the mirror.')"}},
        "else": {"actions": {
            "D3_For_each_empty_row": {
                "runAfter": {}, "type": "Foreach", "foreach": "@body('D1_Empty_row_candidates')",
                "runtimeConfiguration": {"concurrency": {"repetitions": 10}},
                "actions": {
                    "D3a_Delete_enabled": {
                        "runAfter": {}, "type": "If",
                        "expression": {"equals": ["@outputs('Settings')?['DeleteEnabled']", True]},
                        # SharePoint's Delete item: the row goes to the site recycle bin (see report flag).
                        "actions": {"D3b_Recycle_item": dict(G.sp("DeleteItem", {
                            "dataset": G.SITE, "table": G.ORDER_ITEMS,
                            "id": "@items('D3_For_each_empty_row')?['ID']"}), runAfter={})},
                        "else": {"actions": {"D3c_Would_recycle": {"runAfter": {}, "type": "Compose",
                            "inputs": "@concat('would recycle ', string(items('D3_For_each_empty_row')?['ID']))"}}},
                    }
                },
            }
        }},
    }

    # ---- C7: the night's summary - one place to read in the run history
    A["C7a_Confirmed_titles"] = {"runAfter": after("D2_Empty_row_cap_guard", st=ANY), "type": "Select",
                                 "inputs": {"from": "@body('C4_Confirmed_by_archive')", "select": "@item()?['Title']"}}
    reason = ("if(not(%s), 'no archive row at Livraison', if(not(%s), 'archive not Delivered', "
              "if(not(%s), 'archive older than the unit (Modified differs)', "
              "concat('edited within ', string(outputs('Settings')?['GraceDays']), ' days'))))"
              % (HAS_ROW, ARCH_DELIVERED, ARCH_CURRENT))
    A["C7b_Held_back_units"] = {"runAfter": after("C7a_Confirmed_titles"), "type": "Select",
                                "inputs": {"from": "@body('C4b_Held_back')",
                                           "select": {"Id": "@item()?['ID']", "Title": "@item()?['Title']",
                                                      "Modified": "@item()?['Modified']", "reason": "@" + reason}}}
    A["C7c_Disagreeing_units"] = {"runAfter": after("C7b_Held_back_units"), "type": "Select",
                                  "inputs": {"from": "@body('C4c_Archive_done_list_disagrees')",
                                             "select": {"Id": "@item()?['ID']", "Title": "@item()?['Title']",
                                                        "Location": "@item()?['Location']?['Value']",
                                                        "ItemStatus": "@item()?['ItemStatus']?['Value']"}}}
    A["D4_Empty_row_ids"] = {"runAfter": after("C7c_Disagreeing_units"), "type": "Select",
                             "inputs": {"from": "@body('D1_Empty_row_candidates')", "select": "@item()?['ID']"}}
    c_over = "greater(length(body('C4_Confirmed_by_archive')), outputs('Settings')?['Cap'])"
    d_over = "greater(length(body('D1_Empty_row_candidates')), outputs('Settings')?['EmptyRowCap'])"
    A["C7_Summary"] = {
        "runAfter": after("D4_Empty_row_ids"), "type": "Compose",
        "inputs": {
            "deleteEnabled": "@outputs('Settings')?['DeleteEnabled']",
            "cap": "@outputs('Settings')?['Cap']",
            "graceDays": "@outputs('Settings')?['GraceDays']",
            "emptyRowCap": "@outputs('Settings')?['EmptyRowCap']",
            "B_touched": "@length(coalesce(body('B2_Where_TODAY_is_the_answer'), json('[]')))",
            "C_candidates_OrderItems": "@length(outputs('C1_Get_Livraison_candidates')?['body/value'])",
            "C_confirmed_by_archive": "@length(body('C4_Confirmed_by_archive'))",
            "C_capExceeded": "@" + c_over,
            "C_deletedOrWouldDelete": "@if(%s, json('[]'), body('C7a_Confirmed_titles'))" % c_over,
            "C_heldBack": "@length(body('C4b_Held_back'))",
            "C_heldBack_units": "@body('C7b_Held_back_units')",
            "C_archiveDone_listDisagrees": "@length(body('C4c_Archive_done_list_disagrees'))",
            "C_archiveDone_listDisagrees_units": "@body('C7c_Disagreeing_units')",
            "C_archiveDone_noUnitRow_alreadyGone": "@length(body('C4d_Archive_done_no_unit_row'))",
            "D_emptyRowCandidates": "@length(body('D1_Empty_row_candidates'))",
            "D_emptyRowIds": "@body('D4_Empty_row_ids')",
            "D_capExceeded": "@" + d_over,
            "D_recycledOrWouldRecycle": "@if(%s, json('[]'), body('D4_Empty_row_ids'))" % d_over,
        }}

    refs = {}
    for key in ("shared_sharepointonline", "shared_excelonlinebusiness"):
        if key not in (connrefs or {}):
            fail("v001 has no %s connection to carry over" % key)
        r = copy.deepcopy(connrefs[key])
        if not CONNREF_NAMES.get(key):
            fail("no connection reference name for %s - create it in the solution, then pass --excel-ref" % key)
        r["connectionReferenceLogicalName"] = CONNREF_NAMES[key]
        refs[key] = r
    wrapper = {"connectionReferences": refs, "definition": d}
    checks(wrapper, v1, cols, v1name)
    return wrapper


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield path + "/" + k, k, v
            yield from walk(v, path + "/" + k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, "%s[%d]" % (path, i))


def _get(d, *path):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return None
        d = d[p]
    return d


# The only two places a DeleteItem may sit: inside a DeleteEnabled branch, inside a loop, behind a cap.
DELETE_PATHS = {
    "/actions/C5_Cap_guard/else/actions/C6_For_each_confirmed/actions/C6a_Delete_enabled/actions/C6b_Delete_item",
    "/actions/D2_Empty_row_cap_guard/else/actions/D3_For_each_empty_row/actions/D3a_Delete_enabled/actions/D3b_Recycle_item",
}


def checks(w, v1, cols, v1name):
    d = w["definition"]
    A = d["actions"]
    txt = json.dumps(d)
    # 1. no variables at all (v001's SetVariable forced a sequential loop)
    for p, k, v in walk(d):
        if isinstance(v, dict) and v.get("type") in ("SetVariable", "InitializeVariable", "AppendToArrayVariable", "IncrementVariable"):
            fail("variable action at %s - the delete loops must stay variable-free" % p)
    # 2. every Foreach is concurrent
    for p, k, v in walk(d):
        if isinstance(v, dict) and v.get("type") == "Foreach":
            if v.get("runtimeConfiguration", {}).get("concurrency", {}).get("repetitions") != 10:
                fail("%s is not concurrency 10" % p)
    # 3. the caps and the dry-run default
    s = A["Settings"]["inputs"]
    if s.get("DeleteEnabled") is not False:
        fail("DeleteEnabled must default to false")
    if s.get("Cap") != 50:
        fail("cap must be 50 (N2)")
    if s.get("EmptyRowCap") != 10:
        fail("EmptyRowCap must be 10")
    if s.get("GraceDays") != 7:
        fail("GraceDays must be 7")
    if _get(A, "C5_Cap_guard", "expression") != {"greater": ["@length(body('C4_Confirmed_by_archive'))", "@outputs('Settings')?['Cap']"]}:
        fail("C cap guard missing or changed")
    if _get(A, "D2_Empty_row_cap_guard", "expression") != {"greater": ["@length(body('D1_Empty_row_candidates'))", "@outputs('Settings')?['EmptyRowCap']"]}:
        fail("stage D cap guard missing or changed")
    if _get(A, "C5_Cap_guard", "else", "actions", "C6_For_each_confirmed", "foreach") != "@body('C4_Confirmed_by_archive')":
        fail("delete loop is not behind the cap guard, or does not loop over the gate's output")
    if _get(A, "D2_Empty_row_cap_guard", "else", "actions", "D3_For_each_empty_row", "foreach") != "@body('D1_Empty_row_candidates')":
        fail("stage D recycle loop is not behind its cap guard, or does not loop over D1")
    # 3a. every DeleteItem sits exactly where it may, behind a DeleteEnabled == true branch
    dels = {p for p, k, v in walk(d) if isinstance(v, dict) and v.get("type") == "OpenApiConnection"
            and v["inputs"]["host"]["operationId"] == "DeleteItem"}
    if dels != DELETE_PATHS:
        fail("DeleteItem actions at unexpected places: %s" % sorted(dels ^ DELETE_PATHS))
    for guard in (_get(A, "C5_Cap_guard", "else", "actions", "C6_For_each_confirmed", "actions", "C6a_Delete_enabled"),
                  _get(A, "D2_Empty_row_cap_guard", "else", "actions", "D3_For_each_empty_row", "actions", "D3a_Delete_enabled")):
        if guard["expression"] != {"equals": ["@outputs('Settings')?['DeleteEnabled']", True]}:
            fail("a delete is not behind the DeleteEnabled switch")
    # 3b. confirmation #1 keeps BOTH clauses
    c1 = A["C1_Get_Livraison_candidates"]["inputs"]["parameters"]["$filter"]
    for clause in ("Location eq 'Livraison'", "ItemStatus eq 'Delivered'"):
        if clause not in c1:
            fail("C1 filter lacks %r: %r" % (clause, c1))
    # 3c. THE GATE (archive design §5): archive Delivered + Modified equal + grace, all ANDed, over C1
    c4 = A["C4_Confirmed_by_archive"]["inputs"]
    if c4.get("from") != "@outputs('C1_Get_Livraison_candidates')?['body/value']":
        fail("C4 must filter C1's candidates")
    wh = c4.get("where", "")
    if not wh.startswith("@and(") or "or(" in wh:
        fail("C4's where must be a plain and(): %r" % wh[:80])
    for name, clause in (("archive row Delivered", ARCH_DELIVERED), ("Modified equality", ARCH_CURRENT), ("grace", GRACE)):
        if clause not in wh:
            fail("gate lacks the %s condition" % name)
    if _get(A, "C3b_Archive_status_keys", "inputs", "select") != "@" + XL_STATUS_KEY:
        fail("C3b's archive key must be Id|ItemStatus")
    if _get(A, "C3c_Archive_state_keys", "inputs", "select") != "@" + XL_STATE_KEY:
        fail("C3c's archive key must be Id|ItemStatus|Modified")
    if _get(A, "C3_Archive_ids", "inputs", "select") != "@" + xl_id():
        fail("C3's archive key must be the normalised Id")
    for k in ("C3_Archive_ids", "C3b_Archive_status_keys", "C3c_Archive_state_keys"):
        if _get(A, k, "inputs", "from") != "@outputs('C2_Get_archive_Livraison_rows')?['body/value']":
            fail("%s must read C2's rows" % k)
    if _get(A, "C4b_Held_back", "inputs", "where") != "@not(" + wh[1:] + ")":
        fail("C4b (held back) must be exactly the negation of the gate")
    # 3d. stage D: every emptiness condition, never edited, 24 h, ANDed, over all units
    d1 = A["D1_Empty_row_candidates"]["inputs"]
    if d1.get("from") != "@outputs('C1b_Get_all_units')?['body/value']":
        fail("D1 must filter C1b's units (no extra read)")
    dw = d1.get("where", "")
    if not dw.startswith("@and(") or "or(" in dw:
        fail("D1's where must be a plain and()")
    for clause in D_CLAUSES:
        if clause not in dw:
            fail("stage D lacks %s" % clause)
    # 4. pagination >= 5000 on every read (SharePoint and Excel both use operationId GetItems)
    for p, k, v in walk(d):
        if isinstance(v, dict) and v.get("type") == "OpenApiConnection" and v["inputs"]["host"]["operationId"] == "GetItems":
            if v.get("runtimeConfiguration", {}).get("paginationPolicy", {}).get("minimumItemCount", 0) < 5000:
                fail("%s paginates below 5000" % p)
    # 5. every Order Items field an SP-side expression reads exists; every archive key is a real column
    sp_keys = ("B2_Where_TODAY_is_the_answer", "C1c_All_ids", "C4_Confirmed_by_archive", "C4b_Held_back",
               "C4c_Archive_done_list_disagrees", "C7a_Confirmed_titles", "C7b_Held_back_units",
               "C7c_Disagreeing_units", "D1_Empty_row_candidates", "D4_Empty_row_ids")
    sp_exprs = " ".join([json.dumps(A[k]) for k in sp_keys] + [json.dumps(A["C5_Cap_guard"]["else"]),
                                                                json.dumps(A["D2_Empty_row_cap_guard"]["else"])])
    used = set(re.findall(r"item(?:s\('[^']+'\))?\(\)\?\['([A-Za-z0-9_]+)'\]", sp_exprs))
    used |= set(re.findall(r"items\('[A-Za-z0-9_]+'\)\?\['([A-Za-z0-9_]+)'\]", sp_exprs))
    used |= set(re.findall(r"\?\['([A-Za-z0-9_]+)#Id'\]", sp_exprs))
    used -= {"ID"}                      # the connector's own id key
    for f in ("B1_Get_stall_candidates", "C1_Get_Livraison_candidates"):
        used |= set(re.findall(r"([A-Za-z_][A-Za-z0-9_]*) (?:eq|ne|lt|le|gt|ge) ", A[f]["inputs"]["parameters"]["$filter"]))
    unknown = sorted(u for u in used if u not in cols)
    if unknown:
        fail("expressions read Order Items fields not in live/Columns.csv: %s" % unknown)
    xl_exprs = " ".join(json.dumps(A[k]) for k in ("C3_Archive_ids", "C3b_Archive_status_keys", "C3c_Archive_state_keys",
                                                   "C4d_Archive_done_no_unit_row"))
    xl_used = set(re.findall(r"item\(\)\?\['([A-Za-z0-9_]+)'\]", xl_exprs))
    xl_used |= set(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*) eq ", A["C2_Get_archive_Livraison_rows"]["inputs"]["parameters"].get("$filter", "")))
    hdr = load_archive_header()
    if xl_used - hdr:
        fail("archive expressions read columns TableArchiveOrderItems does not have: %s" % sorted(xl_used - hdr))
    # 6. the Excel read is v001's file, id for id, TableArchiveOrderItems BY NAME, filtered to Livraison
    xl = A["C2_Get_archive_Livraison_rows"]
    v1x = v1["actions"]["List_rows_present_in_a_table"]
    for key in ("source", "drive", "file"):
        if xl["inputs"]["parameters"][key] != v1x["inputs"]["parameters"][key]:
            fail("Excel %s differs from v001" % key)
    if xl["inputs"]["parameters"]["table"] != EXCEL_TABLE_NAME:
        fail("Excel table must be read by name %r (v007), got %r" % (EXCEL_TABLE_NAME, xl["inputs"]["parameters"]["table"]))
    if xl["inputs"]["parameters"].get("$filter") != EXCEL_FILTER:
        fail("C2 must filter %r, got %r" % (EXCEL_FILTER, xl["inputs"]["parameters"].get("$filter")))
    v1meta = {k: v for k, v in (v1x.get("metadata") or {}).items() if k != "tableId"}
    if xl["inputs"]["host"] != v1x["inputs"]["host"] or (xl.get("metadata") or {}) != v1meta:
        fail("Excel host/metadata differs from v001 (only tableId may be dropped)")
    if "1899-12-30" in txt:
        fail("Excel serial-date parsing is back - TableArchiveOrderItems holds ISO text")
    # 7. trigger: Eastern zone, 01:30, no UTC startTime
    tr = list(d["triggers"].values())[0]["recurrence"]
    if "startTime" in tr or tr.get("timeZone") != "Eastern Standard Time" or tr["schedule"] != {"hours": ["1"], "minutes": [30]}:
        fail("trigger must be 01:30 Eastern Standard Time with no startTime")
    # 8. connection references: EXACTLY SharePoint + Excel, every one a solution reference
    cr = w["connectionReferences"] or {}
    if set(cr) != {"shared_sharepointonline", "shared_excelonlinebusiness"}:
        fail("connectionReferences must be exactly SharePoint + Excel, got %s" % sorted(cr))
    for k, v in cr.items():
        if not v.get("connectionReferenceLogicalName"):
            fail("%s is a PLAIN connection - a solution flow on plain connections blocks the new designer" % k)
    used_conns = set(re.findall(r'"connectionName": "([^"]+)"', txt))
    if used_conns - set(cr):
        fail("actions use connections with no reference: %s" % sorted(used_conns - set(cr)))
    # 9. every runAfter names an action that exists at the same level
    for p, k, v in walk(d):
        if k == "actions" and isinstance(v, dict):
            for name, act in v.items():
                for dep in (act.get("runAfter") or {}):
                    if dep not in v:
                        fail("%s/%s runs after %s, which is not beside it" % (p, name, dep))
    return used


def main():
    if "--excel-ref" in sys.argv:
        CONNREF_NAMES["shared_excelonlinebusiness"] = sys.argv[sys.argv.index("--excel-ref") + 1]
    w = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(w, f, indent=2, ensure_ascii=False)
        f.write("\n")
    d = w["definition"]
    print("wrote %s  (%d top-level actions)" % (os.path.relpath(OUT, ROOT), len(d["actions"])))
    print("  trigger   daily 01:30 %s, no startTime" % TZ)
    print("  settings  DeleteEnabled=%s  Cap=%d  GraceDays=%d  EmptyRowCap=%d" % (DELETE_ENABLED, CAP, GRACE_DAYS, EMPTY_ROW_CAP))
    print("  gate      %s by name, %s; Id + Delivered + Modified equal + %d-day grace" % (EXCEL_TABLE_NAME, EXCEL_FILTER, GRACE_DAYS))
    print("  checks    no variables; every Foreach concurrency 10; both delete loops behind cap + DeleteEnabled;")
    print("            pagination >= 5000 on every read; Excel ids == v001; fields resolved from the mirror")
    for k, v in w["connectionReferences"].items():
        kind = "solution reference" if v.get("connectionReferenceLogicalName") else "PLAIN connection (%s)" % v.get("source")
        print("  connref   %-28s %s  %s" % (k, kind, v.get("connectionName")))


if __name__ == "__main__":
    main()
