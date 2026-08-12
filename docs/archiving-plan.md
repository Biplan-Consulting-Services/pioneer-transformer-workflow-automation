# Archiving Plan

**Status:** planned, not yet built. Elevated from "noted, not designed" to a real plan
2026-08-12 — user flagged the actual reason: without archiving, `Order`/`Order Items` grow
forever, and SharePoint's practical performance/usability degrades well before any
theoretical row-count ceiling (list view thresholds, slower filtered views, staff wading
through years of delivered/cancelled orders to find active ones). This also happens to
serve the earlier-noted Power BI historical-analysis need — two reasons to build one thing.

**Sequencing**: doesn't block `order-items-build-plan.md` or `phase1-plan.md` starting —
build it soon after `Order Items` goes live (so it's ready before the list actually gets
big), not deferred indefinitely, but not a prerequisite for either other workstream either.

## What exists today, in Excel

`TableOrders.pq` merges against an `ArchivedOrders` query (reading a separate "Archived
Orders" linked workbook, see `infrastructure-overview.md`'s current-state diagram) and
**filters out** any row matching: `Location = LI` (Livraison) with a `Delivery Date`
present, OR `Location = AN` (Annulée/cancelled). I.e. archiving today = removing delivered
or cancelled orders from the live working view once they're done, keeping their record in
a separate workbook instead of the live table.

## Recommended mechanism: move rows to separate Archive lists, not just a flag-in-place

Two ways to do this in SharePoint:

- **(a) Move** — a Power Automate flow copies the row to a separate `Archived Order
  Items`/`Archived Orders` list once it qualifies, then deletes it from the live list.
  Keeps the live list's row count bounded — matches what the old Excel mechanism actually
  did (a genuinely separate store), and directly addresses "the list gets exhaustive."
- **(b) Flag in place** — add an `Archived` Yes/No (or just reuse `Item Status`/`Order
  Status`) and rely on a filtered default view to hide archived rows. Simpler (no
  move/delete flow to build), but the underlying list keeps growing indefinitely — this
  only fixes *view clutter*, not the actual row-count/performance concern the user raised.

**Recommendation: (a).** The user's stated concern is specifically about lists getting
"exhaustive," not just messy filtered views — only physically moving rows out keeps the
live list bounded long-term.

## Trigger criteria — reuses fields already designed, no new fields needed

- **`Order Items` row** archives when `Item Status = Delivered` or `Item Status =
  Cancelled` — direct equivalent of the old `Location = LI` + `Delivery Date` / `Location =
  AN` logic, now expressed through the single `Item Status` field already designed in
  `infrastructure-overview.md`.
- **`Order` row** archives when `Order Status = Cancelled`, OR once **every** one of that
  order's `Order Items` rows has itself been archived (the whole order is fully delivered).

## Build steps

1. Create `Archived Orders` and `Archived Order Items` lists — same schema as the live
   `Order`/`Order Items` lists (SharePoint can save a list as a template to copy the
   schema, rather than rebuilding column-by-column by hand).
2. Power Automate flow: on `Order Items` `Item Status` changing to `Delivered` or
   `Cancelled` → copy the row into `Archived Order Items`, then delete it from the live
   list.
3. Same or a second flow: once an `Order`'s live `Order Items` count reaches zero (its
   last remaining unit just got archived), or `Order Status` becomes `Cancelled` → copy the
   `Order` row into `Archived Orders`, delete from the live list.
4. Repoint Power BI (and whatever in FRM10-12 still reads the old `ArchivedOrders` linked
   workbook) at the new `Archived Orders`/`Archived Order Items` SharePoint lists instead —
   this was already flagged as a "considering" item in `infrastructure-overview.md`; this
   plan makes it concrete.

## Open questions — need answers before building, not blocking the plan existing

- **Immediate archive vs. a grace period** (e.g. archive only 30 days after delivery) in
  case a near-term correction is still needed on a just-delivered unit? Moving immediately
  is simpler; a grace period is safer against needing to "un-archive" something.
- **Should the Archived lists be read-only** for most staff, to prevent accidental edits to
  closed historical records? (Probably yes, but confirm.)
- **Does anyone need to search archived records regularly** (e.g. warranty claims
  referencing an old delivered unit)? If so, that pushes toward either a longer grace
  period, or making sure the Archived lists are easy to search/report against directly
  rather than treated as write-only cold storage.

## Relationship to the other workstreams

Depends on `Item Status`/`Order Status` existing (both already designed in
`order-items-build-plan.md`/`infrastructure-overview.md`) as the trigger conditions — no
new fields needed, just the archive lists and the two flows above.
