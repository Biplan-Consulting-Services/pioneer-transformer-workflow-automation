# Order Items — Manual Build Checklist

**Why this doc exists:** the original plan was a PnP PowerShell script to build this list.
That route is blocked — the `ermcopower` tenant hasn't granted admin consent for the PnP
Management Shell Azure AD app (`AADSTS700016`), and this user doesn't hold a role
(Global Admin / Privileged Role Admin / Application Admin / Cloud Application Admin) that
can grant it. Since *any* PowerShell-based automation (PnP or otherwise) hits the same
tenant-consent wall on first use, this build goes through the SharePoint list UI by hand
instead — same way `Order`/`Models`/`Model Revisions` were originally built. If IT ever
grants that consent, scripting the *next* migration step (backfill, companion columns
elsewhere) becomes an option again — this doc doesn't need to change either way.

Field names, types, and choice values below are the confirmed schema from
`infrastructure-overview.md`'s "Order Items list schema (draft v1)" section, plus decisions
made while preparing this checklist (noted inline where they update that doc).

Site: `https://ermcopower.sharepoint.com/sites/PioneerPlanificatio`

## Progress (7 sub-steps, user's own numbering)

- [x] 1. Identity / merge key
- [x] 2. Test/QA results
- [x] 3. Production tracking
- [x] 4. Production-sequence dates (8 pairs) — done 2026-08-13
- [x] 5. Other dates — done 2026-08-13
- [x] 6. Companion columns on `Order` — done 2026-08-13 (`Protector & Switchgear PO` moved to `Order Items` instead, see note in that section)
- [x] 7. Companion columns on `Model Revisions` — done 2026-08-13
- [x] 8. `Client`/`Model`/`Model Revision` lookups on `Order Items` — done 2026-08-14, all 6
      columns (3 Lookups + 3 TextField companions) built live

**All 8 sub-steps done — the schema build (including step 8) is complete**, and its
TextField sync flow is built too (see `lookup-textfield-reference.md`). Next real task:
`order-items-build-plan.md` step 3, the Excel → SharePoint transfer/backfill flow.

## Step 1 — Create the `Order Items` list

Create a new custom list named **Order Items**, no template, blank.

### Identity / merge key

| # | Field name | Type | Details |
|---|---|---|---|
| 1 | Title (now displayed as **`Unit ID`**) | (default, already exists) | Confirmed live 2026-08-13 — user renamed the display name from `Title` to `Unit ID` (clearer). Underlying field is still the built-in Title field, but reference it as `Unit ID` in Power Query/Power Automate going forward, since SharePoint.Tables reads by display name. At backfill/transfer time, set to the unit ID, e.g. `21408-1/1`. |
| 2 | Order Number | **Lookup** | Get information from: **Order**. In this column: **Order Number** (confirmed — Order's own "Order Number" text field, not `Title`; `Order` list's `Title` field holds something else, not the order number). |
| 2b | Order_Number_TextField | Single line of text | Companion text field for the `Order Number` Lookup, per user's standing convention (2026-08-13): every Lookup gets a sibling `{Field}_TextField` holding a plain-text copy of the looked-up value, for search/filtering. **Manually kept in sync for now — confirmed a real pain point, not hypothetical.** Auto-sync via Power Automate is now a tracked build step, not just a comment — see `order-items-build-plan.md`'s step 2b. |
| 3 | Unit # | Number | No decimals. For an SA (auxiliary) row, **copy the parent unit's value** — confirmed 2026-08-13, not left blank. |
| 4 | Qty | Number | No decimals. Same as Unit # — copied from the parent unit for an SA row. |
| 5 | SA Job | Yes/No | **Real meaning confirmed 2026-08-13** (the earlier "matches TableOrders.pq's computed boolean" note was a placeholder, not an explanation): some transformers ship with an auxiliary unit that needs its own independent production tracking (own `Location`/`Status`/dates) despite conceptually being "the same order item." That auxiliary gets its own `Order Items` row, `Title` = the parent unit ID + ` SA` suffix (e.g. `21408-1/1` and `21408-1/1 SA`). `SA Job = Yes` marks "this row is that auxiliary row," not an abstract property. An SA row does **not** count as a separately priced/reported unit — Power BI today filters SA rows out of reporting and keeps only the main version; keep that in mind whenever calculated columns (`Price`, etc.) or reports get built against this list later. Most important spec fields for an SA unit's construction: `Cable`, `Form`, `Copper (LV)`, `Wire (HV)`, `Overcoil` (all on `Models`/`Model Revisions`, nothing new needed here). |

