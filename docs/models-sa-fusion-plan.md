# Models SA Fusion Plan

**Status:** decided in principle 2026-08-13, disambiguation design resolved the same day
(see below), migration itself not yet started.

## The decision

Fuse `Models SA` into `Models`/`Model Revisions` — SA (auxiliary) model designs become
regular `Models` rows with their own `Model Revisions` history, instead of living in a
separate, structurally-duplicated, never-versioned list.

## Why

- `Models`/`Model Revisions` already went through a deliberate split (identity/workflow
  fields on `Models`, versioned spec fields on `Model Revisions`) so spec changes get real
  history. `Models SA` never got that — it's still the old flat pre-migration shape, so SA
  designs have no revision history at all.
- Practical pain surfaced while building the Lookup→TextField sync flows
  (`lookup-textfield-reference.md`): `Models` and `Models SA` both need a `Client`-sync
  flow, purely because they're separate lists holding the same shape of data — duplicate
  work for no real benefit.
- Resolves a real gap found while discussing this: **`Order Items`' SA auxiliary row (the
  one with `SA Job = Yes`, e.g. `21408-1/1 SA`) has no lookup field pointing at `Models SA`
  at all right now** — user confirmed `Order.Model` always points at `Models`, never
  `Models SA`, regardless of SA status; the SA-specific model link was expected to live on
  the `Order Items` auxiliary row instead, but that field doesn't exist. Fusing removes the
  need for a separate field/mechanism entirely — once SA designs are just `Models` rows,
  the *existing* model-lookup mechanism covers them too.

## What this is NOT

`Order Items`' `SA Job` flag (marks a *physical production unit* as an auxiliary) is a
different axis from `Models SA` (a *model/spec* list) — don't conflate them. This fusion
doesn't touch `SA Job` or the production-tracking side of things at all.

## New requirement this creates

**Order-item generation must pick the right `Model` row.** User's own framing, 2026-08-13:
"it will be at the order item generation phase that it will be important to make sure and
take the right one." Once SA designs are indistinguishable from regular ones at the list
level (both just rows in `Models`), whatever creates the SA auxiliary `Order Items` row
(today: manual; later: the transfer flow, and eventually `phase1-plan.md`'s `Work Order`
fan-out logic) needs correct logic to resolve *which* `Models` row is the SA-specific
design for a given order — not just "the" model, since a main unit and its SA auxiliary
may need different model rows.

## Disambiguation design — decided 2026-08-13

**Confirmed by the user (who built the original `Models SA` logic): pairing is 1:1** —
each SA design belongs to exactly one specific main model, not shared/reused across
several. There is **no existing link column today** — this is new, not something already
built and overlooked; the only prior signal was which list a row lived in, plus the
`Model_Code` naming convention (`"4261870 SA"` implying `"4261870"`), never a real FK.

**New fields on `Models`** (not `Model Revisions` — this is an identity-level
classification, doesn't change revision-to-revision):
- `SA Model` (Yes/No, default No) — marks this row as an SA (auxiliary) design rather than
  a main one. **Not named `Model Type`** — that name's already taken by an unrelated
  existing spec field on both `Models` and `Models SA` (an oil/core/construction
  classification), confirmed by checking the live schema exports before naming this.
- `Parent Model` (self-referencing **Lookup** → `Models` itself) — populated only when
  `SA Model = Yes`; points at the specific main `Models` row this SA design pairs with.
  Blank for main rows. This is what lets order-item generation resolve "which SA model for
  this order" directly (`Models` row where `Parent Model = <the order's Model>`) instead of
  string-matching `Model_Code`.
- `Parent_Model_TextField` — companion text field, per the standing Lookup convention.

## Migration scope

1. ~~Design how to distinguish an "SA-type" `Models` row~~ — **done, see above.**
2. **Migration mapping — confirmed 2026-08-13, see below.** All 15 live `Models SA` rows
   (all `Client = HYDRO QUEBEC`) matched to their parent `Models` row.
3. Repoint anything referencing `Models SA`: `ColumnMap.pq`'s `Models SA` entity,
   `TableOrders.pq`'s merge logic (`#"Imported SA Models"`/`#"Complete Imported Models"`
   branch). **Nothing in live `Order`/`Order Items` data needs repointing** — confirmed
   earlier that `Order.Model` never pointed at `Models SA` in the first place, so there are
   no live lookups to a `Models SA` record anywhere; the only references are in Power Query
   code, not data.
