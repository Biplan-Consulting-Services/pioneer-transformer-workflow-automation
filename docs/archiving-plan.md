# Archiving Plan

**Status:** planned, not yet built. Elevated from "noted, not designed" to a real plan
2026-08-12 — user flagged the actual reason: without archiving, `Order`/`Order Items` grow
forever, and SharePoint's practical performance/usability degrades well before any
theoretical row-count ceiling (list view thresholds, slower filtered views, staff wading
through years of delivered/cancelled orders to find active ones).

**Redesigned 2026-08-31 — mechanism replaced, motivation narrowed.** While building
Workstream 1's reconciliation pass, the user confirmed the Excel Archive workbook (`Archive
active.xlsx`) remains the sole permanent historical record going forward — no need for a
SharePoint-side copy at all. This drops the "also serves the Power BI historical-analysis
need" half of the original motivation below (Power BI, if it ever needs historical data,
reads the Excel Archive directly, not a SharePoint copy) — this plan is now purely about
keeping the *live* `Order Items`/`Order` lists from growing unbounded, nothing else. See
"Mechanism" below for the replacement design; the original "move to a separate Archived
lists" plan is kept struck through beneath it for context, not as the current plan.

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

## Mechanism — redesigned 2026-08-31: grace period + reconfirm against Excel, then delete

**No SharePoint-side archive list at all.** Excel's Archive workbook (`Archive
active.xlsx`) already is the permanent historical record — this plan's only job is
removing rows from the *live* `Order Items`/`Order` lists once they're safely stale, not
preserving them a second time in SharePoint. Replaces the "move to a separate Archived
lists" mechanism below (kept struck through for context — superseded, not current).

- **Scheduled flow** (e.g. nightly or weekly — see open question below), not triggered on
  `Item Status`/`Order Status` change.
- Finds `Order Items` rows where `Item Status` is `Delivered` or `Cancelled` **and** the
  row's `Modified` date is at least **one month** ago — the grace period exists so a row
  isn't yanked out of SharePoint the moment it's marked done, giving time for it to still be
  visible/referenceable there if something comes up shortly after completion.
- **Reconfirms against the Excel Archive before deleting** — same check Workstream 1's
  reconciliation pass already does (pull `Archive active.xlsx`'s `TableArchiveFRM10_12`,
  match on `Order`/`Unit ID`, confirm `Location = AN` or `Location = LI` with a populated
  `Delivery Date`). Only delete the live row once that reconfirmation passes — if the
  Archive doesn't corroborate it (or the row isn't there for some reason), leave it alone
  and let a later run re-check, same fallthrough-and-retry spirit as the reconciliation
  pass's `UnresolvedUnits` log.
- **No flow writes to Excel, at all** — still true here even though the mechanism changed;
  this flow only ever *reads* the Excel Archive and deletes from SharePoint, matches the
  existing `office-scripts` fragility already documented for `TableOrders` in
  `infrastructure-overview.md`/[[pioneer-transformer-frm10-12]].

**Relationship to Workstream 1's reconciliation pass**: the reconciliation pass (built as
part of the Excel→SharePoint transfer flow) deletes immediately once it detects a unit
vanished from `TableOrders` and confirms it via the Archive — that's the mechanism for the
current, pre-cutover era where Excel is still the trigger signal. This workstream's monthly
sweep is the mechanism for the era *after* Excel is retired as the working file (once
`Item Status` starts getting set some other way — a native SharePoint/Power Automate flow,
not staff editing Excel) — there's no "vanished from TableOrders" event to react to anymore
at that point, so this instead watches `Order Items` itself directly (`Item Status` +
`Modified` staleness) and reconfirms against Excel Archive as a safety check before
deleting, the same way the reconciliation pass does. The two aren't redundant: whichever one
actually has a live signal to act on for a given row does the deleting.

## Trigger criteria — reuses fields already designed, no new fields needed

- **`Order Items` row** qualifies when `Item Status = Delivered` or `Item Status =
  Cancelled` **and** `Modified` is ≥1 month ago **and** the Excel Archive reconfirms it
  (see Mechanism above) — direct equivalent of the old `Location = LI` + `Delivery Date` /
  `Location = AN` logic, now expressed through the single `Item Status` field already
  designed in `infrastructure-overview.md`.
- **`Order` row** qualifies when `Order Status = Cancelled`, OR once **every** one of that
  order's `Order Items` rows has itself been deleted per the above (the whole order is
  fully delivered/gone) — same grace-period + reconfirm treatment, not immediate.

## Build steps

1. Scheduled Power Automate flow (nightly or weekly): pull the Excel Archive once (same
   action shape as Workstream 1's reconciliation pass); find live `Order Items` rows meeting
   the criteria above; for each, reconfirm against the pulled Archive data; **Delete item**
   on confirmed matches.
2. Same or a second scheduled flow, same pattern, for `Order` rows once all their `Order
   Items` are gone or `Order Status = Cancelled`.
3. No Power BI repoint needed — Power BI (if it ever needs historical data) reads the Excel
   Archive directly; there's no SharePoint archive list to build a report against.

## Open questions — need answers before building, not blocking the plan existing

- **Is one month the right grace period**, or should it be shorter/longer/configurable?
- **How often should the scheduled flow run** — nightly vs. weekly vs. monthly (given the
  grace period itself is a month, running more than roughly weekly is probably unnecessary).
- **Does the `Order` row treatment need the same grace period+reconfirm rigor**, or is
  deleting an `Order` once every `Order Items` row under it is gone safe to do immediately
  (no separate Excel-side signal to reconfirm against for the order-level record)? Not
  addressed explicitly when this was redesigned — worth a real answer before building.

## Relationship to the other workstreams

Depends on `Item Status`/`Order Status` existing (both already designed in
`order-items-build-plan.md`/`infrastructure-overview.md`) as the trigger conditions, and on
Workstream 1's reconciliation-pass Excel-Archive-pull logic being reusable here (same
pattern, not a shared action) — no new fields needed.

## Superseded 2026-08-31 — original "move to separate Archived lists" mechanism, kept for context

<details>
<summary>Original plan (2026-08-12), replaced by the grace-period design above</summary>

Two ways were considered for keeping the live lists bounded:

- **(a) Move** — a Power Automate flow copies the row to a separate `Archived Order
  Items`/`Archived Orders` list once it qualifies, then deletes it from the live list.
- **(b) Flag in place** — add an `Archived` Yes/No (or reuse `Item Status`/`Order Status`)
  and rely on a filtered default view to hide archived rows. Only fixes view clutter, not
  actual row count.

(a) was recommended and designed in detail: scheduled flow, copy into a new `Archived
Order Items`/`Archived Orders` list, verify the copy matches, only then delete the live
row — mirroring Pioneer's existing Excel archive-refresh pattern (check-before-remove, not
event-triggered). Build steps included creating the two new lists via SharePoint's
save-as-template feature, and repointing Power BI/FRM10-12's `ArchivedOrders` reference at
the new lists.

**Why this was replaced**: it assumed SharePoint needed to become the historical record
(serving a Power BI need). The user confirmed 2026-08-31 that Excel's Archive workbook is
fine as the sole permanent record going forward — building and maintaining a second,
SharePoint-side copy of the same historical data was solving a problem that didn't need
solving. The open questions this original plan raised (should Archived lists be read-only,
does anyone need to search them regularly) are moot now that no such lists get built.

</details>
