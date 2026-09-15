# 🔴 The trigger flow can silently ERASE `Status Date` — found 2026-09-14, unfixed

**Read this before re-enabling the `Order Items` create-or-update trigger flow.**

Predates v004. The same expression is in **v003 and v005**, so this is not something the
lookup-guard work introduced, and it was live during the 09-11 enable attempt.

## The bug

`Update_item` writes:

```
item/StatusDate:  @if(equals(variables('vStatusDateValue'), ''), null, variables('vStatusDateValue'))
```

`vStatusDateValue` initialises to `""` and is set to today **only** inside
`Condition_StatusDate`'s true branch:

```
Condition_StatusDate =
      StepStatus is not null
  AND StepStatus is not ''
  AND StepStatus  ≠  StepStatusStamped        <- i.e. the step actually changed
```

So when the step has **not** changed, the variable stays `""` and the expression writes
**`null`** — which **clears the column**.

Meanwhile `Update_item` does not run only on step changes. It runs whenever `Condition`
(the four `_TextField` mirror comparison) fails, via `Set_variable_16` → `vUpdateOrderItem
= true` → `Condition_3`. The two are independent.

### The destructive combination

> **a mirror needs refreshing, AND the step did not change**
> → `Update_item` fires to fix the mirror
> → `Condition_StatusDate` is false
> → `Status Date` is written as `null` and **erased**

The everyday path is safe: change a step, the row drifts, the condition is true, the date
is stamped. Steps 8 and 9 of the evening runbook both passed for that reason. **The happy
path cannot catch this.**

## How it was caught

Restoring the two test units (`x15`) put `21408-1/1` back to `Terminé`. Its
`Status Date` came back **empty** where `22021-14/20` came back correctly stamped. The
difference: id 4's `Model_Revision_ID_TextField` still disagreed with its revision, so the
flow updated the row to refresh the mirror — with no step drift.

⚠️ **The `x18` revision repair armed this.** Correcting revision 344 to `MR-HYQU-0092-V1`
made every Order Items mirror still holding `M-HYQU-0092` disagree again. Until each unit's
mirror is refreshed, any edit that does not change its step will erase its `Status Date`.
**Roughly 724 units point at a repaired revision.**

## Confirmed ONE-SHOT per row, not a loop — measured 2026-09-15 03:4x

Version trail of `21408-1/1` (id 4), flow running throughout:

| ver | time (Z) | `Status Date` | |
|---|---|---|---|
| 35.0 | 03:31:11 | 2026-09-14 | flow stamps after a step change — correct |
| 37.0 | **03:38:53** | **(EMPTY)** | the flow, moments after `x18` repaired revision 344 |
| 38.0 | 03:41:56 | 2026-07-16 | restored by hand — **and it survived the next poll** |

The write that erased the date **also refreshed the mirror** to `MR-HYQU-0092-V1` in the
same `Update_item`. With the mirrors matching again, `Condition` passes, `Update_item` never
fires, and the row is stable.

**So each affected row loses its `Status Date` exactly once** — on the first trigger after
the mirror goes stale, if that edit does not change the step — and is then safe.

⚠️ A prediction that the clearing would repeat was made and was **wrong**. It is bounded
damage, not a runaway. That lowers the urgency; it does not make it harmless, because the
erased value is a real hand-entered date and nothing announces its loss.

🔑 **This also validates the staff instruction.** "Change the step, leave the date alone, and
if the real date differs correct it *after* the stamp lands — it sticks." Tested on both
units: the corrections held through a full poll with the flow live. Staff can be told this.

## R14 is false for this column

The design relied on **R14 — "the connector ignores a null rather than clearing the
field"** — which is why writing `null` looked like a safe way to say "leave it alone". That
observation is recorded in `x10_trigger_flow_gate.js`'s Gate B notes and is what made the
`coalesce` work on the other mirrors look like belt-and-braces.

**For this DateTime column it does not hold: the null cleared a populated field.** Anywhere
else that reasoning was applied should be re-checked rather than trusted.

## The fix (v006, not yet authored)

One expression — keep the row's existing value instead of writing null, the same shape the
other mirrors already use:

```
item/StatusDate:
  @if(equals(variables('vStatusDateValue'), ''), triggerBody()?['StatusDate'], variables('vStatusDateValue'))
```

### How to test it — NOT the happy path

Testing a step change proves nothing here; that path already works. The test is:

1. a unit whose `Step Status` **does not change**
2. whose `_TextField` mirror **does** disagree (any unit pointing at one of the 29 repaired
   revisions qualifies)
3. edit any other field to fire the trigger
4. confirm `Status Date` is **unchanged**, and the mirror **was** refreshed

### Sequence for tomorrow

1. author v006, assert the diff is that one expression and nothing else
2. paste it — **the editor wrapper** (`_outbox/alternate-shapes/definition-plus-connections.json`),
   not the bare definition; a bare definition drops `connectionReferences` and is silently discarded
3. re-enable, then **touch the test row a second time several minutes later** —
   `GetOnUpdatedItems` ignores the first edit after being switched on
4. run the no-step-change test above
5. **only then** backfill the ~724 stale mirrors. Backfilling before v006 would fire this
   bug on every row it touches.

## Status

**The flow should be OFF until v006 is applied.** Staff entered `Status Date` by hand for
the three days the flow was disabled and can continue to; the handover already records that
as acceptable. Losing dates that are already entered is not.
