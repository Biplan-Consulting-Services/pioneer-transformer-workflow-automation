# Archive every SharePoint list: design

Written 2026-09-27, late session, after the Nightly Sync's first dry runs showed that the Excel archive
has stopped learning anything from SharePoint. **Nothing here has been applied.** This supersedes the
application plan in `archive-cover-all-lists-2026-09-16.md`, keeping its accumulate logic and its
warnings.

## 0. Decisions (user, 2026-09-27)

| # | decision |
|---|---|
| A1 | **The archive tracks every list on the site**, so all the data is backed up, not only the lists that used to have a workbook. |
| A2 | **The archive reads SharePoint directly**, not through the FRM10-12 viewer. |
| A3 | **The Excel archive stays the gate** for the Nightly Sync. It is the only place historical data lives, so a unit leaves Order Items only once the archive holds its final state. |
| A4 | Office Scripts in production print failures and warnings only (done 09-27: `VERBOSE` switch in the refresher). |
| **A5** | **`TableArchiveFRM10_12`, `TableArchiveFRM11` and `TableArchiveFRM13` keep exactly their current shape**, because everything that depends on them breaks otherwise. Everything in this design is **additive**: new tables beside them, never a change to them (§6). |
| — | **Open: where BO lives** (§7). |

## 1. Why the current archive cannot do this

Archive active tracks **workbook tables** only (`TrackRemoteTable` through the `Index` list):
FRM10-12, BO Manager, FRM11, FRM13. After the cutover:

- **Nothing SharePoint-native is archived.** Order, Models, Model Revisions, Clients, ModelChanges,
  EngineeringChangeOrders, Models SA and Index have no archive at all. Order Items reaches the archive
  only second-hand, as the viewer's `TableOrders`: 82 columns of its ~160, renamed, with `Location`
  converted to two-letter codes and `Delivery Date` taken from the **Planned** Delivery Date.
- **It only moves when two workbooks are refreshed in the right order:** the viewer, then Archive
  active. On 09-27 the FRM10-12 and BO archive tables had not taken a single new row since 09-14.
