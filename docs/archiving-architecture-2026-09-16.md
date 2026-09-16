# Archiving architecture for the multi-list system — assessment and recommendation

**Written 2026-09-16.** Asked: what is the best archiving / long-term archiving solution for
the current multi-list SharePoint architecture, given the Power BI charts have to keep
working or be updated to work.

Builds on [`analytics-history-options.md`](analytics-history-options.md) (same day), which
ruled out a lakehouse and sized three tiers. That document is right about the big things and
this one does not relitigate them. It extends it in the two places the question has now moved
to: **the other lists** (`Order` especially, which has no archive of any kind), and **what
Power BI actually consumes** — which turns out to be the fact that decides the design.

**Headline: don't build an archive by copying rows out. Stop deleting them, and build an
immutable export for the permanent record.** Those are two different jobs and the current plan
does them with one mechanism, which is why it breaks. Reasoning below.

---

## 1. The question conflates three goals

"Archiving" has meant one thing in this project since 2026-08-12. It is really three, with
three different best answers and three different urgencies:

| | goal | driver | urgent? |
|---|---|---|---|
| **G1** | Keep the live working set small | performance, staff not wading through delivered orders | **no — see §3** |
| **G2** | Preserve history permanently | audit, disaster recovery, reproducibility | yes, and unserved |
| **G3** | Feed Power BI historical analysis | KPIs over completed work | yes, and partly broken |

`archiving-plan.md` explicitly **narrowed** itself to G1 on 2026-08-31 — "this plan is now
purely about keeping the live lists from growing unbounded, nothing else" — on the grounds
that the Excel Archive already served G2 and G3. The measurements in
[`archive-coverage-gap-2026-09-16.md`](archive-coverage-gap-2026-09-16.md) show it does not:
22 populated unit-data columns have no counterpart in it, and `Order` has no archive sheet at
all. So G2 and G3 came back, unserved, attached to a mechanism designed only for G1.

That is the whole problem. One mechanism, three jobs, and it was scoped for the least urgent
of them.

## 2. 🔑 Power BI does not read SharePoint

This is the fact that changes the design, and it is not stated in
`analytics-history-options.md`.

From `infrastructure-overview.md`'s current-state diagram and the queries themselves, the
dependency chain today is:

```
SharePoint lists ──► Power Query ──► FRM10-12.xlsx TableOrders ──► Power BI
Archive active.xlsx ──► ArchivedOrders.pq ──► ┘
```

`ArchivedOrders.pq` is literally one line:

```m
Source = ImportFromIndex("Archive active", "TableArchiveFRM10_12")
```

and the KPI model (`FRM10-12/power-bi/PriceReg.pq`) reconciles two tables — the Archive
(5,120 rows) and FRM10-12 (1,039 rows). **Power BI reads Excel. It has no SharePoint
connection in the analytics path.**

Three consequences:

1. **Deleting a SharePoint row does not break a chart today.** The charts never saw it. What
   deletion destroys is the ability to *ever* build a chart on those columns — silent, and
   invisible until someone asks for a cycle-time report.
2. **The permanent record is a live, mutable, formula-bearing, hand-edited `.xlsx`.** Against
   this repo's own history — external refs broken by shifted columns, a generic refresh wiping
   native formula columns, view-shaped exports, a blanked workbook recovered from LFS — that
   is the weakest link in the architecture, and every KPI rests on it.
3. **Anything that repoints Power BI is a real project**, not a config change — which argues
   for a design that lets the BI keep working untouched while the archive is built and proven.

The migration's stated direction (`infrastructure-overview.md`: "SharePoint as the source,
Excel/Power BI as consumers") points away from this chain. Nothing has moved it yet.

## 3. G1 is not urgent, and deletion is not the only lever

Measured from the newest exports:

| list | rows | cols |
|---|---:|---:|
| `Order Items` | 1,085 | 151 |
| `ModelChanges` | 1,553 | 23 |
| `Order` | 457 | 51 |
| `Model Revisions` | 391 | 33 |
| `Models` | 390 | 39 |
| `Clients` | 99 | 12 |
| others (`Models SA`, `ECO`, `Index`) | 131 | — |
| **total** | **~4,100** | |

Growth: units carrying a 2026 order date number **833** with the year three-quarters gone —
call it ~1,100–1,200/yr, consistent with `analytics-history-options.md`.

**So `Order Items` reaches SharePoint's 5,000 list-view threshold in roughly three and a half
years.** And the threshold is not a wall: it limits *unindexed* operations. An indexed
`Item Status` with filtered views operates far past it, and lists support millions of items.

Meanwhile the usability half of G1 — "staff wading through years of delivered orders" — is
solved by a **default view filtered to `Item Status = Active`**, which costs an hour and
deletes nothing. And it is about to become moot anyway: `roadmap.md` confirms **Monday.com
becomes the tool the production team works in day to day**, with SharePoint kept as the
authoritative database behind it. Staff will not be browsing these lists at all.

