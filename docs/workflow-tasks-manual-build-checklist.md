# Workflow Tasks — Manual Build Checklist

**Why this doc exists**: same reason as `order-items-manual-build-checklist.md` — PnP
PowerShell is blocked on this tenant (`ermcopower` hasn't granted admin consent), so the
list/columns get created through the SharePoint UI by hand. That block does **not** extend
to Power Automate (Microsoft's first-party SharePoint connector) — every flow below is
buildable now, in the browser, no IT consent needed.

Field names, types, and choice values below are the confirmed schema from
`phase1-plan.md`'s "New list: `Workflow Tasks`" section, resolved against the
2026-08-21-confirmed `Planning Schedule`/`Work Order` reorder and the one-shared-list
decision (also confirmed 2026-08-21) — nothing here is still pending.

Site: `https://ermcopower.sharepoint.com/sites/PioneerPlanificatio` (same site as `Order
Items`/`Order`/`Models`).

## Progress

- [ ] 1. Create the `Workflow Tasks` list + columns
- [ ] 2. Add `Engineering Review Status` to the `Order` list
- [ ] 3. Create department-filtered views
- [ ] 4. Build the "new Order → create Order Entry task" trigger flow
- [ ] 5. Build the "Workflow Tasks — advance on completion" flow
- [ ] 6. Wire in email + Adaptive Card notifications
- [ ] 7. Build the archiving flow (`Status = Completed` trigger)
- [ ] 8. End-to-end test with a multi-unit (`Qty` > 1) order

## Step 1 — Create the `Workflow Tasks` list

Create a new custom list named **Workflow Tasks**, no template, blank.

| # | Field name | Type | Choice values / details |
|---|---|---|---|
| 1 | Title | (default) | e.g. `21865 — Order Entry` or `21865-1/5 — Planning Schedule` — set by the flow that creates each task, not typed by hand. |
| 2 | Order Number | **Lookup** | Get information from: **Order**. In this column: **Order Number**. Always populated, even for unit-level steps (needed for order-wide rollups like the `Work Order` convergence check). |
| 2b | Order_Number_TextField | Single line of text | Companion text field, same convention as every other Lookup system-wide (see `lookup-textfield-reference.md`). |
| 3 | Order Item | **Lookup** | Get information from: **Order Items**. In this column: **Unit ID** (the `Title` field, displayed as `Unit ID`). **Optional** — only populated for unit-level steps (`Planning Schedule`, `Work Order`). Blank for order-level steps. |
| 3b | Order_Item_TextField | Single line of text | Companion text field. |
| 4 | Step Name | Choice | `PO Clarification`, `Order Entry`, `Electrical Preliminary Review`, `Shop Order Preliminary Review`, `Planning Schedule`, `Work Order`, `Confirm Planned Dates with Client`. (Order in this list is just alphabetical/creation order — it doesn't encode process sequence.) |
| 5 | Assigned Department | Choice | `Quotation`, `Inside Sales`, `Electrical Engineering`, `Mechanical Engineering`, `Scheduling` — matches the swimlane a step lives in. Per the 2026-08-21 reorder: `Order Entry` = Quotation, `Work Order` = Inside Sales, `Planning Schedule` = Scheduling. |
| 6 | Assigned To | Person | Optional — can stay blank and rely on department-level notification alone, at least at first. |
| 7 | Status | Choice | `Not Started`, `In Progress`, `Completed`, `Blocked` |
| 8 | Reference Design Available | Choice | `Yes`, `No` (blank = not applicable). Only meaningful on `Electrical Preliminary Review` / `Shop Order Preliminary Review` rows. |
| 9 | Started Date | Date and Time | Stamped by flow when `Status` first becomes `In Progress`. |
| 10 | Completed Date | Date and Time | Stamped by flow when `Status` becomes `Completed` — this is what unlocks the next task(s). |
| 11 | Notes | Multiple lines of text | Free-form, plain text. |

## Step 2 — Add `Engineering Review Status` to `Order`

| Field name | Type | Choice values |
|---|---|---|
| Engineering Review Status | Choice | `Full Duplicate`, `Partial Duplicate`, `New Design` |

Calculated by the main flow once both Preliminary Review tasks for an order are
`Completed` (see Step 5 below) — not a SharePoint-native calculated column (needs both
departments' `Reference Design Available` answers, which live on separate `Workflow Tasks`
rows, not on `Order` itself).

## Step 3 — Department-filtered views

One view per department, each filtered to `Assigned Department = [X] AND Status ≠
Completed`, so a team only sees their own open queue:

- `My Quotation Tasks`
- `My Inside Sales Tasks`
- `My Electrical Engineering Tasks`
- `My Mechanical Engineering Tasks`
- `My Scheduling Tasks`

Sort each by `Started Date` (or creation date) ascending so the oldest open task surfaces
first — that's usually the most overdue one.

## Step 4 — Trigger flow: "New Order → create Order Entry task"

- **Trigger**: `Order` item created.
- **Action**: create one `Workflow Tasks` row — `Step Name = Order Entry`, `Assigned
  Department = Quotation` (2026-08-21 reorder — was Inside Sales), `Order Number` = the new
  Order, `Order Item` blank (order-level), `Status = Not Started`.
- Notify Quotation (email + Adaptive Card, see Step 6).

## Step 5 — Main flow: "Workflow Tasks — advance on completion"

One flow, `Switch` on `Step Name`, triggered on `Workflow Tasks` item modified where
`Status` changed to `Completed`. Sequence reflects the 2026-08-21-confirmed reorder:

1. **`Order Entry` completed** (order-level) → create 2 order-level tasks: `Electrical
   Preliminary Review` (Electrical Engineering) + `Shop Order Preliminary Review`
   (Mechanical Engineering), same Order. Notify both.
2. **`Electrical Preliminary Review` OR `Shop Order Preliminary Review` completed**
   (order-level) → `Get items` filtered to the same Order + the *other* review step.
   - If that sibling isn't `Completed` yet, do nothing — wait for it.
   - If both are `Completed`:
     - If both `Reference Design Available = Yes` → set `Order.Engineering Review Status =
       Full Duplicate`; if one Yes one No → `Partial Duplicate`; if both No → `New Design`.
       Log/notify the early-Purchasing unlock (actual task creation is Phase 2, Purchasing
       isn't in this phase).
     - Fan out (regardless of Yes/No): if this order's `Order Items` rows don't exist yet,
       create them (N rows, N = `Order.Qty`). Then create one **`Planning Schedule`** task
       (Scheduling, unit-level) per `Order Item`.
3. **`Planning Schedule` completed** (unit-level) → create **`Work Order`** task (**Inside
   Sales**, unit-level), same `Order Item`, carrying the planned date forward.
4. **`Work Order` completed** (unit-level) → `Get items` filtered to this Order + `Step
   Name = Work Order`. If **all** are `Completed`, create ONE order-level `Confirm Planned
   Dates with Client` task (Inside Sales). If any sibling is still open, do nothing.
5. **`Confirm Planned Dates with Client` completed** (order-level) → end of Phase 1's
   automated chain (Phase 2 picks up with Engineering execution).

## Step 6 — Notifications

Per task-creation branch above: **Outlook `Send an email (V2)`** (subject = Order Number +
Step Name, body links to the `Workflow Tasks` item) + **Teams `Post an adaptive card and
wait for a response`** (posted to the department channel or assigned person, with a "Mark
as Started" action that flips `Status` directly). See `phase1-plan.md`'s "Notifications"
section and `phase1-tooling-research.md` for the card JSON shape — granularity (per-task vs.
per-department-summary) is still an open decision there, doesn't block building per-task
cards first.

## Step 7 — Archiving flow

Same scheduled, verify-before-delete mechanism as `archiving-plan.md`, gated on `Status =
Completed` (see `phase1-plan.md`'s "Archiving" section). Build alongside the rest, not
deferred — SharePoint's 5,000-item list view threshold applies here too, and a
task-per-step design fills faster than `Order`/`Order Items`.

## Step 8 — End-to-end test

Use one real or dummy order with `Qty > 1` and walk it through every step above, confirming:
fan-out creates the right number of `Planning Schedule` tasks, each unit's `Work Order`
completes independently, and `Confirm Planned Dates with Client` only fires once **every**
unit's `Work Order` is `Completed` — this convergence check is the part most likely to have
an off-by-one/timing bug.

## Open, not blocking

- Named-person `Assigned To` vs. department-queue-only, at least at first.
- Teams: channel post vs. DM.
- Adaptive Card granularity/lifecycle (see `phase1-plan.md`'s "Open decisions").
- A separate `Task Responsibilities` list mapping `Step Name` → owning department, instead
  of hardcoding it in the flow's `Switch` branches (idea logged 2026-08-14, not built).
