# Trigger flow `v002` — paste sheet

`workflow-data/Order Items - Create or Update Trigger flow/_outbox/PASTE-ME.json`

Two changes in one version, because the spec says the stamp must never be added to the
flow as it stands: 2c's stage-stamping is what put this flow at **131 actions** and helped
wedge it against the capacity cap.

> ⚠️ The generic `PASTE-ME.md` beside the file lists `CreateOrderItem` / `UpdateOrderItem`
> field counts. Those are the **transfer** flow's actions and do not exist here — ignore
> that table and use this one.

## What changed

| | v001 | v002 |
|---|---|---|
| top-level actions | 59 | **7** |
| total actions | **131** | **11** |
| `Update_item` field writes | 27 | **6** |
| `Condition_3` runAfter predecessors | 9 | 2 |

**Deleted (54 actions):** every stage date/status variable (23 `InitializeVariable`;
`vUpdateOrderItem` survives) and all 31 stamping blocks — `Condition_1*`, `Condition_2`,
`Condition_4*`, `Condition_5*`. And 23 stage fields dropped from `Update_item`.

**Survivors:** `Initialize_variable` → `Initialize_vStatusDateValue` → `Get_Client` →
`Get_Model` → `Condition` → `Condition_StatusDate` → `Condition_3` → `Update_item`.

**Added:** `Initialize_vStatusDateValue`, `Condition_StatusDate`, and two writes —
`item/StatusDate` and `item/StepStatusStamped`.

## How the stamp knows the status changed

A SharePoint trigger gives you the item's **current** state only. There is no previous
value, and a trigger condition cannot see one either.

But this flow already answers that exact question for four other fields: `Condition`
compares `OrderNumber/Value` against `Order_Number_TextField`, and three more like it. So
the stamp reuses that idiom rather than introducing a new mechanism — a text mirror,
`StepStatusStamped`, created **and pre-filled** by `scripts/n8_split_status.js`.

🔴 **N8 must run first.** If `Step Status` is populated and `Step Status Stamped` is not,
the first touch of each of those 247 rows looks like a change, stamps *today*, and the
status dates N8 just migrated are gone. N8 now writes the mirror equal to the status and
verifies it, so every migrated row starts in agreement.

## Why it does not loop

The write modifies the item, which fires the trigger again. On that second pass
`Step Status` equals its mirror, so `vStatusDateValue` stays `''`, the TextFields also
match, `vUpdateOrderItem` stays `false`, `Condition_3` is false — and **nothing is
written**. One extra evaluation, no loop. It is bounded *because* of the change guard, not
by luck.

Verified by evaluating the authored conditions against real trigger bodies, six scenarios:

| scenario | writes? | `Status Date` |
|---|---|---|
| steady state | no | — |
| staff sets `Step Status` = `En cours` | **yes** | **2026-09-09** |
| the self-retrigger straight after | **no** | — |
| a TextField drifted, status unchanged | yes | `null` → **existing date survives** |
| an N8-migrated row | **no** | untouched |
| row with no `Step Status` | no | — |

The `null` on the unchanged path is safe *because* the connector does not clear a field
passed `null` — the R14 finding, proven by 844 stale `Pending` statuses surviving a full
rewrite. Here that behaviour is exactly what is wanted.

## The one deviation from the code already here

2c wrote `@convertFromUtc(utcNow(), 'Eastern Standard Time')` — an unformatted local
datetime. `v002` writes:

```
@formatDateTime(convertFromUtc(utcNow(), 'Eastern Standard Time'), 'yyyy-MM-dd')
```

A Date-Only column takes a **bare date** as site-local midnight (verified: 552 rows at
`04:00Z` + 416 at `05:00Z`, the DST split). A fuller naive string depends on how the
connector reads it — and while both readings land on the same Eastern day for most of the
clock, they do **not** between midnight and 04:00 Eastern, where a naive string read as
UTC renders as the previous day. That is `R6`'s day-early bug in a new place. The bare
date removes the question rather than betting on the answer.

## Check these after pasting

1. **Action count is 11**, not 131. If the designer still shows dozens of
   `Set variable` blocks, the paste did not take.
2. **`Update_item` writes exactly 6 fields**: the four `*_TextField` mirrors,
   `StatusDate`, `StepStatusStamped`. No `CoilingDate`, no `*Status/Value`.
3. **`Condition_3` runs after `Condition` and `Condition_StatusDate`** — nothing else.
4. **`Condition_StatusDate`** compares `StepStatus/Value` against `StepStatusStamped` and
   contains the `formatDateTime(convertFromUtc(...))` expression.
5. **The connection is unchanged.** `connectionReferences` is carried through untouched,
   so pasting should never re-bind anything. If the designer asks you to re-pick a
   connection, stop — that is the failure mode that once wiped every field mapping.

## Do not turn it on yet

The flow is `Off` (`C1`) and should stay off until:

- `N8` has run (creates and fills the three columns), and
- `X1` / `X2` have run, since they write in bulk and would each trigger a run per row.

Then re-enable and watch for 15 minutes (`X4`). At 11 actions a flood drains in minutes
rather than wedging for days — which is the whole point of doing X3 first.

## Closing the loop

Save in Power Automate, copy the JSON back into `_inbox/`, and say so. `intake` confirms
by hash: match → `v002` flips to `applied`; mismatch → `forked`, and I report exactly what
differs. It stays `local` until an export proves it landed — a paste cannot prove itself.
