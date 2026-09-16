# -*- coding: utf-8 -*-
"""Generate the Nightly Cleanup flow definition as pasteable JSON.

    python scripts/gen_nightly_cleanup.py

Writes workflow-data/nightly-cleanup/Nightly_Cleanup.definition.json.

WHAT THE FLOW DOES -- three stages, one daily run at 01:00 Eastern

  A  SET DELIVERED    Active units at Location = Livraison with a delivery date
                      become Item Status = Delivered / Delivery Status = Completed.
  B  REFRESH STALLED  Touches only the units whose Estimated Delivery Date is
                      currently TODAY()-derived, so the calculated column
                      re-evaluates. See "STAGE B EXISTS AGAIN".
  C  ARCHIVE SWEEP    REPORT ONLY. Counts the rows old enough to delete.
                      IT DELETES NOTHING -- see "STAGE C IS DELIBERATELY INERT".

STAGE B EXISTS AGAIN -- added 2026-09-14, and it is NOT the one killed on 09-11
  The original stage B touched rows nightly so SharePoint would re-evaluate the
  `Estimated Delivery Date` calculated column, which freezes at write time
  because its formula uses TODAY(). It was dropped on two measurements, and both
  have since been answered rather than overturned:

  1. THE COLUMN DID NOT EXIST. True on 09-11. It does now, or will:
     `gen_calc_columns.py` creates it, as a CALCULATED column, decided by the
     user on 09-14 for integrity -- a calculated column cannot be hand-edited,
     recomputes on save rather than after a 5-minute poll, and works while the
     create-or-update trigger flow is off, which it currently is.

  2. THE FILTER DID NOT FILTER -- and the reason turns out to be a WRONG COLUMN,
     not a bad idea. The 09-11 count was:

         total rows                                  1,189
         Item Status = Active                        1,087
           + no Delivery End Date                    1,087   (unchanged!)
           + no Manual Estimated Delivery Date         915

     `Delivery End Date` is the COMPLETION stamp. The formula's first branch
     reads `Planned Delivery Date`, a different column -- the field-mapping trap
     documented in gen_calc_columns.py. So "the second clause is a no-op" was an
     artefact of filtering on a column the formula never looks at.

     More importantly, 915 was never the right target anyway. It is the count of
     rows that REACH a TODAY() branch; the rows whose value actually MOVES each
     night are the subset where TODAY() is the value being returned -- the unit
     is stalled, its latest milestone already in the past. The 2026-08-31
     analysis measured that at ~21 and said so plainly: "It does not need to
     rewrite all 1038 items daily ... ~21 rows/day. Trivial flow."

     B2 is what closes that gap: one Query action filters the ~900 down to the
     rows where TODAY() wins, so the flow READS many and WRITES few. Reads are
     batched and cheap; writes are the cost.

  ⚠️ RE-MEASURE ON THE FIRST RUN. The ~21 comes from the same 08-31 table whose
     rows are labelled "Delivery End Date" / "Tanking End Date", so it may be
     counting a different population too. B2's output count is the honest
     number -- read it off run 1 before quoting 21 to anyone.

WHY A GENERATOR AND NOT HAND-WRITTEN JSON
  Same reason as gen_n3_flows.py: the OData filters and the write payloads carry
  internal column names, and this repo has already lost data to one wrong name
  (R22) and had a read silently return "0 rows" from another -- x2_set_delivered.js
  first hit `DeliveryEndDate`, got a 400, and its `j.value||[]` turned that into
  an empty list rather than an error. Every name below is pinned in one place.

INTERNAL NAMES -- read from the live list schema, never guessed
  Item Status                     -> ItemStatus                   (Choice)
  Location                        -> Location                     (Choice)
  Delivery End Date               -> DeliveryDate                 (!) NOT DeliveryEndDate
  Delivery Status                 -> DeliveryStatus               (Choice)
  Manual Estimated Delivery Date  -> ManualEstimatedDeliveryDate

  (!) Every stage's END date is internally `<Stage>Date`, not `<Stage>EndDate`.
      The columns were created as "Tanking Date"/"Delivery Date" and renamed to
      "... End Date" when the Start Dates were added; a SharePoint rename does
      not change the internal name. The Start Dates, added later, really are
      `<Stage>StartDate`. This exact trap already cost one debugging session.

THE DELIVERED RULE -- the user's own, stated 2026-09-08, already encoded twice
  in x1_clear_fabricated_stages.js and x2_set_delivered.js:

      Delivery is real  <=>  Location = Livraison AND a delivery date is entered.

  Exterieur does NOT count. Ruled 2026-09-08 in the user's words -- "it's
  completed and waiting outside to be shipped" -- so the unit is past tanking
  but has NOT shipped. 24 of X2's 66 units sat at Exterieur; treating that as
  delivered would have been wrong on 24 rows.

TWO GUARDS THAT ARE NOT DECORATION

  1. FUTURE DELIVERY DATES ARE HELD BACK, NOT WRITTEN.
     x2_set_delivered.js deliberately excluded 21792-3/5 and 21792-4/5: both at
     LI, but with an archive delivery date of 2026-09-24, in the future.
     "Delivered on a future date is the same contradiction X1 uses as its hard
     test." Those two units are still not Delivered today, so the first time
     somebody types that date onto the live row this flow would flip them --
     which is exactly the call X2 reserved for a human. Stage A therefore skips
     any row whose delivery date is after today (Eastern) and names it in the
     run history instead.

  2. STAGE A ONLY PROMOTES `Active`.
     Not "anything that isn't Delivered". A unit a human set to Cancelled or
     Regrouped while it happened to sit at Livraison with a date must not be
     silently promoted back to Delivered -- that overwrites a human decision
     with a heuristic, which is the failure mode the whole Item Status design
     exists to prevent (infrastructure-overview.md:445).

THE TOUCH-RESETS-THE-CLOCK BUG, AND WHY IT IS GONE -- fixed 2026-09-16
  It used to read: a touch bumps `Modified`, stage C's grace period keys on
  `Modified`, so any pass over Delivered/Cancelled rows resets the clock on
  exactly the rows stage C is waiting on -- every night, forever -- and nothing
  ever becomes eligible, with no error anywhere. B1's `ItemStatus eq 'Active'`
  clause was the only thing preventing it, load-bearing for a stage it is not
  written in.

  Shortening the grace period to 7 days turned that from a caution into a live
  problem: measured 2026-09-16, the 09-09/09-10 migration passes had put every
  Delivered row within 1.5 days of the threshold -- three of them within 0.4 --
  though the units had really been finished 16 to 62 days earlier.

  🔑 Stage C now keys on `DeliveryDate`, which records WHEN THE UNIT WAS
  DELIVERED and is never rewritten by housekeeping. A touch cannot defer a
  deletion any more, because nothing a pass does changes when delivery happened.

  B1's `ItemStatus eq 'Active'` clause is still worth keeping -- a touch still
  costs a trigger-flow run and a version -- but it is no longer holding up stage
  C, and widening stage B can no longer break the sweep. Cancelled rows do still
  ride on `Modified`; see C1 for why that is unavoidable and what it costs.

STAGE C IS DELIBERATELY INERT
  archiving-plan.md lists three questions, one of them now answered:
    - is one month the right grace period?          ANSWERED 2026-09-16: no, 7 days
    - nightly, weekly or monthly?
    - does the `Order` row need the same reconfirm rigor?
  and the plan requires reconfirming each row against `Archive active.xlsx`
  BEFORE deleting. None of that is settled, and deletion is irreversible, so
  Stage C only counts candidates here. Wiring the Excel reconfirm and the
  Delete item action is a separate change, once those three are answered.
"""
import json
import io
import os

