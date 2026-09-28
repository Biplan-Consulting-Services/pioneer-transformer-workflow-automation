# Archive active Power Query review (agent C, 2026-09-28)

Scope: every query in `power-query/Archive-active/`. This is agent C's review from the plan
`~/.claude/plans/rerunning-the-dry-run-snug-lighthouse.md` (section C). It covers:
- agent A's reader: `SP_*`, `ArchiveFetch`, `ArchiveTyped`, `ArchiveList`, the five `Archive <List>`, `TrackRemoteList`, `Apply-ArchivePowerQuery.ps1`;
- agent B's FRM10-12 adapter: `Archive FRM10-12`, `ArchiveFrm1012*`, `ArchiveLocal*`, `ArchiveBOConflicts`, and the vocabulary copies;
- the legacy live queries, for context only.

There was no Excel and no COM in this review. Every edit below still has to be proven in the integration run.
- **Static checks run after the edits:**
  - `check_frm1012_map.py --base "<BASE 2356>"`: ALL CHECKS PASS.
  - `test_check_frm1012_map.py`: ALL PASS.
  - `test_check_archive_rebuild.py`: ALL PASS.
  - A bracket and `let`/`in` balance scan of every `.pq`: clean. The one hit, `Index.pq`, is the untouched live query.
- **Evidence read straight from the files:**
  - the BASE and WORK copies' DataMashup: query list, and the permissions part `FirewallEnabled=true`;
  - `xl/connections.xml` and the queryTables;
  - the live mirror's `Columns.csv` / `Order Items.csv`.

## 1. Findings

Severity:
- **H**: silent loss of archive data is possible.
- **M**: wrong or silent under a plausible failure.
- **L**: performance, hygiene, or on-paper only.
- **I**: information only.

