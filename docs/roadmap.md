# Roadmap

**Start here.** This ties together the other docs in this repo into one picture. Read this
first, then follow the links into whichever workstream you're picking up.

## Where things stand right now (2026-08-14, see 2026-08-21 update below) — read this first

**Update, 2026-08-21**: workstream 1 step 3's transfer flow is now functionally built and
tested end to end — Lookup resolution (including main-vs-SA disambiguation, closing
Workstream 4's last "still to do" item), the `Order`/`Model Revisions` companion branches,
and the "other dates" fields are all confirmed live (see
`order-items-power-automate-flows.md`'s Progress section for the authoritative current
state — this section below is kept for history/context, not current status). Only the
reconciliation pass remains, and it's been **deliberately deferred to the pre-final-migration
pass** (user's call, 2026-08-21) since it only matters once real cancel/deliver archival
churn is happening — not needed for ongoing development/testing. **Next up: Workstream 2
(Phase 1 business process automation)**, per the user's explicit sequencing.

**Done and verified working:**
- Workstream 1: full `Order Items` schema built live, all 8 sub-steps including step 8
  (`Client`/`Model`/`Model Revision` Lookups + TextField companions, built 2026-08-14 now
  that the Models SA fusion unblocked it). Every Lookup→TextField sync flow built
  system-wide except `Regrouped Into` (deferred).
- Workstream 4 (Models SA fusion): **fully done, schema through data through Power Query**.
  All 15 live `Models SA` rows + 2 new placeholder rows migrated into `Models`/`Model
  Revisions` with real revision history; `FRM10-12`'s `ColumnMap.pq`/`TableOrders.pq`
  repointed off the retired entity (commit `9aeb9c7`); a related stale-model-data bug in
  `TableOrders.pq` found and fixed (commit `516134c`); a data-entry bug (crossed `Latest
  Model Revision` links from the migration paste) found and fixed by the user directly in
  SharePoint, confirmed via refresh. Full detail: `models-sa-fusion-plan.md`.
- Workstream 1 step 2c: production-sequence auto-stamp, **built and tested 2026-08-14** —
  16 Start/End Date stamps, plus (added mid-build) an `N/A` status option and full
  advance-to-Pending chain across all 8 stages. Full-cycle test (In Progress → Completed →
  N/A, repeated for every stage) passed. Full detail: `order-items-power-automate-flows.md`.

**Immediate next steps, not yet started — pick any, none blocked:**
1. Build workstream 1 step 3's transfer flow (Excel → SharePoint, re-runnable, upsert) —
   **build-ready spec drafted 2026-08-17** in `order-items-power-automate-flows.md`'s new
   "Step 3" section (field-by-field mapping, verified against the live workbook's real raw
   data, not guessed). Two design points surfaced and resolved with the user during drafting:
   (a) a **reconciliation pass is required, not optional** — `TableOrders.pq` already filters
   cancelled/delivered rows out of `TableOrders` once they're archived, so this flow can't
   just react to what it sees in the current pull; it has to check the separate Archive
   source for any `Order Items` row that's gone missing since the last run. (b) the backfill
   deliberately does **not** guess which of the 8 production stages is `In Progress` from
   `Location` (the 12 Location values don't map 1:1 onto the 8 stages) — only writes
   `Completed` from an old per-stage date or leaves a stage blank; staff correct the current
   stage by hand once, right after cutover. (c) the `Model Revisions` companion columns'
   matching key resolved directly from `ColumnMap.pq`/`TableOrders.pq` (no new field needed):
   `TableOrders`' `PO Item #` → `Models.Model_Code` → that `Models` row's `Latest Model
   Revision` Lookup ID *is* the target `Model Revisions` row. **No remaining open items —
   ready to build.**
2. Workstream 4 cleanup: retire the old `Models SA` list once nothing points at it; build
   the order-item-generation logic that resolves main-vs-SA `Models` row for a new unit.
3. Workstream 2 (Phase 1 business process automation) — not started, fully spec'd in
   `phase1-plan.md`, one open question (`Workflow Tasks` as one shared list vs. per-department).
4. Workstream 3 (Archiving) — not started, fully spec'd in `archiving-plan.md`.

**Standing things to remember when resuming, regardless of which item above gets picked:**
- Re-read this repo's actual docs fresh before acting — don't trust a memory summary's
  narrative for current state (memory has drifted stale on this project before).
- FRM10-12: never refresh via generic "Refresh All"/COM `RefreshAll` — use the Office
  Script button on the `Orders` sheet (wipes native formula columns otherwise). Check for
  an existing automation script (e.g. `scripts/Sync-PowerQuery.ps1`) before giving manual
  "paste into Advanced Editor" instructions.
- `sharepoint-lists/*.csv` exports use `{List Name} {YYYY-MM-DD} {HHMM}.csv` naming,
  superseded ones move to `Archive/`.

## Four workstreams, mostly independent, all ready to build now

### 1. Order Items migration — **priority** (get staff off editing Excel)
→ `docs/order-items-build-plan.md`

Moves the 42 manually-typed `TableOrders` columns (Location, Status, Tank, dates, test
results, ...) into a real `Order Items` SharePoint list, plus a few companion columns onto
`Order`/`Models`. User's explicit priority call, 2026-08-12: do the **full** migration now,
not a minimal slice — the goal is getting staff off manually editing Excel as soon as
possible, and a half-built list doesn't achieve that for in-flight orders.

Build sequence: schema → companion columns → TextField/date-stamp automation → re-runnable
Excel→SharePoint transfer flow → extend `ColumnMap.pq`/`TableOrders.pq` so Excel becomes a
read-only mirror → staff cutover.

**PnP PowerShell scripting is blocked** (`ermcopower` tenant hasn't consented the PnP
Management Shell app, and the same wall applies to any PowerShell-based automation, not just
PnP) — schema was built manually via `docs/order-items-manual-build-checklist.md` instead
(**done, 2026-08-13**), same as how `Order`/`Models`/`Model Revisions` were originally
built. Power Automate is NOT affected by that block (first-party connector) — the
remaining flows (TextField sync, production-date auto-stamp, the transfer flow) are being
built via `docs/order-items-power-automate-flows.md`.

**Pending, don't block starting**: `Trimestrial Customer`'s exact per-unit grain. (The
`Tank`/`ISO Stack`/`ISO Coil`/`Lead Assembly` `R` = "Received" question is now confirmed,
no longer open.)

### 2. Business process workflow automation ("Phase 1")
→ `docs/phase1-plan.md`

Automates the front of the order process — `Customer PO → Order Entry → Electrical/
Mechanical Preliminary Review → Work Order → Planning Schedule → Confirm Planned Dates
with Client` — with a `Workflow Tasks` list and Power Automate flows that notify (email +
Teams) whoever's turn it is to act next. Fixes the other big current pain: no visibility
into whose turn it is on an order.

The underlying business-process diagram (`workflow-data/Pioneer Transformers Model.vsdx`,
described in `docs/infrastructure-overview.md`) already reflects the final logic: parallel
Electrical/Mechanical duplicate-check reviews, an AND-gate unlocking early Purchasing start
only when both say Yes, and Engineering's start gated on client-date confirmation.

**Not yet confirmed**: one shared `Workflow Tasks` list across departments (recommended,
with department-filtered views) vs. the originally-floated separate list per department;
the list's exact name.

**Tooling choice researched and confirmed 2026-08-12** — see `docs/phase1-tooling-research.md`:
staying in SharePoint + Power Automate is still the right call (vs. Planner Premium, which
turned out to be Dataverse-backed and would break Lookup compatibility with `Order`/`Order
Items`; vs. Power Apps + Dataverse, which is over-engineering at this project's ~1000
orders/year scale). Two changes folded back into `phase1-plan.md` from that research: use
Adaptive Cards for notifications from the start, and give `Workflow Tasks` its own archiving
flow rather than deferring it.

**Dependency on workstream 1**: Phase 1's `Work Order`/`Planning Schedule` steps are
per-unit, so they need `Order Items` rows to exist. Once workstream 1's list/schema exists,
this is satisfied — Phase 1's flow just creates new `Order Items` rows for new orders going
forward (see the fan-out logic in `phase1-plan.md`), on top of whatever workstream 1's
one-time backfill already populated for existing orders. No conflict between the two — just
don't build a redundant "minimal" version of `Order Items` for Phase 1, use the real one.

### 3. Archiving
→ `docs/archiving-plan.md`

Without this, `Order`/`Order Items` grow forever and SharePoint's practical
performance/usability degrades — user's concern, 2026-08-12: the lists getting
"exhaustive." Also serves the earlier-noted Power BI historical-analysis need. Recommended
mechanism: a **scheduled** Power Automate flow (not event-triggered) that copies
delivered/cancelled rows into separate `Archived Orders`/`Archived Order Items` lists,
**verifies the copy matches before deleting** the live row — mirroring an archive-refresh
pattern Pioneer already trusts today — and **never writes to Excel**. Trigger logic reuses
the already-designed `Item Status`/`Order Status` fields (same criteria the old Excel
`ArchivedOrders` mechanism used: `Location = LI` + delivered, or `Location =
AN`/cancelled).

**Sequencing**: doesn't block the other two workstreams starting, and they don't block
this — but build it soon after `Order Items` goes live, before the list actually gets big
enough to matter, not deferred indefinitely.

**Depends on**: `Item Status`/`Order Status` existing (workstream 1) as the trigger
conditions — no new fields needed beyond what's already designed.

### 4. Models SA fusion
→ `docs/models-sa-fusion-plan.md`

**Schema and data migration complete, 2026-08-13** — see `models-sa-fusion-plan.md`: fused
`Models SA` into `Models`/`Model Revisions` so SA (auxiliary) model designs get real
revision history instead of living in a separate, never-versioned, structurally-duplicated
list. Surfaced while building workstream 1's Lookup→TextField sync flows — `Models` and
`Models SA` were about to need the same `Client`-sync flow built twice for no reason. Also
resolves a real gap: `Order Items`' SA auxiliary row had no lookup field pointing at
`Models SA` at all: `Order` always points at `Models`, and the SA-specific link was
expected to live on the `Order Items` auxiliary row instead, but that field was never
built.

Disambiguation confirmed 1:1 by the user (who built the original `Models SA` logic):
`Models` got a new `SA Model` (Yes/No) field plus a self-referencing `Parent Model` Lookup
(populated only for SA rows, pointing at the specific main model it pairs with). All 15
live `Models SA` rows migrated (plus 2 new placeholder `Models` rows for two codes with no
existing match), each with a new `Model Revisions` entry and `Latest Model Revision` link.

**Unblocked, then built, 2026-08-14**: `order-items-manual-build-checklist.md`'s step 8 —
new direct `Client`/`Model`/`Model Revision` Lookups on `Order Items` itself (decided
2026-08-13, to work around SharePoint's inability to cascade through a Lookup in
views/filters/reports — same pattern already used on `Model Revisions`' own `Client`
Lookup). Schema plus TextField sync flow both done — see `order-items-manual-build-checklist.md`
and `lookup-textfield-reference.md`.

`ColumnMap.pq`/`TableOrders.pq` (FRM10-12) repointed off the retired `Models SA` entity,
2026-08-13 (commit `9aeb9c7`) — the existing `Models`/`Model Revisions` merge already
covers the fused SA rows.

**Still to do**: retire the `Models SA` list. The order-item-generation main-vs-SA
disambiguation logic is **built & tested, 2026-08-21** — landed in workstream 1's transfer
flow (`order-items-power-automate-flows.md`'s Step 3, "Resolving the Client/Model/Model
Revision Lookups") rather than as a separate piece, since every row that flow
creates/updates needs it. Phase 1's `Work Order` fan-out can reuse the same resolved
`Models` row, no separate logic needed there.

**Creates new logic work**: whatever generates the SA auxiliary `Order Items` row (the
transfer flow now, `phase1-plan.md`'s `Work Order` fan-out later) needs to correctly
resolve *which* `Models` row is the right one for a given unit, main vs. SA — today the
separate `Models`/`Models SA` lists themselves did that disambiguation implicitly; fusing
removes that free signal, so the logic has to do it explicitly instead.

**Supersedes**: the `lookup-textfield-reference.md` to-do to build a `Models SA`
`Client`-sync flow — don't build one, it would be thrown away.

## Reference (not a build plan — background/audit)
→ `docs/infrastructure-overview.md`

The full column-by-column audit behind workstream 1's schema, the current-state
architecture diagram (SharePoint ↔ Power Query ↔ Excel ↔ Power BI/Power Apps), and the
business-process diagram description. Read this for *why* a field ended up where it did;
read the build-plan docs for *what to actually do*.

→ `docs/lookup-textfield-reference.md`

Every Lookup column across the live SharePoint lists (`Order Items`, `Order`, `Model
Revisions`, `Models`, `Models SA`, `ModelChanges`, `EngineeringChangeOrders`), its
companion `_TextField`, and which sync pattern it needs (Simple / Get-item / the one
chained case). Doubles as a reference for diagramming list relationships, not just for
building the sync flows in `order-items-power-automate-flows.md`.

## Explicitly not planned yet (future phases)

- **Phase 2+ of the business process**: `Electrical Design`/`Mechanical Design` execution,
  `Customer Drawings`, the `P.O.` chain, `Production`. Don't scope-creep into these before
  Phase 1 ships and the team's used it for a while.
- The 7 native-formula calculated columns (`Price`, `Estimated Delivery Date`, `Price
  CAD/USD`, `Navigation Order/Model`, `Archived`) — **analysis done, 2026-08-18**, see
  `calculated-columns-plan.md`: none can be a plain SharePoint calculated column;
  `Price`/`Navigation Order`/`Navigation Model` should be dropped, `Estimated Delivery
  Date`/`Price CAD`/`Price USD` need a Power Automate flow (blocked on `ClientLeadTimes`/
  `TableCanadianProvince`/`Table_USD_CAD_Conversion_Rate` getting a SharePoint home first),
  and `Archived` has no live formula at all anymore — needs a drop/keep decision from you,
  not a port. Not yet built/decided-on-Archived, but no longer just "not yet built."
- FRM09's raw-column-letter external-reference fragility — actually already resolved per
  FRM09's own `CLAUDE.md` (2026-08-12), unrelated to this repo's remaining work.
- **`Clients`/`Models`/`Model Revisions` cascade-refresh flow — assessed, deliberately not
  built, logged 2026-08-19.** Idea: when a master record is edited, push a refresh out to
  every downstream `_TextField` companion pointing at it (today's sync flows only go the
  other direction — refreshing a TextField when the *referencing* item is edited, never
  when the *referenced* one changes). Checked before building: **zero confirmed consumers**
  of any `_TextField` column anywhere (not in Power Query — `ColumnMap.pq`/`TableOrders.pq`
  merge against live Lookup/master values directly, never a TextField; not in any
  documented SharePoint view/filter/report; no Power BI files exist yet) — the only stated
  purpose is `lookup-textfield-reference.md`'s own "for search/filtering" line, with no
  evidence anyone's built against it. Also checked `Models`/`Model Revisions` `Created` vs.
  `Modified` timestamps: only 3 of 224 rows show a genuine standalone post-creation edit
  (the rest collapse into two explainable bulk events), suggesting these lists are
  effectively write-once in practice so far; `Clients` couldn't be checked the same way (no
  timestamp columns exported), but no doc mentions a live row being renamed/merged either.
  **One real counterpoint, not zero risk**: the Models SA fusion did catch a crossed
  `Latest Model Revision` link that had already silently propagated wrong spec data to a
  live order before being fixed directly in SharePoint — real evidence mistakes happen and
  propagate, just not (yet) a recurring pattern. **Revisit if**: a real consumer of a
  `_TextField` gets built (a view, a Power BI report, a filter), or client/model
  renames/merges start happening as routine business events rather than one-off migration
  corrections — don't build the three flows (one, the `ModelChanges` chain, genuinely
  complex) speculatively before either happens.
- **Standing future review point**: once `Order Items`/`Workflow Tasks` have real usage
  history, revisit any field placed on a hunch during this initial design pass (starting
  with `Trimestrial Customer`) — don't wait to be reminded, this is a deliberate open loop.
- **`Duplicate Order` — frozen out of the transfer flow entirely, logged 2026-08-18,
  needs a real requirements review**: raw `TableOrders` data doesn't match the 2026-08-12
  decision that it's a Lookup to the *Order* that last built this model — actual values are
  model-code-shaped (mostly a self-reference to the row's own `PO Item #`, a handful
  pointing at a different model code). User found the real explanation but it's not written
  up yet; for now this column isn't migrated at all, not even as a raw text copy. **A
  possibly-related but distinct new field idea surfaced, not scoped**: `Latest Released
  Design`/`Latest Completed Order` on `Model Revisions` — a pointer to the most recent order
  that used this design, complicated by design-completion vs. order-completion timing not
  being the same thing. Needs design before building. `Family` is unaffected by this freeze
  (plain Text→Choice, per the user's own framing) but is only ~72% clean `A`/`B1`/`B2`/`C`
  data — pulled raw as-is, no filtering, same as everything else migrated this way; check
  whether the live Choice column allows fill-in values before the real run.
- **`Order` → `Order Items` cascade-update flow** for the new `Client`/`Model`/`Model
  Revision` Lookups (workstream 1, step 8): if `Order`'s own `Client`/`Model`/`Model
  Revision` ever changes after an `Order Items` row already exists, nothing currently
  propagates that change down to the row's copy. User's call, 2026-08-13: sync risk
  assessed as low (these values are set once at order creation and essentially never change
  after), so this is a nice-to-have, not needed at launch — build only if drift actually
  turns out to happen in practice.
- **Model Revisions-level production-stage skip list, idea logged 2026-08-14**: step 2c's
  auto-stamp/auto-advance flow (`order-items-power-automate-flows.md`) currently assumes
  every `Order Items` row goes through all 8 production stages (Coiling → Delivery) with no
  skips, and relies on staff manually setting a stage's Status to a new `N/A` choice value
  (added 2026-08-14) when a stage genuinely doesn't apply to a given unit — this clears that
  stage's dates and still advances the next stage to `Pending`, same as `Completed` would.
  **Future idea, not started**: instead of relying on manual `N/A` flagging after the fact,
  add a field on `Model Revisions` listing which of the 8 stages actually apply to that
  design, so `Order Items` rows could be pre-populated (or auto-N/A'd) correctly at creation
  time based on the model, rather than staff catching it stage-by-stage during production.
  Worth revisiting once there's real usage data on which models actually skip which stages.
- **`ModelChanges` linking logic needs a real audit, flagged 2026-08-17**: while doing an
  unrelated `Models` duplicate cleanup (see `models-sa-fusion-plan.md`-adjacent session work,
  not yet written up as its own doc), found 9 duplicate `(Model, ECO)` pairs in
  `ModelChanges` — all on one model (`M-TOHY-0002`), each an old empty `Not Assigned` stub
  alongside a real, actually-worked `Completed` row for the same ECO. User's read: this
  double-linking shouldn't be possible at all, so there's likely a logic flaw somewhere in
  how the Engineering modification-tracking app creates `ModelChanges` rows (duplicate
  trigger firings? no uniqueness check on `Model`+`ECO` before creating a new link?). **Not
  in scope now** — revisit once Phase 2 (the Engineering-side business process, gated on
  Phase 1 shipping through client approbation — see "Phase 2+" above) is actually being
  built, since that's when the real linking flow(s) get designed/rebuilt properly. When
  picked up: (1) find and fix whatever's letting duplicate `(Model, ECO)` pairs get created
  in the first place, (2) decide whether a uniqueness constraint or dedup check belongs in
  the flow itself vs. relying on manual cleanup like today's.
