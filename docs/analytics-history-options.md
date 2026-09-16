# Analytics & history — options assessment

**Written 2026-09-16.** Triggered by a question about whether a **data lakehouse** would help
this project. Short answer: no, by a very wide margin — but the question surfaced a real
problem underneath it, and that problem is **live and on a deadline**. Read §3 even if you
skip everything else.

This is an assessment, not a build plan. It closes the long-open *"design the archiving
mechanism"* item in `infrastructure-overview.md` by turning it into three concrete options
with sizing, and it flags one thing that needs a decision **before the nightly cleanup flow
is deployed**.

---

## 1. The lakehouse question, answered

A lakehouse is a **data lake** (cheap object storage, open file formats — Parquet) plus a
**table format** on top (Delta Lake, Apache Iceberg, Hudi) that adds the things a warehouse
has: ACID transactions, schema enforcement and evolution, and **time travel** — querying a
table as it stood on a past date. Warehouse guarantees, lake economics, one copy of the data.
Products: Databricks, Microsoft Fabric (OneLake is Delta underneath), Snowflake + Iceberg.

It is built for **volume** (terabytes upward), **variety** (telemetry, images, logs beside
tables), **many concurrent analytics consumers**, and **compute scaled separately from
storage**.

Pioneer's entire data estate, measured from the newest exports in `sharepoint-lists/`:

| List | Rows | Export |
|---|---:|---:|
| `Order Items` (141 columns) | ~1,200 | 1.1 MB |
| `Order` | 460 | 273 KB |
| `Models` | 396 | 154 KB |
| `Model Revisions` | 394 | 135 KB |
| `ModelChanges` | 1,555 | 440 KB |
| `Clients` | 101 | 18 KB |
| **Total** | **~4,200** | **~3 MB** |

That is roughly **five orders of magnitude** below where a lakehouse starts paying for itself.
The whole business fits in RAM. A Microsoft Fabric F2 capacity — the smallest — is on the
order of US$260/month pay-as-you-go (**check current pricing, and check whether the tenant
already carries Fabric/Premium capacity**, which would change the arithmetic). That is ~$3k/yr
of infrastructure to manage 3 MB.

There is also a shape problem beneath the size problem. A lakehouse is a **read-optimised
analytics layer**. This system is overwhelmingly **operational** — staff editing rows in
SharePoint and soon Monday, flows writing back, Power Query feeding Excel. A lakehouse would
sit *beside* all of that and replace none of it. It would be one more copy of the data to keep
in sync, and this project's entire accumulated scar tissue — `_TextField` drift, two writers
that don't know about each other, forked flow versions — is about **copies of the same data
disagreeing**. Adding a copy is the wrong direction.

**Verdict: no.** Not now, and not at any volume this business plausibly reaches from order
tracking. Revisit only if something genuinely bulky appears — per-unit test telemetry, scanned
document OCR — and even then the answer is more likely a SQL database than a lakehouse.

---

## 2. The real problem the question exposed

> *"at the moment in the bi it's all calculation based for the statistics and kpis but that
> makes it prone to errors"* — user, 2026-09-16

This is the correct diagnosis and it is worth stating precisely, because it is **not** a
Power BI problem and no amount of better DAX or M fixes it.

There are two ways a number can reach a report:

- **Recorded** — something wrote the fact down at the moment it was true, and the report reads
  it back. `Tanking Start Date = 2026-08-04 07:12`.
- **Derived** — the report recomputes the fact from current state on every refresh.

Derived numbers carry four failure modes that recorded numbers do not:

**a. They move retroactively.** Someone edits an old row; last month's published KPI silently
changes. You cannot reproduce a number you sent to management six weeks ago, which means you
cannot defend it either.

**b. Missing data arrives disguised as real data.** The canonical example is already documented
in this repo, in `FRM10-12/power-bi/PriceReg.pq`:

> `HYPERLINK` renders a null friendly-name as **0**, so a *missing* price arrives as a
> plausible-looking `0`, not a blank.
>
> **KNOWN GAP** — 394 archive rows have `[Price] = 0` AND `[Price Value] = null`; **in the
> August KPI window that is 33 of 71 rows, worth ~$1.0M USD.**

Nearly half of one month's KPI rows, about a million dollars, reading as legitimate zeros. Not
a formula bug — the formula is correct and carefully verified. The *input* lost the
distinction between "zero" and "unknown" before Power Query ever saw it, and a derived model
has no way to recover what was never recorded.