SITE = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio"
ORDER_ITEMS = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d"
TZ = "Eastern Standard Time"

# Grace period for stage C's report, in days. Was 30 (archiving-plan.md's proposed
# "one month", flagged there as an open question). SETTLED 2026-09-16: 7 days, measured
# from the DELIVERY DATE -- see C1. The short grace is only safe because of that: on
# `Modified` it would have been reset by routine housekeeping.
GRACE_DAYS = 7

SP_HOST = {
    "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
    "connectionName": "shared_sharepointonline",
}


def sp(operation_id, params):
    """A SharePoint connector action. `connectionName` is a NAME only -- it
    resolves through the shell's connectionReferences wrapper, not through
    anything in this definition. See docs/n3-deploy-and-test.md Part 1."""
    return {
        "type": "OpenApiConnection",
        "inputs": {
            "parameters": params,
            "host": dict(SP_HOST, operationId=operation_id),
        },
    }


def get_items(odata_filter):
    a = sp("GetItems", {
        "dataset": SITE,
        "table": ORDER_ITEMS,
        "$filter": odata_filter,
        "$top": 5000,
    })
    # Without this the connector stops at its default page size and the flow
    # silently processes a prefix of the list.
    a["runtimeConfiguration"] = {"paginationPolicy": {"minimumItemCount": 5000}}
    return a


