# `Model Revisions.ModelID` — 29 corrupt rows, found and repaired 2026-09-14

Found while testing the `Order Items` trigger flow on the night of 2026-09-14, repaired the
same night. **The flow was never at fault.** Three separate diagnoses said it was, and all
three were wrong; the notes below exist because each one would have broken something that
worked.

## What was wrong

29 rows on `Model Revisions` held **their model's code** in `ModelID`, where their own
revision id belongs:

| | |
|---|---|
| revision 344 `ModelID` | `M-HYQU-0092` |
| should have been | `MR-HYQU-0092-V1` |

`ModelID` on `Model Revisions` **is** the revision identifier — 348 of 393 rows held proper
`MR-…` values — and the `Model Revision` lookup's `ShowField` resolves to it. So the trigger
flow's `@triggerBody()?['ModelRevision/Value']` was reading exactly the right field and
faithfully mirroring a corrupt source into `Order Items.Model_Revision_ID_TextField`.

## How it surfaced

Step 9 of the evening runbook changed the step on a healthy unit and watched what the flow
wrote. `21408-1/1` went `MR-HYQU-0092-V1` → `M-HYQU-0092`.

🔑 **The stale mirror was more accurate than the live list.** The `*_TextField` sync has
been off since **2026-08-21**; revision 344 was corrupted on **2026-09-01**. So the Order
Items mirror still carried the pre-corruption value, and the flow "overwriting" it was the
first visible symptom of damage done two weeks earlier. This is the reverse of the
assumption this repo has worked from since August — that the mirrors are the unreliable
copy.

## Three wrong diagnoses, in order

Recorded because the pattern is the point, not the individual mistakes.

1. **"The flow writes the model's id into the revision's mirror — fix the mapping."**
   Wrong. It reads the revision row's own field.
2. **"No field on `Model Revisions` holds `MR-` values, so there is nothing to source from
   — stop the flow writing that column."** Wrong. 348 rows hold them. The check had looked
   at one row, and that row was one of the 29 broken ones.
3. **"The suspect set is 45 rows and the SA models are implicated."** Wrong. `/^MR-/`
   rejects `MRSA-HYQU-0064-V1`, a *correct* id for an SA model. The real set was 29, and
   the SA revisions were the healthy ones — the conclusion was inverted.

**Every one came from reasoning about field *names* or *patterns* instead of reading
values.** `lookup-textfield-reference.md` contributed directly: it names a source field
`Model_Revion_ID` that does not exist, calls `Client_ID_TextFiel` by a name it does not
have, and prescribes a Get-item pattern for a field that needs none. That document now
carries a warning banner; it was built from CSV exports, which omit every Lookup's values
*and* schema.

## The repair

`scripts/x18_repair_revision_modelid.js`. A revision id is derivable — its model's code with
an `R` inserted after the leading `M`, plus `-V1`:

```
M-HYQU-0092    ->  MR-HYQU-0092-V1
MSA-HYQU-0064  ->  MRSA-HYQU-0064-V1
```

`-V1` always, because there is no `-V2` in this list (user, 2026-09-14). The script **checks
that rule before relying on it** — 0 healthy revisions ending in anything but `-V1`, 0
models carrying more than one revision — and refuses to run if either is non-zero.

**Result: 29 written, 0 failed, 29/29 verified by individual re-read, 0 rows still
mismatching their model.**

### Two near-misses the guards caught

- **A trailing newline.** Model id 503 stores `"M-FIEN-0004\n"`. Invisible in every report
  — the drift check printed `mirror=M-FIEN-0004 live=M-FIEN-0004`, which looked like a false
  positive. It made an already-correct revision (377) read as broken and proposed
  `"MR-FIEN-0004\n-V1"` as its repair. **No validation would have caught that write**: the
  bad value matched its own derived prefix, because the prefix carried the newline too. Only
  the console wrapping the proposal onto a second line revealed it.
- **Deriving the fix from a mirror.** The first version resolved the model code from
  `Pioneer_Model_Code_TextField` — a `_TextField` mirror, in a script written to repair
  damage caused by trusting mirrors. It now resolves through the `ModelId` lookup against
  the live `Models` list.

## Still open

| | |
|---|---|
| **~724 `Order Items` mirrors** | still hold the old value. The flow refreshes each unit's mirror only when that unit is next edited, so this self-heals slowly and now spreads the **correct** value. Run `x16_audit_lookup_mirrors.js` to measure; a backfill would be the same shape as `x11`. |
| **Model id 503** | `ModelID` = `"M-FIEN-0004\n"`. Cosmetic until something joins on it — and FRM10-12 reads `Models` directly through Power Query, where a trailing newline breaks an exact-match join silently. |
| **Revision 417** | orphaned: no `Model` lookup, empty `ModelID`, `ModelName` = `100311916` (looks like a part or order number). Fix by **setting its Model lookup** and re-running x18. Do not hand-type an id. |
| **Revisions 414–416, 419–422** | seven more with no `Model` lookup. Their ids are already correct, so they are not urgent, but nothing can verify them until the lookup is set. |
| **What corrupted them** | unknown. 35 of the suspects were last modified **2026-09-11**, cutover day, and `EditorId 106` accounts for 43 of 45 — but `Modified` records the last touch, not the damage. Worth establishing before the next bulk operation on this list. |

## For anyone working this list

- **Read lookups directly** (`_api/…/items?$select=…Id`), never the `*_TextField` mirrors.
  The mirrors are unmaintained between 2026-08-21 and whenever each row is next edited.
- **A failed `$select` returns 400**, and `j.value||[]` turns that into zero rows — which
  reads as "nothing wrong" rather than "broken query". Probe field names and abort loudly.
- **Trim everything** before comparing or deriving. At least one code carries a newline.
- `x17_audit_revision_modelid.js` audits the revisions; `x16_audit_lookup_mirrors.js` audits
  the Order Items side.
