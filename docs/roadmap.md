# Roadmap

**Start here.** This ties together the other docs in this repo into one picture. Read this
first, then follow the links into whichever workstream you're picking up.

> ## ⚠️ STATE AS OF 2026-09-04 — the block below is a PLAN, not a status report
> **The 2026-09-01 cutover did not complete, and this is a PARALLEL RUN.** Read
> `build-nights/BUILD-NIGHT-2026-09-03.md` (KEY FACTS) for verified live state; it supersedes
> this header.
>
> Three claims in the block below are **false today**:
> - **"the viewer deployed in place"** — **it was not.** Step **D5** was cut; the viewer exists in
>   the repo only, and the `Index` row still resolves to the **live** FRM10-12. Do not "restore" a
>   deployment on the strength of this doc.
> - **"Presentation and hard cutover at 09:00 on 2026-09-01"** — the presentation happened; the
>   **hard cutover did not.** Staff are still filling in FRM10-12.
> - **"stage stamping out of the trigger flow"** — the trigger flow is currently **`Off`**, with
>   instances from 2026-09-02 still in flight.
>
> What *did* land: the 7 new columns exist and are partly populated (`Planned Tanking Date` 913,
> `Planned Delivery Date` 335); the fan-out **is** live on the sales app's Save and is creating
> production rows right now; the transfer flow ran once on 2026-09-01 with only **2 of 7**
> mappings in place.
>
> **So `Order Items` has two writers that don't know about each other** — the app's fan-out and
> the transfer flow. And **72 workbook rows have no `Order Items` row at all**, so they would
> vanish from every view at cutover; run the backfill and re-diff before deciding that date.
>
> `cutover-plan-2026-09-02.md` is **superseded** — wrong premise, and it contains a mapping bug.
> Don't work from it.

> **The 2026-09-01 plan, kept for its decisions:** `cutover-runbook-2026-09-01.md` splits the work
> into five parallel tracks (Power Automate / SharePoint UI / Power Apps / repo / docs) so separate
> sessions can be pointed straight at it, and it carries the 2026-09-01 decisions: 7 new
> `Order Items` columns (5 for viewer parity plus
> `Planned Tanking Date`/`Planned Delivery Date`); Order→Order Items fan-out on the sales
> Power App's Save button; stage stamping out of the trigger flow with a disabled fallback
> copy; TextField sync folded into the transfer flow; the viewer deployed **in place** at the
> `Index` list's FRM10-12 path so FRM09 and BO Manager keep working. Its own header carries the
> per-section corrections.

## Outstanding work — verified 2026-09-04, read this first

Supersedes the 2026-08-14/08-21 status below for *current* state; that section is still the best
description of **why** each workstream exists. Every figure here was measured against the live
tenant or the repos on 2026-09-04, not carried forward from the Sep 1 board, which was wrong in
the same direction about several items — most importantly it records the A6 transfer run as
never having happened. **It ran.**

### The single biggest data problem
**Every `Tanking Status = Completed` value on `Order Items` is fabricated.** 975 tanking + 400
delivery = **1,375 wrong status values**, and by the documented discriminator (a blank
`{Stage} Start Date` means the value came from the backfill) **zero are genuine** — 975 of 975
and 400 of 400 have no Start Date. **939 sit on units still `Active`**, so staff see
"Tanking: Completed" on units that have not been tanked.

A5b fixed the *flow* so it stops fabricating. Nobody cleaned the *data*. The Sep 1 board
estimated ~927/333; measured 2026-09-04 it is 975/400.

### Outstanding work

