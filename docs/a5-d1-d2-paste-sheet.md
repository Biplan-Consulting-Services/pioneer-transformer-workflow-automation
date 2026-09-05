# A5 D1 / D2 — the six mappings, paste-ready

Generated 2026-09-05. **Every name on both sides was read, not typed:**

- **Target** internal names come from the `ListSchema` record at the top of
  `sharepoint-lists/Order Items 2026-09-05 1432.csv`.
- **Source** keys come from a real Excel-connector payload,
  `workflow-data/Excel Table list items raw output.json` (256 rows, 85 columns).

This matters more than it sounds. See the warning under `Protector & Switchgear Item #`.

Add each to **both** `CreateOrderItem` and `UpdateOrderItem`.

## The mappings

| Order Items column | Internal name (target) | Type | Excel key (source) |
|---|---|---|---|
| `Info+` | `Info_x002b_` | Text | `Info+` |
| `Technical Notes` | `Technical_x0020_Notes` | Note | `Technical Notes` |
| `Protector & Switchgear Item #` | `Protector_x0020__x0026__x0020_Sw` | Text | `Protector & Switchgear Item _x0023_` |
| `Configuration` | `Configuration` | Text | `Configuration` |
| `Section Qty` | `Section_x0020_Qty` | Number | `Section Qty` |
| `Order_Number_TextField` | `Order_Number_TextField` | Text | *(from the existing `OrderNumberText` Compose, not Excel)* |

> 🔴 **`Protector & Switchgear Item #` is the one that will bite.** Its internal name is
> `` Protector_x0020__x0026__x0020_Sw `` — SharePoint escaped it and then **truncated at 32 characters**, so it
> stops mid-word and looks nothing like the display name. Type it out or guess the escape and
> the mapping writes **nothing, silently** — exactly how `Planned_x0020_Delivery_x0020_Dat`
> failed once already. And because this column is expected to land **0 populated** (it is blank
> at source), a silent failure here would never show up in verification. **Verify the mapping
> exists by reading the write action's raw inputs in run history, never by counting values.**

## Expressions

### `Info+`  →  `Info_x002b_`

```
@item()?['Info+']
```

### `Technical Notes`  →  `Technical_x0020_Notes`

```
@item()?['Technical Notes']
```

### `Protector & Switchgear Item #`  →  `Protector_x0020__x0026__x0020_Sw`

```
@item()?['Protector & Switchgear Item _x0023_']
```

### `Configuration`  →  `Configuration`

```
@if(or(equals(trim(string(item()?['Configuration'])), ''), equals(trim(string(item()?['Configuration'])), '00:00:00')), null, item()?['Configuration'])
```

### `Section Qty`  →  `Section_x0020_Qty`

```
@if(equals(trim(string(item()?['Section Qty'])), ''), null, int(item()?['Section Qty']))
```

### `Order_Number_TextField`

```
@outputs('OrderNumberText')
```

One mapping, no extra connector calls — and with the TextField sync flows off, this is what
keeps Order Number populated on every backfilled row.

## Two guards that are load-bearing

- **`Configuration`'s `00:00:00` test.** Nine rows hold an Excel *time* value rather than text.
  Without the guard those write `00:00:00` into a Text column. The column is `Text`, not Choice,
  so there is no rejection to warn you.
- **`Section Qty`'s blank test.** An empty string fed to `int()` throws, and that throw surfaces
  as `Action 'Switch' failed` — indistinguishable at a glance from the A5c bug.

## Do NOT map

- **`BO`** (internal `BO`, Choice). It is SharePoint-native now. It comes from `TableBO` in
  BO Manager as a **one-time** transfer (D3), and the mapping is **removed after that run**.
  Sourcing it from `TableOrders` would null the 73 imported rows.
- **`Bo Sort Date`** — unrelated to `BO`, and mapping it was a documented mistake.
- Anything that touches a **List Name dropdown**. Re-selecting one has wiped every mapping on
  both write actions before.

## Verify

Expected populated counts after the run — from the source workbook, not guesses:

| Column | Expect |
|---|---|
| `Info+` | ~96 |
| `Technical Notes` | ~6 |
| `Configuration` | ~491 |
| `Section Qty` | ~112 |
| `Protector & Switchgear Item #` | **0 — verify the mapping exists, never by count** |
| `BO` | **still 73, unchanged** |
