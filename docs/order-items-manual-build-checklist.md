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

## Step 1 — Create the `Order Items` list

Create a new custom list named **Order Items**, no template, blank.

### Identity / merge key

| # | Field name | Type | Details |
|---|---|---|---|
| 1 | Title | (default, already exists) | Rename nothing — just note for later: at backfill time, set to the unit ID, e.g. `21408-1/1`. Nothing to configure now. |
| 2 | Order Number | **Lookup** | Get information from: **Order**. In this column: **Order Number** (confirmed — Order's own "Order Number" text field, not `Title`; `Order` list's `Title` field holds something else, not the order number). |
| 3 | Unit # | Number | No decimals. |
| 4 | Qty | Number | No decimals. |
| 5 | SA Job | Yes/No | |

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

### Production tracking

| # | Field name | Type | Choice values / details |
|---|---|---|---|
| 15 | Location | Choice | `Isolation`, `Bobinage`, `Stacking`, `Assemblage`, `Four`, `Tanking`, `Test`, `Finition`, `Livraison`, `Entrepôt`, `Extérieur`, `Réparation` — **decided this session: full descriptive names, not the short codes** (`IS`/`BO`/etc.). This changes the Delivered-trigger wording documented below from "Location = LI" to "Location = Livraison". |
| 16 | Item Status | Choice | `Active` (default), `Delivered`, `Cancelled`, `Regrouped` |
| 17 | Regrouped Into | **Lookup (multi-value)** | Get information from: **Order Items** itself (self-referencing — you can only pick this once the list already exists, so add this field in a second pass after step 1's other fields are created). In this column: **Title**. Allow multiple values: Yes. |
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
| 29 | Trimestrial Customer | Single line of text | ⚠ Per-unit placement is provisional — see `infrastructure-overview.md`, standing future review point. |

### Production-sequence dates (8 pairs)

Each stage gets a `{Stage} Date` (Date only, no time) + `{Stage} Status` (Choice:
`Pending`, `In Progress`, `Completed`; leave blank = not relevant yet). Date field only
gets filled once its Status = Completed.

| # | Date field | # | Status field |
|---|---|---|---|
| 30 | Coiling Date | 31 | Coiling Status |
| 32 | Stacking Date | 33 | Stacking Status |
| 34 | Assembly Date | 35 | Assembly Status |
| 36 | Drying Date | 37 | Drying Status |
| 38 | Tanking Date | 39 | Tanking Status |
| 40 | Testing Date | 41 | Testing Status |
| 42 | Finishing Date | 43 | Finishing Status |
| 44 | Delivery Date | 45 | Delivery Status |

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
| Protector & Switchgear PO | Single line of text | |
| Order Status | Choice | `Active` (default), `Cancelled` |

## Step 3 — Companion columns on `Model Revisions`

**Decided this session**: both go on **Model Revisions**, not `Models` — the doc left this
ambiguous ("Models/Model Revisions"); reasoning is that both `Family` (complexity rating)
and `Duplicate Order` (last order built against this) can genuinely change revision-to-
revision, not just model-to-model.

| Field name | Type | Choice values / details |
|---|---|---|
| Duplicate Order | **Lookup** | Get information from: **Order**. In this column: **Order Number**. |
| Family | Choice | `A`, `B1`, `B2`, `C` |

## After the list exists

Circle back to `order-items-build-plan.md` step 3 (one-time backfill of existing live
orders' current `TableOrders` data into these new fields) — not covered by this checklist,
which only takes you through having the empty schema in place.
