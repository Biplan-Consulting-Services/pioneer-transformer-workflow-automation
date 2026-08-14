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
- [x] 2c. Production-sequence auto-stamp (16 Start/End Date stamps) — **built & tested
      2026-08-14**, in its own parallel branch alongside 2b's TextField sync branch
- [ ] 2c-extra. N/A status handling (added mid-build, 2026-08-14): schema done, flow logic
      not yet built — see its own section below
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

### Flow A — `Order Items - created or updated trigger`

**Naming decision, 2026-08-13**: this flow is named after its trigger (`Order Items -
created or updated trigger`), not its current purpose — user's call, so that adding more
logic to it later (which is exactly what happened with step 2c below) never requires a
rename. **This is also the single merged flow for both step 2b's TextField sync and step
2c's production-sequence auto-stamp** — both already trigger on the same event on the same
list and both use the same consolidated-variable-then-gated-update shape, so one flow with
one `Update item` call handles both concerns instead of two flows each re-triggering the
other on every write.

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

**Built and tested 2026-08-14.** Built into the same flow as step 2b — `Order Items -
created or updated trigger`, not a separate flow (see the naming decision under Flow A
above). Structured as a **parallel branch** alongside 2b's TextField-sync branch, for
visibility/readability in the designer — both branches feed the same shared gating flag and
converge into the one existing `Update item` call (see "Parallel-branch mechanics" below for
how the join actually works).

**Schema**: each of the 8 stages has `{Stage} Start Date` and `{Stage} End Date` (see
`order-items-manual-build-checklist.md`'s Production-sequence dates section for the full
field list) plus `{Stage} Status` (Choice: `Pending`/`In Progress`/`Completed`/`N/A` — `N/A`
added 2026-08-14, see the N/A section below).

**Why two stamps per stage, not one**: `{Stage} Status` already distinguishes `Pending`
(not started) from `In Progress` (actively being worked) from `Completed`. Capturing the
`Pending → In Progress` transition as `{Stage} Start Date` gives an accurate start time,
unaffected by any idle/waiting time before work actually began — inferring a start time
from the *previous* stage's finish time instead would wrongly count that idle time as work
time.

**The 16 stamp conditions** (2 per stage × 8 stages — Coiling, Stacking, Assembly, Drying,
Tanking, Testing, Finishing, Delivery):

| Stage | Start-stamp condition | End-stamp condition |
|---|---|---|
| Coiling | `Coiling Status Value` = `In Progress` AND `Coiling Start Date` empty | `Coiling Status Value` = `Completed` AND `Coiling End Date` empty |
| Stacking | `Stacking Status Value` = `In Progress` AND `Stacking Start Date` empty | `Stacking Status Value` = `Completed` AND `Stacking End Date` empty |
| Assembly | `Assembly Status Value` = `In Progress` AND `Assembly Start Date` empty | `Assembly Status Value` = `Completed` AND `Assembly End Date` empty |
| Drying | `Drying Status Value` = `In Progress` AND `Drying Start Date` empty | `Drying Status Value` = `Completed` AND `Drying End Date` empty |
| Tanking | `Tanking Status Value` = `In Progress` AND `Tanking Start Date` empty | `Tanking Status Value` = `Completed` AND `Tanking End Date` empty |
| Testing | `Testing Status Value` = `In Progress` AND `Testing Start Date` empty | `Testing Status Value` = `Completed` AND `Testing End Date` empty |
| Finishing | `Finishing Status Value` = `In Progress` AND `Finishing Start Date` empty | `Finishing Status Value` = `Completed` AND `Finishing End Date` empty |
| Delivery | `Delivery Status Value` = `In Progress` AND `Delivery Start Date` empty | `Delivery Status Value` = `Completed` AND `Delivery End Date` empty |

Each condition, if true: set that stage's `v{Stage}{Start/End}DateValue` variable (String,
initialized to the trigger's current value of that field) to
`convertFromUtc(utcNow(), 'Eastern Standard Time')`, and flip the shared gating flag to
`true`. Checking "the field is currently blank" (not just "Status = X") is what makes each
stamp fire exactly once — once set, that field is no longer blank, so re-editing the item
later never re-stamps it.

