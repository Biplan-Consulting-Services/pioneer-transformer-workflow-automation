# Covering every list in the Excel archive

**Decided 2026-09-16: archiving stays in Excel for now.** The SharePoint-side redesign in
[`archiving-architecture-2026-09-16.md`](archiving-architecture-2026-09-16.md) is parked, not
withdrawn. This document is the narrow job that remains: **make `Archive active.xlsx` cover
all the lists, not four workbooks.**

🔑 **The good news is that the mechanism to do it already exists and generalises.** Almost
nothing new has to be invented — one function, one constant, and one three-line query per list.

---

## What the archive does today

Four sheets, each one line of M:

```m
Archive BO        = TrackRemoteTable("BO Manager", "TableBO",        "TableArchiveBO",         "Order")
Archive FRM10-12  = TrackRemoteTable("FRM10-12",   "TableOrders",    "TableArchiveFRM10_12",   "Order")
Archive FRM11     = TrackRemoteTable("FRM11",      "TableFournTank", "TableArchiveFRM11",      "NUMÉRO DE CUVE")
Archive FRM13     = …
```

`TrackRemoteTable(RemoteFileIndex, RemoteTable, LocalTable, PrimaryKey)` reads a table out of
another **workbook** (resolved through the `Index` SharePoint list), then:

1. **anti-joins** the local archive against the source on the key — keeping local rows whose
   key is *no longer in the source*. That is what makes it an archive and not a mirror: a row
   that leaves the live system stays here forever.
2. **stamps** every source row with `Last Synchronisation Date` = today.
3. combines, de-duplicates on the key, and enforces number/date formats.

### 🔑 It is already schema-adaptive, and that changes the problem

```m
#"Removed Remote Columns" = List.Difference(#"Local Columns",  #"Remote Columns"),
#"Added Remote Columns"   = List.Difference(#"Remote Columns", #"Local Columns"),
```

Columns the source has that the archive lacks are **added**. Columns the source has dropped are
**retained** as nulls. So an archive built this way never needs a hand-maintained column list.

**That reframes the finding in
[`archive-coverage-gap-2026-09-16.md`](archive-coverage-gap-2026-09-16.md).** The 22 missing
`Order Items` columns were never a limitation of this machinery. They are missing because
`Archive FRM10-12` tracks **FRM10-12's `TableOrders`** — a different, narrower table that
happens to describe the same units. Point a tracker at the **list** and all 151 columns arrive,
along with every column added in future, for free.

## What is missing, and why it is only one function

The four tracked sources are all **workbook tables**. The lists that exist only in SharePoint
have no workbook to be tracked through, so they are simply absent — `Order`, `Models`,
`Model Revisions`, `Clients`, `ModelChanges`, `Models SA`, `EngineeringChangeOrders`, and
`Order Items` as itself.

But the source is **one line** of `TrackRemoteTable`; everything after it is source-agnostic:

```m
Source = ImportFromIndex(RemoteFileIndex, RemoteTable),   // <- the only coupling
```

So: lift the accumulate logic into its own function, and give it a second front door.

| new query | what it is |
|---|---|
| `AccumulateIntoLocal` | the existing merge/anti-join/stamp logic, unchanged, taking a source **table** instead of fetching one |
| `TrackRemoteList` | `SharePoint.Tables` → `FlattenSharePointLookupLists` → `AccumulateIntoLocal` |
| `ArchiveListMetaColumns` | which SharePoint UI columns to drop — **the archive's own list, not FRM10-12's** |
| `FlattenSharePointLookupLists` | copied from FRM10-12; lookups arrive as nested records |
| `Archive <List>` × 8 | three lines each |

All authored in `power-query/Archive-active/`. **Nothing has been applied to the workbook.**

## The eight queries, and the keys they use

The key is the one decision per list that can quietly destroy data, because
`Table.Distinct(combined, PrimaryKey)` drops duplicate keys **silently** — no error, just fewer
archived rows — and a *null* key cannot match in the anti-join, so such a row is re-added on
every refresh instead of being recognised.

So every key below was **measured** against the newest export: 100% populated **and** 100%
distinct. None was assumed.

| list | rows | key | local table |
|---|---:|---|---|
| `Order Items` | 1,085 | `Title` | `TableArchiveOrderItems` |
| `Order` | 457 | `Order Number` | `TableArchiveOrder` |
| `Models` | 390 | `Model_ID` | `TableArchiveModels` |
| `Model Revisions` | 391 | **`ID`** ⚠️ | `TableArchiveModelRevisions` |
| `Clients` | 99 | `Client_ID` | `TableArchiveClients` |
| `ModelChanges` | 1,553 | `MC_ID` | `TableArchiveModelChanges` |
| `Models SA` | 15 | `Model_ID` | `TableArchiveModelsSA` |
| `EngineeringChangeOrders` | 92 | `ECO_ID` | `TableArchiveECO` |

