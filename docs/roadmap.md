# Roadmap

**Start here.** This ties together the other docs in this repo into one picture. Read this
first, then follow the links into whichever workstream you're picking up.

## Three workstreams, mostly independent, all ready to build now

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

## Reference (not a build plan — background/audit)
→ `docs/infrastructure-overview.md`

The full column-by-column audit behind workstream 1's schema, the current-state
architecture diagram (SharePoint ↔ Power Query ↔ Excel ↔ Power BI/Power Apps), and the
business-process diagram description. Read this for *why* a field ended up where it did;
read the build-plan docs for *what to actually do*.

## Explicitly not planned yet (future phases)

- **Phase 2+ of the business process**: `Electrical Design`/`Mechanical Design` execution,
  `Customer Drawings`, the `P.O.` chain, `Production`. Don't scope-creep into these before
  Phase 1 ships and the team's used it for a while.
- The 7 native-formula calculated columns (`Price`, `Estimated Delivery Date`, `Price
  CAD/USD`, `Navigation Order/Model`, `Archived`) — parallel-run plan decided
  (`infrastructure-overview.md`), not yet built.
- FRM09's raw-column-letter external-reference fragility — actually already resolved per
  FRM09's own `CLAUDE.md` (2026-08-12), unrelated to this repo's remaining work.
- **Standing future review point**: once `Order Items`/`Workflow Tasks` have real usage
  history, revisit any field placed on a hunch during this initial design pass (starting
  with `Trimestrial Customer`) — don't wait to be reminded, this is a deliberate open loop.
