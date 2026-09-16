# Does the industry build ERPs on SharePoint lists? — external check, 2026-09-16

**Asked:** everything here was designed from first principles; check it against what people
actually do. Sources at the bottom; Microsoft Learn / Microsoft Support / PnP preferred over
vendor blogs, and where the two disagree the primary source wins.

**Short version: the design holds up better than the loud consensus would suggest, because the
loud consensus is aimed at a different size class. But the research surfaced one real risk that
was not on anyone's radar, and it is schema-shaped, not volume-shaped — see §4.** It also
settles the archive-format argument from
[`archiving-architecture-2026-09-16.md`](archiving-architecture-2026-09-16.md) on independent
grounds.

---

## 1. "SharePoint is not a database" — true, and mostly not about us

This is the dominant practitioner opinion and it is stated bluntly: *"SharePoint lists are just
a bad database. If you need to store structured data, use an actual database."* The cited
reasons are consistent across sources:

- the 5,000 **list view threshold**, which **cannot be raised in SharePoint Online** (unlike
  on-premises, where an admin could)
- performance degrading "significantly beyond 100,000 records"
- no referential integrity, no constraints, no transactions
- only **20 indexed columns** per list, and automatic indexing **stops above 20,000 items**

Read carefully, almost every objection is about **volume** or **relational integrity**. Pioneer
has ~4,100 rows across all lists, growing ~1,100/yr. The volume objections are two to four
orders of magnitude away from applying. **On size alone, this is a defensible use of the
platform and the internet's blanket "don't" is not addressed to a system this small.**

The integrity objection is a different matter — see §5.

## 2. Where the design already matches industry practice

Independently arrived at, and confirmed as the standard answer:

| Practice | Consensus |
|---|---|
| Index the columns you filter on; use filtered views instead of raising limits | ✅ The universally recommended mitigation. Indexing is described as "the most effective mitigation strategy". |
| Do it **before** the list gets big | ✅ "Remedies should be applied before hitting 5,000 items", and auto-indexing will not help above 20,000. Matches the `Unit Step History` warning already in `analytics-history-options.md`. |
| Snapshot to dated files in one folder for historical reporting | ✅ **This is the named community pattern.** "Save snapshots at different points in time by exporting to a flat file on a regular schedule and storing all these files together in one folder." |
| Scheduled Power Automate flow to do the archiving | ✅ Microsoft's own Power Automate blog documents "How to Archive Completed Items in a SharePoint List" as the standard approach. |

One refinement to steal: the snapshot pattern says to **add an "As of Date" / "Snapshot Date"
column inside each file**, stamped with the export date. Power BI then treats the pile of files
as one table with a date dimension and trend analysis falls out. The plan in
`archiving-architecture-2026-09-16.md` has dated *folders* but no date *column* — add it. It is
free at write time and expensive to retrofit.

## 3. 🔑 The Power BI finding, which settles the format argument

This matters because Power BI is the stated constraint, and it is an argument from a direction
the earlier assessment did not use.

**SharePoint lists are a bad Power BI source, and the reasons are structural:**

- **SharePoint lists are not a foldable source, so incremental refresh gives no benefit.** Query
  folding is what lets Power BI push filters down to the source; without it, every refresh
  drags the whole list across the wire regardless of how the model is partitioned.
- The SharePoint OData API is slow, and the classic list-items endpoint **returns 100 items per
  page by default** — the same pagination trap already logged in `roadmap.md` item 43 against
  the in-loop `Get items` queries.
- Lists over 5,000 items have been observed **throttled with HTTP 429** during dataflow
  refreshes, failing the refresh outright.
- There is a widely-circulated practitioner article titled, flatly, *"Power BI and SharePoint —
  Terrible Together."*

> 🔑 **This kills the archive-as-a-second-SharePoint-list option on Power BI grounds alone.** An
> archive list is the *one* table that only ever grows, is only ever read by analytics, and is
> never filtered by an end user — precisely the table you least want behind a non-foldable,
> throttling, 100-rows-per-page connector. A folder of dated files folds, partitions, and
> prunes.
>
> The earlier recommendation reached "files, not a list" from schema-drift reasoning. The BI
> constraint reaches the same answer independently. Two unrelated arguments, one conclusion.