# "today" in Eastern, as yyyy-MM-dd. Deliberately NOT utcNow(): after 20:00
# Eastern, utcNow() is already on tomorrow's date, which is the same
# off-by-one-day class of bug the whole timezone workstream exists to fix
# (calculated-columns-plan.md:530).
TODAY_EASTERN = "formatDateTime(convertFromUtc(utcNow(), '%s'), 'yyyy-MM-dd')" % TZ

ITEM = "items('A2_For_each_delivery_candidate')"

definition = {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
        "$authentication": {"defaultValue": {}, "type": "SecureObject"},
        "$connections": {"defaultValue": {}, "type": "Object"},
    },
    "triggers": {
        "Every_night_at_01_00_Eastern": {
            "type": "Recurrence",
            "recurrence": {
                "frequency": "Day",
                "interval": 1,
                "timeZone": TZ,
                "schedule": {"hours": ["1"], "minutes": [0]},
            },
        }
    },
    "actions": {},
}

A = definition["actions"]

# ------------------------------------------------------------------ stage A
A["A1_Get_delivery_candidates"] = get_items(
    # Active only -- guard 2 in the module docstring.
    "ItemStatus eq 'Active' and Location eq 'Livraison' and DeliveryDate ne null"
)
A["A1_Get_delivery_candidates"]["runAfter"] = {}

A["A2_For_each_delivery_candidate"] = {
    "runAfter": {"A1_Get_delivery_candidates": ["Succeeded"]},
    "type": "Foreach",
    "foreach": "@outputs('A1_Get_delivery_candidates')?['body/value']",
    "runtimeConfiguration": {"concurrency": {"repetitions": 1}},
    "actions": {
        "A3_Delivery_date_is_not_in_the_future": {
            "runAfter": {},
            "type": "If",
            "expression": {
                "lessOrEquals": [
                    "@formatDateTime(%s?['DeliveryDate'], 'yyyy-MM-dd')" % ITEM,
                    "@%s" % TODAY_EASTERN,
                ]
            },
            "actions": {
                "A4_Mark_delivered": sp("PatchItem", {
                    "dataset": SITE,
                    "table": ORDER_ITEMS,
                    "id": "@%s?['ID']" % ITEM,
                    # Location and DeliveryDate are NOT rewritten: A1's filter
                    # already proved both, and writing back a value you did not
                    # compute is how a read bug becomes a data bug.
                    "item/ItemStatus/Value": "Delivered",
                    "item/DeliveryStatus/Value": "Completed",
                }),
            },
            "else": {
                "actions": {
                    "A5_Held_back_future_delivery_date": {
                        "runAfter": {},
                        "type": "Compose",
                        # A named, greppable step in the run history. This is the
                        # 21792-3/5 and 21792-4/5 case: a human call, not
                        # something to automate away.
                        "inputs": {
                            "heldBack": "@%s?['Title']" % ITEM,
                            "deliveryDate": "@%s?['DeliveryDate']" % ITEM,
                            "reason": "Delivery date is in the future - Delivered would contradict it. Decide by hand.",
                        },
                    }
                }
            },
        }
    },
}

# ------------------------------------------------------------------ stage C
# ------------------------------------------------------------------ stage B
# Keep TODAY() honest on the units nobody is editing.
#
# `Estimated Delivery Date` is a CALCULATED column (see docs/calc-columns-port.md), so
# SharePoint re-evaluates it when the ITEM is written and at no other time. For most rows
# that is enough -- the value only moves when someone changes a milestone, which is itself
# a write. The exception is a unit STALLED in production: its latest milestone is already
# in the past, so the formula returns `MAX(TODAY(), milestone) + buffer` = today + buffer,
# which moves every day while nobody touches the row. Those rows, and only those, need a
# nightly touch.
#
# 🔑 THIS IS NOT THE STAGE B THAT WAS KILLED ON 2026-09-11, and the difference is the
# whole point. That one touched every candidate row to force a calculated column to
# re-evaluate, and measured at 915 of 1,189 rows a night -- because "Active with no
# delivery date" is nearly every active unit, by definition. This filters further, to
# rows where TODAY() is actually the value being returned, which the 2026-08-31 analysis
# measured at ~21. Reads are cheap and batched; WRITES are the cost, and this writes ~21.
#
# ⚠️ Re-measure before trusting the 21. That figure came from a table labelled "Delivery
# End Date" / "Tanking End Date", and the formula reads the PLANNED columns. B2's output
# count is the honest number -- read it off the first run.