4. Retire the `Models SA` list once nothing points at it anymore.
5. Build the order-item-generation logic that resolves the correct `Models` row (main vs.
   SA) for each unit — this is new logic, not just a repoint, since today `Models`/`Models
   SA` being separate lists was itself how "which one" got resolved (the list you queried
   told you which kind), a distinction the fusion removes.

## Migration mapping — confirmed 2026-08-13

Matched by exact `Model_Code` string after stripping `" SA"` — 11 of 15 matched cleanly,
4 needed the user's judgment call since `Model_Code` didn't line up exactly (typos/omissions
in the original data, not a matching-logic problem):

| `Models SA` row | Its `Model_Code` | → Parent `Models` row | Parent's `Model_Code` |
|---|---|---|---|
| MSA-HYQU-0001 | 4251081 SA | M-HYQU-0064 | 4251081 |
| MSA-HYQU-0002 | 4261859 SA | M-HYQU-0066 | 4261859 |
| MSA-HYQU-0003 | 4261871 SA | M-HYQU-0069 | 4261871 |
| MSA-HYQU-0004 | 426870 SA | **NEW placeholder `Models` row** | 426870 |
| MSA-HYQU-0005 | 4251082 SA | M-HYQU-0065 | 4251082 |
| MSA-HYQU-0006 | 4261865 SA | M-HYQU-0067 | 4261865 |
| MSA-HYQU-0007 | 4276087 SA | M-HYQU-0070 | 4276087 |
| MSA-HYQU-0008 | 4276699 SA | **NEW placeholder `Models` row** | 4276699 |
| MSA-HYQU-0009 | 4251001 SA | M-HYQU-0082 | 4251001 / 1166058 |
| MSA-HYQU-0010 | 4276269 (no " SA" suffix — confirmed a data-entry omission, not a different case) | M-HYQU-0071 | 4276269 |
| MSA-HYQU-0011 | 4261870 SA | M-HYQU-0068 | 4261870 |
| MSA-HYQU-0012 | TMP9 SA | M-HYQU-0092 | TMP9 |
| MSA-HYQU-0013 | G21523 SA | M-HYQU-0002 | G21523 |
| MSA-HYQU-0014 | 4251081/1166353 SA | M-HYQU-0076 | 4251081/1166353 |
| MSA-HYQU-0015 | 4251082/1166354 SA | M-HYQU-0077 | 4251082/1166354 |

**Two new placeholder `Models` rows, user's call, 2026-08-13**: rather than force-matching
`MSA-HYQU-0004`/`MSA-HYQU-0008` to the nearest-but-not-exact existing codes (`4261870`/
`4276691`, both already claimed by other rows), create two brand-new `Models` rows using
the SA row's own code (`426870`, `4276699`) as their `Model_Code` — mostly empty otherwise,
"just in case." **Logged as a new standing future review point** (same treatment as
`Trimestrial Customer`): revisit once there's usage history to tell whether these two
placeholders were genuinely needed or should be cleaned up/merged — don't wait to be
reminded.

**`kVA and kV` → `kVA` mapping, confirmed 2026-08-13**: `Model Revisions`' `Primary
Voltage`/`Secondary Voltage` fields aren't in use anywhere yet (system-wide, not just for
SA rows) — so every `Models SA` row's `kVA and kV` value goes straight into `Model
Revisions`' `kVA` field for now, `Primary Voltage`/`Secondary Voltage` left blank like
everywhere else currently. Revisit if/when those two fields ever go into real use.

## Migration checklist — ready to execute, confirmed 2026-08-13

**`Models`-level spec-field duplicates are legacy — confirmed by the user, who built the
original split.** `Models` still carries its own copies of `kVA and kV`, `Model Type`,
`Description`, `Oil Type`, `Oil Amount`, `Core Type`, `Phases`, `Cable`, `Form`, `Copper
(LV)`, `Wire (HV)`, `Overcoil` alongside `Model Revisions` having the same shape (`kVA`,
`Model Type`, `Model Description`, etc.) — these `Models`-level copies are legacy, **leave
them blank on new rows**. The real spec data goes on `Model Revisions` only, which is what
actually needs populating so the new SA-origin `Models` row has something real to link to
via `Latest Model Revision`.

**`Info+`/`Protector & Switchgear Item #`/`SFRA`/`Configuration`/`Section Qty`** exist on
`Models SA`/`Models` but have no `Model Revisions` equivalent — checked all 15 live
`Models SA` rows directly: every one is blank on every one of these fields, so there's
nothing to carry forward. Not a design gap, just nothing to migrate.