## 4. 🔴 The risk nobody flagged: the 12-lookup-column threshold

**This is the finding worth the whole exercise, and it is not about row count at all.**

SharePoint Online caps a single view or query at **12 "lookup-type" columns**, and this limit
is separate from the 5,000-item threshold. What counts toward it is broader than it sounds:

- Lookup columns
- **Person/Group columns — including the built-in `Created By` and `Modified By`**
- Managed Metadata columns and Enterprise Keywords

Exceed it and the query does not degrade, it **fails**: *"The query cannot be completed because
the number of lookup columns it contains exceeds the lookup column threshold."* The view becomes
inaccessible.

`Order Items` is exactly the shape that hits this. It carries **five** lookups — `Order Number`,
`Client`, `Model`, `Model Revision`, `Regrouped Into` — plus `Created By` and `Modified By`,
which is **seven before a single projected field**. And the 2026-09-16 All-Items export carries
**24 projected parent fields** (`Order - Order Status`, `Mod. Rev. - kVA`, `Model - Model_ID`, …).

⚠️ **Whether each projected field counts separately is genuinely undocumented.** Three sources
were checked, including Microsoft Support's own page, and none states it either way. The
empirical evidence here is that the 151-column All-Items export **succeeded**, which suggests
projected fields either do not count or are not counted the same way through the export/`$select`
path as through a rendered view.

**That is not the same as being safe, and it should be tested deliberately rather than
discovered.** The cheap test: build a view exposing a dozen-plus of the projected parent fields
and see whether it renders. Five minutes, and it either retires the risk or reveals a ceiling
that constrains every future view, Power Apps screen, and `$select` in a flow.

If it does bite, the documented workarounds are all "show fewer lookups per view" — split across
multiple views, hide columns, or replace lookups with plain columns. Note that the `_TextField`
mirror pattern this project already built is, accidentally, exactly that last workaround.

## 5. The bigger question the research raises: Dataverse

The honest answer to *"am I wrong?"* is not about the archive design. It is about the substrate.

**Microsoft's own steer for line-of-business apps is Dataverse, not SharePoint lists.** Dataverse
is a true relational platform with constraints, role-based and field-level security, and — the
part that matters here — **native long-term data retention**: archival policies that move
inactive rows to cheap retained storage while keeping them queryable (via FetchXml with
`datasource="retained"`). **The entire mechanism being hand-built in this repo ships as a
platform feature there.**

Two things make that more than a theoretical point:

1. **The integrity objection has already bitten, at tiny volume.** The `_TextField` mirror
   columns are a hand-rolled denormalisation that exists only because SharePoint lookups are
   awkward to query and report on — and they have produced real, expensive bugs: the mirror
   drift audit (`x16`), the 29 corrupt `Model Revisions.ModelID` values (`x17`/`x18`), and the
   `Status Date` erasure that rides on a mirror refresh. That is the classic symptom of
   relational data in a non-relational store, and the consensus predicts it. It is showing up
   at 4,100 rows, not at 100,000.
2. **Microsoft 365 Archive does not help.** It is worth naming because it sounds like the
   answer: it is cold storage for **sites and files**, with file-level archiving reaching GA in
   July 2026. **It does not archive list items.** There is no built-in list-item archive in
   SharePoint, which is why every source describes hand-built flows.

### But: do not migrate now

The counter-argument is strong and it wins today:

- **Volume does not justify it.** ~4,100 rows. Dataverse is the right answer for an org with a
  real LOB app at scale; this is a production tracker for ~1,100 units/yr.
- **Cost and licensing.** Long-term retention requires a **Managed Environment**, and Dataverse
  carries per-user licensing SharePoint does not. Real money against a problem that is currently
  theoretical.
- **The system is built and being cut over right now.** Monday.com is arriving as the working
  layer. Adding a substrate migration on top is how cutovers fail.