> ⚠️ **Actionable and separate from everything else in this document:** that same comment notes
> those rows *are* recoverable from the SharePoint `Order` list, which prices **403 of 417**
> orders. Adding `Order` as a third price source looks like it closes most of a ~$1.0M
> reporting gap. Worth doing on its own merits, independent of any decision below.

**c. The inputs are scheduled for deletion.** See §3.

**d. Every derivation inherits every upstream quirk.** French decimal commas, text-vs-numeric
storage, blanks that mean four different things. `PriceReg.pq` needs 28 lines of comment to
justify 8 lines of code, and that is *good* practice — but it is 28 lines of fragility that
exists only because the number is derived rather than recorded.

---

## 3. 🔴 What is already recorded — and what is about to delete it

This is the part that changes the recommendation, and it is easy to miss because the two
decisions live in different documents and were made three weeks apart.

**You already record production history properly.** Per
`infrastructure-overview.md` (redesigned 2026-08-12, expanded 2026-08-13), every one of the 8
production stages on `Order Items` is a **triple** — `{Stage} Status`, `{Stage} Start Date`,
`{Stage} End Date` — with all 16 date fields confirmed live as **Date *and Time***, explicitly
so that real time-*spent* can be measured rather than inferred from the previous stage's
finish. That is 24 columns of genuine, event-stamped, recorded fact. `Tanking End Date −
Tanking Start Date` is a subtraction of two observed timestamps, not an inference.

**And the cleanup flow will delete all of it.** Per `roadmap.md` (redesigned 2026-08-31), the
archiving workstream is a scheduled flow that finds `Order Items`/`Order` rows sitting at
`Delivered`/`Cancelled` for at least a month, reconfirms them against the Excel Archive, and
**deletes the live row outright** — explicitly *"no copy/verify-then-delete into a new list, no
Power BI repoint needed (Power BI reads the Excel Archive directly if it ever needs historical
data)."*

The gap: **the Excel Archive does not carry the 24 stage columns.** It is the record of
*orders*, not of per-unit production timing. So the moment that flow runs, every unit it
touches loses its entire production timeline permanently — and every trailing-window KPI
computed over the live list (throughput, cycle time, time-in-stage, on-time delivery) silently
starts excluding delivered units, which are precisely the units a completion metric is about.

That decision was made on 2026-08-31, when `Order Items` was newly cut over and held almost no
stage history worth keeping. It is a different proposition now that staff have been stamping
those fields in production, and it gets more expensive every week.

> **The nightly cleanup flow is built but NOT deployed** (`nightly-cleanup-flow.md`, landed
> 2026-09-11). **This must be settled before it is.** That is the deadline.

---

## 4. Recommendation — three tiers, smallest first

The user's instinct that snapshotting *"would be heavy to treat"* is **correct**, and §3 is why:
because you already stamp the events, you do **not** need daily state snapshots to reconstruct
history. Daily snapshots are what you resort to when a system records only current state. This
one doesn't. So the recommendation shrinks accordingly.

Sizing, for reference — roughly 1,200 units/year:

| Approach | Rows/year | Verdict |
|---|---:|---|
| Daily full snapshot of `Order Items` | ~438,000 | **Don't.** Heavy, and redundant given the stage triples. |
| Weekly snapshot, KPI columns only | ~62,000 | Possible, still mostly redundant. |
| `Unit Step History` events (~26 steps) | ~31,000 | **The right shape**, and already the plan. |
| Frozen KPI result per published period | ~850 | Trivial. Do this regardless. |

### Tier 0 — freeze published KPI results *(do this regardless, ~an hour)*

When a KPI number is published for a period, write the **result rows** to a dated file
alongside `KPI output.xlsx` and never touch it again. Numbers you have reported stop moving.
This does not fix any input problem; it makes the outputs reproducible and auditable, which is
most of what "prone to errors" costs you day to day. Smallest possible change, immediate
benefit, no dependency on anything else here.

### Tier 1 — do not let the cleanup flow destroy recorded history *(the actual decision)*

Before `nightly-cleanup-flow.md` is deployed, the per-unit stage timeline must land somewhere
permanent. Three ways, in order of preference:

1. **Make `Unit Step History` the permanent record, and populate it before deletion.** This is
   already the direction — `roadmap.md` (2026-09-14) decided Monday's ~26 steps want a
   **`Unit Step History` child list, not ~52 more columns** on the already-141-column
   `Order Items`. That child list is the *narrow* form of the 24 wide columns you have now.
   The cleanup flow then deletes a unit's `Order Items` row while its timeline survives as
   child rows. This is the coherent end state.