| # | Change | Track | Status | Blocked on / note |
|---|---|---|---|---|
| 1 | **Clean 1,375 fabricated Tanking/Delivery statuses** | 🔵 A | not started | Designer. Spec'd, discriminator proven |
| 2 | **72 workbook rows with no `Order Items` row** | 🔵 A | not started | Run backfill → re-diff. **Do not hunt a matching bug** |
| 3 | **Map A5's remaining 5 columns** — all still 0-populated | 🔵 A | 2 of 7 | Designer |
| 4 | **A4 — fold TextField sync into the transfer flow** | 🔵 A | not started | Designer |
| 5 | **Re-enable the trigger flow** (after backfill) | 🔵 A | off since Sep 1 | Items 3/4 first |
| 6 | **`Location` empty on 841 of 1,016 active units** | 🔵 A | never backfilled | Makes Production Floor near-useless |
| 7 | **B2-verify** — Production Floor + Planning vs real data | 🟢 B | never done | Item 6 first |
| 8 | **A7 reconciliation pass** — ~71 orphan rows waiting | 🔵 A | deferred 2026-08-21 | Deferral reasoning has expired |
| 9 | **A6b** — hand-fix rows failing on one column | 🔵 A | 5 genuine, not 35 | 30 of 35 fix themselves on re-run |
| 10 | **Export the sales Power App** — `power-apps/` is still `.gitkeep` | 🟠 D | not done | Tenant is the only rollback for a live fan-out |
| 11 | **D4 viewer parity check** | 🟠 D | not done | Needs a viewer refresh |
| 12 | **B4 live permissions test** on a staff account | 🟢 B | config verified only | ~30 seconds on a floor machine |
| 13 | **Timezone + 17 date columns** — site back to Eastern | 🔵 A / 🟢 B | **reopened 2026-09-04** | Own section below. Order is critical |
| 14 | **A2 / A3** — park fallback, strip stage stamping | 🔵 A | not started | Not blocking anything |
| 15 | **A5c** `toLower()` on six stages | 🔵 A | not started | Track A recommended skipping |
| 16 | **D5 + A8** — deploy viewer, disable transfer flow | 🟠 D / 🔵 A | **cut by the user** | The Monday cutover decision |
| 17 | **Centralise parents into `Order Items`** — sync `Order`/`Models`/`Model Revisions` down as `Order - X` / `Model - X` / `Mod. Rev. - X` | 🔵 A | **new 2026-09-05** | Picker workbook built (113 columns) — awaiting your selections. Needs a change-guard on every write |
| 18 | **Split the composite `Status`** into `Step Status` + `Status Date` | 🔵 A | **new 2026-09-05** | Code table found; see `infrastructure-overview.md` |
| 19 | **`Current Step` — the third status axis** | 🔵 A | **decided, not built** | Depends on Phase 1 + item 17. **Do not overload `Item Status`** — see `infrastructure-overview.md` |
| 20 | **Estimated Delivery Date** — calculated column + nightly refresh flow | 🔵 A | **new 2026-09-05** | Formula extracted; `TODAY()` freezes at write time, hence the ~21-row nightly touch |
| 21 | **One-time BO Manager → `Order Items` transfer** in the transfer flow | 🔵 A | not started | Key is `TableBO.Order`. **Remove the mapping after the run** or it clobbers SharePoint-native BO edits |

**Items 1, 2, 3, 4, 6 and 13 all need the same thing: a working Power Automate designer.** That
single blocker gates most of what is left, including everything that would make Production Floor
usable. It is worth more attention than any individual row above.

### Closed since build night 1
A0 · A5b (the flow, not the data) · **A6 — the transfer run DID happen** · B0–B3 · C1–C3 ·
D0–D3 · D5b · E1–E3 · **step-8 predicate narrowed** to ISO-date + English-boolean ·
**viewer Office Script patched** · all three repos pushed, 0 unpushed · BO Tracking view ·
`Direction - Prix (demo)` · bilingual views guide · view definitions exported

### Two observations
- **The TextField backlog is draining on its own** — `Order_Number_TextField` nulls went 72 → 52
  and the ID TextFields 86 → 66 between 2026-09-04 ~01:00 and ~12:40. The ~29 flow instances
  stuck in `Running` since Sep 2 are still working through it, so item 5 may partly self-resolve.
- **Decision 6 is reopened**, not closed — see the timezone section.

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

**Second update, 2026-08-21**: a real bug found while running the backfill — raw
`TableOrders` `Tanking Date`/`Delivery Date` are planning/estimate dates, not actual
completion dates, and were wrongly mapped into the automated `Tanking End
Date`/`Delivery End Date` fields (fabricating `Status = Completed`). Fixed going forward
(new `Planned Tanking Date`/`Planned Delivery Date` fields); **a remediation pass against
already-backfilled live rows is still needed, not yet run** — see
`order-items-power-automate-flows.md`'s "Remediation" subsection. Also: **Workstream 5,
Monday.com production-tracking integration, added** — production tracking is moving to
Monday.com per a 2026-08-21 meeting; see below.

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

