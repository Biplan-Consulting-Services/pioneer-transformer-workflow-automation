#!/usr/bin/env python3
"""The Nightly Sync v007 generator's safety checks must FAIL on each unsafe mutation.

    python scripts/test_gen_nightly_sync.py
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_nightly_sync as N  # noqa: E402

fails = []


def expect_abort(name, mutate):
    w = copy.deepcopy(BASE)
    mutate(w["definition"], w)
    try:
        N.checks(w, V1, COLS, "v001")
    except SystemExit as e:
        print("  ok   %-52s -> %s" % (name, str(e)[:90]))
        return
    fails.append(name)
    print("  FAIL %-52s -> passed the checks" % name)


N.CONNREF_NAMES["shared_excelonlinebusiness"] = N.CONNREF_NAMES["shared_excelonlinebusiness"] or "new_test_excel_ref"
BASE = N.build()
V1, _, _ = N.load_v001()
COLS = N.load_columns()
used = N.checks(BASE, V1, COLS, "v001")
print("fields the flow reads, all resolved from live/Columns.csv (%d): %s" % (len(used), ", ".join(sorted(used))))
for must in ("Location", "ItemStatus", "Planned_x0020_Delivery_x0020_Dat", "ManualEstimatedDeliveryDate",
             "FinishingDate", "Title", "Modified", "Created", "OrderNumber", "Model", "Client", "ModelRevision"):
    if must not in used:
        fails.append("field scan missed " + must)
        print("  FAIL field scan missed %s" % must)
A = lambda d: d["actions"]
C2 = lambda d: A(d)["C2_Get_archive_Livraison_rows"]
C4 = lambda d: A(d)["C4_Confirmed_by_archive"]["inputs"]
C6 = lambda d: A(d)["C5_Cap_guard"]["else"]["actions"]["C6_For_each_confirmed"]
D1 = lambda d: A(d)["D1_Empty_row_candidates"]["inputs"]
D2 = lambda d: A(d)["D2_Empty_row_cap_guard"]
D3 = lambda d: D2(d)["else"]["actions"]["D3_For_each_empty_row"]


def sub(get, key, old, new):
    """Replace text inside one expression; the mutation must actually change something."""
    def m(d, w):
        node = get(d)
        if old not in node[key]:
            raise AssertionError("test is stale: %r not in %s" % (old[:60], key))
        node[key] = node[key].replace(old, new)
    return m


print("each unsafe mutation must abort:")
# ---- carried over from v006
expect_abort("SetVariable inside the delete loop", lambda d, w: C6(d)["actions"].update(
    {"X": {"type": "SetVariable", "inputs": {"name": "v", "value": 1}}}))
expect_abort("DeleteEnabled defaults true", lambda d, w: A(d)["Settings"]["inputs"].update(DeleteEnabled=True))
expect_abort("cap raised to 500", lambda d, w: A(d)["Settings"]["inputs"].update(Cap=500))
expect_abort("delete loop moved outside the cap guard", lambda d, w: A(d).update(
    C6_For_each_confirmed=A(d)["C5_Cap_guard"]["else"]["actions"].pop("C6_For_each_confirmed")))
expect_abort("sequential delete loop", lambda d, w: C6(d)["runtimeConfiguration"]["concurrency"].update(repetitions=1))
expect_abort("Excel read paginated at 256", lambda d, w: C2(d)["runtimeConfiguration"]["paginationPolicy"].update(minimumItemCount=256))
expect_abort("Excel file id changed", lambda d, w: C2(d)["inputs"]["parameters"].update(file="SOMETHING-ELSE"))
expect_abort("Excel table back to an internal id", lambda d, w: C2(d)["inputs"]["parameters"].update(table="{17014A43-5D94-47C6-982F-45D962DA4036}"))
expect_abort("Excel table renamed", lambda d, w: C2(d)["inputs"]["parameters"].update(table="TableArchiveBO"))
expect_abort("typo'd field in C1 filter", lambda d, w: A(d)["C1_Get_Livraison_candidates"]["inputs"]["parameters"].update(
    **{"$filter": "Location eq 'Livraison' and ItemStatus eq 'Delivered' and DeliveryEndDate lt '2026-01-01'"}))
expect_abort("C1 missing the ItemStatus clause", lambda d, w: A(d)["C1_Get_Livraison_candidates"]["inputs"]["parameters"].update(
    **{"$filter": "Location eq 'Livraison'"}))
expect_abort("disagreement report reads the wrong field", lambda d, w: A(d)["C4c_Archive_done_list_disagrees"]["inputs"].update(
    where="@equals(item()?['ItemStat']?['Value'], 'Delivered')"))
expect_abort("typo'd field in B2", lambda d, w: A(d)["B2_Where_TODAY_is_the_answer"]["inputs"].update(
    where="@equals(item()?['FinishingDat'], null)"))
expect_abort("UTC startTime on the trigger", lambda d, w: list(d["triggers"].values())[0]["recurrence"].update(
    startTime="2026-09-15T05:00:00Z"))
expect_abort("Excel connection reference dropped", lambda d, w: w["connectionReferences"].pop("shared_excelonlinebusiness"))
expect_abort("SharePoint on a plain connection", lambda d, w: w["connectionReferences"]["shared_sharepointonline"].pop("connectionReferenceLogicalName"))
expect_abort("Excel on a plain connection", lambda d, w: w["connectionReferences"]["shared_excelonlinebusiness"].pop("connectionReferenceLogicalName"))
expect_abort("extra plain connection (_1)", lambda d, w: w["connectionReferences"].update(
    shared_excelonlinebusiness_1={"connectionName": "shared-excelonlinebu-f1d31972", "source": "Embedded"}))
expect_abort("action on an unreferenced connection", lambda d, w: C2(d)["inputs"]["host"].update(
    connectionName="shared_excelonlinebusiness_1"))

# ---- v007: C2 and the gate
expect_abort("C2 back to TableArchiveFRM10_12", lambda d, w: C2(d)["inputs"]["parameters"].update(table="TableArchiveFRM10_12"))
expect_abort("C2 filter back to 'LI'", lambda d, w: C2(d)["inputs"]["parameters"].update(**{"$filter": "Location eq 'LI'"}))
expect_abort("C2 filter dropped", lambda d, w: C2(d)["inputs"]["parameters"].pop("$filter"))
expect_abort("archive key reads a column the table lacks", sub(lambda d: A(d)["C3c_Archive_state_keys"]["inputs"], "select",
             "item()?['Modified']", "item()?['Last_Modified']"))
expect_abort("gate missing the Modified-equality", lambda d, w: C4(d).update(
    where="@and(%s, %s)" % (N.ARCH_DELIVERED, N.GRACE)))
expect_abort("gate Modified key dropped on the archive side", sub(lambda d: A(d)["C3c_Archive_state_keys"]["inputs"], "select",
             ", '|', string(coalesce(item()?['Modified'],''))", ""))
expect_abort("gate missing the 7-day grace", lambda d, w: C4(d).update(
    where="@and(%s, %s)" % (N.ARCH_DELIVERED, N.ARCH_CURRENT)))
expect_abort("gate grace shortened to 1 day", sub(C4, "where", "mul(-1, outputs('Settings')?['GraceDays'])", "-1"))
expect_abort("GraceDays set to 0", lambda d, w: A(d)["Settings"]["inputs"].update(GraceDays=0))
expect_abort("gate on Location only (no Delivered check)", lambda d, w: C4(d).update(
    where="@and(contains(body('C3_Archive_ids'), string(item()?['ID'])), %s)" % N.GRACE))
expect_abort("gate Delivered literal dropped from the key", sub(C4, "where", "'|', 'Delivered', '|'", "'|', '|'"))
expect_abort("gate OR'd instead of AND'd", lambda d, w: C4(d).update(
    where="@or(%s, %s, %s)" % (N.ARCH_DELIVERED, N.ARCH_CURRENT, N.GRACE)))
expect_abort("gate reads all units instead of C1", lambda d, w: C4(d).update(
    **{"from": "@outputs('C1b_Get_all_units')?['body/value']"}))
expect_abort("held back not the gate's negation", lambda d, w: A(d)["C4b_Held_back"]["inputs"].update(where="@false"))
expect_abort("Excel serial parsing reintroduced", lambda d, w: A(d)["C4d_Archive_done_no_unit_row"]["inputs"].update(
    where="@lessOrEquals(addDays('1899-12-30T00:00:00Z', 1), utcNow())"))

# ---- v007: stage D
expect_abort("stage D missing Created==Modified", lambda d, w: D1(d).update(
    where="@and(%s)" % ", ".join(c for c in N.D_CLAUSES if c != N.D_NEVER_EDITED)))
expect_abort("stage D missing the 24 h rule", lambda d, w: D1(d).update(
    where="@and(%s)" % ", ".join(c for c in N.D_CLAUSES if c != N.D_OLDER_24H)))
for lk in N.LOOKUPS:
    expect_abort("stage D missing the %s emptiness" % lk, lambda d, w, lk=lk: D1(d).update(
        where="@and(%s)" % ", ".join(c for c in N.D_CLAUSES if c != N.lookup_empty(lk))))
expect_abort("stage D missing the Title emptiness", lambda d, w: D1(d).update(
    where="@and(%s)" % ", ".join(c for c in N.D_CLAUSES if c != N.D_TITLE_EMPTY)))
expect_abort("stage D missing the Location emptiness", lambda d, w: D1(d).update(
    where="@and(%s)" % ", ".join(c for c in N.D_CLAUSES if c != N.D_LOCATION_EMPTY)))
expect_abort("stage D 24 h shortened to 1 h", sub(D1, "where", "addHours(utcNow(), -24)", "addHours(utcNow(), -1)"))
expect_abort("stage D OR'd instead of AND'd", lambda d, w: D1(d).update(where="@or(%s)" % ", ".join(N.D_CLAUSES)))
expect_abort("stage D reads a second list", lambda d, w: D1(d).update(**{"from": "@outputs('C1_Get_Livraison_candidates')?['body/value']"}))
expect_abort("stage D cap removed (EmptyRowCap)", lambda d, w: A(d)["Settings"]["inputs"].pop("EmptyRowCap"))
expect_abort("stage D cap raised to 100", lambda d, w: A(d)["Settings"]["inputs"].update(EmptyRowCap=100))
expect_abort("stage D cap guard neutered", lambda d, w: D2(d).update(expression={"equals": [1, 2]}))
expect_abort("stage D delete outside the cap guard", lambda d, w: A(d).update(
    D3_For_each_empty_row=D2(d)["else"]["actions"].pop("D3_For_each_empty_row")))
expect_abort("stage D delete outside the DeleteEnabled switch", lambda d, w: D3(d)["actions"].update(
    X=dict(D3(d)["actions"]["D3a_Delete_enabled"]["actions"]["D3b_Recycle_item"])))
expect_abort("stage D DeleteEnabled switch inverted", lambda d, w: D3(d)["actions"]["D3a_Delete_enabled"].update(
    expression={"equals": ["@outputs('Settings')?['DeleteEnabled']", False]}))
expect_abort("stage D sequential loop", lambda d, w: D3(d)["runtimeConfiguration"]["concurrency"].update(repetitions=1))
expect_abort("stage D typo'd lookup field", sub(D1, "where", "item()?['ModelRevision#Id']", "item()?['ModelRev#Id']"))
expect_abort("dangling runAfter", lambda d, w: A(d)["C7_Summary"].update(runAfter={"C7b_Held_back_titles": ["Succeeded"]}))

print("\n%s" % ("ALL PASS" if not fails else "%d FAILED: %s" % (len(fails), fails)))
sys.exit(1 if fails else 0)