2. **Extend the cleanup flow to append the 24 stage values to a dated Parquet/CSV archive
   before deleting.** Smaller, uglier, no new list. A reasonable stopgap if `Unit Step History`
   is months away and the cleanup flow is needed sooner.
3. **Defer deploying the cleanup flow.** The live lists are ~1,200 rows against a 5,000-item
   threshold. There is no urgency forcing deletion right now — which makes "do nothing yet" a
   legitimate option rather than a dodge.

> ⚠️ **Sizing trap on `Unit Step History`, flagged now because it is a day-one design
> constraint, not a later optimisation.** At ~26 steps × ~1,200 units/year ≈ **31,000 rows/yr,
> the list crosses SharePoint's 5,000-item list view threshold in roughly two months.** It
> needs **indexed columns and filtered views from the moment it is created** — retrofitting an
> index onto a list already past the threshold is painful. Power Query and every flow reading
> it need `paginationPolicy: 5000` explicitly; **Get items returns 100 rows by default**, the
> same trap already logged against the existing in-loop queries in `roadmap.md` item 43.

### Tier 2 — periodic archive export *(cheap insurance, not the main event)*

Monthly, export each list to **Parquet** into a dated folder on SharePoint/OneDrive. Never edit
them. Power BI reads a folder of dated Parquet natively and treats the partitions as one table.

This is **audit and disaster-recovery**, not the KPI mechanism — Tier 1 is the KPI mechanism.
Its real value is replacing *"`Archive active.xlsx` is the sole permanent historical record"*
with something that is not a mutable, formula-bearing, hand-edited workbook. Given this repo's
history — external refs breaking on shifted columns, a generic refresh wiping native formula
columns, view-shaped exports, a blanked workbook recovered from LFS — betting the permanent
record on a live `.xlsx` is the weakest link in the architecture.

Most of the parts exist: `load_exports.py` already parses the exports, `stamp_exports.py`
already does dated archival including the view-shaped-export trap check. Cost is storage-free
and roughly a day of work.

---

## 5. What this changes in existing documents

| Document | Change |
|---|---|
| `infrastructure-overview.md` — *"Still open: Archiving for Power BI historical analysis"* | Now has options and a sizing basis. Pointer added. |
| `infrastructure-overview.md` — checklist *"Design the archiving mechanism"* | Pointer added; still unticked, still the user's decision. |
| `roadmap.md` — archiving workstream (2026-08-31) | **Its premise needs revisiting.** "Power BI reads the Excel Archive if it needs history" holds for orders, not for the 24 per-unit stage columns the Archive never carried. Not edited here — it is a decision, not a correction. |
| `roadmap.md` — `Unit Step History` (2026-09-14) | Endorsed, and it now has a second justification (surviving deletion) plus the 5,000-threshold constraint above. |

---

> **→ Extended 2026-09-16 by [`archiving-architecture-2026-09-16.md`](archiving-architecture-2026-09-16.md)**,
> which takes the question to the whole multi-list architecture and the Power BI dependency.
> It agrees with §1 and §2 and refines three things here:
>
> - **Power BI reads Excel, not SharePoint** — `ArchivedOrders.pq` is one line pointing at
>   `Archive active.xlsx`. Not stated here, and it decides the sequencing: nothing breaks on
>   day one because the charts never saw the SharePoint rows.
> - **Daily snapshots are cheap if they are FILES, not list rows.** §4's "~438,000 rows/year —
>   Don't" is right for a SharePoint list and wrong for a document library, where it is 365
>   files at a few MB.
> - **JSON, not Parquet** — Power Automate has no native Parquet writer, so Tier 2's format
>   puts an Azure Function on the critical path. `Get items` already returns lossless JSON.
>
> And it argues G1 does not need deletion at all — an indexed `Item Status` plus filtered
> views, with Monday taking over as the staff UI, defers it for years at zero risk.

## 6. Decisions needed

1. **Does the cleanup flow ship before `Unit Step History` exists?** If yes, Tier 1 option 2 or
   3 is required first. This is the only time-sensitive item here.
2. **Is Tier 2 (monthly Parquet archive) worth a day**, or does `Archive active.xlsx` stay the
   permanent record?
3. **Should the `Order` list be added as a third price source in `PriceReg.pq`?** Independent
   of everything else; looks like it recovers most of a ~$1.0M reporting gap.

Nothing in this document has been built or changed. §3 is the part with a clock on it.