| # | Sev | File (step) | Issue | Fix | Status |
|--|--|--|--|--|--|
| 1 | H | `Archive FRM10-12` (`Accumulated`) | `AccumulateIntoLocal` reads `TableArchiveFRM10_12` inside `try … otherwise null`. A failed read (a privacy/firewall error, a renamed table) would silently rebuild the archive **from SharePoint alone**. That drops every unit already deleted from Order Items, and those are exactly the rows the Nightly Sync gate looks for. `ArchiveList` already guards against this. The FRM10-12 adapter did not. | New steps `Local`/`LocalKeys`: the table is read by name first, **without try**. If it is missing, `ArchiveFRM10_12.NoLocalTable`. If it is unreadable, the error propagates. | **fixed** |
| 2 | H | `ArchiveLocalTable` (`Found`) | The same `try … otherwise null`, on `TableArchiveFRM10_12` (through `ArchiveFrm1012Previous`) and on `TableArchiveBO`. An unreadable table turned into "no previous values". That silently nulls the 12 `legacy` columns and the BO history of every unit still on SharePoint. | The table's existence is tested with `List.Contains(Excel.CurrentWorkbook()[Name], …)`, then it is read without try. A missing table still means empty, as designed for `TableArchiveBO`'s removal. The key's `Text.From` now passes `"en-US"`. | **fixed** |
| 3 | M | `Archive FRM10-12` (after `AccumulateIntoLocal`) | Its final `Table.Distinct(…, "Order")` drops rows **silently**. Several blank-`Order` rows collapse into one, and a hand-made duplicate vanishes. The base has exactly 1 blank-`Order` row today. | `ArchiveFRM10_12.RowsDropped` guard: expected rows = the units SharePoint sends + every local row whose Order it no longer sends (`List.RemoveItems`, nulls counted). This is `ArchiveList`'s `Expected` check. FRM11/FRM13/BO are untouched: they go through `TrackRemoteTable`. | **fixed** |
| 4 | M | `Archive FRM10-12` (end) | The header promised that "a value that cannot take its type becomes a cell ERROR, never a silent null". But Excel loads a cell error as an **empty cell** and reports success. So `BadValue` would reach the Nightly Sync as a blank. | `Out` step: `Table.SelectRowsWithErrors` → the refresh fails with `ArchiveFRM10_12.CellErrors`, naming the first Order, the columns and the message. This is `ArchiveList`'s rule. A failed refresh leaves the table as it was. The base has 0 error cells in FRM10-12 and BO, so nothing pre-existing trips it. | **fixed** |
| 5 | M | `ArchiveFrm1012Source` (`Rows`) | Unbuffered, yet `Archive FRM10-12` enumerates it 3 or more times: AccumulateIntoLocal's anti-join, its stamp step, `SentKeys`, and the new guard. Each pass re-ran `BuildRow`'s 111 rules over every unit. It is CPU only: `Joined` is buffered, so there is no HTTP. | `Table.Buffer(...)` around the output. | **fixed** |
| 6 | L | `ArchiveFrm1012Joined` (`UnitsRaw`, `Checked`) | The typed Order Items table was enumerated by the duplicate check, the joins and the count. `Checked` counted the unbuffered join and then buffered it, so every join ran twice. | `UnitsRaw = Table.Buffer(...)`. `Result = Table.Buffer(WithPrevious)`, and the counts are taken on `Result`. The `Joins` block is unchanged, since the checker parses it. | **fixed** |
| 7 | L | B's files | Culture-dependent conversions: `Number.From(text)` in `ToDate`/`AsDate`, `Text.From(int)` in `Iso`, the status day/month and the keys. They are integer-only in practice, so today they would behave the same under fr-CA. | `Number.FromText(…, "en-US")`, `Text.From(…, "en-US")`, `Iso` = `Date.ToText(d, [Format="yyyy-MM-dd", Culture="en-US"])`, and `TransformColumnTypes(…, "en-US")`. `numtext` stays deliberately `fr-CA` (it is explicit). | **fixed** |
| 8 | I | `ArchiveFetch` (comment) | The comment said "five tables = up to five evaluations; the web cache may serve the repeats". There are six loaded tables, and the cache cannot be relied on. The real count is in §2. | Comment rewritten. This is agent A's file, and only the comment changed. | **fixed** |
| 9 | L | `ArchiveList` (`Remote`) | `ArchiveTyped(title)` is not buffered and is enumerated 3 times: `RemoteIds`, and twice inside `AccumulateIntoLocal`. Each pass re-runs lookup resolution, JSON and typing. It is CPU only. | `Remote = Table.Buffer(ArchiveTyped(title))`. `Value.Type` survives a buffer. | proposed (A's file, verified in Excel; a perf-only change) |
| 10 | L | `ArchiveTyped` (`Infer`) | Every `infer`-kind column runs `Table.Column(Flat, col)` on an unbuffered `Flat`, which is one full pass of steps 1–3 per inferred column. | `Flat = Table.Buffer(Table.TransformColumns(...))` | proposed |
| 11 | L | `ArchiveTyped` (`AddLookup` map, `Resolve`, `UserMap`, `ToText`) | `Text.From(v)` has no culture. Today it only ever sees integers: Ids, and `Order_x0020_Number1`, the show field of `OrderNumber`. So nothing changes, but a decimal show field or a number in a text column would come out `24,9` under fr-CA. | `Text.From(v, "en-US")` in those five spots. | proposed |
| 12 | L | `ArchiveTyped` (`TargetRows`) | `AppAuthor`/`AppEditor` are lookups to `AppPrincipals`, which is not a site list, on all five lists (mirror `Columns.csv`). They are skipped today only because REST items do not carry `AppAuthorId`. If they ever do, the fallback `SP_ItemsRaw("lists(guid'…')")` would 404 and fail the refresh. That fails loudly, but for no reason. | In `TargetRows`, a `listId` that is not in `Fetch[TitleById]` gets no display column. Leave the Id raw. | proposed |
| 13 | L | `EnforceFormats` (legacy, via `AccumulateIntoLocal`) | It does a per-cell pass that is an **identity**: `digitGroupSeparator` is `""`, so `Text.Contains` is always true, and the replaces are `""→""` and `"."→"."`. It also **strips every column type**. The logic is inverted too: it runs when Enforced = Display, which is when there is nothing to do. The cost is about 590k cells for FRM10-12, a few seconds. | **Leave it.** It is shared with FRM11/FRM13/BO through `TrackRemoteTable`, and both new callers re-type afterwards. If it is ever touched, skip the call in `AccumulateIntoLocal` rather than editing `EnforceFormats`. | proposed: no change |
| 14 | M | `Apply-ArchivePowerQuery.ps1` l.223 | Tables loaded through the **Data Model** (`TableArchiveFRM10_12`, via `ModelConnection_ExternalData_1`) are refreshed with `$lo.TableObject.Refresh()`. Nothing proves that this re-runs the Power Query, or that an M error surfaces as a COM exception. If it doesn't, a failed `Archive FRM10-12` refresh leaves the rows unchanged. That is not "shrank", so the script would **save as success**. That matters now that #1–#4 fail loudly by design. | After each refresh, require proof that the query ran: for a table with `Last Synchronisation Date`, its max must equal today. Also refresh the `Query - Archive FRM10-12` workbook connection explicitly before the TableObject. | proposed (A's file) |
| 15 | M | workbook setting | Formula.Firewall: see §3. It works on this PC as measured. It is setting-dependent elsewhere. | Set `Queries.FastCombine = $true` on the copy in the integration run (user decision). | proposed |
| 16 | L | `AccumulateIntoLocal` (`Today`) | `DateTime.LocalNow()` is the machine's date. That is right on desktop Excel in Eastern time, DST included, since only the date is used. A cloud refresh (Excel for the web, where the refresher's `refreshAllDataConnections` could run) would be UTC and would stamp tomorrow between 19:00/20:00 and 24:00 ET. Whether Excel for the web can refresh `Web.Contents` + Organizational at all is also untested. | Refresh only in desktop Excel (go-live step 3 already says so). If web refresh is ever needed, compute the Eastern date explicitly. The same is true of the live `TrackRemoteTable`. | proposed |
| 17 | L | `Query1` (workbook + `.pq`) | **Dead, confirmed:** <br>- nothing references it (repo grep); <br>- it is not loaded: its connection `Query - Query1` has no queryTable, and the Data Model's only model connections are `Archive FRM10-12` and `Archive FRM11`; <br>- its body is an inline copy of `TrackRemoteTable` aimed at `TableArchiveFRM10_12`, minus `EnforceFormats`. <br>If anything evaluates it, it downloads the whole viewer workbook for nothing. | Delete the query from the workbook in the integration run (`$wb.Queries.Item("Query1").Delete()`), then delete `Query1.pq`. | proposed |
| 18 | L | workbook connection `Query - Query2` | An **orphan connection**: there is no `Query2` query in Archive active's mashup (BASE or WORK), only the connection. This is not FRM10-12's `Query2`, which is a reader in another workbook. | Delete the connection (`$wb.Connections.Item("Query - Query2").Delete()`). | proposed |
| 19 | L | 09-16 drafts | `Archive EngineeringChangeOrders`, `Archive ModelChanges`, `Archive Models SA` call `TrackRemoteList` with natural keys. `TrackRemoteList` now errors on any key but `Id`, so they are dead (never in the workbook; A1 dropped them). The same goes for `TrackRemoteList` itself (0 callers), `FlattenSharePointLookupLists` (no `// Query:` header, 0 references) and `ArchiveListMetaColumns` (0 references). | Move all six to `power-query/Archive-active/_obsolete/`. The Apply script reads `*.pq` from the folder without recursing, and its `-Queries` is an explicit list, so the move is safe. It was not done here, so that the lead's pathspec commit is not surprised. | proposed |
| 20 | I | `SortBySortKeys` (legacy live) | It is in the live workbook, but nothing in Archive active references it. | Leave it (legacy). It can be deleted with `Query1`. | info |
| 21 | L | `Archive FRM10-12` (`Backfilled`) | 19 chained `Table.ReplaceValue` passes, one per BO column, over about 5,300 rows. That is correct and cheap enough. | It could be a single `Table.TransformRows`. Not worth the risk. | no change |
| 22 | I | `ArchiveFrm1012Joined` (`Units`) | 2 Order Items rows have a blank `Title` (live mirror). They are dropped from FRM10-12 by design, because the recipe says to drop blank Title and they cannot be keyed. They **are** archived by `Id` in `TableArchiveOrderItems`. | none | info |
| 23 | I | `Archive FRM10-12` (`AsDateText`) | Taking the first 10 characters of an ISO datetime is right for `EstimatedDeliveryDate` only because SharePoint's calculated value is local midnight (`T04:00Z`/`T05:00Z`). A datetime with a real time near midnight would give the UTC date. No other datetext column comes from a datetime. | none | info |
| 24 | I | buffers | `Table.Buffer` over a table with cell errors either keeps them (and then the guards in #4 and `ArchiveList` report them) or raises. Both outcomes are loud. | none | info |

Checked and fine:
- `SP_Json` uses a static base URL plus `RelativePath`/`Query`, so there is one credential and no dynamic-source error.
- `SP_ItemsRaw` refuses to truncate: it errors on `odata.nextLink` and on a zero-row read.
- `ArchiveTyped` reads a date-only value as its first 10 characters. That is correct for T00/T04/T05Z, DST included, and culture-free.
- The joins are on buffered parents with Int64 keys, with a row-multiplication guard.
- `ArchiveLocalTable` errors on duplicate keys.
- `ArchiveList` checks null and duplicate Ids, the row count and cell errors.

## 2. HTTP reads per refresh

Power Query evaluates each **loaded** table separately. Nothing is shared between those evaluations, and `Apply-ArchivePowerQuery.ps1` refreshes one table at a time. Within one evaluation, `ArchiveFetch`'s record fields are lazy and memoised, and each list's items are `Table.Buffer`ed. So within a table's refresh, each list is read **at most once**, however many lookups reuse it.

Every evaluation makes one `_api/web/lists` read (list GUIDs) and one `_api/web/siteusers` read, because every list has `AuthorId`/`EditorId`. On top of that, it makes one `_api/v2.0/…/columns` read per list it **types**, and one `…/items` read per list it types **or resolves a lookup into**. Lookup targets are from the live `Columns.csv`, counting only lookups whose `<Name>Id` appears in REST items.

| Table refreshed | Lists typed | Extra lists read for lookups | GETs |
|---|---|---|---|
| `Archive Clients` | Clients | none | 1+1+1+1 = **4** |
| `Archive Models` | Models | Clients, Model Revisions (and Models itself for ParentModel) | 1+1+1+3 = **6** |
| `Archive Model Revisions` | Model Revisions | Clients, Order (DuplicateOrder), Models (`ModelId2`) | 1+1+1+4 = **7** |
| `Archive Order` | Order | Clients, Models, Model Revisions | 1+1+1+4 = **7** |
| `Archive Order Items` | Order Items | Order, Models, Model Revisions, Clients (and itself for RegroupedInto) | 1+1+1+5 = **8** |
| `Archive FRM10-12` | Order Items, Order, Model Revisions, Clients | Models (through the lookups) | 1+1+4+5 = **11** |
| **all six** | | | **43** (ideal: 5 items + 5 catalogs + 2 = 12) |

A connection-only `ArchiveBOConflicts` costs another 11 if someone loads it. `ArchiveLocalBO`, `ArchiveFrm1012Previous` and `ArchiveLocalTable` touch only the workbook. After the fixes (#5, #6), no step re-reads SharePoint: every repeated enumeration is now on a buffer.

**Accepted, not optimised.**
- The only way to get down to 12 is a staging table loaded to a sheet and read back through `Excel.CurrentWorkbook`. That loses the types (the 09-27 incident), creates a refresh-order dependency, and adds a firewall combination.
- The largest payload (Order Items, about 1,130 × 170 fields) is read by only two tables. Order is read by four.
- A cheaper tweak is possible: read lookup targets with `$select=Id,<showField>`. It saves bytes, not requests, so it's not worth a change to A's verified reader.
- Side effect to know about: the six tables are six snapshots taken a minute or two apart. `TableArchiveFRM10_12` and `TableArchiveOrderItems` can differ if someone edits a unit mid-refresh. The next refresh converges them.

## 3. Formula.Firewall / privacy design

**Measured state.**
- The BASE and WORK copies both carry `FirewallEnabled=true` in the DataMashup permissions part (read from the file). That is `Queries.FastCombine = False`, meaning the file does not ignore privacy levels.
- On this PC, A measured `GlobalPrivacyLevel = 0` and refreshed the five list tables with **no firewall error**. That is the same combination the live `TrackRemoteTable` has always used: `Index`/`Web.Contents` together with `Excel.CurrentWorkbook` in one function.

**Partition layout as built.**
- Web access is isolated in `ArchiveFetch`: `SP_Json`/`SP_ColumnsRaw` → `Web.Contents(SP_Site, [RelativePath…])`, one data source `https://ermcopower.sharepoint.com/sites/PioneerPlanificatio`.
- Workbook access happens in the loaded queries themselves:
  - `ArchiveList` and `AccumulateIntoLocal`;
  - `Archive FRM10-12`: its own guard read, plus `AccumulateIntoLocal` and `EnforceFormats`;
  - B's workbook-only staging queries `ArchiveLocalBO` / `ArchiveFrm1012Previous`, through `ArchiveLocalTable`.
- No workbook value ever flows into a SharePoint request. Every URL is static, or built from SharePoint's own list GUIDs.
- `ArchiveList` and `Archive FRM10-12` still read `Excel.CurrentWorkbook` directly **and** reference ArchiveFetch-derived queries. That is not the textbook "staging" shape. It works here, as measured.

**What could break it.**
- A machine whose global option is "Always combine data according to your Privacy Level settings for each source", with the two sources at different levels: for example the SharePoint site Organizational and Current Workbook Private.
- Since fixes #1 and #2, that fails **loudly** (the refresh errors and the table stays as it was). It can no longer come back as an empty archive. Legacy `TrackRemoteTable` (FRM11/FRM13/BO) still has its `try` and would fail silently in that case. It is untouched, by constraint.

**Required settings, pick one:**
1. **Recommended: ignore privacy levels in this file.** Set `$wb.Queries.FastCombine = $true`, which is Query Options → Current Workbook → Privacy → "Ignore the Privacy Levels". The file's own setting then governs on any PC with the default global option. It is safe because both sources are in-tenant and nothing from the workbook is sent to SharePoint. This is one line in the integration run.
2. Keep `FastCombine = False` and make sure every PC that refreshes has the SharePoint site and Current Workbook at the **same** level (Organizational), with the global option left at its default.

**Full staging, if option 1 is ever refused and option 2 cannot be guaranteed:**
- Add one workbook-only staging query per local table (`Local_TableArchiveOrder = Excel.CurrentWorkbook(){[Name=…]}[Content]`, and so on).
- Add an `AccumulateIntoLocal` variant that takes the local table as a **value** instead of a name.
- Each loaded query then references both halves and touches no source itself.

This is not recommended now: it means more queries for the same behaviour, and `AccumulateIntoLocal` is meant to be reused unchanged.

## 4. The mapping approach: keep `ArchiveFrm1012Map` as is

**Recommendation: keep it. No python generator.** Rationale:

- **It is already one source.** The map is data, one row per pinned column (source list + internal field, rule, arg, type, basis). It drives `Joined` (the fields to fetch), `Source` (the values) and the final typing. `check_frm1012_map.py` parses **the same file**. A generator (`gen_archive_frm1012.py` → `.pq`) would put the truth in Python and make the `.pq` a build artifact. That means two files, a regeneration step, and the classic risk of someone hand-editing the generated file: the drift class it would be meant to remove.
- **The `gen_mirror_synced_from.py` pattern fits external facts, not decisions.** That script turns the live catalog, which is data owned elsewhere, into M. The map's content is human decisions (D2, D3, the recipe, the legacy rules). Those are best kept where they execute and are reviewed, and the checker already enforces them against:
  - the live catalog (source rule, `syncedFromList`);
  - the viewer (`Basis = viewer`);
  - the 09-27 base (every archived value fits its Type).
- **Viewer `ColumnMap`/`ValueConversions` are compared, not consumed.** That is the right coupling for a workbook that is retiring. When the viewer goes, re-label its `viewer` rows `recipe` (or freeze a copy of the two viewer files) so the check does not start failing on a missing folder.
- **`LocationCodes`/`StatusStampCodes` verbatim copies: keep, with the drift test.** Power Query cannot share a query between workbooks without `ImportFromIndex` reading a table from the viewer, and removing that viewer dependency is the whole point of D1. When the viewer retires, Archive active's copies become the owners. At that point, drop the "VERBATIM COPY" header line and remove the viewer comparison from `check_vocab`.
- Minor, no change: the checker requires one map record per line, in field order. It fails loudly with the line number when that is broken, and the rule is written at the top of the map.

## 5. Edits made (all under `power-query/Archive-active/`)

| File | Owner | Change | Reason (finding) |
|---|---|---|---|
| `Archive FRM10-12.pq` | B | `Local`/`LocalKeys` read without try; `RowsDropped` guard around a buffered `AccumulateIntoLocal`; final `CellErrors` guard (`Out`); `Iso` via `Date.ToText` en-US; `AsDate` `Number.FromText` en-US; `TransformColumnTypes(…, "en-US")`; header notes the guards | #1, #3, #4, #7 |
| `ArchiveLocalTable.pq` | B | existence test + read without try; key `Text.From(…, "en-US")`; header | #2, #7 |
| `ArchiveFrm1012Source.pq` | B | `Table.Buffer` on the output; `ToDate` `Number.FromText` en-US; status `Text.From(…, "en-US")` | #5, #7 |
| `ArchiveFrm1012Joined.pq` | B | `UnitsRaw` buffered; buffer-then-count (`Result`); key `Text.From(…, "en-US")` | #6, #7 |
| `ArchiveFetch.pq` | A | comment only (the HTTP-count paragraph) | #8 |
| `Archive FRM10-12.pq` (2nd pass) | B | D2 backfill as one `TransformRows` with record dictionaries (was 2 NestedJoins + 19 ReplaceValue); `Typed` buffered; `NonPrimitive` guard | §6.2, §6.3 |
| `ArchiveFrm1012Map.pq` | B | row 89 `Client Desired Date` `date` → `datetext`; comment | §6.1 |
| `ArchiveTyped.pq` | A | `Flat` buffered (perf only) | §6.2 (#10) |
| `scripts/check_frm1012_map.py`, `test_check_frm1012_map.py` | B | `converts()` mirrors M exactly (real dates only); new mutation + 26 cases | §6.1 |
| `docs/archive-frm10-12-column-recipe.md` | B | 89 moved from the real-date list to the datetext list | §6.1 |

## 6. Follow-up after the first real Excel evaluation (WORK-FRM, 2026-09-28)

The lead ran `Archive FRM10-12` on WORK-FRM (a working copy of the archive) and found three problems. Fixed:

1. **Blocker: `Client Desired Date` (89) typed `date`, but 10 archived values are the placeholder `2025-99-99`.**
   - It failed loudly, as designed (`CellErrors`).
   - Map row 89 is now `datetext`, the same treatment as the other placeholder-carrying date columns. Real dates are written ISO, and the refresher's step 8 (whose date list includes this column) turns them back into dates.
   - Why the checker missed it: `--base` accepted any `\d{4}-\d{1,2}-\d{1,2}`.
   - `converts()` in `check_frm1012_map.py` is now a line-by-line mirror of `AsDate`/`AsNumber`/`AsLogical`:
     - an ISO-shaped text must make a **real** `#date`;
     - anything else must be a valid `m/d/yyyy [h:mm[:ss] [AM|PM]]`;
     - a bool is never a number or a date;
     - numbers are en-US after `,`→`.`;
     - a serial must be inside the OADate range.
   - `test_check_frm1012_map.py` gains a mutation (row 89 back to `date` must fail on the base) and 26 `converts()` cases (`2025-99-99`, `2025-02-30`, `9/31/2026`, `True` as number, and so on).
   - **Audit:** with the strict test, every real-typed map row passes against all values of `TableArchiveFRM10_12` and (for `bo` rows) `TableArchiveBO` in BASE 2356, WORK and WORK-FRM. Row 89 was the only failure. The recipe doc was updated to match.
2. **Performance: about 126 s (sheet) and 340 s (Data Model).** The main suspect was the D2 backfill for rows SharePoint no longer sends.
   - That backfill ran two `Table.NestedJoin`s, and then **19 chained `Table.ReplaceValue` passes** read the nested tables per row. A nested-join table read row by row is a lazy filter over the right-hand table (TableArchiveBO, 1,955 rows; sent keys, about 1,130), so each pass re-scanned it for all 5,321 rows. That is on the order of 10⁸ row comparisons.
   - It is now **one `Table.TransformRows` pass** with record dictionaries (`SentSet`, `BOByOrder`: O(1) field lookup) and the same per-column rule. The rule is spelled out in the step's comment.
   - `Typed` is buffered once, so the cell-error and primitive guards and the load(s) don't re-run the pipeline.
   - `ArchiveTyped`'s `Flat` is buffered, because `Infer` re-ran the lookup and people steps once per inferred column. Joined types four lists, so this counts four times over.
   - This came on top of the earlier buffers (#5, #6).
   - Still in place, and what to look at if it is still over 60 s:
     - `EnforceFormats`' identity pass over about 590k cells (#13), which sits inside the shared `AccumulateIntoLocal`;
     - three reads of `TableArchiveFRM10_12` through `Excel.CurrentWorkbook`: the guard, `ArchiveFrm1012Previous` and `AccumulateIntoLocal`.
   - To localise any remainder, time a row count of each stage (`ArchiveFrm1012Joined`, `ArchiveFrm1012Source`, `Archive FRM10-12`), each as its own diagnostic load.
3. **Data Model "Column '…' is too large".** New `NonPrimitive` guard (`PrimCheck`), which runs after the cell-error check.
   - Every one of the 111 columns may hold only null, text of at most 32,767 characters, number, date or logical. Anything else fails the refresh, naming the column, the first Order and the value's kind (list, record, table, datetime…).
   - By construction the normalisers already turn non-primitives into `BadValue` errors, and the longest text on the live mirror is 515 characters. So if the error recurs with no guard firing, its cause is outside the values. The first suspect is the cell errors of the earlier run: before `CellErrors` existed, errors reached the model.

For the integration run (lead): re-apply `Archive FRM10-12` together with its B dependencies, then check three things:
1. **FRM10-12 refresh time.** It should fall, with fewer passes.
2. **No new errors on the WORK copy**, whose one blank-`Order` row passes the `RowsDropped` guard.
3. **The negative test.** Rename `TableArchiveFRM10_12` on a throwaway copy and refresh: this must now fail with `NoLocalTable`, not rebuild from SharePoint.
