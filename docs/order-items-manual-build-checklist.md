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

**All 7 sub-steps done — the manual schema build is complete.** Next real task (not part
of this checklist): the TextField auto-sync Power Automate flow — see
`order-items-build-plan.md` step 2b, elevated to a tracked build step since manual
TextField upkeep has been a genuine pain point, not just a "nice to have."

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
| 22 | Tank | Single line of text | Confirmed: `R` = "Received." Stays Text, not Choice — deliberately manually-filled. |
| 23 | Frame | Choice | `Plaspak`, `Reçu`, `0` — re-verified directly against `Table20` on the `List` sheet (`Y8:Y11`); all 3 are real values in the source, not a typo. Meaning of `0` as a choice is unconfirmed (likely "none/not applicable") but include it as-is. |
| 24 | ISO Stack | Single line of text | Same as Tank — confirmed `R` = "Received," manually-filled. |
| 25 | ISO Coil | Single line of text | Same as Tank — confirmed `R` = "Received," manually-filled. |
| 26 | Lead Assembly | Single line of text | Same as Tank — confirmed `R` = "Received," manually-filled. |
| 27 | Winder | Single line of text | Must stay Text — values mix plain IDs and ranges (e.g. `100-104`). Manually-filled, not derived. |
| 28 | Coil Winder | Single line of text | Same as Winder — Text even though samples look numeric. Manually-filled. |
| 29 | Trimestrial Customer | Single line of text | ⚠ Stays Text, not Choice — a full-history data check (2026-08-13) found `N` (never `Y`) and 2 real date-like values in `TableOrders`, plus a formula-glitch reveal that the real French label is `Pénalité Trimestrielle` ("Trimestrial Penalty"), suggesting this may track a penalty date, not a yes/no attribute. **Pending clarification from business users once they're back from holidays** — don't build a Choice/Yes-No list until then. Per-unit placement is also still separately provisional — see `infrastructure-overview.md`. |

### Production-sequence dates (8 triples — expanded 2026-08-13)

**Expanded from Date+Status pairs to Date+Status+Started triples**: user wants real
time-spent tracking per stage (not just when it finished), and since `Status` already
distinguishes `Pending` (not started) from `In Progress` (actively being worked), a
`{Stage} Started` stamp captured at that specific transition gives an accurate start time
— unaffected by any idle/waiting time before work actually began (the alternative,
inferring start from the previous stage's finish time, would wrongly count that idle time
as work time). Each stage now needs:
- `{Stage} Date` (**Date and Time**) — stamped when `Status` becomes `Completed` (existing).
- `{Stage} Status` (Choice: `Pending`, `In Progress`, `Completed`; blank = not relevant yet)
  (existing).
- `{Stage} Started` (**Date and Time**, NEW) — stamped when `Status` first becomes
  `In Progress`.

Both date fields are auto-stamped by a Power Automate flow (see `order-items-build-plan.md`
step 2c), not typed by hand — each only fills in once, guarded by the field itself being
blank, so re-editing the item later doesn't re-stamp it.

| # | Started field (NEW) | # | Date field | # | Status field |
|---|---|---|---|---|---|
| — | Coiling Started | 30 | Coiling Date | 31 | Coiling Status |
| — | Stacking Started | 32 | Stacking Date | 33 | Stacking Status |
| — | Assembly Started | 34 | Assembly Date | 35 | Assembly Status |
| — | Drying Started | 36 | Drying Date | 37 | Drying Status |
| — | Tanking Started | 38 | Tanking Date | 39 | Tanking Status |
| — | Testing Started | 40 | Testing Date | 41 | Testing Status |
| — | Finishing Started | 42 | Finishing Date | 43 | Finishing Status |
| — | Delivery Started | 44 | Delivery Date | 45 | Delivery Status |

**To-do**: the 8 `{Stage} Started` columns still need to be added in SharePoint (schema
step, manual, same PnP-blocked situation as the rest of this migration) before the
auto-stamp flow can be built against them.

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

## After the list exists

Circle back to `order-items-build-plan.md` step 3 (one-time backfill of existing live
orders' current `TableOrders` data into these new fields) — not covered by this checklist,
which only takes you through having the empty schema in place.
