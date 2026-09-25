#!/usr/bin/env python3
"""Generate Order Items - Nightly Sync v003 (board E11; spec docs/nightly-sync-review-2026-09-25.md §5).

v003 (2026-09-25) supersedes v002, which was withdrawn before paste: its C1 keyed on DeliveryDate,
which is EMPTY on every unit. C1 is now Livraison AND Delivered; Excel is the grace clock; C4c/C4d
report where Excel and the list disagree (what v001 would delete on Excel alone).

    python scripts/gen_nightly_sync.py            # -> workflow-data/_generated/Order_Items_Nightly_Sync_v003.json

The user's v001 (workflow-data/Order Items - Nightly Sync/v001, hand-built) deletes a unit once the
Excel archive says LI + delivered >= 7 days ago, visiting all ~1,127 units sequentially (~6,800 actions,
throttled -> "runs forever"), trusting Excel alone, with no cap and no dry run. v003 keeps the rule and:

  B  RECALC  - gen_nightly_cleanup.py's stage B, reused by import (not copied): B1 Active + no Planned/
     Manual date, B2 one Query for "TODAY() is the branch", B3/B4 touch CalcRefreshed. Concurrency 10.
  C  ARCHIVE DELETE - two independent confirmations (Order Items itself: Livraison AND Delivered;
     Excel: LI + Delivery Date >= 7 days ago, the grace clock), a cap of 50, DeleteEnabled = false (dry run:
     "would delete <Title>"). One pass per source, no per-unit rescan, NO variables (so the delete
     loop can run at concurrency 10).
  Stage A (mark Delivered) is dropped: the trigger flow's CompletOrder already does it.
  Trigger: daily 01:30 "Eastern Standard Time" - no UTC startTime (DST-proof).

The Excel action keeps v001's exact source / drive / file / table ids, its metadata and its connection.
The output is the editor wrapper {connectionReferences, definition}, with v001's connectionReferences.

Hand the output path to the planning session: it snapshots it --local and stages
it (v003 supersedes v002, parent v001). This script never writes into workflow-data/<flow>/.
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
OUT = os.path.join(ROOT, "workflow-data", "_generated", "Order_Items_Nightly_Sync_v003.json")
COLUMNS = os.path.join(ROOT, "sharepoint-lists", "mirror", "live", "Columns.csv")

CAP = 50            # N2: at most this many deletions in one night; more = delete nothing, report
DELETE_ENABLED = False
GRACE_DAYS = 7      # delivered at least 7 days ago (09-16 rule, v001's rule)
TZ = G.TZ           # "Eastern Standard Time" (Windows zone name; covers EST/EDT)

# today - N, as an Eastern calendar date. Never utcNow()'s date: after 20:00 Eastern it is tomorrow.
def eastern_minus(days):
    return "formatDateTime(addDays(convertFromUtc(utcNow(), '%s'), -%d), 'yyyy-MM-dd')" % (TZ, days)


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


def build():
    v1, connrefs, v1name = load_v001()
    cols = load_columns()

    # ---- names this flow depends on, resolved from the platform's catalog, not typed from memory
    # DeliveryDate is NOT needed any more: fillRate 0 on every unit (mirror catalog, 2026-09-25) - see C1.
    need = ["Title", "ItemStatus", "Location", "Planned_x0020_Delivery_x0020_Dat",
            "ManualEstimatedDeliveryDate", "CalcRefreshed", "FinishingDate", "TestingDate",
            "Planned_x0020_Tanking_x0020_Date", "TankDeliveryDate"] + G.COILING
    missing = [n for n in need if n not in cols]
    if missing:
        fail("Order Items has no column(s) %s (live/Columns.csv)" % missing)
    choices = lambda n: [c.strip() for c in (cols[n].get("choices") or "").split("|")]
    if "Livraison" not in choices("Location"):
        fail("'Livraison' is not a Location choice: %s" % choices("Location"))
    for v in ("Active", "Delivered"):
        if v not in choices("ItemStatus"):
            fail("'%s' is not an ItemStatus choice: %s" % (v, choices("ItemStatus")))

    # ---- v001's Excel read, kept exactly (ids, metadata, host/connection)
    xl1 = v1["actions"].get("List_rows_present_in_a_table")
    if not xl1:
        fail("v001 has no List_rows_present_in_a_table action")
    excel = copy.deepcopy(xl1)
    excel["runAfter"] = {}
    excel["inputs"]["parameters"]["$filter"] = "Location eq 'LI'"      # C2: far below the 5,000 ceiling
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

    # ---- settings: the two knobs, visible at the top of the flow in the designer
    A["Settings"] = {"runAfter": {}, "type": "Compose",
                     "inputs": {"DeleteEnabled": DELETE_ENABLED, "Cap": CAP, "GraceDays": GRACE_DAYS,
                                "note": "DeleteEnabled=false is a DRY RUN: C6 only composes 'would delete <Title>'. "
                                        "Flip to true after one night's report has been checked against the mirror."}}

    # ---- stage B, reused from gen_nightly_cleanup.py
    for k in ("B1_Get_stall_candidates", "B2_Where_TODAY_is_the_answer", "B3_Touch_each_stalled_unit"):
        A[k] = copy.deepcopy(G.A[k])
    A["B1_Get_stall_candidates"]["runAfter"] = {"Settings": ["Succeeded"]}
    A["B3_Touch_each_stalled_unit"]["runtimeConfiguration"] = {"concurrency": {"repetitions": 10}}

    # ---- stage C
    # C1: Order Items' OWN state - confirmation #1: at Livraison AND Delivered (the trigger flow's
    # CompletOrder sets Delivered on arrival at Livraison). v002 filtered on DeliveryDate instead; the
    # mirror catalog showed that column is EMPTY on every unit (fillRate 0, 2026-09-25) - v002 would
    # never have matched a row. The grace clock is therefore Excel's Delivery Date alone (C3).
    A["C1_Get_Livraison_candidates"] = G.get_items(
        "Location eq 'Livraison' and ItemStatus eq 'Delivered'")
    A["C1_Get_Livraison_candidates"]["runAfter"] = {"B3_Touch_each_stalled_unit": ["Succeeded", "Failed", "Skipped"]}

    # C1b/C1c: every unit's Title + state, ONE paged read - only to REPORT where Excel and the list
    # disagree (C4c/C4d). v001 deletes on Excel's word alone; the user needs to see those units.
    A["C1b_Get_all_units"] = G.sp("GetItems", {"dataset": G.SITE, "table": G.ORDER_ITEMS, "$top": 5000})
    A["C1b_Get_all_units"]["runtimeConfiguration"] = {"paginationPolicy": {"minimumItemCount": 5000}}
    A["C1b_Get_all_units"]["runAfter"] = {"C1_Get_Livraison_candidates": ["Succeeded"]}
    A["C1c_All_titles"] = {"runAfter": {"C1b_Get_all_units": ["Succeeded"]}, "type": "Select",
                           "inputs": {"from": "@outputs('C1b_Get_all_units')?['body/value']", "select": "@item()?['Title']"}}

    A["C2_Get_Excel_LI_rows"] = excel
    A["C2_Get_Excel_LI_rows"]["runAfter"] = {"C1c_All_titles": ["Succeeded"]}

    # C3: Excel rows delivered >= 7 days ago - confirmation #2. Delivery Date comes back as an Excel
    # SERIAL (v001: addDays('1899-12-30', int(...))). Logic Apps evaluates and()/if() arguments eagerly,
    # so int() must never see '' or a fraction: blanks become '0' (and are excluded by not(empty)).
    s = "string(coalesce(item()?['Delivery Date'],''))"
    serial = "int(first(split(if(empty(%s),'0',%s),'.')))" % (s, s)
    A["C3_Excel_old_enough"] = {
        "runAfter": {"C2_Get_Excel_LI_rows": ["Succeeded"]}, "type": "Query",
        "inputs": {"from": "@outputs('C2_Get_Excel_LI_rows')?['body/value']",
                   "where": "@and(not(empty(%s)), lessOrEquals(formatDateTime(addDays('1899-12-30T00:00:00Z', %s), 'yyyy-MM-dd'), %s))"
                            % (s, serial, eastern_minus(GRACE_DAYS))}}
    A["C3b_Excel_orders"] = {
        "runAfter": {"C3_Excel_old_enough": ["Succeeded"]}, "type": "Select",
        "inputs": {"from": "@body('C3_Excel_old_enough')", "select": "@item()?['Order']"}}
    # C4: both confirmations. One Query over ~100 candidates, not a per-unit rescan of the archive.
    A["C4_Confirmed_by_both"] = {
        "runAfter": {"C3b_Excel_orders": ["Succeeded"]}, "type": "Query",
        "inputs": {"from": "@outputs('C1_Get_Livraison_candidates')?['body/value']",
                   "where": "@contains(body('C3b_Excel_orders'), item()?['Title'])"}}
    A["C4b_Held_back"] = {
        "runAfter": {"C4_Confirmed_by_both": ["Succeeded"]}, "type": "Query",
        "inputs": {"from": "@outputs('C1_Get_Livraison_candidates')?['body/value']",
                   "where": "@not(contains(body('C3b_Excel_orders'), item()?['Title']))"}}
    # C4c (REPORT ONLY): Excel says LI + delivered >= 7 days, but the unit is NOT (Livraison AND
    # Delivered). v001 would delete exactly these. Location / ItemStatus are CHOICE columns: the
    # connector returns them as objects, so compare ?['Value'] - a bare string compare never matches.
    A["C4c_Excel_done_list_disagrees"] = {
        "runAfter": {"C4b_Held_back": ["Succeeded"]}, "type": "Query",
        "inputs": {"from": "@outputs('C1b_Get_all_units')?['body/value']",
                   "where": "@and(contains(body('C3b_Excel_orders'), item()?['Title']), "
                            "not(and(equals(item()?['Location']?['Value'], 'Livraison'), "
                            "equals(item()?['ItemStatus']?['Value'], 'Delivered'))))"}}
    # C4d (REPORT ONLY): Excel LI + old rows with no Order Items row at all - already gone, normal.
    A["C4d_Excel_done_no_unit_row"] = {
        "runAfter": {"C4c_Excel_done_list_disagrees": ["Succeeded"]}, "type": "Query",
        "inputs": {"from": "@body('C3_Excel_old_enough')",
                   "where": "@not(contains(body('C1c_All_titles'), item()?['Order']))"}}

    # C5: the cap. Over it -> delete NOTHING tonight, say so.
    A["C5_Cap_guard"] = {
        "runAfter": {"C4d_Excel_done_no_unit_row": ["Succeeded"]}, "type": "If",
        "expression": {"greater": ["@length(body('C4_Confirmed_by_both'))", "@outputs('Settings')?['Cap']"]},
        "actions": {
            "C5a_Cap_exceeded_nothing_deleted": {"runAfter": {}, "type": "Compose",
                "inputs": "@concat('CAP EXCEEDED: ', string(length(body('C4_Confirmed_by_both'))), ' candidates > cap ', "
                          "string(outputs('Settings')?['Cap']), ' - nothing deleted tonight. Check the Excel read and the mirror.')"}},
        "else": {"actions": {
            # C6: NO variables anywhere in here - that is what makes concurrency 10 safe.
            "C6_For_each_confirmed": {
                "runAfter": {}, "type": "Foreach", "foreach": "@body('C4_Confirmed_by_both')",
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

    # C7: the night's summary - one place to read in the run history.
    titles = lambda src: "@body('%s')" % src
    A["C7_Summary"] = {
        "runAfter": {"C5_Cap_guard": ["Succeeded", "Failed", "Skipped"]}, "type": "Compose",
        "inputs": {
            "deleteEnabled": "@outputs('Settings')?['DeleteEnabled']",
            "cap": "@outputs('Settings')?['Cap']",
            "B_touched": "@length(coalesce(body('B2_Where_TODAY_is_the_answer'), json('[]')))",
            "C_candidates_OrderItems": "@length(outputs('C1_Get_Livraison_candidates')?['body/value'])",
            "C_confirmed_by_Excel": "@length(body('C4_Confirmed_by_both'))",
            "C_capExceeded": "@greater(length(body('C4_Confirmed_by_both')), outputs('Settings')?['Cap'])",
            "C_deletedOrWouldDelete": "@if(greater(length(body('C4_Confirmed_by_both')), outputs('Settings')?['Cap']), json('[]'), "
                                      "body('C4_Confirmed_by_both'))",
            "C_heldBack_notConfirmedByExcel": "@length(body('C4b_Held_back'))",
            "C_heldBackTitles": titles("C4b_Held_back"),
        }}
    # Keep the summary readable: titles only, not whole rows.
    A["C7_Summary"]["inputs"]["C_deletedOrWouldDelete"] = (
        "@if(greater(length(body('C4_Confirmed_by_both')), outputs('Settings')?['Cap']), json('[]'), "
        "body('C7a_Confirmed_titles'))")
    A["C7_Summary"]["inputs"]["C_heldBackTitles"] = "@body('C7b_Held_back_titles')"
    A["C7_Summary"]["inputs"]["C_excelDone_listDisagrees"] = "@length(body('C4c_Excel_done_list_disagrees'))"
    A["C7_Summary"]["inputs"]["C_excelDone_listDisagrees_units"] = "@body('C7c_Disagreeing_units')"
    A["C7_Summary"]["inputs"]["C_excelDone_noUnitRow_alreadyGone"] = "@length(body('C4d_Excel_done_no_unit_row'))"
    A["C7c_Disagreeing_units"] = {"runAfter": {"C7b_Held_back_titles": ["Succeeded"]}, "type": "Select",
                                  "inputs": {"from": "@body('C4c_Excel_done_list_disagrees')",
                                             "select": {"Title": "@item()?['Title']",
                                                        "Location": "@item()?['Location']?['Value']",
                                                        "ItemStatus": "@item()?['ItemStatus']?['Value']"}}}
    A["C7a_Confirmed_titles"] = {"runAfter": {"C5_Cap_guard": ["Succeeded", "Failed", "Skipped"]}, "type": "Select",
                                 "inputs": {"from": "@body('C4_Confirmed_by_both')", "select": "@item()?['Title']"}}
    A["C7b_Held_back_titles"] = {"runAfter": {"C7a_Confirmed_titles": ["Succeeded"]}, "type": "Select",
                                 "inputs": {"from": "@body('C4b_Held_back')", "select": "@item()?['Title']"}}
    A["C7_Summary"]["runAfter"] = {"C7c_Disagreeing_units": ["Succeeded"]}

    wrapper = {"connectionReferences": copy.deepcopy(connrefs), "definition": d}
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


def checks(w, v1, cols, v1name):
    d = w["definition"]
    txt = json.dumps(d)
    # 1. no variables at all (v001's SetVariable forced a sequential loop)
    for p, k, v in walk(d):
        if isinstance(v, dict) and v.get("type") in ("SetVariable", "InitializeVariable", "AppendToArrayVariable", "IncrementVariable"):
            fail("variable action at %s - the delete loop must stay variable-free" % p)
    # 2. every Foreach inside is variable-free and concurrent
    for p, k, v in walk(d):
        if isinstance(v, dict) and v.get("type") == "Foreach":
            if v.get("runtimeConfiguration", {}).get("concurrency", {}).get("repetitions") != 10:
                fail("%s is not concurrency 10" % p)
    # 3. the cap and the dry-run default
    s = d["actions"]["Settings"]["inputs"]
    if s["DeleteEnabled"] is not False:
        fail("DeleteEnabled must default to false")
    if s["Cap"] != 50:
        fail("cap must be 50 (N2)")
    if "greater" not in d["actions"]["C5_Cap_guard"]["expression"]:
        fail("cap guard missing")
    if "C6_For_each_confirmed" not in d["actions"]["C5_Cap_guard"]["else"]["actions"]:
        fail("delete loop is not behind the cap guard")
    # 3b. confirmation #1 must keep BOTH clauses (v003: DeliveryDate is empty everywhere, so the
    #     ItemStatus clause is what stops an undelivered unit at Livraison from being deleted)
    c1 = d["actions"]["C1_Get_Livraison_candidates"]["inputs"]["parameters"]["$filter"]
    for clause in ("Location eq 'Livraison'", "ItemStatus eq 'Delivered'"):
        if clause not in c1:
            fail("C1 filter lacks %r: %r" % (clause, c1))
    # 4. pagination >= 5000 on every read
    for p, k, v in walk(d):
        if isinstance(v, dict) and v.get("type") == "OpenApiConnection" and v["inputs"]["host"]["operationId"] == "GetItems":
            if v.get("runtimeConfiguration", {}).get("paginationPolicy", {}).get("minimumItemCount", 0) < 5000:
                fail("%s paginates below 5000" % p)
    # 5. every Order Items field an SP expression reads exists (Excel keys excluded: they have their own names)
    sp_exprs = [json.dumps(d["actions"][k]) for k in ("B2_Where_TODAY_is_the_answer", "C4_Confirmed_by_both", "C4b_Held_back",
                                                        "C4c_Excel_done_list_disagrees", "C7c_Disagreeing_units", "C1c_All_titles",
                                                        "C7a_Confirmed_titles", "C7b_Held_back_titles")]
    sp_exprs += [json.dumps(d["actions"]["C5_Cap_guard"]["else"])]
    used = set(re.findall(r"item(?:s\('[^']+'\))?\(\)\?\['([A-Za-z0-9_]+)'\]", " ".join(sp_exprs)))
    used |= set(re.findall(r"items\('[A-Za-z0-9_]+'\)\?\['([A-Za-z0-9_]+)'\]", " ".join(sp_exprs)))
    used -= {"ID"}                      # the connector's own id key
    for f in ("B1_Get_stall_candidates", "C1_Get_Livraison_candidates"):
        used |= {t for t in re.findall(r"([A-Za-z_][A-Za-z0-9_]*) (?:eq|ne|lt|le|gt|ge) ", d["actions"][f]["inputs"]["parameters"]["$filter"])}
    unknown = sorted(u for u in used if u not in cols)
    if unknown:
        fail("expressions read Order Items fields not in live/Columns.csv: %s" % unknown)
    # 6. the Excel read is v001's, id for id
    xl = d["actions"]["C2_Get_Excel_LI_rows"]
    v1x = v1["actions"]["List_rows_present_in_a_table"]
    for key in ("source", "drive", "file", "table"):
        if xl["inputs"]["parameters"][key] != v1x["inputs"]["parameters"][key]:
            fail("Excel %s differs from v001" % key)
    if xl["inputs"]["host"] != v1x["inputs"]["host"] or xl.get("metadata") != v1x.get("metadata"):
        fail("Excel host/metadata differs from v001")
    # 7. trigger: Eastern zone, 01:30, no UTC startTime
    tr = list(d["triggers"].values())[0]["recurrence"]
    if "startTime" in tr or tr.get("timeZone") != "Eastern Standard Time" or tr["schedule"] != {"hours": ["1"], "minutes": [30]}:
        fail("trigger must be 01:30 Eastern Standard Time with no startTime")
    # 8. connection references: both present
    cr = w["connectionReferences"] or {}
    for need in ("shared_sharepointonline", "shared_excelonlinebusiness"):
        if need not in cr:
            fail("connectionReferences lacks %s (v001 %s)" % (need, v1name))
    return used


def main():
    w = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(w, f, indent=2, ensure_ascii=False)
        f.write("\n")
    d = w["definition"]
    print("wrote %s  (%d top-level actions)" % (os.path.relpath(OUT, ROOT), len(d["actions"])))
    print("  trigger   daily 01:30 %s, no startTime" % TZ)
    print("  settings  DeleteEnabled=%s  Cap=%d  GraceDays=%d" % (DELETE_ENABLED, CAP, GRACE_DAYS))
    print("  checks    no variables; every Foreach concurrency 10; cap guard wraps the delete loop;")
    print("            pagination >= 5000 on every read; Excel ids == v001; fields resolved from live/Columns.csv")
    for k, v in w["connectionReferences"].items():
        kind = "solution reference" if v.get("connectionReferenceLogicalName") else "PLAIN connection (%s)" % v.get("source")
        print("  connref   %-28s %s  %s" % (k, kind, v.get("connectionName")))


if __name__ == "__main__":
    main()