⚠️ **`Model Revisions` is the one exception.** Its natural key `Model_Revion_ID` (the typo is
in the column name) is unique but **blank on 1 of 391 rows**, and one null key is enough to
make that row immortal — never matched, re-added every refresh. It uses the SharePoint `ID`
until that blank is filled, at which point it can move to the natural key.

## Gotchas that will bite, in the order they will bite

1. 🔴 **Do not reuse `SharepointListMetaColumns` from FRM10-12.** It strips 23 columns
   including `ID`, `Title`, `Created`, `Modified`, `Created By` and `Modified By`. Right for a
   working table; fatal here — it removes the key on two lists and every scrap of provenance an
   archive exists to keep. `ArchiveListMetaColumns` drops 15 purely-UI columns and nothing else.

2. 🔴 **The first refresh of a new archive table is the dangerous one.** `AccumulateIntoLocal`
   reads the local table it writes back to. On the first run the table does not exist, and the
   `otherwise null` fallback seeds it from the source's own columns — correct, but it means the
   archive is only ever as complete as its first successful run plus everything since. **Create
   each table from a full, All-Items-sourced refresh, and confirm the row count before trusting
   it.** A view-shaped or partial first read becomes the archive's baseline permanently.

3. ⚠️ **These are self-referencing queries** — the same shape that makes `Refresh All` destroy
   FRM10-12's native formula columns. The failure mode here is different (no native formulas to
   lose) but the caution transfers: refresh deliberately, one query at a time on first build,
   and snapshot the workbook before the first run.

4. ⚠️ **`Implementation = "2.0"`** on `SharePoint.Tables` is not cosmetic — the legacy endpoint
   pages 100 rows at a time. Already logged against the in-loop `Get items` queries in
   `roadmap.md` item 43.

5. ⚠️ **Calculated columns export blank but read fine over REST** (CLAUDE.md). `SharePoint.Tables`
   is a REST read, so they should populate — but check `Bo Sort Date` on the first run rather
   than assuming, since the key-measurement above came from exports, which are blind to them.

6. ⚠️ **Lookup columns are absent from CSV exports entirely** (CLAUDE.md, measured twice). The
   key measurements therefore could not consider lookup columns as candidates. That is fine —
   no lookup was wanted as a key — but it means the archive will gain columns on first refresh
   that no export has ever shown.

## Applying it

Existing tooling, no new scripts:

```powershell
# dry run first — it lists what it would change
powershell -File FRM10-12/scripts/Sync-PowerQuery.ps1 `
    -WorkbookPath "...\linked-workbooks\Archive active.xlsx"

# then -Apply, and -AllowNew for the queries that do not exist yet
```

Order of operations:

1. **Snapshot `Archive active.xlsx`** (it is LFS-tracked; commit the copy first).
2. Sync the four support queries — `AccumulateIntoLocal`, `TrackRemoteList`,
   `ArchiveListMetaColumns`, `FlattenSharePointLookupLists`. Nothing uses them yet, so this
   cannot change existing behaviour.
3. Add **one** list — `Order` is the best first, it has no archive today and nothing depends on
   it — load it to a new sheet, refresh, and check the row count is 457.
4. Repeat per list. `Order Items` last: it is the biggest and the one with a column-count claim
   to verify (expect ~151, not 93).
5. Leave `TrackRemoteTable` alone.

### Follow-up, deliberately not done here

`TrackRemoteTable` now duplicates the logic that lives in `AccumulateIntoLocal`. It should be
reduced to its source line plus a call:

```m
Source = ImportFromIndex(RemoteFileIndex, RemoteTable),
Accumulated = AccumulateIntoLocal(Source, LocalTable, PrimaryKey)
```

Behaviourally identical, and it removes the duplication. **Not done in this pass** because four
production archive sheets depend on it and there is no reason to touch them in the same change
that adds eight new ones. Do it after the new sheets are proven.

## What this does and does not solve

**Does:** every list gets an archive; `Order` gets one for the first time; `Order Items` gets
all 151 columns including the 22; new columns are picked up automatically from then on; the
reconfirm-before-delete step in `archiving-plan.md` finally has something complete to read.

**Does not:** the permanent record is still a mutable, hand-edited, formula-bearing `.xlsx`,
and Power BI still reads it through FRM10-12. Those are the parked questions, and they are
parked — not answered.

⚠️ **The M in this folder is authored, not tested.** It has never been run against the workbook.
Treat the first refresh of each query as the test.