## Five workstreams, mostly independent, all ready to build now

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
Management Shell app~~, and the same wall applies to any PowerShell-based automation, not just
PnP~~ — **the struck clause is false, corrected 2026-09-03: site-context REST is unaffected and
does schema changes fine; 19 field creates + 73 item updates all returned 2xx on 2026-09-03.
Test a GET on `_api/web/lists/getbytitle('Order Items')/fields` before assuming manual**)
— schema was built manually via `docs/order-items-manual-build-checklist.md` instead
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
Mechanical Preliminary Review → Planning Schedule → Work Order → Confirm Planned Dates
with Client` (reorder confirmed 2026-08-21 — see `phase1-plan.md`) — with a `Workflow
Tasks` list and Power Automate flows that notify (email +
Teams) whoever's turn it is to act next. Fixes the other big current pain: no visibility
into whose turn it is on an order.

The underlying business-process diagram (`workflow-data/Pioneer Transformers Model.vsdx`,
described in `docs/infrastructure-overview.md`) already reflects the final logic: parallel
Electrical/Mechanical duplicate-check reviews, an AND-gate unlocking early Purchasing start
only when both say Yes, and Engineering's start gated on client-date confirmation.

**Confirmed 2026-08-21**: one shared `Workflow Tasks` list across departments, with
department-filtered views (not the originally-floated separate list per department). List's
exact name still TBD, defaulting to `Workflow Tasks`.

**Tooling choice researched and confirmed 2026-08-12** — see `docs/phase1-tooling-research.md`:
staying in SharePoint + Power Automate is still the right call (vs. Planner Premium, which
turned out to be Dataverse-backed and would break Lookup compatibility with `Order`/`Order
Items`; vs. Power Apps + Dataverse, which is over-engineering at this project's ~1000
orders/year scale). Two changes folded back into `phase1-plan.md` from that research: use
Adaptive Cards for notifications from the start, and give `Workflow Tasks` its own archiving
flow rather than deferring it.

**Dependency on workstream 1**: Phase 1's `Planning Schedule`/`Work Order` steps are
per-unit, so they need `Order Items` rows to exist. Once workstream 1's list/schema exists,
this is satisfied — Phase 1's flow just creates new `Order Items` rows for new orders going
forward (see the fan-out logic in `phase1-plan.md`), on top of whatever workstream 1's
one-time backfill already populated for existing orders. No conflict between the two — just
don't build a redundant "minimal" version of `Order Items` for Phase 1, use the real one.

### 3. Archiving
→ `docs/archiving-plan.md`

Without this, `Order`/`Order Items` grow forever and SharePoint's practical
performance/usability degrades — user's concern, 2026-08-12: the lists getting
"exhaustive."

**Redesigned 2026-08-31**: no separate SharePoint archive list — Excel's Archive workbook
(`Archive active.xlsx`) stays the sole permanent historical record, so this workstream is
purely about keeping the *live* lists bounded, not preserving a second copy. Mechanism: a
**scheduled** Power Automate flow that finds `Order Items`/`Order` rows sitting at
`Delivered`/`Cancelled` for at least a month, **reconfirms them against the Excel Archive**
(same check Workstream 1's reconciliation pass does), and **deletes** the live row outright
once confirmed — no copy/verify-then-delete into a new list, no Power BI repoint needed
(Power BI reads the Excel Archive directly if it ever needs historical data). Trigger logic
still reuses the already-designed `Item Status`/`Order Status` fields.

**Relationship to Workstream 1's reconciliation pass**: that pass deletes immediately once
a unit vanishes from `TableOrders` (the pre-cutover era, while Excel still drives
completions) — this workstream is the post-cutover mechanism, once `Item Status` starts
getting set some other way and there's no "vanished from TableOrders" event to react to.

**Sequencing**: doesn't block the other two workstreams starting, and they don't block
this — but build it soon after `Order Items` goes live, before the list actually gets big
enough to matter, not deferred indefinitely.

**Depends on**: `Item Status`/`Order Status` existing (workstream 1) as the trigger
conditions, and Workstream 1's Excel-Archive-pull pattern being reusable here.

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

### 5. Monday.com production-tracking integration
→ `docs/document-library-plan.md` (document library / NC storage / design-doc routing)

**Blocked, 2026-08-21**: user's Monday.com account access is pending approval — anything
requiring a Monday login (native automations, the Link-column inline-preview test) waits on
that. The SharePoint-side half of `document-library-plan.md` (library/view setup, tagging
drawings) has no such dependency and can proceed now.

**Added 2026-08-21**, per a meeting the user attended that day. **Confirmed scope:
production tracking only** — this does not touch Phase 1 (`phase1-plan.md`'s Workflow
Tasks / front-of-process automation), which stays a separate SharePoint + Power Automate
build exactly as already planned.

**Confirmed shape of the integration:**
- **Monday.com is the tool the production team works in day to day** going forward — not
  SharePoint directly.
- **SharePoint's `Order Items` list stays the authoritative "database"** — it's what KPI/
  Power BI reporting syncs against, and what the rest of the workflow (`Order`, and
  eventually Phase 1's `Workflow Tasks`) cross-references. Monday is a working layer synced
  on top via connector, not a replacement source of truth. Same columns/schema as already
  built — nothing in `order-items-manual-build-checklist.md` changes because of this move.
- **The existing SharePoint production-stage automation is being paused** — the 16 Start/End
  Date stamps + `N/A` auto-advance flow (built/tested 2026-08-14, workstream 1 step 2c).
  Equivalent stage-advance logic will live inside Monday instead. **Action item, not yet
  done**: disable that flow in the Power Automate portal — this is a manual portal action,
  not a doc change.
- Worth noting for whoever picks this up: `docs/phase1-tooling-research.md` (2026-08-12)
  already evaluated monday.com and rejected it as a *system of record* (third-party Power
  Automate connector, cost, a 25,000-automations/month cap) — recommending it only as a
  "synced presentation layer" at most. This new design (SharePoint as the database, Monday
  as the working layer) lines up with that recommendation rather than contradicting it.

**New, genuinely unbuilt scope, raised in the same meeting**: syncing a document library
covering two distinct needs — engineering design docs routed to the correct production step
(replacing today's local-file-server + multi-copy-print + color-coded-folder distribution,
with a goal of shop-floor tablets pulling the right drawings automatically when a Monday
task starts), and a place to store NC (non-conformance) photos/notes per unit/production
step (nothing like this exists today). A completed department/drawing-needs analysis already
exists to seed this — see `document-library-plan.md` for the real design questions still
open; not duplicated here.

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

## 🔴 Site timezone + the 17 date columns — the UTC flip is a workaround, not a fix

**Status: NOT resolved.** Recorded elsewhere as "decision 6, closed by the timezone flip." It is
worked around, and the workaround is one the user has ruled out.

**User requirement (2026-09-04): the site and all columns should be Eastern** — Montreal office,
Granby factory. The site is currently `(UTC) Coordinated Universal Time` (Id 93, bias 0),
verified by REST.

### What is actually wrong
17 columns on `Order Items` — all 8 stage `Start Date`, all 8 stage `End Date`, and
`Tank Delivery Date` — are configured **Date and Time**, and their values are stored at
`T00:00:00Z`, i.e. **UTC** midnight. On an Eastern site that instant is 7:00 PM the *previous*
day, so every one of those dates reads a day early. Flipping the site to UTC hid that.

### ⚠️ Why the obvious fixes do not work
**A Date Only column on an Eastern site stores *local* midnight as UTC.** Provable from the two
correctly-configured columns on this same list:

| Column | Format | Stored |
|---|---|---|
| `Original Tanking Date` | Date Only | `2026-01-21T05:00:00Z` ← EST midnight |
| `Manual Estimated Delivery Date` | Date Only | `2026-08-15T04:00:00Z` ← EDT midnight |
| `Coiling End Date` (one of the 17) | Date **and Time** | `2026-04-14T00:00:00Z` ← **UTC** midnight |

The 17 columns are stored **4–5 hours earlier than Eastern midnight**, so on an Eastern site they
fall on the previous day **whatever display format is applied**. Therefore:

- Setting the site back to Eastern **alone** re-breaks all 17 columns.
- Setting the 17 columns to Date Only **alone** does not fix them — it hides the time while still
  showing the wrong date.

**The stored data is wrong for an Eastern site, not merely displayed wrong.**

### Required sequence — order is critical
1. **Set the 17 columns to Date Only.** Schema first.
2. **Set the site timezone to Eastern** — Id 10, *(UTC-05:00) Eastern Time (US & Canada)*.
3. **Rewrite the existing values** to Eastern midnight. **This rides along with the transfer-flow
   backfill already required** — those values come from the flow reading FRM10-12, which holds
   plain Excel dates with no timezone, so a re-run after steps 1–2 writes them correctly. Not a
   separate migration.
4. **Verify** end to end: pick a unit, compare its stage dates against FRM10-12.

**Running the backfill before steps 1 and 2 writes UTC-midnight values all over again.**

### ⚠️ CORRECTION — 🔵 A, 2026-09-04 14:0x. Steps 1 and 2 are already done, and step 3 rests on a cherry-picked sample.

Measured by REST against the live list, not sampled:

**Step 1 is already complete — or was never true.** All **24** date columns on `Order Items` are
`DisplayFormat = 0` (**Date Only**). **Zero** are Date-and-Time, including all 8 stage
`Start Date`, all 8 `End Date`, and `Tank Delivery Date`. So "set the 17 columns to Date Only"
is a no-op today. **Step 2 is also done** — the site is now `(UTC-05:00) Eastern Time` (Id 10),
flipped ~13:39 today. This section was written while the site was still UTC.

**Step 3's premise does not survive measurement.** The proof table above cites one value each
from `Original Tanking Date` and `Manual Estimated Delivery Date` to establish that a Date Only
column stores *local* midnight. Those two columns are actually **mixed**, and are mostly the
opposite of what was cited:

| Column | `00:00:00Z` (UTC midnight) | `04:00`/`05:00Z` (Eastern midnight) |
|---|---|---|
| `Original Tanking Date` | **894** | 47 + 15 |
| `Manual Estimated Delivery Date` | **306** | 20 + 6 |
| `Tanking End Date` | 975 | 0 |
| `Coiling End Date` | 209 | 0 |
| `Planned Tanking Date` | 913 | 0 |
| `Tank Delivery Date` | 58 | 0 |

The cited values are the **minority** in their own columns — most plausibly rows a person entered
through the SharePoint UI, which does localise. Every value the transfer flow wrote is
`00:00:00Z`, with **zero** exceptions across 2,155 values in four columns that are Date Only
today. **So "a re-run after steps 1–2 writes them correctly" is not supported**, and following
this sequence as written risks a 40-minute production run that changes nothing.

**What is genuinely still open:** whether those columns were already Date Only *at the time* the
flow wrote them. If they were, the connector demonstrably does not localise and a re-run cannot
fix this. SharePoint does not expose field-schema history, so this cannot be settled by reading.

### ✅ SETTLED — 🔵 A, 2026-09-04 14:2x. Step 3 is CORRECT. My "unsupported" verdict above was wrong. No one-row test needed.

**The connector DOES localise, and it is the column format that decides it.** Settled from
existing data, no write and no flow run. The 64 rows the Sep 1 run never touched still carry
values from the **August 18–21** runs — same connector, same credentials, same runs — and within
those *same rows*:

| Column | Format at write time | Stored |
|---|---|---|
| `Original Tanking Date` | Date Only | 41 × `04:00Z` + 15 × `05:00Z` — **100% Eastern midnight** |
| `Manual Estimated Delivery Date` | Date Only | 17 × `04:00` + 6 × `05:00` — **100% Eastern midnight** |
| `Tanking End Date` | Date **and Time** | 56 × `00:00:00Z` |
| `Coiling End Date` | Date **and Time** | 32 × `00:00:00Z` |
| `Delivery End Date` | Date **and Time** | 44 × `00:00:00Z` |

**The `04:00` / `05:00` split is EDT vs EST, correctly chosen per date.** That is genuine
timezone localisation, not a constant offset — conclusive. The site was Eastern in August, so a
Date Only column received Eastern midnight while a Date-and-Time column in the same write
received the literal UTC-midnight instant.

**So the model is column format, not write path.** Two hypotheses die here: my "the connector
always stores UTC midnight" (it doesn't — 79 counter-examples with the right DST offsets), and
the follow-up "storage depends on the write path" (it doesn't — one write path, two behaviours,
split by format).

**Consequence: all 24 columns are Date Only *now*, so a fresh backfill writes Eastern midnight
into every one of them. Step 3 works as written.** The only thing this section got wrong is that
step 1 is already complete.

**The correct sequence today is therefore: refresh FRM10-12 (Office Script button only) → run the
transfer flow → verify.** Running does **not** need the flow designer — an instant flow runs from
the Run button on its detail page — so the designer blocker does **not** block this fix. Mapping
the 5 remaining columns (A.3) does need the designer, and doing it first avoids a second
40-minute run, but it is not a prerequisite for correcting the dates.

**Do not rewrite the ~4,711 values by hand.** That was my earlier recommendation and it is now
the wrong tool — the backfill does it correctly and is required anyway.

#### ✅ Assumption 1 is now CLOSED by observation — 🔵 A, 2026-09-04 14:5x

Read from the **Aug 21 run's `UpdateOrderItem` output body** in run history (run
`08584143197095564899725031235CU24`, iteration 1, unit `21408-1/1`). Same action, same response,
same August write:

```
CoilingDate          "2026-04-14T00:00:00Z"   <- full instant
StackingDate         "2026-04-17T00:00:00Z"
AssemblyDate         "2026-04-20T00:00:00Z"
DryingDate           "2026-04-20T00:00:00Z"
TankingDate          "2026-04-23T00:00:00Z"
TestingDate          "2026-07-14T00:00:00Z"
FinishingDate        "2026-07-16T00:00:00Z"
DeliveryDate         "2026-08-31T00:00:00Z"
TankDeliveryDate     "2026-01-07T00:00:00Z"
OriginalTankingDate  "2026-01-21"             <- BARE DATE, no time component
```

**Stated strictly, because this is an OUTPUT body — SharePoint's response *after* the write, i.e.
SharePoint serialising the STORED value according to column type. It is not a record of what the
connector sent.** The claim it supports is:

> In August, **SharePoint reported** `Original Tanking Date` as a bare date and the stage columns
> as full instants — which means those columns genuinely **were** Date Only vs Date-and-Time
> **at write time**.

**That closes the one inferred link** (a Sep-1 format label applied to August writes). Do **not**
cite this as evidence of how the connector serialises outbound values — that was not observed.
Precision credit: 🟢 B.

Cross-check: a bare `2026-01-21` on an Eastern site stores as `05:00:00Z` (EST midnight), which
is exactly the 15 winter-dated values measured in that column. Consistent both ways.

**Consequence: all 24 columns are Date Only now, so the connector will serialise all of them as
bare dates and SharePoint will store site-local (Eastern) midnight. The backfill fixes the
dates.** Confidence is high.

#### Assumption 2 — still open, but no longer load-bearing

The remaining alternative was that the split came from *different mapping expressions* rather
than column format. The evidence above makes that redundant as an explanation — one payload, one
action, and the shape difference tracks the column type exactly. The action's **inputs** body was
also read and carries no date fields in a comparable shape, so the expressions were not directly
compared. **Verify on the outcome anyway** (below) — it costs nothing and settles it for good.

#### Original caveat text, retained for the record (raised by 🟢 B)

Act on the conclusion; it is well supported. But do not read the table above as fully measured,
because two links in it are inference:

1. **Column format in August is inferred, not observed.** The columns are labelled by their
   format in the **Sep 1 export**, and that label is applied to writes made **Aug 18–21**.
   SharePoint keeps no field-schema history, so nobody can confirm the format was unchanged in
   between. If a format was altered in that window, the comparison loses its control.
2. **"Same mapping expression" is documented, not verified.** The alternative explanation for the
   split is that the flow simply maps these columns with *different expressions* — which would
   mean the run writes UTC midnight into the stage columns again and does **not** fix them.
   Partial control: `order-items-power-automate-flows.md` groups `Tank Delivery Date`,
   `Original Tanking Date` and `Manual Estimated Delivery Date` as one "other dates" set using
   **the same Excel-serial conversion**, and their storage splits on format anyway —
   `Tank Delivery Date` (one of the 17) is `00:00:00Z` 58/58 while the other two are 100% Eastern
   midnight. **But that grouping comes from the doc, not from reading the flow**, and
   `Tank Delivery Date` has only **n=1** among the 64 August rows. Confirming it needs the
   designer.

**What this means for execution:** the fix is still worth running — the run is required anyway
and the downside of being wrong is that the dates stay as they already are, not that anything
new breaks. **But verify on the actual outcome, not on this reasoning:** after the run, re-count
stored time-of-day on `Tanking End Date` and `Coiling End Date`. `04:00`/`05:00Z` means it
worked. `00:00:00Z` means the expression hypothesis was right, and the fix is then to correct the
mappings rather than to rewrite data.

**Meanwhile, flipping the site back to UTC is a safe holding position** — Eastern-midnight values
render correctly under *both* timezones, UTC-midnight only under UTC. It re-hides rather than
fixes, but it breaks nothing, including the 53 BO dates. (🟢 B asserted the opposite on the board
and has since retracted it.)

**Unrelated stray, found in the same pass:** `Coiling Start Date` holds one value at `08:03:52`
and 15 `Delivery End Date` values carry random times. Neither fix above corrects those.

### Two caveats
- **Site timezone is site-wide.** It affects every list and library on
  `/sites/PioneerPlanificatio`, including `Created`/`Modified` stamps — not just `Order Items`.
- **Rows the backfill does not touch keep their bad values** — the ~14 app-created units and the
  ~71 orphan rows with no `TableOrders` row. Separate pass, or accept that their stage dates are
  mostly empty anyway.

### Why this matters beyond display
`order-items-power-automate-flows.md:273-275` specifies **Eastern** for the stage auto-stamp
flow: *"Pioneer's shop floor runs on Eastern time, so every stamp expression [must convert]."*
While the site is UTC, any genuinely time-stamped value renders 4–5 hours off local — a
correctness problem for shift times, not only a cosmetic one for dates.

## Deferred out of the 2026-09-01 cutover — decided, not forgotten

Each of these was consciously cut from the overnight window, not overlooked. Full context in
`cutover-runbook-2026-09-01.md`.

- **Date-urgency conditional formatting on `Planned Tanking Date`** (deferred 2026-09-04 by the
  user, after two failed attempts). Intent: yellow when tanking is within 14 days, red when
  overdue, so a BO row's deadline pressure reads at a glance. **Two blockers, both real, both
  worth knowing before anyone retries this:**
  - **Hand-written column formatting using `@now` froze the `BO Tracking` view.** Reproduced
    A/B/A/B: fills + strikethrough expand fine; add a date formatter and expanding a group hangs
    the renderer; revert and it works; re-add a *minimal* style-only version with no conditional
    `txtContent` and no cross-field reference, and it hangs again. `@now` is the only common
    factor — its value changes continuously, which appears to drive a re-render loop on a
    grouped 23-column view.
  - **A calculated column is NOT the workaround.** SharePoint evaluates `TODAY()` in a
    calculated column at **write** time, not read time, so a `Late`/`Soon` flag is correct the
    day it is created and silently wrong afterwards. (`Bo Sort Date` is safe precisely because
    it uses no `TODAY()` — pure same-row arithmetic on `Planned Tanking Date`.)

  **Routes not yet tried, in order of promise:** (1) the built-in *Format this column →
  Conditional formatting* UI, which offers native "is before today" date rules and may use a
  supported path rather than a raw `@now` expression; (2) a scheduled Power Automate flow that
  stamps a `BO Urgency` text column daily, then plain string-comparison formatting on that
  column — robust, no `@now`, but real machinery.

  If it is built, Excel's own CF presets keep it consistent with BO Manager: late = fill
  `#FFC7CE` / text `#9C0006`; approaching = fill `#FFEB9C` / text `#9C6500`.

  **Note:** column formatting in SharePoint is **field-level**, so whatever lands on
  `Planned Tanking Date` also appears in `Planning` and `Angelique réunion du lundi`. There is
  no per-view column formatting.

  *Not blocking anything.* The view already sorts most-urgent-first via `Bo Sort Date`, which
  carries most of the signal — `21910-1/3` (overdue since 2026-07-16) sits at the top of the
  `BO` group without any colour.

