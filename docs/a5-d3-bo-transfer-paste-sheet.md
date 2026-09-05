# A5 D3 — the one-time BO transfer, paste-ready

Generated 2026-09-05 (`scripts/gen_d3.py`). **Both sides read, not typed:** `TableBO` headers
from `BO Manager.xlsx`, target internal names from the Order Items export's `ListSchema` record.

## The source

`BO Manager.xlsx` → sheet **`Sheet1`**, table **`TableBO`**, ref **`B5:X1019`** — header on row 5,
**1014 data rows**, 23 columns. Live path: `General/FAB/Achat/BO`.

**Join key is `Order`**, which matches `Order Items.Title` exactly, including the ` SA` suffix.

## 🔴 This mapping is removed after the run

The transfer flow is re-runnable. Left in place, every future run overwrites SharePoint-native BO
edits with whatever the workbook held — so **D3 and R7 are a pair**: add it, run once, take it out.
R7 already covers removing it alongside the five `Order` companion writes.

And never source `BO` from `TableOrders`. FRM10-12's `BO` column is itself pulled from BO Manager,
so it is a stale second-hand mirror — that is the 69-vs-76 gap.

## Shape of the data

| | |
|---|---|
| `BO` populated | **76** of 1014 |
| …values | `OK` 65, `BO` 11 |
| `BO1 Part Numbre` populated | 39 |
| `BO2 Part Numbre` populated | 17 |
| `BO3 Part Numbre` populated | 5 |

⚠️ **Do not blind-map the `BO{n} OK` booleans.** Their distribution:

| Column | Values |
|---|---|
| `BO1 OK` | `False` 988, `True` 26 |
| `BO2 OK` | `False` 1004, `True` 10 |
| `BO3 OK` | `False` 1011, `True` 3 |

Mapping them unconditionally writes a value to **every** row and makes units look like they carry
BO data. This is the same trap that produced a bogus "626 expected" figure earlier — counting
Boolean `FALSE` cells as populated. **Only write a `BO{n} …` group where that group's
`Part Numbre` is non-blank.**

## Flow shape

Add a second `List rows present in a table` **before** the `Apply to each`, pointed at `TableBO`.
Inside the loop use a `Filter array` — the flow already uses that pattern, so no second nested
loop and no extra connector calls per row:

```
Filter array   From:  body('List_rows_present_in_a_table_BO')?['value']
               Where: item()?['Order']  is equal to  <the current RawOrder>
```

Then read the matched row with `first()`. Guard every field on the match existing —
`first()` of an empty array is null, and a null fed to a Choice write fails the row.

## Mappings

| Order Items column | Internal name | Type | `TableBO` column |
|---|---|---|---|
| `BO` | `BO` | Choice | `BO` |
| `BO1 Part Numbre` | `BO1PartNumber` | — | `BO1 Part Numbre` |
| `BO1 Description` | `BO1Description` | — | `BO1 Description` |
| `BO1 PO Intern` | `BO1POIntern` | — | `BO1 PO Intern` |
| `BO1 Date` | `BO1Date` | — | `BO1 Date` |
| `BO1 Fournisseur Interne` | `BO1Fournisseur` | — | `BO1 Fournisseur Interne` |
| `BO1 OK` | `BO1OK` | — | `BO1 OK` |
| `BO2 Part Numbre` | `BO2PartNumber` | — | `BO2 Part Numbre` |
| `BO2 Description` | `BO2Description` | — | `BO2 Description` |
| `BO2 PO Intern` | `BO2POIntern` | — | `BO2 PO Intern` |
| `BO2 Date` | `BO2Date` | — | `BO2 Date` |
| `BO2 Fournisseur Interne` | `BO2Fournisseur` | — | `BO2 Fournisseur Interne` |
| `BO2 OK` | `BO2OK` | — | `BO2 OK` |
| `BO3 Part Numbre` | `BO3PartNumber` | — | `BO3 Part Numbre` |
| `BO3 Description` | `BO3Description` | — | `BO3 Description` |
| `BO3 PO Intern` | `BO3POIntern` | — | `BO3 PO Intern` |
| `BO3 Date` | `BO3Date` | — | `BO3 Date` |
| `BO3 Fournisseur Interne` | `BO3Fournisseur` | — | `BO3 Fournisseur Interne` |
| `BO3 OK` | `BO3OK` | — | `BO3 OK` |

> **`BO` is a Choice** with options `BO`, `OK` and **fill-in `FALSE`**. Anything outside that domain is
> rejected — per row, silently, inside the loop. `TableBO`'s `List` sheet confirms the domain is
> exactly `BO`/`OK`, so it lines up today; it is worth re-checking if anyone edits the workbook.

## Expressions

Take `Filter_BO` as the name of the Filter array. For the roll-up:

```
@if(empty(body('Filter_BO')), null, first(body('Filter_BO'))?['BO'])
```

For each detail field, guarded on that group's part number being present:

```
@if(or(empty(body('Filter_BO')),
      equals(trim(string(coalesce(first(body('Filter_BO'))?['BO1 Part Numbre'], ''))), '')),
   null, first(body('Filter_BO'))?['BO1 Description'])
```

Same shape for `BO2`/`BO3`, swapping the group prefix in both places. The source really is spelled
**`Numbre`** — that is the workbook's spelling and the SharePoint column matches it, so it is not a
typo to fix here.

## Verify

Afterwards, count `BO` populated on `Order Items`. Track B's earlier import covered **73**; the
real source holds **76**, so expect the gap to close rather than the number to stay put. Anything
far above that means the roll-up was sourced from the wrong table.
