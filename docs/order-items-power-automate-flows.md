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
- [x] 2c-extra. N/A status handling + advance-to-Pending logic — **built & tested
      2026-08-14**, full production cycle (all 8 stages) confirmed working end-to-end
- [ ] 3. Excel → SharePoint transfer flow (re-runnable) — spec fully drafted and resolved
      2026-08-17. Full field-by-field mapping below, verified against the live workbook's
      raw `TableOrders` data (not guessed) — see "How this was verified" at the end of the
      step. All design questions raised during drafting (archive reconciliation, the
      `In Progress` stage guess, the `Model Revisions` matching key) are resolved — no open
      design items blocking the build. **Build itself is in progress, started 2026-08-17 —
      see "Build progress" right below this list for exactly what's built/tested vs. not, so
      resuming doesn't require re-deriving state from memory.**

### Build progress (live Power Automate flow — updated as pieces land, not just the spec)

Flow name: **`Order Items - Excel transfer flow`**. Status as of 2026-08-18:

**Built and tested:**
- **All 8 production-sequence stages' `{Stage} End Date`/`{Stage} Status`** (16 fields, on
  both `CreateOrderItem` and `UpdateOrderItem`) — built and confirmed passing all 256 rows
  2026-08-18. `{Stage} Start Date` deliberately **not mapped at all** (user's call — an
  unmapped field on a new `Create item` row stays blank exactly like an explicit `null()`
  would, so there's no need to spell it out; note this means a re-run of `UpdateOrderItem`
  will **not** clear a manually-set `Start Date` the way the rest of the "always overwrite"
  design does for every other field — accepted as fine since Start Date is never written by
  this flow in the first place, so there's nothing of its own to reset).
  - **Real production data gotcha, found via a live test failure (6 of 256 rows, first
    failure at iteration 114)**: `int()` on the raw serial value threw
    `"The value cannot be converted to the target type"` — root cause was **not** a bad
    value, it's a real, intentional non-date marker. The per-stage `{Stage} Date` columns
    can hold the literal text `EC` (**"En cours"**, i.e. "in progress") instead of a serial
    number, when that specific stage is actively being worked and not yet finished — the
    same `EC` code already documented (2026-08-17) as the composite `Status` field's
    in-progress prefix, just also used per-stage in these columns, previously undiscovered.
    **This does not violate the 2026-08-17 "don't infer In Progress from Location" decision**
    — that rule was about not *guessing* which of the 8 stages is active from an unrelated
    field; `EC` in a stage's own date column is an explicit, per-stage signal, not an
    inference. Final expressions (both fields check for `EC` in addition to blank):
    `{Stage} Status` = `if(equals(trim(item()?['{Stage} Date']), ''), null,
    if(equals(trim(item()?['{Stage} Date']), 'EC'), 'In Progress', 'Completed'))`;
    `{Stage} End Date` = `if(or(equals(trim(item()?['{Stage} Date']), ''),
    equals(trim(item()?['{Stage} Date']), 'EC')), null, addDays('1899-12-30',
    int(item()?['{Stage} Date'])))`. **Lesson for any future raw-`TableOrders` field parsing
    in this flow**: check for known non-numeric status-code markers (`EC` and possibly other
    composite-`Status` prefixes — `AT`/`RE`/`BO`/`TE`/`B1`-`B3`) before assuming a "date"
    column is cleanly numeric-or-blank, same category of gotcha as `indéterrminé`/`CONFRIMED`
    elsewhere in this data.
- Trigger (manual) + `List rows present in a table` on `TableOrders` (pagination
  threshold set to `5000` for the real run; was temporarily lowered to `10` during
  testing — **confirm it's back to `5000` before the next real transfer run**).
- `Filter array` dropping blank-`Order` rows.
- Apply to each, with identity Composes: `RawOrder`, `IsSA`, `OrderNumberText`,
  `UnitFraction`.
- `Get Orders` (was called `GetOrderItem` earlier in this doc's walkthrough — the actual
  built name is `Get Orders`) filtered on `Order_x0020_Number1 eq '<OrderNumberText>'`
  — **note the real internal field name has a trailing `1`** (`Order_x0020_Number1`),
  confirmed live, not `Order_x0020_Number`. `CheckOrderMatch` condition (`length(...) =
  1`) with an `UnmatchedOrder` flag Compose in the "no match" branch.
  `ResolvedOrderId` Compose pulls the matched `Order` item's `ID`.
- `Get Order Items` (was called `GetExistingOrderItem` earlier in this doc — built name
  is `Get Order Items`) filtered on `Title eq '<RawOrder>'`, feeding a **Switch** on
  `length(...)` with cases `0` (→ `CreateOrderItem`), `1` (→ `UpdateOrderItem`), default
  (→ `DuplicateOrderItem` flag Compose).
- `CreateOrderItem`/`UpdateOrderItem` both built, kept in sync field-for-field, with:
  identity (`Title`, `SA Job`, `Unit #`, `Qty`, `Order NumberId`); all 8 Test/QA fields;
  all production-tracking fields **including the corrected Yes/No mapping** for `Tank`/
  `ISO Stack`/`ISO Coil`/`Lead Assembly` (live schema is Yes/No, not Text as originally
  documented — see the correction note in the Production tracking table above); `Frame`
  as a plain-text copy (`item()?['Frame']`) — the live field was briefly changed to
  Yes/No, found not to fit its real 3-value data (`Plaspak`/`Reçu`/`0`), and changed
  back to Choice, at which point both actions had to be **fully rebuilt** (an accidental
  List-Name-dropdown reselection wiped every existing field mapping — see the
  `feedback_dont_rebuild_existing_artifacts` lesson logged in memory, a different
  incident than this one but same "don't lose completed work" theme) — confirmed
  rebuilt and working afterward; `MappedLocation`/`ItemStatus` Composes wired into
  `Location`/`Item Status`.
- Confirmed via real test runs: pagination fix (256→full table), identity parsing
  (including an SA row), the upsert round-trip (same test rows Create then Update,
  no duplicates), and the Yes/No fix for `Tank`/`ISO`/etc.

**Not yet built:**
- The 3 remaining "other dates" (`Tank Delivery Date`, `Original Tanking Date`, `Manual
  Estimated Delivery Date`) + `Tanking date change justification` — not yet added.
- The reconciliation pass (missing-row → check Archive source → finalize
  `Cancelled`/`Delivered`) — not started at all.
- `Order` companion columns branch (`Engineering Required`, `LDs`, `Client Date Status`,
  `Sales Notes`, `Order Status`) — not started.
- `Model Revisions` companion columns branch (`Family`, `Duplicate Order`, the
  `PO Item #` → `Models.Model_Code` → `Latest Model Revision` resolution, plus sorting
  rows by `Order Date` ascending for `Duplicate Order`'s last-write-wins semantics) — not
  started.
- The structured test plan (synthetic `AN` row, `indéterrminé` edge case run for real,
  reconciliation-pass test) and the real full-scale initial-transfer run (threshold back
  to `5000`) — not done; only ad hoc spot-checks so far.

**Next concrete step when resuming**: the 3 remaining "other dates" fields + the
justification text field (same section further down this doc, "Other dates" heading) — same
Excel-serial conversion as the production-sequence dates. **Checked directly against raw
`TableOrders` data 2026-08-18 (unzip+parse, not guessed) before assuming the `EC` gotcha
carries over**: it doesn't — `Tank Delivery Date` (79 non-blank), `Original Tanking Date`
(413 non-blank), and `Manual Estimated Delivery Date` (1000/1000 rows non-blank — notably
not sparse like the other two, worth a heads-up that this one might actually be a
computed/native column rather than truly manual, contradicting how it's currently
documented) are all cleanly numeric-or-blank, zero non-numeric values found in any of the
three. Plain `if(equals(trim(...), ''), null, addDays('1899-12-30', int(...)))` is enough —
no composite-status-code guard needed here, unlike the production-sequence dates.

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
5. **Setting a variable to `null` in the designer**: click the Value box → Expression tab →
   type `null()` (a function call, not the bare word `null`) → Add. This is what the 8
   clear-on-N/A actions below use to blank out the date variables.

## N/A status handling + advance-to-Pending logic

**Built and tested 2026-08-14.** Both pieces below, built together in one pass (the N/A
extension is just part of the advance-to-Pending conditions' final form, not a separate
edit — see chat history if picking this apart later).

**Why**: the advance-to-Pending logic assumes every unit goes through all 8 stages with no
skips. Since that's not always true, staff need a manual way to mark a stage as not
applicable to a given unit, without breaking the auto-advance chain or leaving stale dates
behind. **Future idea** (logged in `roadmap.md`, not started): a Model Revisions-level field
listing which stages actually apply to a design, so this could be inferred automatically
instead of relying on staff to catch it — not needed to ship this.

- [x] Schema: added **`N/A`** as a 4th Choice option on all 8 `{Stage} Status` fields.
- [x] Flow logic — both pieces below, built and tested.

**A. The 7 advance-to-Pending conditions** treat `N/A` the same as `Completed` as a trigger
for advancing the next stage: `({Stage} Status Value = Completed OR {Stage} Status Value =
N/A) AND {NextStage} Status Value is empty`. Built with a **nested row group** in the
Condition action (top-level And, with a nested Or group for Completed/N/A).

**B. Clear dates when a stage is set to `N/A`** — 8 conditions, one per stage (including
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

## Advance-to-Pending logic (built together with the N/A handling above)

**Why**: when a stage finishes (`Completed`) or is skipped (`N/A`), the *next* stage should
automatically move from blank ("not relevant yet") to `Pending` ("queued, not started"), so
staff don't have to manually advance every stage themselves. Fires on `Completed` **or**
`N/A`, only when the next stage is currently blank (so it never overwrites a stage a human
has already touched).

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

**Built as**:
1. **7 "Initialize variable" actions** (String), one per next-stage
   (`v{NextStage}StatusValue`), initial value = that stage's current trigger Status value.
2. **7 Condition actions**, per the table, using the nested-row-group technique (Or inside,
   And outside).
3. **7 field mappings on the shared `Update item`**: `{NextStage} Status` =
   `if(equals(variables('v{NextStage}StatusValue'), ''), null, variables('v{NextStage}StatusValue'))`
   — same null-safe wrapper as the dates, since blank is a valid real state here too.

Confirmed no loop: once `{NextStage} Status` flips from blank to `Pending`, the
self-triggered re-run sees it's no longer blank and the guard stops it from firing again.

## Full-cycle test — passed 2026-08-14

Tested per stage, repeated for all 8 (Coiling through Delivery), in this order:
1. Set `{Stage} Status` to `In Progress` → confirmed `{Stage} Start Date` gets stamped.
2. Set `{Stage} Status` to `Completed` → confirmed `{Stage} End Date` gets stamped **and**
   `{NextStage} Status` advances to `Pending`.
3. Set `{Stage} Status` to `N/A` → confirmed both `{Stage} Start Date` and `{Stage} End
   Date` get cleared back to blank.

All 8 stages passed. **Step 2c (including N/A handling and advance-to-Pending) is fully
built and tested.** Not yet tried: the bulk-edit case (changing two non-adjacent stages'
Status in a single save) — logic analysis says it should behave correctly (advances exactly
one stage past whichever was last explicitly touched, no double-cascade), but this hasn't
been run for real. Worth a quick test if this flow gets revisited, not blocking anything now.

## Step 3 — Excel → SharePoint transfer flow (re-runnable upsert)

**Spec drafted 2026-08-17.** Per `order-items-build-plan.md` step 3: a manually-triggered,
re-runnable Power Automate flow, Excel `TableOrders` → SharePoint (`Order Items` + the
companion columns on `Order`/`Model Revisions`), upserting on the unit identifier so it's
safe to run twice (once now to seed real data, once again right before cutover).

**Scope, per the build plan**: only the ~40 manually-typed columns that are moving, plus the
`Order`/`Model Revisions` companion columns. **Explicitly out of scope for this flow**: the
`Client`/`Model`/`Model Revision` Lookups added to `Order Items` in step 8 — those aren't
data that "moved from Excel" (TableOrders never had them), they're a new cross-reference
resolved from the parent Order, and the SA-row disambiguation logic they need is a separate,
still-open piece of work (`roadmap.md`'s Workstream 4 "still to do" item). Don't build that
resolution here — it's the `Work Order` fan-out's job later, or a dedicated follow-up.

### Trigger and source

- **Trigger**: Manually trigger a flow (button trigger) — matches the plan's "triggered
  manually/on-demand," not an automatic trigger.
- **Source action**: Excel Online (Business) *"List rows present in a table"* — Table:
  `TableOrders`. **File location not yet confirmed** — pick the actual file from wherever
  FRM10-12.xlsx lives in OneDrive/SharePoint in the connector's file picker when building
  this (the repo only holds a staging copy, not the live file's cloud path) — don't guess a
  site/library URL.
- **Row filter — do this first, before any mapping runs**: `TableOrders`' formatted range
  extends well past the last real row (confirmed live: 2,616 rows scanned, 1,616 with a
  blank `Order` column). Add a **Filter array** (or a Condition inside Apply to each) that
  skips any row where `Order` (the unit ID, e.g. `21408-1/1`) is empty — otherwise the flow
  tries to upsert ~1,600 blank/junk rows.

### Parsing the unit ID (`Order` column)

`Order` values look like `21408-1/1` or, for an SA auxiliary row, `21408-1/1 SA` (confirmed
live 2026-08-17: 43 rows currently carry the ` SA` suffix directly in this column — the
suffix is already native to the Excel data, not something derived elsewhere). Everything
below is one row's worth of parsing, done once per row via string functions (no regex action
needed in Power Automate — `split()`/`indexOf()`/`substring()`/`endsWith()` cover this):

| Target field | Derivation |
|---|---|
| `Unit ID` (Title) | The raw `Order` value, as-is — already in final form, including the ` SA` suffix where present. |
| `SA Job` | `endsWith(trim(item()?['Order']), ' SA')` → Yes/No. |
| Order Number (for the Lookup, see below) | Text before the first `-`, e.g. `21408` from `21408-1/1` or `21408-1/1 SA`. |
| `Unit #` | The numerator between `-` and `/` — strip ` SA` first if present, then parse, e.g. `1` from `21408-1/1`. |
| `Qty` | The denominator after `/` — same strip-then-parse, e.g. `1` from `21408-1/1`. |

### Resolving the `Order Number` Lookup

`Order Number` is a Lookup to the `Order` list, so it needs that list's item ID, not just the
text. Same **Get-item pattern** already used elsewhere in this system (`lookup-textfield-reference.md`):
**Get items** from `Order`, filter on `Order Number eq '<parsed Order Number>'`, take the
first result's `ID`, and use that for `Order NumberId` on the `Order Items` create/update
call (SharePoint Lookup fields are set via the `{Field}Id` suffix in Power Automate, not the
plain field name). If no match is found, log/skip the row rather than silently creating an
orphaned `Order Items` row — this shouldn't happen for any row with a real `Order` value
(the `Order` list should already exist for every live order), so treat a miss as a data
problem worth surfacing, not a normal case to swallow.

### Upsert logic

**Get items** from `Order Items`, filter `Title eq '<Unit ID>'`. If the count of results is 0
→ **Create item**. If 1 → **Update item** using that item's `ID`. (If ever >1, that's a
duplicate that shouldn't exist — surface it, don't just pick one.) Same shape as the
`Order`/`Model Revisions` companion writes below, each keyed on their own natural match
instead of `Title`.

### Field mapping — `Order Items`

**Identity fields**: see the parsing table above (`Unit ID`, `SA Job`, `Unit #`, `Qty`,
`Order Number`/`Order NumberId`). `Order_Number_TextField` — leave blank on create/update;
the existing `Order Items - created or updated trigger` flow (step 2b) fills it in
automatically on the next trigger, no need to duplicate that logic here.

**Test/QA results** — verified live 2026-08-17 against ~2,600 rows: every one of these except
`SFRA` uses `'x'` for pass/done and blank otherwise, but `SFRA` uses `'Y'` instead (6 live
rows) — **map on "non-blank" for all of them, not on the literal value `'x'`**, so this
inconsistency doesn't silently drop `SFRA`'s real data:

| Excel column | Order Items field | Mapping |
|---|---|---|
| Witness/Other | Witness/Other | Direct copy (Text → Text). |
| Temperature Rise | Temperature Rise | `if(empty(trim(...)), 'No', 'Yes')` |
| Impulse | Impulse | Same non-blank→Yes/No pattern. |
| DB | DB | Same pattern. |
| Partial D | Partial D | Same pattern. |
| Oil Analysis | Oil Analysis | Same pattern. |
| SFRA | SFRA | Same pattern — confirmed source uses `'Y'` not `'x'`, non-blank check still works. |
| CSA | CSA | Same pattern (0 live values currently, still map it). |
| Protector Status | Protector Status | Direct copy — confirmed 100% blank in current live data, so there's nothing to validate against the Choice list yet; if a future non-blank value doesn't match one of `Entrepôt SN`/`Reçu`/`à vérifier` exactly, the write will fail loudly rather than silently mismatching, which is fine here. |
| Protector & Switchgear PO | Protector & Switchgear PO | Direct copy (Text → Text; 100% blank in live data today, same as above). |

**Production tracking**:

| Excel column | Order Items field | Mapping |
|---|---|---|
| Location | Location | **Needs the code→name lookup below** — Excel stores the short code (`TA`, `XT`, `FO`, ...), the list wants the full name. |
| — | Item Status | **Not a direct copy — derived.** See "Item Status derivation" below. |
| Status | Status | Direct copy (Text → Text, composite value like `TE-Jui-16` stays as one string). |
| Core Status | Core Status | Direct copy — confirmed live 2026-08-17: Excel already stores the full display value (`Reçu`, `Entrepôt SN`), not a separate code, so no lookup table needed here (unlike Location). |
| Production Line | Production Line | Direct copy — same as Core Status, Excel already stores the full value (`Power`, `Power / Ligne 1`, `Zone B`). |
| Time (days) | Time (days) | Direct copy (Number). |
| Tank | Tank | **Correction, confirmed live 2026-08-17**: actually a **Yes/No** field live, not Text — same as `ISO Stack`/`ISO Coil`/`Lead Assembly` below. `not(equals(item()?['Tank'], ''))`. |
| Frame | Frame | Direct copy — confirmed live: Excel already stores the full value (`Plaspak`, `Reçu`, `0`), same as Core Status/Production Line. |
| ISO Stack / ISO Coil / Lead Assembly | (same names) | **Correction, confirmed live 2026-08-17**: these are actually **Yes/No** fields in the live list, not Text as `order-items-manual-build-checklist.md` originally specified (docs vs. live reality mismatch, found while testing this flow — docs updated to match). Same non-blank pattern as the test markers: `not(equals(item()?['ISO Stack'], ''))`, one per field. |
| Winder / Coil Winder | (same names) | Direct copy each (Text → Text — don't coerce to Number, values mix IDs and ranges like `100-104`). |
| Trimestrial Customer | Trimestrial Customer | Direct copy (Text → Text) — per `infrastructure-overview.md`, stays Text pending the business-user clarification on `Pénalité Trimestrielle`; don't build any Yes/No logic against this column. |

**`Location` code→name table** (confirmed live 2026-08-17 from `TableValidationLocationCodes`
on the workbook's `List` sheet — this is the authoritative source, not a guess):

| Code | Full name |
|---|---|
| IS | Isolation |
| BO | Bobinage |
| ST | Stacking |
| AS | Assemblage |
| FO | Four |
| TA | Tanking |
| TE | Test |
| FI | Finition |
| LI | Livraison |
| ENT | Entrepôt |
| XT | Extérieur |
| RE | Réparation |
| AN | *(not a Location value — see below)* |

Build as a **Switch** (or nested `if()`) on the raw code. **`AN` (Annulée) is the one code
that doesn't map to a `Location` Choice value at all** — it was deliberately dropped from the
new Location list (`infrastructure-overview.md`'s cancellation-logic section) in favor of the
new `Item Status = Cancelled`. Also true historically of `GR` (regroup) — already confirmed
elsewhere as untraceable and not present in current data, so it needs no mapping at all, just
don't treat an unrecognized code as an error if it's `GR`.

**Why no live row has `Location = AN` today, and why that's structural, not incidental —
raised by the user 2026-08-17**: `TableOrders.pq` (the existing Excel Power Query) already
merges every row against a separate `ArchivedOrders` source (a linked "Archived Orders"
workbook, `TableArchiveFRM10_12` table, resolved via the SharePoint `Index` list — see
`ImportFromIndex.pq`) and **filters out of `TableOrders` entirely** any row where that
Archive match shows `Location = AN` or (`Location = LI` and `Delivery Date` populated) — see
`#"Filtered Out Archived Orders"` in `TableOrders.pq`. So the moment staff mark a unit
cancelled or delivered *and the workbook refreshes*, that row **disappears from
`TableOrders`** — it never sits there showing `AN`/`LI` for this flow to read directly. Its
final state only survives in the separate Archive workbook from that point on. **This means a
straight upsert isn't enough**: a unit could go from `Active` to `Cancelled`/`Delivered` and
vanish from `TableOrders` entirely in the gap between two runs of this flow, and a create/
update-only flow would never see that transition — it would just leave the `Order Items` row
stuck at whatever `Active` state it last synced.

### Reconciliation pass — required, not optional, per the above

After the main per-row upsert loop, add a second pass that catches rows that **disappeared**
from `TableOrders` since the last run:

1. **Get items** from `Order Items` where `Item Status eq 'Active'` (only active rows can go
   missing meaningfully — already-`Delivered`/`Cancelled` rows are done, no need to re-check
   them every run).
2. For each, check whether its `Unit ID` appears in **this run's** `TableOrders` pull (the
   filtered, non-blank `Order` values collected earlier in the flow — e.g. via
   `contains(...)` against a compose'd array of this run's Unit IDs, not a second live query).
3. **If found** → already handled by the main upsert loop, skip.
4. **If missing** → it was archived since the last run. **Get rows** from the same Archive
   source `TableOrders.pq` already reads (`TableArchiveFRM10_12`, via an Excel Online action
   against the "Archive active" workbook — resolve its file location the same way
   `ImportFromIndex.pq` does, by checking the `Index` SharePoint list's `Archive active` row
   for the path, not a hardcoded file), filtered on `Order eq '<Unit ID>'`:
   - Archive row's `Location = AN` → `Item Status = Cancelled`, `Location` left blank (same
     rule as a direct `AN` sighting above).
   - Archive row's `Location = LI` **and** `Delivery Date` populated → `Item Status =
     Delivered`, `Location = Livraison`.
   - **No match found in the Archive either** → don't guess; flag this row for the user to
     check by hand (it's now missing from both live and archived Excel data, which shouldn't
     happen and is worth a human look rather than a silent assumption).

**This is the same logic a direct `AN`/`LI`+`Delivery Date` sighting in `TableOrders` itself
would trigger** (see the `Item Status` derivation below) — the reconciliation pass just
covers the case where that sighting already happened and got filtered out of Excel *before*
this flow ever ran, rather than being visible in the current pull.

### `Item Status` derivation (not a direct copy from any one column)

Per `infrastructure-overview.md`'s completion/cancellation logic, for rows actually present in
this run's `TableOrders` pull:
- Raw `Location = AN` → `Item Status = Cancelled` (see above). **Expected to be rare-to-never
  seen directly** per the structural reason above — most cancellations will instead surface
  through the reconciliation pass once the row's already been archived out of `TableOrders`.
- Else if `Location = Livraison` (post-mapping) **and** `Delivery Date` is populated →
  `Item Status = Delivered`. Same rarity caveat as above.
- Else → `Item Status = Active` (the default for every other live row).
- `Regrouped`/`Regrouped Into` — **not handled by this flow at all**. No live row is
  currently regrouped (the old `GR` code is untraceable/unused today), and regrouping is a
  manual, two-step action per the schema (create the new item(s) first, then point the old
  one at them) — not something a bulk backfill should ever infer.

### Production-sequence dates (8 stages)

`TableOrders` only ever had **one** date per stage (`Coiling Date`, `Stacking Date`, ...
`Delivery Date`) — there's no historical "start date" in Excel, only the "finished" date the
new schema calls `{Stage} End Date`. The new schema's `{Stage} Start Date` only starts
getting populated going forward, by the already-built step 2c auto-stamp flow, once a row's
`Status` transitions to `In Progress` *after* this backfill.

**Decided 2026-08-17 — don't guess `In Progress` from `Location` at all.** `Location`'s 12
values don't map 1:1 onto the 8 production stages (`Isolation`, `Entrepôt`, `Extérieur`,
`Réparation` don't correspond to any of the 8 at all), so this flow only ever writes
`Completed` (from an old per-stage date that's actually present) or leaves a stage fully
blank — never an inferred `In Progress`. Staff correct the actual current stage by hand,
once, right after cutover — safer than a guess propagating a wrong "in progress" stage into
live data.

- If the old `{Stage} Date` column has a value → `{Stage} End Date` = that value, `{Stage}
  Status` = `Completed`, `{Stage} Start Date` = **leave blank** (genuinely unknown history,
  don't fabricate one — e.g. by copying the previous stage's end date, which would
  misrepresent idle time as work time, the exact trap step 2c's own design notes already
  warn about).
- Every stage with no old date → leave `Status`/dates fully blank (not `Pending`, not
  `In Progress`) — consistent with step 2c's own convention that blank means "not relevant
  yet," only becoming `Pending` once the stage immediately before it actually completes for
  real, and only becoming `In Progress` when staff (or step 2c) actually sets it after cutover.

**Confirmed 2026-08-17 — always overwrite on re-run, deliberately, not preserve-on-blank.**
`UpdateOrderItem` uses the exact same expressions as `CreateOrderItem` for every date/status
field below, with no "don't clobber what's already live" protection. User's explicit call:
during this build/testing phase, re-running the flow is the intended way to **reset a test
row's `Order Items` data back to whatever `TableOrders` currently says**, discarding any
manual poking done directly in SharePoint in between (e.g. testing step 2c's auto-stamp on a
seeded row). This is safe specifically because `TableOrders`/the workbook gets **locked for
edits once SharePoint goes fully live** — after that point nobody edits Excel anymore, so
there's no live-progress-in-SharePoint scenario left to protect against; the always-overwrite
behavior only matters during this pre-cutover window, where it's a feature (a reset button),
not a risk.

**Note for later, not used by this flow**: the composite `Status` column's prefix code
`EC` = *"En cours"* ("in progress") **is** the real in-progress marker in the old system —
confirmed by the user 2026-08-17 (see `TableValidationStatusCode` in the "Status field"
section above: `Attente`/`AT`, `En cours`/`EC`, `Réparation`/`RE`, `Manque Pièces`/`BO`,
`Terminé`/`TE`, `Bobine 1-3`/`B1`-`B3`). It doesn't solve the stage-guessing problem above
(`EC` says *something* is in progress, not *which* of the 8 stages) — `Status` stays a
single opaque Text copy per the schema, not decomposed — but it's worth keeping in mind if
this ever gets revisited: a per-unit "is anything in progress right now" check should key off
`Status` starting with `EC`, not off `Location`.

### Other dates — need the serial-number conversion below, not a plain copy

`Tank Delivery Date`, `Original Tanking Date`, `Manual Estimated Delivery Date` need the same
serial-number handling as the production-sequence dates above (see "Date fields" hard-won
lesson below) — only `Tanking date change justification` (Text, not a date) is a true direct
copy.

### Hard-won lesson, confirmed 2026-08-17 from a real test-run JSON — read before mapping any date

**Every date-like value comes back from "List rows present in a table" as a plain string
holding the raw Excel serial number** (e.g. `"Order Date": "45398"`, `"Coiling Date":
"46126"`) — not an ISO date string. Confirmed directly from a saved test-run output
(`workflow-data/Excel Table list items raw output.json`), so this isn't a guess: **every**
date field mapped anywhere in this flow (all 16 production-sequence Start/End dates, `Tank
Delivery Date`, `Original Tanking Date`, `Manual Estimated Delivery Date`) needs this
conversion, not a direct copy:

```
if(equals(<rawValue>, ''), null, addDays('1899-12-30', int(<rawValue>)))
```

Excel's date epoch is December 30, 1899 (the classic Excel/Lotus leap-year quirk baked into
the serial system) — `addDays` from that anchor reproduces the real date. The `if(equals(...,
''), null, ...)` wrapper is the same null-safety pattern step 2c's own build notes already
established (an empty string fed to `int()` errors, and `Update item` rejects `""` for Date
fields) — reuse it here rather than rediscovering it.

**Field-name encoding, also confirmed from the same test-run JSON**: any source column whose
display name contains `#` or `.` comes back from the connector with that character XML-encoded
in its JSON key — e.g. `JS #` → `JS _x0023_`, `Ing. Due Date` → `Ing_x002e_ Due Date`, `PO
Item #` → `PO Item _x0023_`. This matters for the `Model Revisions` companion step below,
which reads `PO Item #` as a join key — **always insert that field via the dynamic-content
picker, never hand-type `item()?['PO Item #']`**, since the picker resolves the real
underlying key automatically and typing the plain display name will silently return nothing
instead of erroring.

### Field mapping — `Order` companion columns

Matched by **Get items** on `Order`, filter `Order Number eq '<parsed Order Number>'` (same
lookup as above — reuse the result rather than querying twice per row if both are needed),
then **Update item** (these columns are being added to *existing* Order rows, never created
fresh here).

| Excel column | Order field | Mapping |
|---|---|---|
| Engineering Required | Engineering Required | Y/N → Yes/No. **Data-quality exception found live 2026-08-17**: one row's raw value is `indéterrminé` (a typo'd French "undetermined"), neither `Y` nor `N` — don't let this crash the flow. Map anything that isn't exactly `Y` or `N` to blank/leave-unset and let the condition fall through, rather than defaulting it to `No` (which would assert something false). Worth flagging to the user directly once found in a real test run, not silently absorbed. |
| LDs | LDs | Y/N → Yes/No, clean binary in the live data (167 `Y`, 38 `N`, rest blank) — no exceptions found. |
| Client Date Status | Client Date Status | **Needs normalization, not a direct copy** — live data is inconsistent: `CONFIRMED`/`CONFIRMED ` (trailing space)/`Confirmed`/`CONFRIMED` (typo) all mean `Confirmed`; `PENDING `/`Pending` mean `Pending`. Build as `trim(toUpper(...))` compared against `CONFIRMED`/`CONFRIMED` → `Confirmed`, `PENDING` → `Pending`, blank → leave blank. **No live row currently maps to `Not Confirmed`** — that Choice value exists in the schema but has no historical Excel equivalent found; don't force blank rows into it. |
| Sales Notes | Sales Notes | Direct copy (Multi-line text) — confirmed 100% blank in current live data, still map the column for whenever it does get used. |
| — | Order Status | **Not from Excel — set to `Active` for every row this flow touches.** There's no raw "is this order cancelled" column on `TableOrders` (cancellation was smuggled into `Location = AN` at the unit level, not tracked order-wide) — every currently-live order is implicitly active, so this is a safe default, not a real mapping. |

### Field mapping — `Model Revisions` companion columns

**Matching key confirmed 2026-08-17, from `ColumnMap.pq`/`TableOrders.pq` directly (not
guessed)**: there's no single shared field between `TableOrders` and `Model Revisions` — the
real chain is two hops, exactly how `TableOrders.pq` itself already resolves a Model Revision
for each order (`#"Merged Model Revisions"` step):

1. `TableOrders`' `PO Item #` column (already present, already SharePoint-backed as the
   `Orders`/`Models` merge key — confirmed reliably populated for every live order) matches
   `Models`' `Model_Code` field. **Get items** from `Models`, filter `Model_Code eq '<PO Item
   #>'`.
2. That `Models` item's **`Latest Model Revision`** field is itself a Lookup pointing directly
   at the target `Model Revisions` row — its `Latest Model RevisionId` (the `{Field}Id` form)
   *is* the `Model Revisions` item's SharePoint ID. No second Get-items call needed — skip
   straight to updating that ID.

**⚠ Raw-data conflict found 2026-08-18, resolution deferred — read before touching either
field.** Pulling the actual raw `TableOrders` data for `Family`/`Duplicate Order` (not just
trusting the 2026-08-12 decision) found real contamination: `Duplicate Order` overwhelmingly
equals that row's own `PO Item #` (a self-reference, not an Order Number — live Order
Numbers are 5-digit, these values are model-code-shaped), with a handful of rows pointing at
a genuinely *different* model code instead. `Family` is only ~72% clean `A`/`B1`/`B2`/`C`
Choice values — the rest are stray plain numbers (`91`, `99`, `133`, `167`, `178`, `342`,
`1234`, `46264`/`46446`, `107`/`108`, `0`) that also show up contaminating the *old* `Duplicate`
Y/N column on the same rows, suggesting a shared legacy data-quality issue on older rows, not
three independent problems. **User's call after finding the real explanation** (not written
up here — ask the user directly if this needs revisiting): **for now, just pull the raw
Excel values across as-is, don't build any validation/resolution logic against the
2026-08-12 "Lookup → Order" assumption.** Flagged as a standing item to review with the
engineering team later, once real usage/domain input is available — same "provisional
placement, revisit later" treatment as `Trimestrial Customer` elsewhere in this project.

Once resolved:

| Excel column | Model Revisions field | Mapping |
|---|---|---|
| Family | Family | Direct copy, whatever raw value is in Excel (no validation against the `A`/`B1`/`B2`/`C` Choice list — some rows won't match, that's expected and fine for now) — matched to the resolved `Model Revisions` row. |
| Duplicate Order | `Duplicate_Order_TextField` | Direct copy of the raw Excel value as plain text — **not** the actual `Duplicate Order` Lookup field itself, since the raw values don't resolve to real `Order` items (see the conflict above). Leave the Lookup field unmapped/untouched until the real semantics are confirmed. |

**Multiple `TableOrders` rows can point at the same `Model Revisions` row** (every order built
against that model/revision) — last-write-wins as the flow processes rows, same reasoning as
before (whichever value should "win" once the real meaning is confirmed, it should be the
most recent order's, not an arbitrary one). Row *processing order* therefore still matters —
if `TableOrders` rows aren't already in a meaningful order, sort by `Order Date` ascending
before this step.

**`Duplicate` (the old Y/N field) is excluded from this flow entirely** — confirmed elsewhere
(`infrastructure-overview.md`) as superseded by the `EngineeringChangeOrders`/`ModelChanges`
tracker, not migrated as-is.

### Testing plan, once built

1. Run once against a **small manual test slice first** if possible (a saved copy of
   `TableOrders` with a handful of rows), not the full ~1,000 live orders on the first run —
   this flow writes to four different lists across three logic branches, worth confirming the
   mapping end-to-end on a few rows before trusting it at scale.
2. Specifically verify: an SA row (`21408-1/1 SA`) creates correctly with `SA Job = Yes` and
   `Unit #`/`Qty` matching its parent; a row with `Location = AN` (manually add one to the
   test slice, since none exist live) produces `Item Status = Cancelled` and blank `Location`;
   the `indéterrminé` `Engineering Required` row (or a synthetic equivalent) doesn't crash the
   flow; re-running the same test slice a second time updates the same rows rather than
   duplicating them (the actual upsert requirement).
3. **Specifically test the reconciliation pass**: run once with a test row present and
   `Active`, then remove that row from the test `TableOrders` slice entirely (simulating it
   getting archived) and add a matching row to a test Archive slice with `Location = AN` (and
   separately, on another test row, `Location = LI` + a `Delivery Date`) — confirm the second
   run correctly flips those `Order Items` rows to `Cancelled`/`Delivered` without them ever
   having shown that value directly in the main `TableOrders` pull.
4. Only after that, run against the full live `TableOrders` data — this is the "initial
   transfer" run from `order-items-build-plan.md` step 3, done to get real data into
   SharePoint to develop the rest of the system against. A second, final run happens again
   right before cutover.

### How this was verified (2026-08-17)

Every raw-value claim above (Location codes, which fields already store full text vs. codes,
the `SFRA`/`indéterrminé`/`Client Date Status` data-quality exceptions, the SA-suffix
behavior, the absence of live `AN`/`GR` rows) came from unzipping the actual staging copy of
`FRM10-12.xlsx` (`workbook/FRM10-12.xlsx`) and reading `TableOrders`' real cell data plus the
`List` sheet's validation tables directly — the same audit method `infrastructure-overview.md`
used originally, re-run fresh rather than trusted from memory. The archive-reconciliation
mechanism and the `Model Revisions` matching key came from reading the actual
`TableOrders.pq`/`ArchivedOrders.pq`/`ColumnMap.pq`/`ImportFromIndex.pq` M code directly, not
from any doc's prose description of them. Re-verify against the live file/M code before
actually building if either's been edited significantly since 2026-08-13/17 (the copy's last
sync dates).
