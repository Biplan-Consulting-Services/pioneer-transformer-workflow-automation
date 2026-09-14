# Estimated Delivery Date — solving the `TODAY()` freeze with column formatting

Written 2026-09-14. Setup guide. `calculated-columns-plan.md` is still the analysis of
*what the formula is and where it should live*; this is how the `TODAY()` half of it
actually gets built, and it supersedes that doc's nightly-touch decision.

---

## The problem, in one line

A SharePoint calculated column evaluates `TODAY()` **when the item is written and never
again**. The value freezes at last save and drifts a day further out of date every day
after — and a row that looks correct today is not evidence, because that row was written
today. This is by design in SharePoint Online, not a bug to work around.

## The two workarounds, scored against this project

| | what it is | verdict here |
|---|---|---|
| **Daily Power Automate touch** | a scheduled flow rewrites rows so SharePoint re-evaluates | ❌ **dead, and measured dead.** The 2026-09-11 nightly-cleanup build measured the touch pass at **915 of 1,189 rows a night** — `calculated-columns-plan.md:548` claimed its filter cut the work ~50×; against the live list it cuts it **1.3×**, because an Active unit has no delivery date *by definition*. That is ~334,000 versions a year and ~1,830 actions a night against a 2,000/day allowance, which would starve the five event-triggered flows. |
| **JSON column formatting with `@now`** | the browser evaluates the formula at render time | ✅ **this.** Never stale, no flow, no writes, no versions, no allowance. |

**The trade, stated plainly: column formatting *displays* a value, it does not *store*
one.** The column stays empty. So the estimate cannot be **sorted, filtered, grouped,
exported to Excel, read by Power Query, or picked up by the BO Report** — which is a
view-bound Export-to-Excel web query and so exports the stored value, i.e. nothing.

## Which is fine, because the workbook side does not need the list to store it

The viewer already rebuilds `TableOrders` in Power Query. It can compute this same
formula in M against `DateTime.LocalNow()` and get a genuinely live value on every
refresh — also for free, also with no flow. So:

| consumer | where the estimate comes from |
|---|---|
| staff reading the SharePoint list | **column formatting** (this doc) |
| FRM10-12 viewer, FRM11, FRM13, BO Manager | **Power Query in the viewer** (not built yet) |
| sorting / filtering a SharePoint **view** by the estimate | ⚠️ **nothing covers this** — see the open question at the bottom |

---

## Part 1 · Create the column

The list has **no `Estimated Delivery Date` column at all** today — `roadmap 20` says
buildable, not built, and the nightly-cleanup build confirmed it against the live list.

1. `Order Items` → **Add column** → **Single line of text**.
2. Name it **`Estimated Delivery Date`**.
3. Leave everything else default. **Never type anything into it** — it stays empty on
   every row, forever. The formatting draws over it.

> **Why a Text column and not a Date column.** The formatting emits a formatted date
> *string*, and on the eight-branch fallback it emits the literal `no order` or
> `defaut formule`. A Date column would also invite someone to sort by it, which would
> sort 1,189 identical blanks and quietly look like it worked.

## Part 2 · Apply the formatting

1. Click the column header → **Column settings** → **Format this column**.
2. Choose **Advanced mode** (the link at the bottom of the pane).
3. Replace everything in the box with the contents of:

   ```
   sharepoint-lists/formatting/EstimatedDeliveryDate.format.json
   ```

4. **Preview**, then **Save**.

Regenerate it at any time — never hand-edit the JSON, edit the generator:

```bash
python scripts/gen_estimated_delivery_format.py
```

It refuses to emit JSON that reads a field it does not declare, that reads either of the
two completion-stamp columns named below, or that leaves a paren open.

## Part 3 · Check it

1. Pick a unit whose **Tanking Date is in the past** and which has **no Delivery Date** —
   that is the population where `TODAY()` is the thing doing the work.
2. The cell should read **today + 14 days** (+30 more if `BO` is not `OK`/blank).
3. Come back tomorrow without touching the row. **It should read tomorrow + 14.** That
   single observation is the whole point — it is what a calculated column cannot do.
4. Check a delivered unit (branch 1) and a brand-new one with only an Order Date
   (branch 7) to confirm the non-`TODAY()` branches agree with FRM10-12.

---

## Two field-mapping traps this formula walks into

Both are settled by the viewer's `ColumnMap.pq`, verified value-for-value at cutover
(18,946 values, 3 differences, all understood). **The workbook column names do not map to
the same-sounding SharePoint columns:**

| workbook column | SharePoint internal name | NOT |
|---|---|---|
| `Delivery Date` | `Planned_x0020_Delivery_x0020_Dat` | ~~`DeliveryDate`~~ |
| `Tanking Date` | `Planned_x0020_Tanking_x0020_Date` | ~~`TankingDate`~~ |

`DeliveryDate` ("Delivery End Date") and `TankingDate` ("Tanking End Date") are the
**completion stamps**, and neither has a workbook column at all. The columns staff have
always typed into are the **planning** dates. Mapping by name would silently compute a
different formula on all 1,189 rows and still look entirely plausible.

🔴 **Consequence worth checking before anyone leans on it.**
`calculated-columns-plan.md`'s 2026-08-31 impact table — the one that concludes
`TODAY()` only matters for **21 rows** — labels its rows *"Delivery End Date"* and
*"Tanking End Date"*. If it really counted those columns, it measured the completion
stamps rather than the planning dates the formula reads, and the 21 is about a different
population. **Raised rather than corrected**: re-measure before that number is used to
argue this is a small problem.

## One deliberate difference from the workbook

Branch 7 is `Order Date + 90 + LeadTime × 7`. Excel gets the lead time from
`XLOOKUP(Client, ClientLeadTimes, …, 52)` — a **52-week** default for a client missing
from the table. `calculated-columns-plan.md` settled that this contradicts FRM13's own
`GENERIC VALUE` of **26 SEM**, and should be retired. The lead time is already synced onto
`Order Items` as `CliLeadTimeWeeks`, so the formatting reads that column and falls back to
**26**, not 52. It is `GENERIC_WEEKS` at the top of the generator.

## One quirk preserved on purpose

Branch 6's **condition** tests only `Coiling..Drying`, but its **value** also maxes in
`Tank Delivery Date`. So a unit with a Tank Delivery Date and no other milestone falls
through to branch 7 and never sees it. That is what the workbook does. If it is wrong it
is wrong in Excel too, and should be fixed in both or neither.

---

## Open question — does anything need to **sort or filter** a view by this?

This is the one thing neither half covers, and it is the question the 2026-09-11
nightly-cleanup build left open in the same words: *"either a plain column the flow owns,
written only on change, or not stored at all and computed in Power Query / DAX — the
deciding question is whether anything needs to sort or filter a list view by it."*

- **No** → done. Column formatting plus the viewer's Power Query cover every consumer,
  at zero cost, with nothing to maintain.
- **Yes** → a real stored column is needed, and the honest cost is a write. Not the dead
  nightly touch, though: fold the computation into the **`Order Items` create-or-update
  trigger flow** (which already guards against self-retrigger and only writes on change),
  and add a small daily recurrence for the rows a create-or-update trigger structurally
  cannot reach — units stalled in production, whose milestone is in the past and whose
  estimate therefore moves without anyone editing them. That is ~21 rows a day by the
  2026-08-31 count, not 915 — **subject to the re-measure flagged above.**
