# Porting FRM10-12's calculated columns onto `Order Items`

Written 2026-09-14. **Supersedes `calculated-columns-plan.md`'s central conclusion.**
That doc opens with *"none of the 7 columns below can be a plain SharePoint calculated
column"* — true when it was written, and no longer true.

---

## The wall that moved

It named two walls. Only one still stands.

| wall | status |
|---|---|
| **No cross-list lookups** | 🟢 **gone.** N3 fanned 48 parent columns down onto `Order Items`, so every input the price columns need is now on the same item. `BO` is on the list too, retiring that doc's *"needs a `BO` field created first — it exists on neither list today"*. |
| **No volatile functions, no Hyperlink output** | 🔴 stands — and it settles three of the six by deleting them rather than porting them. |

The two Excel lookup tables were never the obstacle they looked like: `TableCanadianProvince`
is 13 province codes that have not changed since 1999, and `Table_USD_CAD_Conversion_Rate`
is six rows. Both are inlined. A SharePoint list around either would be ceremony.

## Where the seven landed

| column | outcome |
|---|---|
| `Navigation Order` | ❌ **dropped** — it *is* the `Order Number` lookup |
| `Navigation Model` | ❌ **dropped** — it *is* the `Model Revision` lookup |
| `Price` | ❌ **dropped** — `Order - Price` already holds the real currency |
| `Archived` | ❌ dropped — deprecated, and the workbook has no formula left for it |
| `Price CAD` | ✅ calculated column |
| `Price USD` | ✅ calculated column |
| `Estimated Delivery Date` | ✅ **calculated column** + a nightly touch |

### Why the three hyperlink columns go rather than becoming column formatting

Decided by the user, 2026-09-14: **the navigation columns are the lookup columns.**
`Order Items` already carries `Order Number` and `Model Revision` as real lookups whose own
UI navigates to the parent, so a column whose entire content is a link to that parent is a
second copy of a control SharePoint already renders.

An earlier pass here argued they were *not* redundant, because Excel's `HYPERLINK()` opens
a **filtered view of every row for that order** while a lookup opens the **single parent
item**. That distinction is real, and it is not worth a column: this is a list now, and
filtering `Order Items` by order is what a list view does natively. Recorded so the
argument is not re-derived and re-lost a third time.

`Price` goes with them for the same reason. Excel's version existed only to make the
number clickable — `HYPERLINK(order url, [Price Value])` — and once the click-through is
redundant there is nothing left for it to add over the real currency column.

## Estimated Delivery Date is a calculated column, not a stored one

`Price CAD` and `Price USD` read it — they take `YEAR()` of it to pick an FX rate — and a
calculated column can only reference a **stored** field. So column formatting alone was
never going to satisfy them: it renders a string into the page and stores nothing for a
formula to read.

That left two ways to make it real, and **they cost the same**:

| | rows written per night |
|---|---|
| Calculated column + touch to force re-evaluation | ~21 |
| Stored column + a flow that writes the value | ~21 |

Same rows, same versions, same action count — so cost does not decide it. **Calculated
wins on everything else** (user, 2026-09-14):

- **It cannot be hand-edited.** Read-only in the UI. A stored column can be overwritten,
  and only self-heals if the trigger flow's change-guard compares the estimate *itself*
  rather than just its inputs — which it does not, today.
- **It works right now.** The create-or-update trigger flow has been **off** since
  09-11. A stored-column design is inert until v004 lands; this is live the moment the
  column exists.
- **It recomputes on save**, not after a ≤5 minute poll.
- **The formula is visible in list settings** instead of buried in a flow definition.
- **The whole chain becomes one mechanism** rather than a flow stitched to five
  calculated columns.

### The one thing it costs: `TODAY()` freezes at last write

Which is what **stage B of the nightly cleanup flow** is for — see below. And it is why
`gen_estimated_delivery_format.py` and its column-formatting JSON are **kept, not
deleted**: column formatting's `@now` is evaluated in the browser, so it has no freeze
*and no UTC trap*. If the calculated column's evening-UTC behaviour turns out to be
intolerable, that is the escape hatch, already built.

⚠️ **Test the UTC trap before trusting evening readings.**
`calculated-columns-plan.md:528` flags that `TODAY()` in a SharePoint calculated column is
UTC-based rather than site-local. The 01:00 Eastern refresh neutralises it for the day, but
a row edited between roughly **20:00 and midnight Eastern** recomputes with UTC already on
tomorrow and reads **a day ahead** until the next pass. There is a written-down test:
*check the existing test column on `Order Items` after 8pm Eastern.*

## The nightly touch — stage B of the cleanup flow

Added to the **existing, already-built** `Nightly_Cleanup` flow rather than a new one. It
runs at 01:00 Eastern, which is also what neutralises the UTC trap above.

| action | what |
|---|---|
| `B1_Get_stall_candidates` | `Active`, no `Planned Delivery Date`, no `Manual Estimated Delivery Date` |
| `B2_Where_TODAY_is_the_answer` | **one** Query action narrowing those to the rows where `TODAY()` is the value being returned |
| `B3_Touch_each_stalled_unit` | writes `Calc Refreshed`, forcing re-evaluation |

🔑 **This is not the stage B killed on 09-11**, and the difference is the point. That one
touched every candidate row to force a re-evaluation and measured 915 a night. Two things
were wrong with that measurement:

1. It filtered on **`Delivery End Date`** — the completion stamp — where the formula reads
   **`Planned Delivery Date`**. *"The second clause is a no-op"* was an artefact of
   filtering on a column the formula never looks at.
2. More importantly, 915 was never the target. It counts rows that *reach* a `TODAY()`
   branch; the rows whose value actually **moves** nightly are the subset where the unit
   is stalled and `TODAY()` is what gets returned. B2 is the action that closes that gap —
   the flow **reads many and writes few**, and reads are batched and cheap.