- **Tanking/Delivery cleanup.** The original backfill wrote raw `TableOrders` planning dates into
  `Tanking End Date`/`Delivery End Date` and stamped a fabricated `Status = Completed`. Fully
  spec'd, with the safety discriminator already designed: a blank `{Stage} Start Date` means the
  value came from the backfill; a populated one means a genuine live completion that must not be
  touched. **Safe to run any time now** — the 2026-09-01 viewer re-source means clearing those
  fields no longer blanks anything downstream. Before that change it would have.

  > **⚠️ Bigger and more urgent than this entry implies. Updated 2026-09-04.** Measured live:
  > **975** units carry a fabricated `Tanking Status = Completed`, **400** a fabricated
  > `Delivery Status = Completed` — and by the discriminator above it is **975 of 975 and 400 of
  > 400, with zero genuine.** The Sep 1 estimate was ~927/333. **939 of them are on units still
  > `Active`**, so staff are currently looking at "Tanking: Completed" on units that have not
  > been tanked. A5b stopped the flow fabricating *new* ones; nobody cleaned the existing data.
  >
  > **This resolves a decision left open on 2026-09-01** (`BUILD-NIGHT-STATUS.md`, the 🔵 A
  > decision also numbered 6). The choice was: leave the 4 fields *unmapped* — which stops new
  > fabrication but leaves the old values — or map them to `@null`, which clears every one of
  > them **for free during a run that has to happen anyway.** It was left deferred on exactly one
  > objection: *"it blanks those fields for any unit where the value is genuinely correct."*
  > **That objection is now measured to be empty — there are no genuinely correct ones.**
  >
  > Two things have also changed since that entry was written:
  > - It said the choice had to be made **before A6** because **A8** would disable the flow and
  >   there would be no second run. **A8 never ran.** The flow is still enabled, so this is no
  >   longer a one-chance decision.
  > - The cleanup therefore **rides along with the backfill** rather than needing its own pass.
  >
  > **Recommended, and this is the refinement worth keeping:** make the null **conditional on the
  > discriminator**, not unconditional — null the field only where `{Stage} Start Date` is blank.
  > Unconditional `@null` is safe *today* precisely because the genuine count is zero, but staff
  > could legitimately complete a tanking between now and the run, and that row would have a
  > populated Start Date. The conditional form is safe whatever happens in between, and it uses
  > the discriminator that is already designed and documented. Costs nothing extra.