**Timezone: Eastern.** Pioneer's shop floor runs on Eastern time, so every stamp expression
uses `convertFromUtc(utcNow(), 'Eastern Standard Time')`, not bare `utcNow()` (which would
store UTC and misrepresent shift times).

### Hard-won build lessons (2026-08-14) — read before touching this flow again

1. **Choice fields need the `Value` suffix here too** — originally assumed (wrongly) that
   only Lookup fields get wrapped in a `{Field} Value` dynamic-content variant and Choice
   fields come through as plain strings. Not true for this list/connector: `Coiling Status`
   alone didn't match; **`Coiling Status Value`** was needed. Confirmed by checking the raw
   trigger output JSON in a test run — do that first if a condition mysteriously never
   fires, rather than guessing at dynamic-content shape.
2. **Blank literal comparison silently fails on Date fields** — the simple Condition UI's
   "is equal to" with an empty right-hand box compares against literal `""`, but an unset
   SharePoint Date field's trigger value is `null`, and `null ≠ ""`. Fix: use the `empty()`
   expression function instead of a blank-literal comparison.
3. **`Update item` rejects `""` for Date fields** — a String variable initialized from a
   blank/null trigger date silently becomes `""`, and writing `""` back to a SharePoint Date
   parameter throws `Input parameter '...' is required to be of type 'String/date-time'`.
   Fix applied to all 16 date field mappings on `Update item`:
   `if(equals(variables('v{Stage}{Start/End}DateValue'), ''), null, variables('v{Stage}{Start/End}DateValue'))`
   — converts the empty string back to true `null`, which the connector accepts as "leave
   blank." Plain Text/Choice TextField mappings don't need this wrapper — empty string is
   fine for those, this is Date-type-specific.
4. **Parallel-branch mechanics**: the join isn't a UI action, it's the **"Configure run
   after"** setting on whatever action sits right after both branches (here, the shared
   `Update item`) — open its "..." menu → Configure run after → confirm both branches' last
   actions are listed with "is successful" checked. If only one branch shows up there, the
   flow will race ahead without waiting for the other.

## N/A status handling (added mid-build, 2026-08-14) — schema done, flow logic NOT built yet

**Why**: the auto-advance logic below (still to build) assumes every unit goes through all
8 stages with no skips. Since that's not always true, staff need a manual way to mark a
stage as not applicable to a given unit, without breaking the auto-advance chain or leaving
stale dates behind. **Future idea** (logged in `roadmap.md`, not started): a Model
Revisions-level field listing which stages actually apply to a design, so this could be
inferred automatically instead of relying on staff to catch it — not needed to ship this.

- [x] Schema: added **`N/A`** as a 4th Choice option on all 8 `{Stage} Status` fields.
- [ ] Flow logic — **not yet built**, two pieces:

**A. Extend the 7 advance-to-Pending conditions** (see next section — these aren't built
yet either) to treat `N/A` the same as `Completed` as a trigger for advancing the next
stage: `({Stage} Status Value = Completed OR {Stage} Status Value = N/A) AND {NextStage}
Status Value is empty`. Needs a **nested row group** in the Condition action (top-level
And, with a nested Or group for Completed/N/A) — see chat for the exact "Add row group" UI
steps, or use advanced/expression mode with `and(or(...), empty(...))`.

**B. Clear dates when a stage is set to `N/A`** — 8 new conditions, one per stage (including
Coiling, since staff can mark it N/A directly with nothing "previous" involved):

