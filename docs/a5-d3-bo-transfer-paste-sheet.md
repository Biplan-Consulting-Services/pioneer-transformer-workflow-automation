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

---

## Resolved and authored 2026-09-07 — `scripts/apply_d3.py`, version **v004**

This sheet left three things open. All three are now answered, and D3 is authored rather than
pasted by hand.

### The connector parameters, resolved live

| | |
|---|---|
| `source` | `sites/ermcopower.sharepoint.com,88b9ed6c-…511f6,7f8472f6-…3e6bcc` |
| `drive` | `b!bO25iIbWvku0RU51OtUR9vZyhH-JipFFoRaYoXg-a8zPqBmaybwgS5qVv6sntK64` |
| `file` | `01DI2JQP7NBWFPJE6RMBFL5PPWQWB7HUO7` |
| `table` | `{3580DC32-2968-4A81-A234-0D14634618E2}` |

🔴 **The path in this sheet was wrong.** It is `General/FAB/Achat/**BOs**`, plural — there is no
`Achat/BO` folder. The `BOs` folder holds `BO Manager.xlsx` and a `test` folder.

**Where the table GUID comes from, and why it can be trusted.** The Excel Online connector's
`table` parameter is the table's **`xr:uid`** from the workbook XML. Confirmed rather than
assumed: `TableOrders`'s `xr:uid` in FRM10-12 is `{72371618-48E3-4FA4-B667-3B76BFA2D42A}`, which
is character-for-character the `table` value the live flow already uses. `TableBO`'s is the value
above. ⚠️ Read from the 2026-09-03 local snapshot — `xr:uid` is stable across saves and only
changes if the table is deleted and recreated, but a wrong id fails the action loudly rather than
silently, so the D4 smoke test settles it.

### 🔴 `TBD` in the date columns — a second EC-shaped landmine

The date columns are not clean:

| column | populated | non-date values |
|---|---|---|
| `BO1 Date` | 39 | **`TBD`** on `21838-1/5`, `21840-1/10` |
| `BO2 Date` | 17 | **`TBD`** on `21521-1/1` |
| `BO3 Date` | 5 | none |

`int('TBD')` throws, and the throw surfaces as `Action 'Switch' failed` — the same signature as
the EC bug. **And the part-number guard does not catch it:** all three rows carry a part number,
so the group guard passes and the value reaches the conversion. Both guards are required, and the
`TBD` test is **case-insensitive** for exactly the reason `'EC'` was not.

### The group guard is otherwise sound

Checked across all three groups: **zero rows** carry a `BO{n} Date` without a `BO{n} Part Numbre`.
So guarding a group on its part number really does cover the whole group.

### Shape of the change

| | v002 | v004 |
|---|---|---|
| top-level actions | 5 | **6** — adds `List_rows_present_in_a_table_BO` |
| in-loop actions | 10 | **11** — adds `Filter_BO` |
| `CreateOrderItem` `item/*` | 50 | **75** |
| `UpdateOrderItem` `item/*` | 58 | **83** |
| `toLower(` | 28 | **34** — 3 TBD guards × 2 write actions |

The chain is spliced, not appended: `List_rows → List_rows_BO → Filter_array → … → Apply_to_each`,
and in the loop `RawOrder → Filter_BO → IsSA → …`. `apply_d3.py` asserts the rewiring held and
that nothing outside the two new actions and the two parameter objects moved.