COILING = ["CoilingDate", "StackingDate", "AssemblyDate", "DryingDate"]


def _set(f):
    return "not(equals(coalesce(item()?['%s'],''),''))" % f


def _past(f):
    # ⚠️ coalesce to a sentinel rather than guarding: Logic Apps evaluates BOTH branches
    # of if() and both arguments of and() eagerly, so a formatDateTime() sitting on the
    # unselected branch still runs and still throws on a null. The sentinel never reaches
    # a result -- it only stops the expression exploding on rows where the field is blank.
    return ("less(formatDateTime(coalesce(item()?['%s'],'1900-01-01T00:00:00Z'),"
            "'yyyy-MM-dd'), %s)" % (f, TODAY_EASTERN))


def _still_ahead(f):
    return "and(%s,not(%s))" % (_set(f), _past(f))


# Branch 6: at least one coiling-range date is set, and NONE of the five dates it maxes
# over is still today or later. Expressed as "nothing is ahead" rather than as a max(),
# which the expression language has no equivalent of.
_coiling_stalled = "and(or(%s),not(or(%s)))" % (
    ",".join(_set(f) for f in COILING),
    ",".join(_still_ahead(f) for f in COILING + ["TankDeliveryDate"]))

# The same exclusive cascade the calculated column walks, in the same order. Branches 1,
# 2 and 7 never call TODAY() and are excluded by B1's filter or fall through to false.
TODAY_WINS = "if(%s,%s,if(%s,%s,if(%s,%s,%s)))" % (
    _set("FinishingDate"), _past("FinishingDate"),
    _set("TestingDate"), _past("TestingDate"),
    _set("Planned_x0020_Tanking_x0020_Date"), _past("Planned_x0020_Tanking_x0020_Date"),
    _coiling_stalled)

A["B1_Get_stall_candidates"] = get_items(
    # Branches 1 and 2 short-circuit the whole formula, so a row with either of these
    # never reaches a TODAY() branch at all. Note these are the PLANNING columns.
    #
    # `ItemStatus eq 'Active'` also keeps this pass off Delivered/Cancelled rows. That
    # used to protect stage C, whose grace clock was their `Modified` stamp; since
    # 2026-09-16 stage C keys on `DeliveryDate` and a touch cannot defer a deletion.
    # Keep the clause anyway -- a touch still costs a trigger-flow run and a version --
    # but it is no longer load-bearing for another stage. Cancelled rows are the
    # exception that still rides on `Modified`; see C1.
    "ItemStatus eq 'Active' and Planned_x0020_Delivery_x0020_Dat eq null "
    "and ManualEstimatedDeliveryDate eq null"
)
A["B1_Get_stall_candidates"]["runAfter"] = {"A2_For_each_delivery_candidate": ["Succeeded"]}

# ONE action, not one per row. A Condition inside a Foreach over ~900 items would cost
# ~900 actions against a 2,000/day allowance and starve the five event-triggered flows;
# a Query action evaluates the same predicate over the whole array for the price of one.
A["B2_Where_TODAY_is_the_answer"] = {
    "runAfter": {"B1_Get_stall_candidates": ["Succeeded"]},
    "type": "Query",
    "inputs": {
        "from": "@outputs('B1_Get_stall_candidates')?['body/value']",
        "where": "@" + TODAY_WINS,
    },
}

