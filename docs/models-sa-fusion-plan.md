# Models SA Fusion Plan

**Status:** decided in principle 2026-08-13, not yet scoped in detail or started. Logged
here so the decision and its consequences aren't lost before work on it begins.

## The decision

Fuse `Models SA` into `Models`/`Model Revisions` — SA (auxiliary) model designs become
regular `Models` rows with their own `Model Revisions` history, instead of living in a
separate, structurally-duplicated, never-versioned list.

## Why

- `Models`/`Model Revisions` already went through a deliberate split (identity/workflow
  fields on `Models`, versioned spec fields on `Model Revisions`) so spec changes get real
  history. `Models SA` never got that — it's still the old flat pre-migration shape, so SA
  designs have no revision history at all.
- Practical pain surfaced while building the Lookup→TextField sync flows
  (`lookup-textfield-reference.md`): `Models` and `Models SA` both need a `Client`-sync
  flow, purely because they're separate lists holding the same shape of data — duplicate
  work for no real benefit.
- Resolves a real gap found while discussing this: **`Order Items`' SA auxiliary row (the
  one with `SA Job = Yes`, e.g. `21408-1/1 SA`) has no lookup field pointing at `Models SA`
  at all right now** — user confirmed `Order.Model` always points at `Models`, never
  `Models SA`, regardless of SA status; the SA-specific model link was expected to live on
  the `Order Items` auxiliary row instead, but that field doesn't exist. Fusing removes the
  need for a separate field/mechanism entirely — once SA designs are just `Models` rows,
  the *existing* model-lookup mechanism covers them too.

## What this is NOT

`Order Items`' `SA Job` flag (marks a *physical production unit* as an auxiliary) is a
different axis from `Models SA` (a *model/spec* list) — don't conflate them. This fusion
doesn't touch `SA Job` or the production-tracking side of things at all.

## New requirement this creates

**Order-item generation must pick the right `Model` row.** User's own framing, 2026-08-13:
"it will be at the order item generation phase that it will be important to make sure and
take the right one." Once SA designs are indistinguishable from regular ones at the list
level (both just rows in `Models`), whatever creates the SA auxiliary `Order Items` row
(today: manual; later: the transfer flow, and eventually `phase1-plan.md`'s `Work Order`
fan-out logic) needs correct logic to resolve *which* `Models` row is the SA-specific
design for a given order — not just "the" model, since a main unit and its SA auxiliary
may need different model rows. **How to distinguish them once fused is not yet designed —
open question, needs answering before the fusion is implemented, not just before it's
used.**

## Migration scope (not yet detailed — sketch only)

1. Design how to distinguish an "SA-type" `Models` row from a regular one post-fusion
   (a flag? a naming convention? something else?) — the open question above, needed before
   step 2 can be done correctly.
2. Migrate every existing `Models SA` row into `Models` + a new `Model Revisions` entry
   for it.
3. Repoint anything referencing `Models SA`: `ColumnMap.pq`'s `Models SA` entity,
   `TableOrders.pq`'s merge logic (`#"Imported SA Models"`/`#"Complete Imported Models"`
   branch), any live `Order`/`Order Items` rows currently pointing at `Models SA` records.
4. Retire the `Models SA` list once nothing points at it anymore.
5. Build the order-item-generation logic that resolves the correct `Models` row (main vs.
   SA) for each unit — this is new logic, not just a repoint, since today `Models`/`Models
   SA` being separate lists was itself how "which one" got resolved (the list you queried
   told you which kind), a distinction the fusion removes.

## Relationship to other work

- **Supersedes** the `lookup-textfield-reference.md` to-do item "Build the `Client`-sync
  flow for `Models` and `Models SA`" — only build it for `Models` now; don't build a
  `Models SA` version that's about to be retired.
- **Depends on / feeds into** `order-items-build-plan.md`'s transfer flow (step 3) and
  `phase1-plan.md`'s `Work Order` fan-out — both eventually need step 5's order-item
  generation logic once this fusion happens, but neither is blocked from proceeding on
  other fronts in the meantime.
- Don't start the actual migration until the open question (how to distinguish SA rows
  post-fusion) is answered — starting the data move before that risks having to redo it.
