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
| **No volatile functions, no Hyperlink output** | 🔴 stands, and it is what splits the remaining work in two. |

The two Excel lookup tables were never the obstacle they looked like: `TableCanadianProvince`
is 13 province codes that have not changed since 1999, and `Table_USD_CAD_Conversion_Rate`
is six rows. Both are inlined. A SharePoint list around either would be ceremony.

`Archived` is out — deprecated per the user, and the workbook has no formula left for it
anyway (6 of the 7 flagged columns carry a `calculatedColumnFormula`; `Archived` does not).

## The six split cleanly into two kinds

| column | kind | becomes |
|---|---|---|
| `Price` | UI — `HYPERLINK()` | column formatting on the **existing** `Order - Price` column |
| `Navigation Order` | UI — `HYPERLINK()` | column formatting on a new empty Text column |
| `Navigation Model` | UI — `HYPERLINK()` | column formatting on a new empty Text column |
| `Price CAD` | data — money | **calculated column** |
| `Price USD` | data — money | **calculated column** |
| `Estimated Delivery Date` | data — volatile | **stored column + flow** — see below |

**The three UI columns were never data.** They are hyperlinks into a filtered list view —
*"show me everything for this order"* — which is why they are **not** redundant with
SharePoint's lookup columns, despite `calculated-columns-plan.md`'s "drop `Price`"
recommendation. A lookup navigates to the single parent item; these navigate to a
**filtered view of all rows for that order**. Different question, still worth answering.

🔑 **The `Price` one comes out strictly better than Excel's.** `HYPERLINK()` in Excel
*replaced* the number with a link, losing it as a value. Column formatting paints over a
column that still holds real currency — so `Order - Price` stays sortable, filterable and
summable **and** gains the link.

## 🔴 The dependency that settles this morning's open question

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

## A correction worth recording

An earlier pass at this assumed `Order Items` carried **both** a native `Price` /
`Province/State` / `Initial Promised Date` and an N3-fanned `Ord*` copy, and treated
choosing between them as a decision for the user.

That was wrong. Those three columns are on the **`Order`** list. `column-reference.md`
says so plainly — if you read it by **section** rather than grepping the whole file, which
is what produced the wrong answer. `Order Items` has exactly one copy of each: the `Ord*`
one N3 puts there. There is no choice, and the fact that the port is possible at all is
*precisely because* N3 fanned them down.

`gen_calc_columns.py`'s verification is now section-aware. The already-shipped
`EstimatedDeliveryDate.format.json` was re-checked against the same rule: all 14 of its
fields are genuinely `Order Items` columns, so nothing there needed changing.

---

## Setup

### Part 1 · The three UI columns — do these now, they depend on nothing

1. **`Price`** — no new column. Open `Order - Price` → Column settings → **Format this
   column** → **Advanced mode**, paste `sharepoint-lists/formatting/Price.format.json`.
2. **`Navigation Order`** — add a **Single line of text** column with that exact name,
   leave it empty forever, format it with `NavigationOrder.format.json`.
3. **`Navigation Model`** — same, with `NavigationModel.format.json`.

Both navigation formats read the **`Order Number` lookup**, not `Order_Number_TextField`.
The mirror is written by the create-or-update trigger flow, which is **off** — so it is the
one field on the row that may be stale. A lookup cannot be.

### Part 2 · Estimated Delivery Date as a stored column — the prerequisite

Not built yet. It needs the create-or-update trigger flow to compute it on change, plus a
small daily recurrence for the stalled rows. **Do this before Part 3.**

### Part 3 · The five calculated columns

```
scripts/n9_create_calc_columns.js      DRY RUN by default; set APPLY = true
```

Five, not two, because the chain is split so each piece is independently readable and
checkable in a view rather than buried in one unreadable formula:

| column | type | why it exists |
|---|---|---|
| `Is Canadian` | Boolean | `TableCanadianProvince`, inlined |
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

- **`Province/State` holds `NO` on 1 row** — neither a US state nor a Canadian code, so it
  falls to the non-Canadian branch and prices in USD. Carried over from
  `calculated-columns-plan.md`; still worth a data check.
- **30 of 441 orders have no `Province/State`** and likewise default to USD. Confirm that
  default is right — it decides the currency on real invoices.
- **Navigation labels are French** (`UI_LANGUAGE` in the generator). Excel switched on a
  `SelectedLanguage` defined name; column formatting cannot see the viewer's UI language,
  so one had to be chosen. Related to the still-open question of whether anyone at Granby
  sees SharePoint in French at all.
- **FX rates stop at 2029.** `Fx Rate` returns 1.47 for anything later, which is correct
  until it silently is not. Add years to `FX` in the generator.