A["B3_Touch_each_stalled_unit"] = {
    "runAfter": {"B2_Where_TODAY_is_the_answer": ["Succeeded"]},
    "type": "Foreach",
    "foreach": "@body('B2_Where_TODAY_is_the_answer')",
    "runtimeConfiguration": {"concurrency": {"repetitions": 1}},
    "actions": {
        "B4_Write_Calc_Refreshed": dict(sp("PatchItem", {
            "dataset": SITE,
            "table": ORDER_ITEMS,
            "id": "@items('B3_Touch_each_stalled_unit')?['ID']",
            # The write itself is the point; the value is only so the row says why it has
            # a version. Everything real on the row is recomputed by SharePoint, not here.
            "item/CalcRefreshed": "@%s" % TODAY_EASTERN,
        }), runAfter={}),
    },
}

# Each touch fires the Order Items create-or-update trigger flow once -- ~21 runs that
# find nothing changed and write nothing, which is the flow's own change-guard doing its
# job. calculated-columns-plan.md:546 proposes a trigger CONDITION so a touch-only update
# never creates a run at all. Worth it at 915 rows; not worth it at 21.

# ------------------------------------------------------------------ stage C
A["C1_Get_deletion_candidates_REPORT_ONLY"] = get_items(
    # 🔑 THE GRACE CLOCK IS THE DELIVERY DATE, NOT `Modified` -- decided 2026-09-16.
    #
    # `Modified` measured the wrong thing: when a row was last TOUCHED, not when the
    # unit was finished. Every pass over the list reset it, so the 7-day grace could
    # be deferred indefinitely by housekeeping -- see the module docstring's red note.
    # `DeliveryDate` is written once, by delivery, and never moves. Verified on the 11
    # rows retired 2026-09-16: all 11 matched `Archive active.xlsx`'s `Delivery Date`
    # exactly, and all 11 were 16-62 days old while `Modified` put them at 5-6 days.
    #
    # ⚠️ `DeliveryDate` IS `Delivery End Date`. Not `DeliveryEndDate`, which 400s --
    # the same trap already recorded at the top of this file. Not `Planned Delivery
    # Date` either: that is the PLAN (sparse, 781 of 1085 rows empty, and editable
    # after the fact -- `21792-3/5` was corrected on 2026-09-15), where this is the
    # EVENT. Stage A keys on the same column, so the two stages agree by construction.
    #
    # 🔴 CANCELLED ROWS KEEP THE `Modified` CLOCK, and must. A cancelled unit was never
    # delivered and has no delivery date -- 73 of the archive's 116 `AN` units carry
    # none at all. Filtering them on `DeliveryDate` would match nothing, forever, and
    # stage C would report a candidate count that silently omitted every cancellation.
    # There are 0 `Cancelled` rows today, so this would have gone unnoticed until the
    # first one aged out. Two halves, because the two statuses record different events.
    "(ItemStatus eq 'Delivered' and DeliveryDate lt '@{addDays(utcNow(), -%d)}') "
    "or (ItemStatus eq 'Cancelled' and Modified lt '@{addDays(utcNow(), -%d)}')"
    % (GRACE_DAYS, GRACE_DAYS)
)
A["C1_Get_deletion_candidates_REPORT_ONLY"]["runAfter"] = {
    "B3_Touch_each_stalled_unit": ["Succeeded"]
}

A["C2_Deletion_candidate_report"] = {
    "runAfter": {"C1_Get_deletion_candidates_REPORT_ONLY": ["Succeeded"]},
    "type": "Compose",
    # Count only. The rows themselves are one click away in C1's output in the
    # run history; re-serialising them here would be a second place to get the
    # column names wrong for no gain.
    "inputs": {
        "graceDays": GRACE_DAYS,
        "candidateCount": "@length(outputs('C1_Get_deletion_candidates_REPORT_ONLY')?['body/value'])",
        "note": "REPORT ONLY - nothing is deleted. Wiring the delete needs the Archive active.xlsx reconfirm plus the three open answers in archiving-plan.md.",
    },
}


def main():
    out = os.path.join("workflow-data", "nightly-cleanup",
                       "Nightly_Cleanup.definition.json")
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(definition, indent=2, ensure_ascii=False))
        f.write("\n")
    print("wrote %s" % out)
    print("  trigger : daily 01:00 %s" % TZ)
    print("  stage A : promote Active + Livraison + delivery date -> Delivered")
    print("  stage C : REPORT ONLY, grace %d days" % GRACE_DAYS)
    print("  stage B : touch the units where TODAY() is the answer "
          "(B2 reports the real count)")


if __name__ == "__main__":
    main()
