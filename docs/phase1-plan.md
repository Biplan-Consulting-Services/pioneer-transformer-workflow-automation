# Phase 1 Plan: Order Creation → Planning → Client Date Confirmation

**Status:** ready to build. Written 2026-08-12 so work can start directly next session
without re-deriving this. Update the checkboxes as pieces land; update the plan itself if
reality diverges from it.

## ⚠ Proposed reordering, raised 2026-08-14 — NOT confirmed, do not build against this yet

User raised a possible change to this plan's step order/ownership, but explicitly does **not**
want it treated as replacing the plan below — it needs confirming with the actual business
users (department staff) first. **The plan below (Work Order before Planning Schedule,
Scheduling-owned) remains the build-ready version until this is resolved.**

**What's being proposed:**
1. **`Order Entry` moves from Inside Sales to Quotation** — since Quotation already has all
   the necessary data from the quote and can fill/link everything directly, removing a
   handoff.
2. **Engineering Preliminary Review** (Electrical + Mechanical, parallel) stays next,
   expected turnaround **15-30 minutes**.
3. **Possible reordering**: Planning produces the planned/due dates *before* `Work Order`
   (the job scope workorder) exists, then sends those dates to Internal (Inside) Sales, who
   creates the job scope workorder using that date and *then* confirms with the client. This
   would reverse the plan's current assumption that `Work Order` (Scheduling) unlocks
   `Planning Schedule` — instead `Planning Schedule` would unlock `Work Order`, and `Work
   Order` may become an Inside Sales deliverable rather than Scheduling's. **Rationale given**:
   Inside Sales can't create the job scope workorder without a due date, so confirming with
   the client before that workorder exists is backwards / inefficient.

**Still unresolved, not yet asked**: does Scheduling still own something called `Work Order`
under this reordering, or does that step/name move entirely to Inside Sales? Needs a real
answer before this can be turned into a build plan, not just my inference from the
description above.

**Action before building any of this**: confirm the full reordering (and the Order Entry
department change) with the actual department staff, not just take it as decided from this
conversation alone.

## Why this slice, first

This is the front end of the business-process workflow documented in
`infrastructure-overview.md` (`## Business process workflow diagram`) —
`Customer PO → PO Docs Complete? → Order Entry → Electrical Preliminary Review + Shop Order
Preliminary Review (parallel) → Both Reference Designs Available? → Work Order → Planning
Schedule → Confirm Planned Dates with Client`. User's call, 2026-08-12: this is the biggest
current pain (no visibility/notification into whose turn it is to act, order-to-order) and
it's small enough to ship and start using immediately.