| Stage | Condition | Action |
|---|---|---|
| Coiling | `Coiling Status Value` = `N/A` | Set `vCoilingStartDateValue` = `null`, `vCoilingEndDateValue` = `null`, flag = `true` |
| Stacking | `Stacking Status Value` = `N/A` | Set `vStackingStartDateValue` = `null`, `vStackingEndDateValue` = `null`, flag = `true` |
| Assembly | `Assembly Status Value` = `N/A` | Set `vAssemblyStartDateValue` = `null`, `vAssemblyEndDateValue` = `null`, flag = `true` |
| Drying | `Drying Status Value` = `N/A` | Set `vDryingStartDateValue` = `null`, `vDryingEndDateValue` = `null`, flag = `true` |
| Tanking | `Tanking Status Value` = `N/A` | Set `vTankingStartDateValue` = `null`, `vTankingEndDateValue` = `null`, flag = `true` |
| Testing | `Testing Status Value` = `N/A` | Set `vTestingStartDateValue` = `null`, `vTestingEndDateValue` = `null`, flag = `true` |
| Finishing | `Finishing Status Value` = `N/A` | Set `vFinishingStartDateValue` = `null`, `vFinishingEndDateValue` = `null`, flag = `true` |
| Delivery | `Delivery Status Value` = `N/A` | Set `vDeliveryStartDateValue` = `null`, `vDeliveryEndDateValue` = `null`, flag = `true` |

Place these 8 conditions **after** the 16 stamp conditions in the branch, so a stage
corrected to `N/A` after already picking up a stamp has the clear win out (defensive
ordering — a stage can't actually be both `In Progress`/`Completed` and `N/A` at once, but
order matters if that assumption is ever wrong).

## Advance-to-Pending logic — NOT built yet

**Why**: when a stage finishes (`Completed`) or is skipped (`N/A`), the *next* stage should
automatically move from blank ("not relevant yet") to `Pending` ("queued, not started"), so
staff don't have to manually advance every stage themselves. Confirmed design 2026-08-14:
fires on `Completed` **or** `N/A` (not just Completed), only when the next stage is
currently blank (so it never overwrites a stage a human has already touched).

7 transitions (Delivery has no next stage):

| Previous stage | Next stage | Condition | Action if true |
|---|---|---|---|
| Coiling | Stacking | (`Coiling Status Value` = `Completed` OR `= N/A`) AND `Stacking Status Value` is empty | Set `vStackingStatusValue` = `Pending`, flag = `true` |
| Stacking | Assembly | (`Stacking Status Value` = `Completed` OR `= N/A`) AND `Assembly Status Value` is empty | Set `vAssemblyStatusValue` = `Pending`, flag = `true` |
| Assembly | Drying | (`Assembly Status Value` = `Completed` OR `= N/A`) AND `Drying Status Value` is empty | Set `vDryingStatusValue` = `Pending`, flag = `true` |
| Drying | Tanking | (`Drying Status Value` = `Completed` OR `= N/A`) AND `Tanking Status Value` is empty | Set `vTankingStatusValue` = `Pending`, flag = `true` |
| Tanking | Testing | (`Tanking Status Value` = `Completed` OR `= N/A`) AND `Testing Status Value` is empty | Set `vTestingStatusValue` = `Pending`, flag = `true` |
| Testing | Finishing | (`Testing Status Value` = `Completed` OR `= N/A`) AND `Finishing Status Value` is empty | Set `vFinishingStatusValue` = `Pending`, flag = `true` |
| Finishing | Delivery | (`Finishing Status Value` = `Completed` OR `= N/A`) AND `Delivery Status Value` is empty | Set `vDeliveryStatusValue` = `Pending`, flag = `true` |

**Build steps**:
1. **7 new "Initialize variable" actions** (String), one per next-stage
   (`v{NextStage}StatusValue`), initial value = that stage's current trigger Status value.
2. **7 new Condition actions**, per the table — needs the same nested-row-group technique as
   the N/A extension above (Or inside, And outside).
3. **7 new field mappings on the shared `Update item`**: `{NextStage} Status` =
   `if(equals(variables('v{NextStage}StatusValue'), ''), null, variables('v{NextStage}StatusValue'))`
   — same null-safe wrapper as the dates, since blank is a valid real state here too.

This won't loop: once `{NextStage} Status` flips from blank to `Pending`, the self-triggered
re-run sees it's no longer blank and the guard stops it from firing again.
