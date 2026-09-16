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

🔴 **The MECHANISM below is under review as of 2026-09-16 — see
[`archiving-architecture-2026-09-16.md`](archiving-architecture-2026-09-16.md).** It
recommends not deleting at all: an indexed `Item Status` with filtered views answers the
"live lists grow forever" motivation for years at zero risk, while a nightly immutable export
of every list becomes the permanent record. If that is accepted, this plan's copy/delete
mechanism is replaced rather than repaired, and `Order` needs neither an archive list nor a
cleanup.

🔴 **The premise below is in question as of 2026-09-16 — read
[`archive-coverage-gap-2026-09-16.md`](archive-coverage-gap-2026-09-16.md) before wiring
any delete.** "Excel already holds everything" was true when `Order Items` mirrored
`TableOrders`. It no longer is: **22 populated unit-data columns have no counterpart in the
archive workbook** — every step `Status`, `Item Status`, `Step Status`, and the
hand-entered `Status Date` among them — and `Order` has no archive at all. Deleting a row
destroys them. The 7-day grace makes that reachable in a week rather than a month.

**No SharePoint-side archive list at all.** Excel's Archive workbook (`Archive
active.xlsx`) already is the permanent historical record — this plan's only job is
removing rows from the *live* `Order Items`/`Order` lists once they're safely stale, not
preserving them a second time in SharePoint. Replaces the "move to a separate Archived
lists" mechanism below (kept struck through for context — superseded, not current).

- **Scheduled flow** (e.g. nightly or weekly — see open question below), not triggered on
  `Item Status`/`Order Status` change.
- Finds `Order Items` rows where `Item Status` is `Delivered` and the row's **delivery
  date** (`DeliveryDate` = `Delivery End Date`) is at least **7 days** ago, or `Cancelled`
  and its `Modified` date is at least 7 days ago — the grace period exists so a row isn't
  yanked out of SharePoint the moment it's marked done, giving time for it to still be
  visible/referenceable there if something comes up shortly after completion.
  *(Revised 2026-09-16 from "one month, measured on `Modified`" — see the answered
  questions below for why both halves of that changed.)*
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

- ~~**Is one month the right grace period**, or should it be shorter/longer/configurable?~~
  **ANSWERED 2026-09-16: 7 days.** `GRACE_DAYS` in `gen_nightly_cleanup.py` updated and the
  definition regenerated; the only changes are C1's `$filter` and C2's reported `graceDays`.

- ~~**What does the grace period measure from?**~~ **ANSWERED 2026-09-16: the delivery
  date (`DeliveryDate`, the list's `Delivery End Date`), not `Modified`.**

  The 7-day grace made the old clock untenable. `Modified` recorded when a row was last
  *touched*, so routine housekeeping reset it: measured the day this was decided, every
  already-`Delivered` row sat within **1.5 days** of the threshold — the `E21010`/`E21014`
  rows within **0.4 days** — purely because the 09-09/09-10 migration passes had touched
  them, though the units were delivered 62, 20 and 16 days earlier. The sweep could have
  been deferred indefinitely with nothing visibly wrong.

  🔑 `DeliveryDate` is written by delivery and never rewritten, so the failure mode is
  removed rather than guarded against. Verified on the 11 rows retired 2026-09-16: all 11
  matched `Archive active.xlsx`'s `Delivery Date` exactly. Stage A keys on the same
  column, so the two stages agree by construction.

  ⚠️ **`Cancelled` rows keep the `Modified` clock** — a cancelled unit has no delivery
  date (73 of the archive's 116 `AN` units carry none), so C1 is two clauses, one per
  status. There are 0 `Cancelled` rows today; a single-clause filter would have looked
  correct until the first one aged out.
- ~~**How often should the scheduled flow run** — nightly vs. weekly vs. monthly.~~
  **ANSWERED 2026-09-16: nightly.** The old reasoning ("the grace period itself is a month,
  so running more than roughly weekly is probably unnecessary") assumed 30 days; against a
  7-day grace a weekly sweep makes a row wait up to 14. No code change — stage C already
  runs inside `Nightly Cleanup`, whose trigger is daily at 01:00 Eastern.
- 🔴 **NEW, 2026-09-16 — where do the 22 unit-data columns go when the row is deleted?**
  Blocking: the delete cannot be wired until this is answered. Three shapes, none chosen —
  a SharePoint archive list (what this plan ruled out, on a premise that has since
  changed), widening the Excel archive (means writing to Excel, which this plan forbids),
  or accepting the loss column by column and writing down which. See
  [`archive-coverage-gap-2026-09-16.md`](archive-coverage-gap-2026-09-16.md) for the
  measurements and for the pending — not yet realised — BO question.
- 🔴 **NEW, 2026-09-16 — `Order` needs an archive before it can have a cleanup.** There is
  no `Order` sheet in `Archive active.xlsx`, so the reconfirm-before-delete step this plan
  requires has nothing to read for an order. Order `22021` is the first live case: all its
  units were deleted on 2026-09-16 and the order row now has nothing under it.
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
