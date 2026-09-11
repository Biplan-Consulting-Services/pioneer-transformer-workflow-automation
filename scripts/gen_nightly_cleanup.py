# -*- coding: utf-8 -*-
"""Generate the Nightly Cleanup flow definition as pasteable JSON.

    python scripts/gen_nightly_cleanup.py

Writes workflow-data/nightly-cleanup/Nightly_Cleanup.definition.json.

WHAT THE FLOW DOES -- two stages, one daily run at 01:00 Eastern

  A  SET DELIVERED    Active units at Location = Livraison with a delivery date
                      become Item Status = Delivered / Delivery Status = Completed.
  C  ARCHIVE SWEEP    REPORT ONLY. Counts the rows old enough to delete.
                      IT DELETES NOTHING -- see "STAGE C IS DELIBERATELY INERT".

THERE IS NO STAGE B, AND THAT IS THE POINT -- measured 2026-09-11
  The plan called for a third stage: touch rows nightly so SharePoint
  re-evaluates the `Estimated Delivery Date` calculated column, which freezes at
  write time because its formula uses TODAY(). Two measurements killed it.

  1. THE COLUMN DOES NOT EXIST. `Order Items` has no `Estimated Delivery Date`
     and no calculated column at all. The only estimate columns are
     `Manual Estimated Delivery Date` (hand-typed) and `Model - Estimated
     Effort` (parent-sync). Roadmap item 20 reads "SharePoint accepts TODAY(),
     so the column is buildable" -- buildable, not built. A refresh pass for a
     column nobody has created is pure cost.

  2. THE FILTER DOES NOT FILTER. calculated-columns-plan.md:548 says narrowing
     to `Item Status = Active` + both delivery-date columns null "cuts the work
     by roughly 50x". Counted against the live list it cuts it by 1.3x:

         total rows                                  1,189
         Item Status = Active                        1,087
           + no Delivery End Date                    1,087   (unchanged!)
           + no Manual Estimated Delivery Date         915

     Of course it does -- an Active unit has no delivery date BY DEFINITION, so
     the second clause is a no-op and the third removes 172. That is 915 writes
     a night: ~334,000 versions a year, and ~1,830 Power Automate actions every
     night, which on a standard Office 365 allowance of 2,000/day consumes the
     entire daily budget and starves the five event-triggered flows.

  WHEN THE COLUMN IS ACTUALLY BUILT, do not build it as calculated + touch pass.
  Either:
    - make it a PLAIN column this flow owns, computed in the flow and written
      only when the value differs -- the same needsUpdate -> If -> Patch shape
      the N3 flows already use, which tested clean on 2026-09-10 ("needsUpdate
      false, write skipped"). Steady-state writes fall to the few rows that
      actually crossed a boundary, and a plain column sorts, filters and indexes
      properly, which a TODAY()-based calculated column does badly anyway; or
    - do not store it at all -- compute it in Power Query for the viewer and in
      DAX for Power BI. Zero writes, never stale, but no SharePoint view can
      sort or filter on it.
  The deciding question is whether anyone needs to sort/filter a list view by
  it. Yes -> plain flow-owned column. No -> compute it in the consumers.

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

🔴 IF A TOUCH PASS IS EVER ADDED, IT MUST NOT TOUCH Delivered/Cancelled ROWS
  A touch bumps `Modified`, and Stage C's grace period keys on `Modified`. A
  pass that touched Delivered/Cancelled rows would reset the grace clock on
  exactly the rows Stage C is waiting on -- every night, forever -- so nothing
  would ever become eligible for deletion and the archive sweep would silently
  never fire. Whatever replaces the dropped stage, keep it off those rows, or
  move Stage C onto a dedicated "delivered on" timestamp instead of `Modified`.

STAGE C IS DELIBERATELY INERT
  archiving-plan.md lists three questions with no answer yet:
    - is one month the right grace period?
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

# Grace period for stage C's report, in days. archiving-plan.md proposes one
# month and flags the number itself as an open question -- change it here.
GRACE_DAYS = 30

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
# (no stage B -- see "THERE IS NO STAGE B" in the module docstring)
A["C1_Get_deletion_candidates_REPORT_ONLY"] = get_items(
    "(ItemStatus eq 'Delivered' or ItemStatus eq 'Cancelled') "
    "and Modified lt '@{addDays(utcNow(), -%d)}'" % GRACE_DAYS
)
A["C1_Get_deletion_candidates_REPORT_ONLY"]["runAfter"] = {
    "A2_For_each_delivery_candidate": ["Succeeded"]
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
    print("  (no stage B - see the module docstring)")


if __name__ == "__main__":
    main()