### Test/QA results

| # | Field name | Type | Choice values |
|---|---|---|---|
| 6 | Witness/Other | Single line of text | |
| 7 | Temperature Rise | Yes/No | |
| 8 | Impulse | Yes/No | |
| 9 | Partial D | Yes/No | |
| 10 | Oil Analysis | Yes/No | |
| 11 | DB | Yes/No | |
| 12 | SFRA | Yes/No | |
| 13 | CSA | Yes/No | |
| 14 | Protector Status | Choice | `Entrepôt SN`, `Reçu`, `à vérifier` |
| 14b | Protector & Switchgear PO | Single line of text | **Moved here from the `Order` companion columns (step 2) by user decision, 2026-08-13**: it's a per-transformer purchasing column, not per-order — each unit's protector/switchgear can be a separate PO. Pairs naturally with `Protector Status` above, which is per-unit for the same reason. |

### Production tracking

| # | Field name | Type | Choice values / details |
|---|---|---|---|
| 15 | Location | Choice | `Isolation`, `Bobinage`, `Stacking`, `Assemblage`, `Four`, `Tanking`, `Test`, `Finition`, `Livraison`, `Entrepôt`, `Extérieur`, `Réparation` — **decided this session: full descriptive names, not the short codes** (`IS`/`BO`/etc.). This changes the Delivered-trigger wording documented below from "Location = LI" to "Location = Livraison". |
| 16 | Item Status | Choice | `Active` (default), `Delivered`, `Cancelled`, `Regrouped` |
| 17 | Regrouped Into | **Lookup (multi-value)** | Get information from: **Order Items** itself (self-referencing — you can only pick this once the list already exists, so add this field in a second pass after step 1's other fields are created). In this column: **Title**. Allow multiple values: Yes. |
| 17b | Regrouped_Into_TextField | Single line of text | Companion text field, same convention as `Order_Number_TextField` above. |
| 18 | Status | Single line of text | Composite value, e.g. `TE-Jui-16` — kept as plain text, not split. |
| 19 | Core Status | Choice | `Entrepôt SN`, `Reçu`, `Transport` |
| 20 | Production Line | Choice | `Power / Ligne 1`, `Distribution`, `Power`, `Zone B`, `Ligne 1` (as found in the original validation list — the near-duplicate "Power" entries are verbatim from the source, not a typo introduced here) |
| 21 | Time (days) | Number | |
| 22 | Tank | **Yes/No** | **Corrected 2026-08-17 — built live as Yes/No, not Text as originally planned below.** Original intent (2026-08-12) was Text (`R` = "Received," deliberately manually-filled, not Choice) — found to be Yes/No instead while building the transfer flow (`order-items-power-automate-flows.md` step 3), confirmed directly against the live list. Not reverted — Yes/No is simpler for staff to check off and the transfer flow now maps to it (`'R'` present → `Yes`) — but flagging the discrepancy rather than silently treating it as always-intended. |
| 23 | Frame | Choice | `Plaspak`, `Reçu`, `0` — re-verified directly against `Table20` on the `List` sheet (`Y8:Y11`); all 3 are real values in the source, not a typo. Meaning of `0` as a choice is unconfirmed (likely "none/not applicable") but include it as-is. |
| 24 | ISO Stack | **Yes/No** | Same correction as `Tank` above — confirmed live 2026-08-17. |
| 25 | ISO Coil | **Yes/No** | Same correction as `Tank` above — confirmed live 2026-08-17. |
| 26 | Lead Assembly | **Yes/No** | Same correction as `Tank` above — confirmed live 2026-08-17. |
| 27 | Winder | Single line of text | Must stay Text — values mix plain IDs and ranges (e.g. `100-104`). Manually-filled, not derived. |
| 28 | Coil Winder | Single line of text | Same as Winder — Text even though samples look numeric. Manually-filled. |
| 29 | Trimestrial Customer | Single line of text | ⚠ Stays Text, not Choice — a full-history data check (2026-08-13) found `N` (never `Y`) and 2 real date-like values in `TableOrders`, plus a formula-glitch reveal that the real French label is `Pénalité Trimestrielle` ("Trimestrial Penalty"), suggesting this may track a penalty date, not a yes/no attribute. **Pending clarification from business users once they're back from holidays** — don't build a Choice/Yes-No list until then. Per-unit placement is also still separately provisional — see `infrastructure-overview.md`. |

### Production-sequence dates (8 triples — expanded 2026-08-13)

**Expanded from Date+Status pairs to Start Date+End Date+Status triples**: user wants real
time-spent tracking per stage (not just when it finished), and since `Status` already
distinguishes `Pending` (not started) from `In Progress` (actively being worked), a
`{Stage} Start Date` stamp captured at that specific transition gives an accurate start
time — unaffected by any idle/waiting time before work actually began (the alternative,
inferring start from the previous stage's finish time, would wrongly count that idle time
as work time). Each stage now has (confirmed live 2026-08-13):
- `{Stage} Start Date` (**Date and Time**, NEW) — stamped when `Status` first becomes
  `In Progress`.
- `{Stage} End Date` (**Date and Time**) — stamped when `Status` becomes `Completed`.
  **Renamed from the original `{Stage} Date`** for symmetry with the new `Start Date`
  field — same field, new name.
- `{Stage} Status` (Choice: `Pending`, `In Progress`, `Completed`; blank = not relevant yet)
  (unchanged).

Both date fields are auto-stamped by a Power Automate flow (see `order-items-build-plan.md`
step 2c), not typed by hand — each only fills in once, guarded by the field itself being
blank, so re-editing the item later doesn't re-stamp it.

| # | Start Date field (NEW) | # | End Date field (renamed) | # | Status field |
|---|---|---|---|---|---|
| — | Coiling Start Date | 30 | Coiling End Date | 31 | Coiling Status |
| — | Stacking Start Date | 32 | Stacking End Date | 33 | Stacking Status |
| — | Assembly Start Date | 34 | Assembly End Date | 35 | Assembly Status |
| — | Drying Start Date | 36 | Drying End Date | 37 | Drying Status |
| — | Tanking Start Date | 38 | Tanking End Date | 39 | Tanking Status |
| — | Testing Start Date | 40 | Testing End Date | 41 | Testing Status |
| — | Finishing Start Date | 42 | Finishing End Date | 43 | Finishing Status |
| — | Delivery Start Date | 44 | Delivery End Date | 45 | Delivery Status |

**Fixed 2026-08-13**: the `Delivery Data` typo is resolved — deleted and recreated as
`Delivery Date` (safe, zero data-loss since the list was still empty), also picking up a
clean matching internal name in the process.

### Other dates (plain, not split into Date+Status pairs)

| # | Field name | Type |
|---|---|---|
| 46 | Tank Delivery Date | Date only |
| 47 | Original Tanking Date | Date only |
| 48 | Manual Estimated Delivery Date | Date only |
| 49 | Tanking date change justification | Multiple lines of text (plain, not rich text) |

## Step 2 — Companion columns on `Order`

| Field name | Type | Choice values / details |
|---|---|---|
| Engineering Required | Yes/No | Matches the pattern of Order's existing workflow booleans (e.g. `Receive CRM Sales Order`). |
| LDs | Yes/No | Verified directly against `TableOrders` column Y across ~1000 rows: clean binary `Y`/`N` text flag (175 `Y`, 38 `N`, rest blank), not a numeric amount. One stray row had a formula-glitch value, ignored as noise. |
| Client Date Status | Choice | `Confirmed`, `Not Confirmed`, `Pending` |
| Sales Notes | Multiple lines of text | |
| Order Status | Choice | `Active` (default), `Cancelled` |

*(`Protector & Switchgear PO` moved to `Order Items` — see row 14b above — per-unit, not
per-order.)*

## Step 3 — Companion columns on `Model Revisions`

**Decided this session**: both go on **Model Revisions**, not `Models` — the doc left this
ambiguous ("Models/Model Revisions"); reasoning is that both `Family` (complexity rating)
and `Duplicate Order` (last order built against this) can genuinely change revision-to-
revision, not just model-to-model.

| Field name | Type | Choice values / details |
|---|---|---|
| Duplicate Order | **Lookup** | Get information from: **Order**. In this column: **Order Number**. |
| Duplicate_Order_TextField | Single line of text | Companion text field, same convention as `Order_Number_TextField` above. |
| Family | Choice | `A`, `B1`, `B2`, `C` |

## Step 8 — `Client`/`Model`/`Model Revision` lookups on `Order Items` (added 2026-08-13, built 2026-08-14)

**Why**: `Order Items` currently has no lookup to `Client`/`Models`/`Model Revisions` at
all — that data only exists one hop away, on the parent `Order`. SharePoint can't cascade
through a Lookup in views/filters/reports, so anything wanting an Order Item's client or
model has to join through `Order` every time. User's call: duplicate these three directly
onto `Order Items`, same pattern already used on `Model Revisions` (which has its own
`Client` Lookup rather than cascading through `Models`).

**Side benefit**: this also resolves the older gap where the SA auxiliary row (`SA Job =
Yes`) had nowhere to point at its own (different) model — a normal unit's `Model`/`Model
Revision` mirrors the parent `Order`'s value, an SA row's points at the SA-specific
model/revision instead. One column serves both cases.

**Blocked on the Models SA fusion, not on anything else**: a Lookup column can only target
one list, so this can't be built cleanly until `Models SA` is fused into `Models`/`Model
Revisions` (see `models-sa-fusion-plan.md`) — otherwise an SA row's `Model` lookup would
need to point at a different list than a normal row's, which SharePoint doesn't support on
one column. Don't build this step until that fusion's disambiguation question is answered.

**Sync risk assessed as low, 2026-08-13**: these three values are set once at order
creation and essentially never change afterward (unlike `Location`/`Status`), so a
one-time stamp at row-creation (the backfill/transfer flow now, the `Work Order` fan-out
later) is enough — no continuous sync flow needed at launch. **Logged as a future
nice-to-have in `roadmap.md`**: a "parent changed → update children" flow (if `Order`'s
`Client`/`Model`/`Model Revision` ever changes after creation, propagate to that order's
`Order Items` rows) — not needed now, worth building if that turns out to happen in
practice.

**Client source, resolved 2026-08-14**: unlike `Model`/`Model Revision`, `Client` doesn't
need SA branching — every unit in an order belongs to the same client regardless of
`SA Job`, so it always mirrors the parent Order's client. Built as a direct Lookup to
**Clients** (same pattern as `Model Revisions`' own `Client` Lookup, not chained through
`Order`), not through `Order`/`Models SA`.

| Field name | Type | Details |
|---|---|---|
| Client | **Lookup** | Get information from: **Clients** (direct). Value always mirrors the parent Order's client, no SA branching. **Built 2026-08-14.** |
| Client_ID_TextField | Single line of text | Companion text field, same convention as every other `Client` Lookup system-wide — see `lookup-textfield-reference.md`. **Built 2026-08-14.** |
| Model | **Lookup** | Get information from: **Models** (post-fusion). Normal row mirrors parent Order's Model; SA row (`SA Job = Yes`) points at the SA-specific model instead. **Built 2026-08-14.** |
| Model_ID_TextField | Single line of text | Companion text field. **Built 2026-08-14.** |
| Model Revision | **Lookup** | Get information from: **Model Revisions** (post-fusion). Same SA branching as `Model`. **Built 2026-08-14.** |
| Model_Revision_ID_TextField | Single line of text | Companion text field. **Built 2026-08-14.** |

**Data not yet populated** — schema only, same status as the rest of `Order Items` (empty
list). Backfill happens at `order-items-build-plan.md` step 3, same as every other field.
**TextField sync flow for these 3 new Lookups built 2026-08-14**, added into the existing
merged `Order Items - created or updated trigger` flow — see `lookup-textfield-reference.md`.

## After the list exists

Circle back to `order-items-build-plan.md` step 3 (one-time backfill of existing live
orders' current `TableOrders` data into these new fields) — not covered by this checklist,
which only takes you through having the empty schema in place.