**One Query action, not a Condition in a loop.** A Condition inside a Foreach over ~900
items costs ~900 actions against a 2,000/day allowance and would starve the five
event-triggered flows. A Query evaluates the same predicate over the whole array once.

⚠️ **Re-measure on the first run.** The ~21 comes from the same 08-31 table whose rows are
labelled *"Delivery End Date"* / *"Tanking End Date"*, so it may be counting a different
population too. **B2's output count is the honest number** — read it off run 1 before
quoting 21 to anyone.

🔴 **`ItemStatus eq 'Active'` in B1 is load-bearing for stage C, not for stage B.** A touch
bumps `Modified`, and stage C's grace period keys on `Modified` — so a pass that touched
Delivered/Cancelled rows would reset the grace clock every night, forever, and the archive
sweep would silently never fire. Do not drop that clause to widen the refresh.

## The currency rule — decided, not inherited

**A recognised Canadian province code prices in CAD. Everything else — blank, a US state,
an unrecognised code — prices in USD.** No exceptions, no data cleanup first (user,
2026-09-14).

This is what the ported formula already did, since `OR()` over the 13 codes is false for a
blank and false for anything unrecognised. What changed is that it is now a **decision**
rather than the two questions `calculated-columns-plan.md` carried open — *30 of 441 orders
have no `Province/State`* and *1 holds `NO`*. Both are answered: USD, deliberately.

`LOWER(TRIM())` is applied on **both sides** — the rule says "is one of the Canadian
provinces", and a trailing space or a lowercase `qc` would otherwise quietly flip an
order's currency.

⚠️ **Do not take the `LOWER` back out.** A first pass here used `TRIM` alone, on the
grounds that `=` is case-insensitive. That is true of *Excel*; the SharePoint
calculated-column engine is Excel-**like** and documents no such guarantee — and this repo
has already paid for assuming a comparison was case-forgiving. The whole **P3 `toLower`
pass** exists because unguarded uppercase-only tests were a live bug class, and
`flow_version.py`'s manifest still carries `toLower` and `'EC'` as columns specifically to
watch for it. Different engine, same cheap guard.

`Is Canadian` lands at **690 characters** against SharePoint's **1024-character** formula
limit, which the engine enforces by returning an unhelpful `400` rather than saying so.
`LOWER(TRIM([Order - Province/State]))` is 38 characters and appears once per province, so
adding codes or renaming that column moves the number fast — the generator asserts the
limit.

## A correction worth recording

An earlier pass assumed `Order Items` carried **both** a native `Price` / `Province/State` /
`Initial Promised Date` and an N3-fanned `Ord*` copy, and treated choosing between them as
a decision for the user.

That was wrong. Those three columns are on the **`Order`** list. `column-reference.md` says
so plainly — if you read it by **section** rather than grepping the whole file, which is
what produced the wrong answer. `Order Items` has exactly one copy of each: the `Ord*` one
N3 puts there. There is no choice, and the fact that the port is possible at all is
*precisely because* N3 fanned them down.

`gen_calc_columns.py`'s verification is now section-aware. The already-shipped
`EstimatedDeliveryDate.format.json` was re-checked against the same rule: all 14 of its
fields are genuinely `Order Items` columns, so nothing there needed changing.

---

## Setup

### Part 1 · The eight columns

```
scripts/n9_create_calc_columns.js      DRY RUN by default; set APPLY = true
```

Eight, not two, because the chain is split so each piece is independently readable and
checkable in a view rather than buried in one unreadable formula:

| column | type | why it exists |
|---|---|---|
| `Calc Refreshed` | DateTime | the **only** non-calculated column, and the only thing anything writes to — what stage B touches |
| `Bo Penalty` | Number | the 30-day back-order penalty, split out because it appears in all four milestone branches |
| `Estimated Delivery Date` | DateTime | the eight-branch formula, **828 chars** against the 1024 limit |
| `Is Canadian` | Boolean | `TableCanadianProvince`, inlined, `TRIM`-ed |
| `Fx Year` | Number | Excel's two-deep date cascade: Estimated Delivery Date, else Initial Promised Date. `0` = neither is set |
| `Fx Rate` | Number | **the one place to edit when a new year's rate is agreed** |
| `Price CAD` | Currency | Canadian order → already CAD. Otherwise USD, converted |
| `Price USD` | Currency | the mirror image |

The script creates them **sequentially** — `Fx Rate` references `Fx Year` and the price
columns reference both, and SharePoint rejects a `FieldRef` to a field that does not exist
yet. It aborts on any existing name rather than creating duplicates with a `0` suffix
(which is why `x9_delete_duplicate_status_columns.js` exists), and reads every field back
afterwards, because a `200` is not proof SharePoint stored the `ResultType` you asked for.

## Two deliberate differences from Excel

1. **Rates clamp instead of erroring below 2024.** `XLOOKUP(..., -1)` is *exact or next
   smaller*, so a year **above** the table takes the last rate — reproduced. Below the
   table Excel returns `#N/A` (Price CAD) or a string that then breaks the arithmetic
   (Price USD). Here a pre-2024 date prices at the oldest known rate. A money column
   should not render an error.
2. **`Price USD` divides** rather than multiplying by `(1/rate)` — same value, one less
   rounding step.

## Still open

- **FX rates stop at 2029.** `Fx Rate` returns 1.47 for anything later, which is correct
  until it silently is not. Add years to `FX` in the generator.
- **The UTC evening trap**, untested — see above. It is the one thing that could send us
  back to column formatting for the display.
- **Stage B's real row count**, unknown until run 1.
- **Deploying the cleanup flow.** It has never been deployed at all, stage A included.