> 🔑 **Deletion is irreversible; a view is not.** G1's own deadline is years out, its usability
> half has a free fix, and the layer that made it urgent is being replaced. There is no reason
> to pay an irreversible cost for it now.

The one genuine sizing constraint is elsewhere and already flagged: `Unit Step History` at
~26 steps × ~1,200 units ≈ **31,000 rows/yr** crosses 5,000 in about two months and needs
indexed columns and filtered views from the day it is created.

## 4. Options

### A. Soft archive — status + views, no deletion

Rows stay forever. `Item Status` already distinguishes Active / Delivered / Cancelled /
Regrouped. Index it, filter the default views.

- ✅ Zero data loss, all 151 columns, automatically, including every future column.
- ✅ Nothing to build, nothing to sync, no Power BI change. Reversible.
- ✅ Completed units stay searchable in the same UI staff already use.
- ❌ Does not give an immutable record — the live list is still editable, so it cannot answer
  "what did this row say in August".
- ❌ Lists grow; revisit in ~3 years.

### B. SharePoint archive lists — copy, then delete

`Order Items Archive`, `Order Archive`, … same schema, a flow copies then deletes.

- ✅ Live lists stay small; archived rows remain queryable in SharePoint; Power BI *could*
  read them.
- ❌ **Schema drift, forever.** Every column added to a live list must be added to its twin or
  history quietly stops recording it. That is precisely the failure mode being fixed here —
  the Excel Archive is a hand-maintained subset and that is *why* it lost 22 columns.
- ❌ Doubles the list count; Power BI must union two sources per entity.
- ❌ Copy-then-delete is a two-step flow that can fail between the steps, on irreversible work.
- ❌ Still not immutable — an archive list is as editable as a live one.

`archiving-plan.md` proposed this in its original form and struck it out. **The reasons for
striking it out were good and still hold.**

### C. Dated immutable exports to a document library ⭐

A scheduled flow writes **one file per list per run** into a dated folder. Never edited,
never overwritten.

- ✅ **No schema to maintain** — exporting a whole list captures whatever columns exist,
  including the 22, including columns added next year. This is the structural difference from
  B and from the Excel Archive.
- ✅ **Covers `Order` for free**, and every other list, by the same mechanism. No per-entity
  design.
- ✅ Genuinely immutable: the permanent record stops being a mutable workbook.
- ✅ Power BI reads a folder of dated files as one table, and treats the dates as partitions.
- ✅ Doubles as disaster recovery, which nothing currently provides.
- ❌ Snapshots are state-in-time, not an event log — though the stage triples are already
  event-stamped, so the events are *inside* the snapshots.
- ❌ Needs a retention policy, or it accumulates quietly.

### D. A database / Dataverse / Fabric

Ruled out for volume in `analytics-history-options.md` and nothing here changes that. ~4,100
rows and ~3 MB. Revisit only if something genuinely bulky appears.

### E. `Unit Step History` child list

Already planned, for Monday's ~26 board groups. **Complementary, not an alternative** — it is
the right permanent home for the *step timeline* and it survives row deletion, but it does not
preserve the other unit columns. C and E solve different halves.

## 5. Recommendation — layered, cheapest adequate mechanism per goal

| goal | mechanism | effort |
|---|---|---|
| **G1** working set | Option A — index `Item Status`, filter the default views. **No deletion.** | ~1 hour |
| **G2** permanent record | Option C — dated immutable exports of every list | ~1 day |
| **G3** analytics | repoint `ArchivedOrders.pq` at the export folder, once C is proven | ~½ day |
| *(orthogonal)* | freeze published KPI results per period — `analytics-history-options.md` Tier 0 | ~1 hour |

The ordering matters more than the pieces. **Nothing destructive happens until the
non-destructive thing is built and proven**, and at no point do the charts break.

### On format — JSON, not Parquet

`analytics-history-options.md` Tier 2 proposes Parquet. Right instinct, wrong tool for the
writer available: **Power Automate has no native Parquet writer**, so Parquet means an Azure
Function, an Office Script, or a Python step — real complexity on the critical path.

`Get items` already returns JSON, losslessly, including lookups and types. Power BI reads
JSON folders natively. CSV is the worst of the three here: it loses types and walks straight
into the traps this repo has already logged — French decimal commas, lookups serialising as
`[{"@odata.type":…,"Value":"X"}]`, embedded newlines.

**Write JSON. Convert to Parquet later if volume ever justifies it** — at ~3 MB a snapshot,
it will not for years.

### On cadence — daily, and why that is not extravagant

`analytics-history-options.md` rejects daily snapshots as "~438,000 rows/year — **Don't.**
Heavy, and redundant." That is correct *if the snapshot lands in a SharePoint list*, where
rows are the cost unit. As **files in a library** it is 365 files a year at a few MB each —
low single-digit GB annually, against a tenant allowance measured in terabytes.

