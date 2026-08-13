# Order Items — Power Automate Flows to Build

Build-ready specs for the flows tracked in `order-items-build-plan.md`'s build sequence
(steps 2b, 2c, 3). Not blocked by the PnP consent issue — Power Automate's first-party
SharePoint connector is available now, buildable directly at make.powerautomate.com.

**Scope note (2026-08-13)**: the TextField auto-sync work (2b) turned out to span every
Lookup column across the whole system, not just `Order Items`/`Model Revisions` — see
`docs/lookup-textfield-reference.md` for the complete list-by-list table (which fields need
the Simple pattern vs. the Get-item pattern vs. the one chained case), kept there as a
standalone reference rather than duplicated here.

## Progress

- [x] 2b. TextField auto-sync — **done 2026-08-13 for every Lookup that currently has a
      TextField column**: `Order Items`/`Order Number` (built & tested), `Model Revisions`
      (all three: `Duplicate Order`, `Client`, `Pioneer Model Code`), `Models`,
      `EngineeringChangeOrders`, and `ModelChanges` (all three, including the chained
      `Client_ID_TextField`). Full detail in `lookup-textfield-reference.md`. Two things
      remain, both already known, not new gaps: `Regrouped Into` (deferred, nice-to-have)
      and the three `Order` fields (blocked — missing their TextField columns in SharePoint
      entirely, a schema step first).
- [ ] 2c. Production-sequence auto-stamp
- [ ] 3. Excel → SharePoint transfer flow (re-runnable)

## Step 2b — TextField auto-sync

**Why**: every Lookup field (`Order Number`, `Regrouped Into` on `Order Items`;
`Duplicate Order` on `Model Revisions`) has a companion `_TextField` holding a plain-text
copy, for search/filtering. Keeping these in sync by hand has been a real pain point —
this automates it.

**⚠ Infinite-loop risk — read before building.** Both flows below update the *same item*
that triggered them. A naive "when item created or modified → update item" flow can
re-trigger itself forever. **Guard every flow with a condition that skips the update if
the TextField already matches the looked-up value** — the self-triggered re-run then finds
nothing to change and exits without looping.

### Flow A — `Order Items` Lookup sync

**Built and tested 2026-08-13** (the `Order Number` piece):
- **Trigger**: SharePoint *"When an item is created or modified"* — Site:
  `https://ermcopower.sharepoint.com/sites/PioneerPlanificatio`, List: `Order Items`.
- **Condition**: `Order Number Value` (the dynamic-content variant that holds the
  looked-up item's display text — not `Order Number` or `Order Number Id`) **is equal to**
  `Order_Number_TextField`.
  - **If yes**: nothing (already in sync).
  - **If no**: Update item (Id = trigger's `ID`, only `Order_Number_TextField` set = `Order
    Number Value`) — this is the loop-prevention guard, structured around "equal" instead
    of "not equal" but same effect.
- **Tested**: changing `Order Number` on a row produces exactly one flow run and updates
  the TextField correctly — confirmed no loop.

**`Regrouped Into` piece — deferred, 2026-08-13.** Not needed now, user's call — nothing's
been regrouped yet and it's a nice-to-have, not blocking. If picked up later: same
condition/update structure as `Order Number`, but `Regrouped Into` is multi-value, so its
dynamic content is an array, not a plain string — needs a `join(select(...), ', ')`-style
expression to flatten it to text first. Check the actual dynamic-content picker output for
this field before trusting any specific expression syntax.

### Flow B — `Model Revisions` Lookup sync

**Built 2026-08-13** — three Lookups synced (`Duplicate Order`, `Client`, `Pioneer Model
Code`, not just `Duplicate Order` as originally scoped — see `lookup-textfield-reference.md`).
`Client` used the **Get-item** pattern (fetch `Client_ID` from `Clients`); the other two are
Simple. Built using the consolidated-update shape (variables per field, one boolean flag
flipped on any mismatch, one final `Update item` gated on that flag) rather than three
separate update actions.

### Testing before trusting this

1. ✅ **Done 2026-08-13** (`Order Items`/`Order Number`): changed `Order Number` on one
   `Order Items` row, confirmed `Order_Number_TextField` updated and exactly **one** flow
   run in the run history — no loop.
2. **`Model Revisions` — confirm before moving on**: test each of the three fields
   independently (change `Duplicate Order` alone, `Client` alone, `Pioneer Model Code`
   alone) and check the run history shows exactly one run per change, all three TextFields
   land correctly, and no loop. Also worth one test changing more than one field at once,
   to confirm the consolidated update still fires exactly once and gets all of them right.
3. `Regrouped Into` — deferred, see note above. Test whenever it's picked up.

## Step 2c — Production-sequence auto-stamp

**Schema ready as of 2026-08-13** — each of the 8 stages now has `{Stage} Start Date`
(NEW) and `{Stage} End Date` (renamed from the original `{Stage} Date`), confirmed live via
a fresh export. See `order-items-manual-build-checklist.md`'s Production-sequence dates
section for the full field list. Expanded from "stamp finish time only" to "stamp start
*and* finish" for real time-spent tracking, not just completion dates — see
`order-items-build-plan.md` step 2c for why.

**Why two stamps per stage, not one**: `{Stage} Status` already distinguishes `Pending`
(not started) from `In Progress` (actively being worked) from `Completed`. Capturing the
`Pending → In Progress` transition as `{Stage} Start Date` gives an accurate start time,
unaffected by any idle/waiting time before work actually began — inferring a start time
from the *previous* stage's finish time instead would wrongly count that idle time as work
time.

**Flow — `Order Items`, "When an item is created or modified"**: for each of the 8 stages,
two independent stamp checks:
- `{Stage} Status = In Progress` **AND** `{Stage} Start Date` is blank → that stage needs
  its start stamped now.
- `{Stage} Status = Completed` **AND** `{Stage} End Date` is blank → that stage needs its
  finish stamped now.

Same consolidated-update shape as the TextField flows: one variable per field that needs
stamping (up to 16, though usually far fewer will fire in any single run), one boolean flag
flipped by any check above, one final `Update item` gated on that flag. Checking "the field
is currently blank" (not just "Status = X") is what makes each stamp fire exactly once —
once set, that field is no longer blank, so re-editing the item later never re-stamps it.

**Timezone — decided 2026-08-13: Eastern.** Pioneer's shop floor runs on Eastern time, so
every stamp expression uses `convertFromUtc(utcNow(), 'Eastern Standard Time')`, not bare
`utcNow()` (which would store UTC and misrepresent shift times). Apply this consistently to
all 16 stamp expressions (`Start Date` and `End Date`, all 8 stages).