**Explicitly out of scope for Phase 1** (Phase 2+): `Electrical Design`/`Mechanical Design`
execution, `Customer Drawings`, the `P.O.` chain, `Production`, the full `Order Items`
column migration (the 42 manually-typed production-tracking fields), the calculated-column
parallel-run. Don't scope-creep into these — Phase 1 ends at `Confirm Planned Dates with
Client`.

## Order-level vs. unit-level: where the fan-out happens

**Corrected 2026-08-12** (an earlier draft of this plan wrongly assumed the whole chain was
order-level — it isn't): not every item in a multi-unit order shares the same delivery
date, so planning and client-date-confirmation genuinely happen **per unit**, not once per
order. Confirmed split:

- **Order-level** (one `Workflow Tasks` row per Order): `Order Entry`, `Electrical
  Preliminary Review`, `Shop Order Preliminary Review`. Engineering's duplicate-check is a
  property of the *order/model*, not a specific unit.
- **Fan-out point: `Work Order`.** This is where one Order becomes N per-unit records
  (N = `Order`'s `Qty`) — confirmed per-unit, one step earlier than Planning Schedule.
- **Unit-level**: `Work Order`, `Planning Schedule` — one `Workflow Tasks` row per **Order
  Item**, not per Order, since units in the same order can end up with different planned
  dates.
- **Back to order-level: `Confirm Planned Dates with Client`.** Corrected again
  2026-08-12 — even though the planning underneath it is per-unit, Sales treats the actual
  client confirmation as **one conversation covering every unit in the order**, not a
  separate confirmation per unit. So this step **converges back** to one `Workflow Tasks`
  row per Order, created only once **all** of that order's per-unit `Planning Schedule`
  tasks are `Completed` — not as soon as the first one finishes.

**This means Phase 1 needs `Order Items` to exist** as the per-unit anchor for `Work
Order`/`Planning Schedule`. **Superseded 2026-08-12**: this used to say "just build a
minimal identity-only slice, defer the rest" — the user has since elevated the *full*
`Order Items` migration (all confirmed fields, not just identity) to immediate priority,
independent of this plan, specifically to get staff off manually editing Excel as soon as
possible. See `order-items-build-plan.md` for that build — once it's done, Phase 1 just
consumes the resulting list, no separate minimal version needed here.

## Architecture decision: one shared `Workflow Tasks` list, not one list per department

User's original idea was a separate SharePoint list per department, each holding that
department's tasks/progress. **Recommended instead**: a single `Workflow Tasks` list
(exact name TBD, see below) covering every department, with **department-filtered views**
so each team still only sees their own queue day to day — looks the same to users, but:

- **One Power Automate flow to build and maintain**, not one per department list. Adding a
  6th department later means adding a filter value, not a whole new list + a whole new flow.
- **One place to look for "where is this order right now"** across every department,
  instead of a person having to check 4-5 different lists to find which one currently holds
  the order.
- **One source for a future Power BI dashboard** on order/task progress, instead of
  stitching multiple lists together.
- Department-specific "niceness" (a clean, only-my-stuff view) comes from a **filtered
  view** (`Assigned Department = [X] AND Status ≠ Completed`), which SharePoint/Microsoft
  Lists supports natively — no loss of the clean-per-department feel the original idea was
  going for.

This is a recommendation, not yet confirmed with the user — flag it explicitly when
resuming if they'd rather keep separate lists after all; the flow design below still mostly
works either way, just multiplied per list instead of centralized.

## New list: `Workflow Tasks` (name not yet confirmed)

One row per **task instance** — a specific step, for a specific order, assigned to a
specific department/person, with its own status and dates. This is intentionally generic
(not "Electrical Tasks" with electrical-specific columns) so the same list/flow handles
every department and every step, for this phase and future ones.

| Field | Type | Notes |
|---|---|---|
| Title | Text | e.g. `21865 — Order Entry` or `21865-1/5 — Planning Schedule` (readability in views) |
| Order Number | Lookup → `Order` list | Always populated — even unit-level tasks need this for grouping/rollup (e.g. "are all this order's Planning Schedule tasks done"). |
| Order Item | Lookup → `Order Items` list (optional) | **Only populated for unit-level steps** (`Work Order`, `Planning Schedule`). Blank for order-level steps (`Order Entry`, both Preliminary Reviews, `Confirm Planned Dates with Client`). |
| Step Name | Choice | Phase 1 values: `PO Clarification`, `Order Entry`, `Electrical Preliminary Review`, `Shop Order Preliminary Review`, `Work Order`, `Planning Schedule`, `Confirm Planned Dates with Client`. Add more Choice values as later phases are scoped — don't need a schema change, just a new Choice option. |
| Assigned Department | Choice | `Quotation`, `Inside Sales`, `Electrical Engineering`, `Mechanical Engineering`, `Scheduling` — matches the swimlane a step lives in on the workflow diagram |
| Assigned To | Person (optional) | Specific person, if the department wants named assignment rather than a department queue. Can stay blank and rely on department-level notification alone, at least at first. |
| Status | Choice | `Not Started`, `In Progress`, `Completed`, `Blocked` |
| Reference Design Available | Choice: Yes/No (blank until answered) | Only meaningful on `Electrical Preliminary Review` and `Shop Order Preliminary Review` rows — this is the actual duplicate-check answer feeding the AND-gate logic below. Blank/not applicable on other Step Name values. |
| Started Date | Date | Set when Status first becomes `In Progress` |
| Completed Date | Date | Set when Status becomes `Completed` — this is what unlocks the next task(s) |
| Notes | Multi-line text | Free-form |

**Why one list still works with mixed order-level/unit-level rows**: `Order Number` is
always populated (so "give me every task for order X, regardless of level" always works),
`Order Item` is populated only when relevant. The flow logic below is what actually decides
whether a given `Step Name` creates one row per Order or one row per Order Item.

## Changes to the existing `Order` list

- **`Engineering Review Status`** (Choice: `Full Duplicate` / `Partial Duplicate` / `New
  Design`, calculated) — reads both `Reference Design Available` answers off the two
  `Workflow Tasks` rows for that order (Electrical + Mechanical) once both are `Completed`.
  Confirmed 2026-08-12 as categorical, not a numeric time estimate (see
  `infrastructure-overview.md` for why).
- **Do NOT build the earlier-proposed per-`Order Step`-stage Date+Status field pairs**
  (14 pairs, floated 2026-08-12 in `infrastructure-overview.md` as unconfirmed) — the
  `Workflow Tasks` list now covers that need directly (one task row per stage, with its own
  Started/Completed dates), which is cleaner than duplicating that history onto `Order`
  itself. Treat that earlier proposal as **superseded** by this plan, not a separate
  parallel thing to still build.
- `Order Status` (Active/Cancelled, already decided in `infrastructure-overview.md`) is
  unrelated to this phase and can happen independently, in either order.

## Not blocked by the PnP PowerShell issue

**Added 2026-08-13**: while building `Order Items`, PnP PowerShell (a scripting route for
SharePoint *schema* changes) turned out to be blocked — `ermcopower` hasn't granted tenant
admin consent for that specific third-party app. That block is narrow: it does **not**
extend to the Power Automate flows this whole plan depends on. Power Automate's SharePoint
connector is Microsoft's first-party connector, already available under the existing
Microsoft 365 license, buildable directly in the browser with no IT consent needed. Nothing
in this plan is stuck — the only thing that requires manual, no-script UI work is
*creating* the `Workflow Tasks` list/columns themselves (see `order-items-manual-build-checklist.md`'s
approach for the equivalent step on `Order Items`); every flow below is fully buildable now.

## Power Automate flows

**Recommendation: one flow with branching logic (a `Switch` on `Step Name`), not one flow
per transition.** A flow per Order→next-step transition (7+ flows for this phase alone)
gets unmaintainable fast once later phases add more steps. One flow, triggered on
`Workflow Tasks` item modified, is easier to reason about and extend.

**Flow: "Workflow Tasks — advance on completion"**
- **Trigger**: `Workflow Tasks` item modified, where `Status` changed to `Completed`.
- **Logic** (`Switch` on `Step Name` of the just-completed task):
  - `Order Entry` completed (order-level) → create 2 new **order-level** tasks:
    `Electrical Preliminary Review` (Electrical Engineering) + `Shop Order Preliminary
    Review` (Mechanical Engineering), both for the same Order. Notify both.
  - `Electrical Preliminary Review` OR `Shop Order Preliminary Review` completed
    (order-level) → **Get items** from `Workflow Tasks` filtered to the same Order + the
    *other* review step. If that sibling task is also `Completed`:
    - If **both** `Reference Design Available` answers = `Yes` → this is when
      `Engineering Review Status = Full Duplicate` becomes derivable, and (per the
      workflow diagram) the early-start Purchasing path unlocks. For Phase 1's scope,
      logging/notifying this is enough — the actual early-Purchasing task creation is
      Phase 2 territory (Purchasing isn't in this phase).
    - Either way (both siblings done, regardless of Yes/No): **fan out** — if this order's
      `Order Items` rows don't exist yet, create them now (N rows, N = `Order`'s `Qty`,
      same unit-identifier scheme as `TableOrders.pq`'s `Order` column, e.g. `21865-1/5`).
      Then create one **unit-level** `Work Order` task (Scheduling) per `Order Item`, not
      one for the whole order. If the sibling review isn't done yet, do nothing — wait for
      it to trigger this same logic when *it* completes.
  - `Work Order` completed (unit-level) → create `Planning Schedule` (Scheduling),
    **unit-level** — same `Order Item` as the `Work Order` task that just completed.
  - `Planning Schedule` completed (unit-level) → **converge back to order-level**: `Get
    items` from `Workflow Tasks` filtered to this Order + `Step Name = Planning Schedule`.
    If **all** of them are now `Completed` (not just this one — Sales needs every unit's
    date before talking to the client), create ONE **order-level** `Confirm Planned Dates
    with Client` task (Inside Sales). If any sibling `Planning Schedule` task for this
    order is still open, do nothing yet.
  - `Confirm Planned Dates with Client` completed (order-level) → **end of Phase 1's
    automated chain.** (Phase 2 picks up here with Engineering execution.)
- A separate, simpler **trigger flow** creates the *first* task (`Order Entry`,
  order-level, Inside Sales) whenever a new `Order` item is created — this is what kicks
  off the whole chain per order.

## Notifications

**Updated 2026-08-12 per `phase1-tooling-research.md`**: use Adaptive Cards from the start,
not a plain Teams message — this was previously an "open decision for later," but research
into exactly this "whose turn is it" problem shows Adaptive Cards is the established
pattern, and it's not meaningfully more setup effort than a plain message.

Every task-creation branch above should also **notify the newly-responsible
person/department** so they can start immediately — this is the actual pain point being
fixed. Use both:
- **Email** (Outlook `Send an email (V2)` action) — subject includes Order Number + Step
  Name, body links directly to the `Workflow Tasks` item (or a filtered view).
- **Adaptive Card in Teams** (`Post an adaptive card and wait for a response`, posted to the
  relevant department's channel or the assigned person's chat) — shows task title, order
  number, due context, and current status in a consistent layout, with a "Mark as Started"
  (or similar) action button that flips `Status` directly from the card, not just a
  read-only ping.

Both Outlook and Teams are standard (non-premium) Power Automate connectors under most
Microsoft 365 plans — shouldn't need extra licensing, but wasn't independently confirmed
for Pioneer's specific tenant.

## Archiving — needed for this list too, not deferred

**Added 2026-08-12 per `phase1-tooling-research.md`**: SharePoint Online has a hard,
non-configurable 5,000-item List View Threshold per query scan, and a task-per-step design
generates rows faster than `Order`/`Order Items` do. Reuse the same scheduled,
verify-before-delete archiving mechanism `archiving-plan.md` already designs for
`Order`/`Order Items` — gate it on `Status = Completed` (mirroring that mechanism's
delivered/cancelled trigger). Don't defer this until the list is already large; build it
alongside the rest of Phase 1, not after.

## Nice-to-have, not blocking Phase 1

A Microsoft Planner board or a small Power App front-end over the `Workflow Tasks` list
would look nicer than a raw SharePoint list view for day-to-day use — but that's a
presentation layer over the same data model above, addable later without reshaping the
list or the flow. Don't build it as part of getting Phase 1 functional; a filtered
SharePoint list view is enough to ship and start using. **Note (2026-08-12 research):** if
this is ever revisited, it means Microsoft **Planner Premium** specifically — Planner
Premium is Dataverse-backed, not SharePoint-backed, so it could only ever be a
Power-Automate-synced *view* of `Workflow Tasks`, never the list itself, without breaking
this project's native-Lookup compatibility with `Order`/`Order Items`.

## Build order (checklist)

- [ ] Confirm the `Workflow Tasks` list name and the "one shared list vs. per-department"
      decision with the user (recommendation above, not yet confirmed).
- [ ] `Order Items` list exists — see `order-items-build-plan.md` (elevated priority, full
      build, not just an identity slice; tracked there, not duplicated here).
- [ ] Create `Workflow Tasks` list in SharePoint with the schema above (both `Order Number`
      and `Order Item` lookups).
- [ ] Create department-filtered views (`My Electrical Tasks`, `My Scheduling Tasks`, etc.)
- [ ] Add `Engineering Review Status` to the `Order` list.
- [ ] Build the "new Order → create Order Entry task" trigger flow.
- [ ] Build the main "Workflow Tasks — advance on completion" flow (the Switch-based one
      above), including the AND-gate sibling-check logic, the fan-out at `Work Order`
      (create `Order Items` rows + one `Work Order` task per unit), and the converge-back
      "all Planning Schedule tasks done" check before creating `Confirm Planned Dates with
      Client`.
- [ ] Wire in email + Adaptive Card notifications on every task-creation branch.
- [ ] Build the archiving flow for `Workflow Tasks` (`Status = Completed` trigger, same
      scheduled/verify-before-delete mechanism as `archiving-plan.md`) alongside the rest of
      this build, not deferred.
- [ ] Test end-to-end with one real or dummy multi-unit order (`Qty` > 1) through the whole
      Phase 1 chain before rolling out to the team — the fan-out/converge logic is the part
      most likely to have an off-by-one or timing bug, worth deliberately testing with more
      than one unit, not just a `Qty = 1` order.
- [ ] Roll out to the team; get feedback before scoping Phase 2 (Engineering execution
      onward).

## Open decisions (not blocking, but need an answer eventually)

- Named-person `Assigned To` vs. department-queue-only notification, at least at first?
- Teams: channel post vs. DM to the assigned person?
- **Adaptive Card granularity and lifecycle — added 2026-08-14, discuss when this workstream
  is actually picked up, not decided yet:**
  - Cards should **link directly to the actual `Workflow Tasks` item in SharePoint**, so
    clicking through goes straight to the task, not just a generic list view.
  - Open question on granularity — three options floated, none chosen: **(a)** one card per
    department/person showing a *total count* of how many open tasks they currently have
    (a summary/dashboard-style card), **(b)** one card per task *type* (`Step Name`),
    listing open tasks of that kind, or **(c)** one card per individual task (today's
    default assumption in this plan, one `Post an adaptive card` call per task-creation
    branch).
  - **Requirement, whichever granularity is chosen**: cards should disappear or update once
    their underlying task is `Completed`, so a person's Teams view only ever shows
    outstanding work, not a growing pile of stale completed-task cards. Note for whoever
    builds this: Power Automate's Teams connector can **update or delete a previously
    posted adaptive card** if the message ID from the original post is captured and stored
    (e.g. on the `Workflow Tasks` row itself) — a live-count summary card (option a) would
    need this same message-ID-tracking approach, updated in place rather than reposted, to
    behave like a running dashboard rather than a new message every time.
- **New idea, 2026-08-14**: a separate **`Task Responsibilities`** list (name TBD) mapping
  each `Step Name` to its owning department/person, instead of hardcoding that mapping
  inside the Switch-based flow's branches. Would let responsibility assignments be edited by
  an admin directly in SharePoint without touching the Power Automate flow logic — worth
  weighing against the current plan's simpler hardcoded-in-flow approach when this
  workstream is built.

(Adaptive card vs. plain message is no longer open — decided 2026-08-12, see
`phase1-tooling-research.md`: build the interactive Adaptive Card from the start.)