- 🔑 **This project's entire accumulated scar tissue is copies of the same data disagreeing.** A
  migration is the largest copy-disagreement event available. The same reasoning that correctly
  killed the lakehouse kills this, for now.

### Tripwires — when the answer changes

Write these down now, so the decision is made on evidence rather than frustration:

- any list crosses **20,000 items** (automatic indexing stops; manual indexes must exist first)
- the **12-lookup threshold** starts forcing view gymnastics (§4 — test this early)
- Power BI refreshes get slow or start **429-throttling**
- **item-level permissions** become a requirement (explicitly advised against on SharePoint lists)
- referential-integrity incidents stop being one-offs and become routine

None is tripped today. The third and fifth are closest.

## 6. What actually changes in the recommendation

Less than expected, which is itself the answer to the question asked.

| | change |
|---|---|
| Don't delete; index + filter | **Unchanged.** Confirmed as the standard mitigation, and explicitly "before you hit 5,000". |
| Dated immutable exports as the permanent record | **Unchanged, and now supported by two independent arguments** — schema drift (§4 of the architecture doc) and Power BI foldability (§3 here). |
| **Add an `As of Date` column inside each snapshot file** | **NEW** — the community pattern's own refinement. Free now, painful later. |
| Archive-as-a-second-list | **Further weakened.** It was rejected on schema drift; the Power BI connector's behaviour rejects it again. |
| JSON over Parquet | **Unchanged.** Note the snapshot pattern is usually described with CSV; the type-loss and lookup-serialisation traps this repo has already logged still argue for JSON. |
| Test the 12-lookup threshold | **NEW, and it is the near-term action.** |
| Dataverse | **New section, deliberately not a recommendation.** Documented with tripwires so it is a decision, not a surprise. |

---

## Sources

- [Working with the List View Threshold limit — Microsoft Support](https://support.microsoft.com/en-us/office/working-with-the-list-view-threshold-limit-for-all-versions-of-sharepoint-4a40bbdc-c5f8-4bbd-b9b6-745daf71c132)
- [Living Large with Large Lists and Large Libraries — Microsoft 365 Community / PnP](https://pnp.github.io/community-docs/articles/large-lists-large-libraries-in-SharePoint.html)
- [Create list relationships by using lookup columns — Microsoft Support](https://support.microsoft.com/en-us/sharepoint/lists/data-and-lists/create-list-relationships-by-using-lookup-columns)
- [How to avoid Lookup Column Threshold limit on a view — SharePoint Maven](https://sharepointmaven.com/how-to-avoid-lookup-column-threshold-limit-on-a-view/)
- [Dataverse long term data retention overview — Microsoft Learn](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/data-retention-overview)
- [Long-term data retention (developer) — Microsoft Learn](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/long-term-retention)
- [Overview of Microsoft 365 Archive — Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-365/archive/archive-overview)
- [How to Archive Completed Items in a SharePoint List — Power Automate blog](https://powerautomate.microsoft.com/en-us/blog/how-to-archive-completed-items-in-sharepoint-list/)
- [Power BI and SharePoint – Terrible Together — Excelerator BI](https://exceleratorbi.com.au/power-bi-and-sharepoint-terrible-together/)
- [How to Fix Slow SharePoint List Refresh in Power BI — Vojtech Sima](https://www.vojtechsima.com/post/how-to-fix-slow-sharepoint-list-refresh-in-power-bi)
- [How to Store Historical Data in Power BI — Bricks](https://www.thebricks.com/resources/guide-how-to-store-historical-data-in-power-bi)
- [SharePoint Lists as a Database: Building Relational Data — skybow](https://www.skybow.com/blog/sharepoint-lists-as-a-databas)
- [Using SharePoint as a Database – Why It's a Bad Idea — Nakivo](https://www.nakivo.com/blog/why-you-shouldnt-use-sharepoint-online-as-a-database/)
- [When To Use Dataverse vs. SharePoint Lists — TenHats](https://tenhats.com/when-to-use-dataverse-vs-sharepoint-lists/)

**Nothing built or changed by this document.**