- **The viewer route turns dates into text.** The 09-27 23:28 refresh left all 15 date columns of
  `TableArchiveFRM10_12` as `"2/20/2024 12:00:00 AM"` text, and the Nightly Sync stopped at C3.
  (Fixed on the Excel side by the refresher's new step 8 converter. The route itself is still fragile.)

## 2. Target design: two layers

```
                         ┌─ Layer 1: one typed table per core list ─────────────┐
SharePoint (REST, raw) ──┤   TableArchiveOrderItems, …Order, …Models,           ├─► Archive active.xlsx
  every list on the site │   …ModelRevisions, …Clients                           │   (on SharePoint:
                         │                                                       │    versioned, backed up)
                         └─ Layer 2: one universal table, EVERY list ───────────┘
                             TableArchiveAllLists: List | Id | Title | Modified | RowJson
```

**Layer 2 is the backup promised by A1.** One table holds one row per item of **every** list: the list
name, the item `Id`, `Title`, `Modified` (raw ISO), and the whole item as JSON text. It is built from a
**catalog of the site's lists**, so **a list created tomorrow is archived on the next refresh with no
query written for it.** Excel cannot create a new sheet per list from Power Query, and that is why
this layer is one table in a long format rather than one table per list.

**Layer 1 is for reading.** The five lists that people, Power BI and the Nightly Sync actually query
get their own table with real columns: Order Items, Order, Models, Model Revisions and Clients. A list
graduates from layer 2 to layer 1 when someone needs to filter or chart it. Until then it is still
fully backed up.

Why both, rather than layer 1 for everything: a layer-1 table needs a query and a sheet written by hand
for every list, so the list nobody remembered is the one that is lost. Layer 2 cannot forget.

### 2.1 The catalog of lists

```
_api/web/lists?$filter=Hidden eq false and BaseTemplate eq 100&$select=Id,Title,ItemCount,LastItemModifiedDate
```

- `BaseTemplate 100` = custom lists. Document libraries are **out of scope**: they hold files, which
  SharePoint's version history and recycle bin already protect. If a library's **metadata** ever
  matters (e.g. the planned Engineering Drawings library), add it to the catalog explicitly.
- The catalog keys each list on its **Id (GUID), not its title**, so a renamed list stays the same
  archive stream. Title is stored beside it.
- The mirror's health report gets one more check: **any list in the catalog that the mirror does not
  snapshot** is flagged, so a new list reaches the mirror too.

## 3. How the archive reads SharePoint

**Reuse the mirror's REST reader (`power-query/SharePoint mirror/SP_Json`, `SP_ItemsRaw`, `SP_Mirror`).
Do not use the 09-16 draft's `SharePoint.Tables`.**

- 🔴 `SharePoint.Tables` returns date-only values shifted a day early (found 2026-09-24, CLAUDE.md
  "FRM10-12's SharePoint.Tables queries shift Date-Only values"). The 09-16 `TrackRemoteList` uses it,
  so as authored it would archive every date-only column one day early. That is silent and permanent.
- `SP_Mirror(listTitle)` already does everything the archive needs: raw REST, every field, `Id` kept,
  each lookup as both its id and its display value, person columns as email, and nested values as JSON
  text. It also **refuses** a zero-row read or a page that would truncate. The archive adds nothing to
  the read.

**Conversion rules, applied once, between the read and the accumulate step:**

| raw REST value | archive value | why |
|---|---|---|
| date-only column (`dateTime (dateOnly)` in the mirror's `Columns` catalog) | **the first 10 characters** as a real date: `2026-09-01T04:00:00Z` → 2026-09-01 | SharePoint stores a date-only value as midnight Eastern in UTC (`T04:00Z` / `T05:00Z`). The six E7 orders are stored at `T00:00Z`. The date part is right in all three cases. Converting to local time is not, because it depends on the machine. |
| date-and-time column, `Created`, `Modified` | ISO text, unchanged | Exact and unambiguous. `Modified` is compared as-is by the Nightly Sync gate (§5). |
| lookup | display value + `<Name>Id` | as the mirror |
| multi-choice, multi-lookup, URL | JSON text | never flattened to a guess (R22) |

**Column names are internal names** (`Planned_x0020_Delivery_x0020_Dat`), as in the mirror. A display
rename on SharePoint then never splits an archive column in two. `docs/data-inventory.md` maps them to
display names.

## 4. Keys and the accumulate step

- **Key = the item `Id`** on every list. SharePoint never reuses an item id within a list, it is always
  populated, and it survives a Title edit. (The 09-16 draft keyed Order Items on `Title`. A Title typo
  fixed on SharePoint would then leave two archive rows for one unit.) In layer 2 the key is `List Id + Id`.
- **`AccumulateIntoLocal` is reused unchanged**: local rows whose key has left SharePoint are kept
  forever; every current row overwrites its archive row; new columns are added; dropped columns are
  kept as nulls.
- **"When did this item leave SharePoint?"** is its `Last Synchronisation Date`, the last day a refresh
  still saw it. No extra column needed.
- ⚠️ The archive keeps each item's **latest state**, not its history of changes. Change history is the
  mirror's journal plus SharePoint version history (`change-tracking-design-2026-09-24.md`).

## 5. The Nightly Sync's new gate (v006)

Today's gate reads `TableArchiveFRM10_12` (`Location eq 'LI'`, Delivery Date ≥ 7 days ago). After the
switch it reads **`TableArchiveOrderItems`** and deletes a unit only when **all** of these hold:

1. Order Items: `Location = Livraison` and `ItemStatus = Delivered` (as now).
2. The archive has a row with the same `Id`, also at Livraison + Delivered.
3. **The archived row is the unit's current version**: its `Modified` equals the unit's `Modified`.
   This check is what actually proves "safely archived". Any edit after the last archive refresh
   blocks the delete until the next refresh catches up.
4. The unit has not been edited for 7 days (`Modified` ≤ today − 7). That's a real grace period for
   corrections, unlike today's, which counts from the *planned* delivery date.

Cap 50, the dry-run switch and the summary stay as in v005. SA twins need no special case, because
they are ordinary items with their own `Id`. A generator change (`gen_nightly_sync.py` → v006) plus
mutation tests, the same way as v005.

## 6. The existing archive tables: same shape, still fed (A5)

**Shape = the column names, their order, and each column's type** (a date stays a date: the 09-27
text-date incident *was* a shape break). The new layer-1 and layer-2 tables are added beside these
three. None of the three is renamed, reshaped, repointed or frozen.

| table | fed from | rule |
|---|---|---|
| `TableArchiveFRM10_12` | viewer `TableOrders`, today | **Keeps its 93 columns exactly, and keeps receiving every unit.** Readers include FRM11's `Rows to purge` (two-letter `Location` codes), the viewer's "already archived" filter, and whatever else reads it through `Index`. **It is never frozen while anything reads it**: a frozen table stops FRM11 learning which tanks are done. |
| `TableArchiveFRM11` | FRM11 `TableFournTank` | unchanged |
| `TableArchiveFRM13` | FRM13 | unchanged |
| `TableArchiveBO` | BO Manager `TableBO` | shape kept whatever §7 decides |
| `Table3`, `Table4` | none (old imports) | untouched |

**Two things this rules out, and one it requires:**

- ❌ **No schema drift on the three legacy tables.** `AccumulateIntoLocal` is schema-adaptive: a column
  the source gains is **added** to the archive. That is exactly right for the new tables and wrong
  for these three. For them the column list is **pinned**: the accumulate step selects the pinned
  columns in the pinned order, and **a source that has lost a pinned column fails the refresh loudly**
  instead of padding it with nulls. The pinned lists are read from today's workbook, not typed by hand.
- ❌ **No "freeze once readers move".** An earlier draft of this section proposed it. Withdrawn: A5 means
  the readers do not move.
- ✅ **The viewer-route fragility still has to go**, so `TableArchiveFRM10_12` gets a **legacy-shape
  adapter** later: the same 93 columns, codes and types, built from `TableArchiveOrderItems` (same
  mapping as the viewer: `LocationCodes`, `ColumnMap`, `Planned Delivery Date` → `Delivery Date`)
  instead of from the viewer workbook. Its output must be **identical** to what the viewer route
  produces for the same data, checked column by column on a copy before it replaces anything. Until
  that check passes, the viewer route stays.

**Measured across every saved copy (09-08 → 09-27 23:28):** names and counts never changed (FRM10-12
93, FRM11 39, FRM13 55, BO 24). **FRM10-12's column order changed once, between 09-10 and 09-16**
(cutover week), and has been identical since. The 09-27 incident broke **types** only. Pin tonight's
23:28 copy as the reference shape.

**A shape check runs on every refresh** (in the refresher script, failures only): the three legacy
tables' headers must equal their pinned lists, and their date columns must hold no text. Otherwise
the script reports which table and column, so it gets noticed the same day and not three weeks later.

## 7. BO: open decision

Order Items already carries `BO` plus **three part slots** (`BO1…BO3` × part, description, PO,
supplier, date, OK), copied once from BO Manager on 09-05 (`a5-d3-bo-transfer-paste-sheet.md`). Slot 3
is filled on 0.3% of units.

**The question to settle first: where is BO edited now?** The viewer still takes BO **from BO
Manager** ("BO Manager stays the authority"). While purchasing edits BO Manager, the BO columns on
Order Items are a stale copy, and archiving Order Items would archive stale BO.

| option | archive | when it fits |
|---|---|---|
| **B1 (recommended if BO is edited on Order Items)** BO lives on Order Items | archived with the unit in `TableArchiveOrderItems`. `TableArchiveBO` frozen as BO Manager's history. | three parts per unit is enough (it is today) |
| **B2** a `Back Order Parts` list, one row per part, looking up the unit | its own layer-1 table (or layer 2 until needed) | a unit can need more than three parts, or each part has its own status and dates to track |
| **B3** stay on BO Manager | `TableArchiveBO` keeps tracking it | only as a transition. It keeps a workbook in the loop the migration is removing. |

## 8. Refresh and scheduling

- The archive is only as current as its last refresh, and the Nightly Sync gate (§5) waits for it
  automatically. A stale archive delays deletes, and never causes a wrong one.
- **Daily, before the Nightly Sync (01:30 Eastern)**, in this order: Archive active refresh, then the
  refresher script (the step 8 date converter). The viewer no longer needs to come first once
  `TableArchiveFRM10_12` is frozen.
- ❓ **Unattended refresh is not solved yet.** Whether Excel for the web can refresh these REST queries
  from Power Automate or an Office Script alone must be **tested, not assumed**. The known-good path is
  a desktop Excel refresh over COM, the way `Refresh-SharePointMirror.ps1` works, run by the scheduling
  infrastructure (punch list `h-scheduling`). Until then: a manual refresh, and the Nightly Sync deletes
  only on nights that follow one.

## 9. Switch-over, in order

Each step is safe to stop after. The Nightly Sync stays **off** (or dry run) until step 7.

1. **Fix the dates first.** Run the updated refresher (09-27) on Archive active. Confirm the 24 text
   date columns are real dates again. *(punch list `ns-date-fix-verify`)*
2. **Snapshot** Archive active (a dated copy in `workbooks/`, older copies to `workbooks/Archive/`) and
   the mirror.
3. **Settle BO** (§7).
4. **Author** (repo only): the catalog query; `ArchiveAllLists` (layer 2); the date conversion step;
   `TrackRemoteList` rewritten on `SP_Mirror`; five layer-1 queries keyed on `Id`. Validate each against
   the mirror's CSVs: same row counts, same ids, and dates equal to the raw value's first 10 characters.
5. **Apply to a COPY of Archive active first**, one query at a time. Order first (smallest, 473 rows),
   Order Items last. The first refresh of a new archive table is the dangerous one
   (`archive-cover-all-lists-2026-09-16.md` §"Applying it"). Check row counts after each.
6. **Apply to the live Archive active**, same order, and refresh.
7. **Nightly Sync v006** (§5): generate, test, dry run, compare its summary with the mirror, then enable
   deletes.
8. **Pin the three legacy tables' shapes** and add the shape check (§6). This can happen any time,
   and doing it early protects them during steps 5–6.
9. **Legacy-shape adapter** for `TableArchiveFRM10_12` (§6): build it on a copy, prove its output
   identical to the viewer route's, then swap the source. The table's shape never changes.
10. **Automate the refresh** (§8).

## 10. Checks that must hold (and fail loudly if not)

- Every list in the catalog has rows in layer 2 after a refresh. A list with items but no archive rows
  is an error, not an empty list.
- Layer-2 `RowJson` must fit Excel's **32,767-character cell limit**. Measure the longest Order Items
  row before step 5. A row over the limit is refused with its list and id, never silently truncated.
- Archive row count ≥ the previous refresh's, per list. The archive only grows. A drop means rows were
  lost and the save must not happen.
- Date-only columns: 0 text values after the refresher runs.

## 11. Questions for the user

1. **BO (§7):** is BO edited in BO Manager or on Order Items now?
2. **Which lists are new since 09-16?** The catalog will find them anyway. Knowing them lets step 4 be
   checked by hand.
3. **Document libraries:** leave them to SharePoint's own version history (proposed), or archive their
   metadata too?
4. ~~Repoint FRM11's purge?~~ Settled by A5: no. `TableArchiveFRM10_12` keeps its shape and keeps
   being fed; only its source changes later, through the adapter (§6).
5. **Who else reads the three legacy tables?** FRM11's purge and the viewer are known. Anything
   else (Power BI, FRM09, FRM13, BO Manager) is worth listing, so the shape check guards all of them.
