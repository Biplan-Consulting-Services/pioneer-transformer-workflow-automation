# Does the industry build ERPs on SharePoint lists? — external check, 2026-09-16

**Asked:** everything here was designed from first principles; check it against what people
actually do. Sources at the bottom; Microsoft Learn / Microsoft Support / PnP preferred over
vendor blogs, and where the two disagree the primary source wins.

**Short version: the design holds up better than the loud consensus would suggest, because the
loud consensus is aimed at a different size class.** The one risk this raised — the 12-lookup
threshold — was **measured and downgraded the same day** (§4): the parent-prefixed columns are
flow-synced plain columns, not projected lookups, so the list sits at roughly 7–8 of 12. What
survives from it is the observation that the cost of that choice is a 47-column consistency
burden this project has already paid for in bugs. It also settles the archive-format argument from
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

## 4. The 12-lookup-column threshold — flagged, then measured, then downgraded

**Corrected 2026-09-16, same day, after the user pointed out the premise was wrong.** Kept
in full rather than deleted, because the limit is real and the reasoning about *which* shape
trips it is worth having on file.

SharePoint Online caps a single view or query at **12 "lookup-type" columns**, separate from
the 5,000-item threshold, and it counts more than it sounds like: lookup columns, managed
metadata, **and person columns including the built-in `Created By` and `Modified By`**.
Exceeding it does not degrade the query, it **fails** it — *"the number of lookup columns it
contains exceeds the lookup column threshold"* — and the view becomes inaccessible.

The alarm here assumed `Order Items`' 47 parent-prefixed columns (`Order - Order Status`,
`Mod. Rev. - kVA`, `Model - Model_ID`, …) were SharePoint **projected lookup fields**, which
would have put the list far past 12. **They are not.** Measured from the export's own
`ListSchema` record:

| the 47 `Order - X` / `Mod. Rev. - X` columns are declared as | count |
|---|---:|
| `Text` | 16 |
| `Choice` | 13 |
| `Number` | 8 |
| `DateTime` | 3 |
| `Note` | 3 |
| `Boolean` | 2 |
| `URL` / `Currency` | 1 each |

**Plain columns, every one of them** — kept in step by Power Automate, not projected through a
lookup. Lookups are used only to *link* the entities: `Order Items` ↔ `Order`, `Models`,
`Model Revisions`, `Engineering Change Orders`, `Model Changes`.

So the count against the threshold is roughly **five or six lookups plus `Created By` and
`Modified By` ≈ 7–8**, against a limit of 12. Headroom, not a ceiling. **No test needed and no
action required** — though the margin is worth remembering before anyone adds four more
lookups to one view.

⚠️ **One thing this exercise did establish, and it matters for other work:** the export's
`ListSchema` record is **not a complete description of the list**. It carries 152 field
definitions, and *none* of the relationship columns — `Order Number`, `Client`, `Model`,
`Model Revision`, `Regrouped Into` — appears among them. So the schema record cannot be used
to enumerate lookups, and "zero lookup-type fields in the schema" means the export omits them,
not that the list has none. `infrastructure-overview.md`'s relationship graph remains the
authority there, because it was read from `_api/…/fields` directly.

> 🔑 **The real cost of this design is not a platform limit, it is a consistency burden — and
> it has already been paid, repeatedly.** Avoiding projected lookups means ~47 columns of
> flow-maintained denormalised copy on `Order Items`, on top of the `_TextField` mirrors. That
> is the same pattern that produced the mirror-drift audit (`x16`), the 29 corrupt
> `Model Revisions.ModelID` values (`x17`/`x18`), and the `Status Date` erasure that fires
> precisely *when a mirror refreshes without a step change*. The platform limit was avoided;
> the reconciliation problem was bought.
>
> It also cuts the other way for archiving, in a good direction: because those columns hold a
> real value written to the row rather than a live projection, **a snapshot of the row captures
> what the parent said at that moment.** That is better history than a lookup, which would
> always render today's parent value. It strengthens the export-archive case rather than
> weakening it.

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
| Test the 12-lookup threshold | **Raised, then retired.** Measured: ~7–8 of 12, with headroom. No action. |
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