The cost model changes with the destination, and the conclusion changes with it. Daily also
buys the one thing that actually fixes the retroactivity problem in that document's §2:
**you can reconstruct any number you published, on the date you published it.**

Suggested retention: daily for 90 days, then keep month-end only, forever. Prune on a
schedule, not by hand.

### What this does NOT do

It does not make deletion possible tomorrow, and deliberately so. Deletion stays unwired until
the export has run for long enough to be trusted. When that day comes it is safe, because by
then the row's full content is in an immutable file — which is exactly the reconfirm-before-
delete guarantee `archiving-plan.md` already requires, finally backed by something that
carries every column.

## 6. The Power BI path

Three steps, each independently useful and independently reversible:

**BI-0 — today, unchanged.** Charts read FRM10-12 + `Archive active.xlsx`. Nothing in this
recommendation breaks them, because nothing gets deleted. This is the *point* of sequencing it
this way: there is no flag day.

**BI-1 — repoint the archive query.** `ArchivedOrders.pq` is one line. Point it at the export
folder instead of `Archive active` and the historical half of the model stops depending on a
hand-edited workbook. This is exactly what `infrastructure-overview.md` records the user as
already considering — *"switching the existing archive Power Query to pull from SharePoint
instead of FRM10-12"* — and the export makes it a better trade than repointing at a live list,
because the target is immutable.

**BI-2 — direction, not a next step.** Power BI reads SharePoint + the export archive
directly; Excel leaves the analytics path. Matches the migration's stated direction. Large;
do not start it to solve this problem.

> ⚠️ **Independent of all of the above, and worth doing on its own:** `PriceReg.pq` documents
> 394 archive rows with `[Price] = 0` and `[Price Value] = null` — **33 of 71 rows in the
> August KPI window, ~$1.0M USD** — recoverable from the `Order` list, which prices 403 of 417
> orders. That is a live reporting error today, unrelated to archiving, already diagnosed in
> the query's own comments.

## 7. Suggested order of work

1. **Confirm the cleanup flow's delete stays unwired.** Already true — stage C counts only.
2. **Index `Item Status`; filter the default views** to `Active`. Solves G1's real complaint,
   costs an hour, reversible.
3. **Build the export flow** — all lists, nightly, dated JSON folders, retention policy.
4. **Let it run and check it**, including through a schema change.
5. **BI-1**: repoint `ArchivedOrders.pq`.
6. **Only then** revisit whether deletion is wanted at all. It may simply never be.
7. **Tier 0** (freeze published KPI results) and the `Order` price-source fix — any time,
   independent of everything above.

> **→ Checked against industry practice 2026-09-16:
> [`sharepoint-as-erp-industry-check-2026-09-16.md`](sharepoint-as-erp-industry-check-2026-09-16.md).**
> The recommendation survives, and the dated-file archive gains a second, independent
> argument: **SharePoint lists are not a foldable Power BI source**, so incremental refresh
> buys nothing against a list, while a folder of dated files folds and prunes. Three changes
> come back from it:
>
> - **Add an `As of Date` column inside each snapshot file** — the community snapshot pattern's
>   own refinement, free now and painful to retrofit. Folder dates alone are not enough.
> - ~~Test the 12-lookup-column threshold.~~ **Raised and retired the same day.** The
>   parent-prefixed columns are flow-synced plain columns (`Text`/`Choice`/`Number`/…), not
>   projected lookups, so `Order Items` sits at ~7–8 of the 12. What survives is the trade it
>   reveals: ~47 columns of flow-maintained denormalised copy, the same pattern behind `x16`,
>   `x17`/`x18` and the `Status Date` erasure. It *helps* the archive case — those columns hold
>   what the parent said at the time, so a row snapshot is real history, not a live projection.
> - **Dataverse is the substrate Microsoft would steer this to**, and its long-term retention
>   ships the mechanism being hand-built here. Not recommended now — volume, cost, and an
>   in-flight cutover — but recorded with tripwires.

## 8. Decisions needed

1. **Accept "stop deleting" as the answer to G1?** This is the load-bearing one. It says the
   archive is not a place rows move to, it is a copy taken of rows that stay.
2. **Export destination and retention** — which document library, and is daily/90-day +
   month-end-forever right?
3. **Does `Unit Step History` still get built as planned?** Yes on its own merits (Monday's
   ~26 groups need a home) — but note it is no longer the *only* thing standing between the
   cleanup flow and permanent data loss, which lowers its urgency.
4. **Is `Order` ever deleted from?** If §5 is accepted, `Order` needs no archive list and no
   cleanup — it needs the same nightly export as everything else. Order `22021` (all units
   deleted 2026-09-16, order row now empty) stops being a problem to solve and becomes a row
   that sits there.

---

**Nothing in this document has been built or changed.** The measurements are reproducible from
the exports in `sharepoint-lists/` and the queries in the FRM10-12 repo.