- **Surfacing planned vs actual separately in the workbook.** The viewer keeps its frozen
  76-column layout, with `Tanking Date`/`Delivery Date` re-sourced from the `Planned` columns.
  Exposing the actuals as their own columns is a real migration: `BO Manager.xlsx` reads
  `Tanking Date` by name, and other worksheets may too — they need identifying first.
- **`Order Items - BO sync`** — spec'd 2026-08-31. Affects 8 of ~1000 rows; the viewer takes `BO`
  from `BO Manager.xlsx` directly, so it was never on the cutover's critical path.
- **`Estimated Delivery Date` computation + daily sweep** — spec'd, unblocked. The viewer keeps
  it as a native Excel formula, so nothing depended on it for cutover.
- **Automating the viewer refresh.** Cutover shipped a documented daily *manual* refresh with a
  named owner. Without a refresh, FRM09 and `BO Manager.xlsx` freeze at the last good data
  **with no error** — see `FRM10-12/CLAUDE.md`. Automating this is the highest-value item on
  this list.
- **Qty-change handling for the fan-out.** The sales app now creates `Order Items` on Save, but
  nothing reacts to an `Order`'s `Qty` changing afterwards. No mechanism existed before either —
  `Regrouped Into` is schema-only and manual — so it's not a regression, but it is now a known
  hole in an automated path rather than in a manual one.