### Step 1 — schema additions on `Models` (manual, PnP still blocked)

| Field name | Type | Details |
|---|---|---|
| SA Model | Yes/No, default No | See "Disambiguation design" above. |
| Parent Model | **Lookup**, self-referencing → `Models` | Get information from: **Models** itself. In this column: **Model_ID** (or `Model_Code`, whichever `Order`/`Model Revisions`' existing Lookups use for `Models` — match that convention). Only populate for rows where `SA Model = Yes`. |
| Parent_Model_TextField | Single line of text | Companion text field, per the standing Lookup convention. |

### Step 2 — two new placeholder `Models` rows

Continue the `M-HYQU-####` sequence from whatever the current highest is (was `M-HYQU-0095`
as of the 2026-08-13 16:54 export — re-check the live list, more may have been added
since). Identity only, everything else blank:

| New Model_ID | Client | Model_Code | SA Model |
|---|---|---|---|
| (next in sequence) | HYDRO QUEBEC | 426870 | No |
| (next in sequence) | HYDRO QUEBEC | 4276699 | No |

### Step 3 — 15 new `Models` rows, one per `Models SA` row

Continuing the `M-HYQU-####` sequence (after the two placeholders above). For each row:
`Client` = HYDRO QUEBEC, `Model_Code` = the `Models SA` row's own code (keep the `" SA"`
suffix, e.g. `4261870 SA`), `SA Model` = Yes, `Parent Model` = the matched row from the
mapping table above, `Modification_Status` = `Up to Date`, `Estimated Effort` = 0,
`Current Changes Priority` = `ASAP`, `Is Cancelled` = No. Everything else (the legacy spec
fields) blank — see note above.

### Step 4 — 15 new `Model Revisions` rows, one per new `Models` row

Naming convention confirmed from the live list: `MR-HYQU-{same number}-V1` (e.g. `Model_ID
M-HYQU-0096` → `Model_Revion_ID MR-HYQU-0096-V1`). For each: `Client` = HYDRO QUEBEC,
`Pioneer Model Code` = Lookup to the new `Models` row from step 3, and copy straight across
from the matching `Models SA` row:

| `Models SA` field | → `Model Revisions` field |
|---|---|
| Model Type | Model Type |
| Description | Model Description |
| kVA and kV | kVA (`Primary Voltage`/`Secondary Voltage` stay blank — see above) |
| Oil Type | Oil Type |
| Oil Amount | Oil Amount |
| Core Type | Core Type |
| Phases | Phases |
| Cable | Cable |
| Form | Form |
| Copper (LV) | Copper (LV) |
| Wire (HV) | Wire (HV) |
| Overcoil | Overcoil |

`Spec_ID`, `Spec_Revision`, `Spec_Date`, `Client_Model_Code`, `Notes`, `JS #`, `Duplicate
Order`, `Family` — no source data on `Models SA`, leave blank.

### Step 5 — link back

Set each new `Models` row's `Latest Model Revision` Lookup to point at its new `Model
Revisions` row from step 4. (The two placeholder rows from step 2 have no `Model Revisions`
entry — nothing to link, by design, since they're empty placeholders.)

### After that

Steps 3-5 of "Migration scope" above (repoint `ColumnMap.pq`/`TableOrders.pq`, retire
`Models SA`, build order-item-generation logic) — not started, come back to these once the
15+2 new `Models`/`Model Revisions` rows exist live.

## Relationship to other work

- **Supersedes** the `lookup-textfield-reference.md` to-do item "Build the `Client`-sync
  flow for `Models` and `Models SA`" — only build it for `Models` now; don't build a
  `Models SA` version that's about to be retired.
- **Depends on / feeds into** `order-items-build-plan.md`'s transfer flow (step 3) and
  `phase1-plan.md`'s `Work Order` fan-out — both eventually need step 5's order-item
  generation logic once this fusion happens, but neither is blocked from proceeding on
  other fronts in the meantime.
- **Also blocks** `order-items-manual-build-checklist.md`'s step 8 (new direct
  `Client`/`Model`/`Model Revision` Lookups on `Order Items`, decided 2026-08-13, to work
  around SharePoint's lack of cascading Lookups) — a Lookup column can only target one
  list, so the `Model`/`Model Revision` lookups can't be built until SA designs and regular
  designs live in the same list. **This is now unblocked design-wise** (disambiguation
  resolved above) — still blocked on the migration steps below actually happening.
