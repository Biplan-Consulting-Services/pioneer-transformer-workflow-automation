#!/usr/bin/env python3
"""The Nightly Sync v002 generator's safety checks must FAIL on each unsafe mutation.

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
        print("  ok   %-44s -> %s" % (name, str(e)[:90]))
        return
    fails.append(name)
    print("  FAIL %-44s -> passed the checks" % name)


BASE = N.build()
V1, _, _ = N.load_v001()
COLS = N.load_columns()
used = N.checks(BASE, V1, COLS, "v001")
print("fields the flow reads, all resolved from live/Columns.csv (%d): %s" % (len(used), ", ".join(sorted(used))))
for must in ("Location", "ItemStatus", "Planned_x0020_Delivery_x0020_Dat",
             "ManualEstimatedDeliveryDate", "FinishingDate", "Title"):
    if must not in used:
        fails.append("field scan missed " + must)
        print("  FAIL field scan missed %s" % must)
A = lambda d: d["actions"]
C6 = lambda d: A(d)["C5_Cap_guard"]["else"]["actions"]["C6_For_each_confirmed"]

print("each unsafe mutation must abort:")
expect_abort("SetVariable inside the delete loop", lambda d, w: C6(d)["actions"].update(
    {"X": {"type": "SetVariable", "inputs": {"name": "v", "value": 1}}}))
expect_abort("DeleteEnabled defaults true", lambda d, w: A(d)["Settings"]["inputs"].update(DeleteEnabled=True))
expect_abort("cap raised to 500", lambda d, w: A(d)["Settings"]["inputs"].update(Cap=500))
expect_abort("delete loop moved outside the cap guard", lambda d, w: A(d).update(
    C6_For_each_confirmed=A(d)["C5_Cap_guard"]["else"]["actions"].pop("C6_For_each_confirmed")))
expect_abort("sequential delete loop", lambda d, w: C6(d)["runtimeConfiguration"]["concurrency"].update(repetitions=1))
expect_abort("Excel read paginated at 256", lambda d, w: A(d)["C2_Get_Excel_LI_rows"]["runtimeConfiguration"]["paginationPolicy"].update(minimumItemCount=256))
expect_abort("Excel file id changed", lambda d, w: A(d)["C2_Get_Excel_LI_rows"]["inputs"]["parameters"].update(file="SOMETHING-ELSE"))
expect_abort("typo'd field in C1 filter", lambda d, w: A(d)["C1_Get_Livraison_candidates"]["inputs"]["parameters"].update(
    **{"$filter": "Location eq 'Livraison' and ItemStatus eq 'Delivered' and DeliveryEndDate lt '2026-01-01'"}))
expect_abort("C1 missing the ItemStatus clause", lambda d, w: A(d)["C1_Get_Livraison_candidates"]["inputs"]["parameters"].update(
    **{"$filter": "Location eq 'Livraison'"}))
expect_abort("disagreement report reads the wrong field", lambda d, w: A(d)["C4c_Excel_done_list_disagrees"]["inputs"].update(
    where="@equals(item()?['ItemStat']?['Value'], 'Delivered')"))
expect_abort("typo'd field in B2", lambda d, w: A(d)["B2_Where_TODAY_is_the_answer"]["inputs"].update(
    where="@equals(item()?['FinishingDat'], null)"))
expect_abort("UTC startTime on the trigger", lambda d, w: list(d["triggers"].values())[0]["recurrence"].update(
    startTime="2026-09-15T05:00:00Z"))
expect_abort("Excel connection reference dropped", lambda d, w: w["connectionReferences"].pop("shared_excelonlinebusiness"))

print("\n%s" % ("ALL PASS" if not fails else "%d FAILED: %s" % (len(fails), fails)))
sys.exit(1 if fails else 0)
