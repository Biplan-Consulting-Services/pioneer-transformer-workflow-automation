# Status Date auto-stamp — spec for the Order Items trigger flow

Requirement (user, 2026-09-08): **when a staff member sets `Step Status`, `Status Date`
fills in with the date of the change.** Plus: `Step Status` becomes a **Choice** column.

This is a change to the **Order Items trigger flow** (`When an item is created or
modified`), *not* the Excel transfer flow. Those are two different flows and it matters:
the transfer flow must never write these columns (see
`n8-transfer-flow-interaction-2026-09-08.md`).

## 🔴 Blocked on one thing: no export of this flow exists

`workflow-data/` holds a tracked version history for the **transfer** flow only. The
trigger flow has **never been exported**, so per this repo's own rule — *nothing modifies
a flow until the current definition has been snapshotted* — this cannot be authored yet.

**What's needed:** export the Order Items trigger flow as a `.zip`, then
`python scripts/flow_version.py snapshot <export.zip> --note "baseline pre Status Date stamp"`.
The versioning system already supports a second flow; it is one folder per flow.

Two changes then ride in on the same export, which is the right way round because they
touch the same actions:

| | |
|---|---|
| **`X3`** | strip the 2c stage-stamping (~100 actions → ~5). Already on the roadmap as a *capacity prerequisite* for N3. |
| **this** | add the `Status Date` stamp (~5 actions). |

⚠️ **Do not add this stamp to the flow as it stands.** 2c's stage-stamping is what put the
flow at 100+ actions and helped wedge it against the capacity cap. Strip first, add second,
or this small feature inherits that whole problem.

## The hard part: SharePoint's trigger gives you no previous value

"When a status is **set**" cannot be read off the trigger payload. The SharePoint trigger
hands you the item's *current* state only — there is no `oldValue`, and a trigger condition
cannot compare against one either. So "did `Step Status` change?" has to be answered some
other way.

**Recommended: the `Get changes for an item or a file (properties only)` action.** It is
built exactly for this — given a version to compare against, it returns a per-column
"has changed" boolean, so the flow asks SharePoint the question instead of maintaining its
own bookkeeping.

```
Trigger:  When an item is created or modified   (list: Order Items)
   |
   +-- Get changes for an item or a file (properties only)
   |      Id    = triggerOutputs()?['body/ID']
   |      Since = sub(int(triggerOutputs()?['body/{VersionNumber}']), 1)
   |
   +-- Condition:  the Step Status column changed  AND  Step Status is not blank
   |
   +-- (true) Update item
          Status Date = formatDateTime(
                          convertFromUtc(utcNow(), 'Eastern Standard Time'),
                          'yyyy-MM-dd')
```

🔎 **Confirm the change-flag's exact property name from one real run before building on
it.** The action's output shape is not documented per-column, and this repo has been bitten
by exactly this: `Planned Delivery Date` wrote nothing at all because a name was retyped
rather than read from the platform, and the N3 internal names turned out to be actively
misleading (`Pioneer Model Code` is `Model`, `Model Description` is `Description`). Do not
guess it.

**Fallback if that action does not behave:** a shadow column `StepStatusStamped` holding
the last-stamped value; stamp when `Step Status ≠ StepStatusStamped`, writing both. Costs
one hidden column but needs nothing undocumented. Keep it in reserve, not as the first
choice.

## Three traps, each of which fails silently

**1 · The self-retrigger loop.** The flow writes to the item it triggered on, so the write
fires the trigger again. This is *self-limiting* with the guard above — the second run sees
`Step Status` unchanged and does nothing — so it costs one extra cheap run per edit, not a
loop. But it is only self-limiting **because** of the change guard. Without it: infinite.

Consider also a **trigger condition** so touch-only updates never create a run at all.
`R12` already notes this is free — conditions are evaluated *before* a run exists.

**2 · The date must be written site-local, not UTC.** This is `R6`/`R12`'s bug waiting to
happen again. `utcNow()` after ~20:00 Eastern is **already tomorrow**, so a staff member
setting a status at 9pm would get tomorrow's date stamped. Hence `convertFromUtc(...,
'Eastern Standard Time')` — the Windows zone id, which handles DST — formatted as a **bare
`yyyy-MM-dd`**. A Date-Only column receives a bare date as site-local midnight (verified:
552 rows at `04:00Z` + 416 at `05:00Z`, the DST split); a full instant stores UTC midnight
and renders as *the previous day*, which is the exact defect the whole backfill existed to
fix.

**3 · Do not let it overwrite a historical date.** `N8` back-fills `Status Date` for the
247 rows that already carry a composite. If this flow's first run stamps *today* over
those, the migrated history is destroyed. The `Step Status`-changed guard is what prevents
it — N8 writes both columns in one PATCH, so the next trigger run sees `Step Status`
unchanged relative to the version N8 wrote. Worth verifying on **one** row before enabling
the flow over the whole list.

## `Step Status` as a Choice column — done, and it is the right call

✅ Applied to `scripts/n8_split_status.js`. It **reverses** that script's earlier stated
decision, which cited `N2`'s rule that a synced Choice *"silently rejects any value outside
its option list, per row"* — the `Family` failure mode.

That rule is real, but it governs columns a **flow writes from an open-ended external
source**. `Step Status` is neither:

- the vocabulary is **closed at 8 values**, from FRM10-12's own authoritative
  `TableValidationStatusCode` — and only **5** occur in the data (`Terminé` 180,
  `En cours` 58, `Bobine 1` 5, `Bobine 2` 2, `Bobine 3` 2);
- after N8's one-time write, **nothing writes it but staff**. The transfer flow must not,
  and this stamp writes the *date*, not the status.

So the rejection hazard has no path in, and Choice buys what Text cannot: a dropdown
instead of free text, no typos, and real grouping, filtering and colour formatting.

🔑 **The option list is generated from the same `PREFIX` table the parse uses**, so the
options and the values written cannot drift apart — a hand-typed second copy is precisely
how a Choice write starts failing per row. `FillInChoice="FALSE"`, since "allow custom
values" would hand back the free text this change removes.

The script now also **proves every value it is about to write is a valid option before
writing any of the 247 rows**, and warns if it finds `Step Status` already existing as Text
from an earlier run.

```
<Field Type="Choice" DisplayName="Step Status" Name="StepStatus" StaticName="StepStatus"
  Required="FALSE" Group="Status Split" Format="Dropdown" FillInChoice="FALSE"><CHOICES>
  <CHOICE>Attente</CHOICE><CHOICE>En cours</CHOICE><CHOICE>Réparation</CHOICE>
  <CHOICE>Manque Pièces</CHOICE><CHOICE>Terminé</CHOICE><CHOICE>Bobine 1</CHOICE>
  <CHOICE>Bobine 2</CHOICE><CHOICE>Bobine 3</CHOICE></CHOICES></Field>
```

⚠️ **`Status` (the composite) stays Text and stays put.** FRM11's purge rule parses that
format — `Text.Contains([Status.1], "TE")`. `Step Status` is additive, not a replacement.