- **Export the sales Power App into `FRM10-12/power-apps/`.** It carries the fan-out logic as of
  2026-09-01 and is otherwise undocumented and unbacked-up.
- **The `Archived` column** is still structurally present in the live workbook's table
  definition — depopulated, not deleted, despite `FRM10-12/CONTEXT.md` saying it was dropped.
  Cosmetic, but it makes column-count audits confusing.

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

## Future workstream — retire `BO Manager.xlsx` into SharePoint

**Added 2026-08-31 at user's request.** Goal: `BO Manager.xlsx` stops being a separate
hand-maintained workbook; its data lives in SharePoint alongside `Order Items`. This also
deletes the `Order Items - BO sync` flow (see
`order-items-power-automate-flows.md`) — that flow exists only to bridge the gap this
workstream closes.

**Do not treat this as one migration.** `TableBO`'s 23 columns split into three groups with
three different correct destinations, and one of them should not be migrated at all.

### 1. `BO` summary → `Order Items.BO`
Single text column, three states (`"BO"` 8, `"OK"` 61, blank 945 of 1014 rows). Already
specced as the sync target; becomes native once the workbook is retired.

### 2. `BO1`/`BO2`/`BO3` detail → new **`Back Order Parts`** child list
**Not 18 flattened columns on `Order Items`.** The workbook stores a repeating group in three
fixed slots, each `Part Numbre` / `Description` / `PO Intern` / `Date` /
`Fournisseur Interne` / `OK`. Correct SharePoint shape is a child list, one row per
back-ordered part, with a Lookup to `Order Items`.

