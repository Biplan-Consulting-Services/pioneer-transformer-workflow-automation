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
| `Estimated Delivery Date` | ⛔ **stored column + flow** — the prerequisite for the two above |

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

## 🔴 The dependency that settles the Estimated Delivery Date question

`Price CAD` and `Price USD` both read `Estimated Delivery Date` — they take `YEAR()` of it
to pick an FX rate. **A calculated column can only reference a stored field.**

So **Estimated Delivery Date must be a stored column.** Column formatting alone does not
satisfy them: it renders a string into the page and stores nothing for a formula to read.
The open question in `estimated-delivery-date-today.md` is therefore closed by
**dependency, not preference** — and it was never really about sorting.

It also **rules out the unfloored-storage idea** (store `milestone + buffer`, apply the
`@now` floor at display, zero daily writes). For a unit whose milestone is in the past,
floored and unfloored can land in **different calendar years**, which picks a different FX
rate and so a different price. Fidelity to the workbook needs the floored value, which
needs the daily pass over the stalled rows — ~21 of them, not 915.

`n9_create_calc_columns.js` **refuses to run** until that column exists, and refuses again
if it finds it is itself a Calculated column — which would reintroduce the `TODAY()` freeze
this whole port exists to get past.

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

### Part 1 · Estimated Delivery Date as a stored column — the prerequisite

Not built yet. It needs the create-or-update trigger flow to compute it on change, plus a
small daily recurrence for the stalled rows. **Nothing below works until this exists.**

### Part 2 · The five calculated columns

```
scripts/n9_create_calc_columns.js      DRY RUN by default; set APPLY = true
```

Five, not two, because the chain is split so each piece is independently readable and
checkable in a view rather than buried in one unreadable formula:

| column | type | why it exists |
|---|---|---|
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
- **Estimated Delivery Date itself** — Part 1 above is the only remaining blocker, and it
  is a flow, not a column definition.