Current usage (measured 2026-08-31): **36** units have a 1st part, **16** a 2nd, **4** a 3rd
— roughly 56 part rows total. `BO1 OK` is a hand-ticked Yes/No (TRUE on 26 rows), not a
formula.

Reasons for a child list over flattening:
- The 3-slot cap is an Excel artifact, not a business rule. A child list removes it.
- `Order Items` is already **89 columns**; 18 more for a sparse repeating group used by ~36
  units is the wrong direction.
- Per-part querying ("which POs are we waiting on, from which supplier") is natural on a
  child list and awkward across `BO1..BO3`.

### 3. `Location`, `Status`, `Tanking Date` → **pulled context — replace with a view, don't migrate**

**Corrected 2026-08-31 after user input.** An earlier version of this section called these
"hand-keyed copies" that had "drifted", and framed reconciling them as a data-quality task.
That was wrong.

`BO Manager` **pulls this data from FRM10-12 via Power Query** so the person managing
back-orders can see what to work on. Confirmed in the file: `xl/connections.xml` carries
`Query - ImportFromIndex`, `Query - Index`, `Query - ReplaceAllErrors`,
`Query - SelfRefColumns`, `Query - Table_BO_SelfRef` — the same `ImportFromIndex` mechanism
FRM10-12 uses, plus a self-referencing query that preserves the hand-entered columns while
the pulled ones refresh. (Zero formula cells in those columns is consistent with a Power
Query load, not with manual typing — that was my misreading.)

So `TableBO` has two kinds of column:
- **Pulled context** (`Order`, `Location`, `Status`, `Tanking Date`) — read-only, refreshed
  from FRM10-12.
- **Owned data** (`BO`, `BO1..BO3` groups) — hand-entered here and nowhere else.

The 60-of-181 `Location` divergence measured against `Order Items` is therefore **refresh
staleness, not conflicting data**. There is nothing to reconcile and no system that is
"wrong" — the snapshot is simply older than the list. (Decoded through
`TableValidationLocationCodes`: `XT`→`Extérieur`, `FI`→`Finition`, `LI`→`Livraison`, 13
entries, no unknown codes.)

**Constraint confirmed by user 2026-08-31: the purchaser needs *every* column currently in
`BO Manager`** — the replacement must lose nothing.

That rules out a plain `Order Items` view, which cannot show child-list rows. The shape that
does satisfy it: build the replacement view **on `Back Order Parts`**, not on `Order Items`,
with its Lookup to `Order Items` projecting the additional parent fields (`Unit ID`,
`Location`, `Status`, `Tanking Date`, `BO`). SharePoint Lookup columns can surface extra
columns from the parent item, so one grid carries parent context *and* part detail.

This is arguably better than the workbook's own layout, which crams up to three parts across
a single row: here each part is its own row with full context, there is no 3-slot cap, and
the context is live rather than as-of-last-refresh. **Walk the purchaser through this view
before retiring the workbook** — it is the one step where "loses nothing" has to be confirmed
by the person who uses it rather than asserted.

Retiring the workbook therefore eliminates, in one step: the pull, the `SelfRefColumns` /
`Table_BO_SelfRef` machinery that exists only to survive it, the staleness, **and** the
`Order Items - BO sync` flow.

### 4. Unmatched keys
**14** `TableBO` keys have no matching `Order Items` row (1014 vs 1038, 1000 matched).
Expected to be a symptom of the same refresh lag rather than orphan data — re-check after a
refresh, and only investigate keys that persist.

### Sequencing
Nothing here blocks the Estimated Delivery Date work. Order: (a) ship the `BO` sync flow so
`Order Items.BO` is populated and correct; (b) build `Back Order Parts` and move the detail;
(c) build the filtered `Order Items` view that replaces the pulled-context columns and
confirm the purchaser can work from it; (d) retire the workbook and delete the sync flow.

No drift-reconciliation step is needed — that item was a consequence of the misreading
corrected above.
