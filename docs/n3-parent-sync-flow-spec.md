# N3 — the parent sync flows, build spec

Generated 2026-09-05 (`scripts/gen_n3.py`). Mapping tables come straight from the N2 field
definitions, so every target name here is exactly what `n2_create_columns.js` creates.

**Prerequisites:** N2 (the 48 columns exist) and **A3** (2c stage-stamping stripped out of the
`Order Items` trigger flow). A3 is not optional — see *Capacity* below.

## 🔴 Read the lookup internal names before you build

The fan-out filter needs the internal name of each lookup **on `Order Items`** — the columns
pointing back at `Order`, `Models` and `Model Revisions`. **I could not read them.** They are
absent from the list export's `ListSchema` record entirely, and the tenant timed out on the REST
call. So they are deliberately left as placeholders below rather than guessed.

Run this first and substitute the real values:

```
/_api/web/lists/getbytitle('Order Items')/fields
   ?$select=Title,InternalName,TypeAsString,LookupList,LookupField
   &$filter=TypeAsString eq 'Lookup'
```

This is the same rule as everywhere else in this repo: a retyped internal name writes nothing,
silently. `Protector & Switchgear Item #` on this very list is `Protector_x0020__x0026__x0020_Sw`,
truncated mid-word at 32 characters.

## Shape — the same five blocks in each flow

```
1  Trigger      When an item is created or modified   (the parent list)
2  Guard        Trigger condition -- skip our own writes
3  Fan out      Get items on Order Items, Filter Query on the lookup Id
4  Apply to each
     4a  Compose  needsUpdate   -- OR of per-field comparisons
     4b  Condition needsUpdate is true
           Update item  (one call, all changed fields)
5  (Order/Models only)  the SA branch -- see below
```

### 2 — the trigger condition matters more than it looks

A sync flow that writes to `Order Items` does not re-trigger *itself*, but it **does** fire the
`Order Items` create-or-update trigger flow once per row written. Put a **trigger condition** on
that flow so a sync-only write never creates a run — conditions are evaluated *before* a run
exists, so they cost nothing. A first-action Condition does not help: the run is already charged.

### 3 — the fan-out filter

```
Get items
  Site / List:   Order Items
  Filter Query:  <LookupInternalName>Id eq @{triggerOutputs()?['body/ID']}
  Top Count:     5000
  Pagination:    on, threshold 5000
```

Filter on the lookup's `Id`, not on a `_TextField` mirror. The mirrors are stale — their sync
flows have been off since Aug 21 — so filtering on them would silently miss rows.

### 4a — the change-guard is mandatory, not an optimisation

Without it, one edit to a `Models` row rewrites every unit using that model, and each of those
writes fires the trigger flow. Build one `Compose` per flow that ORs the comparisons:

```
@or(
  not(equals(coalesce(items('Apply_to_each')?['<target>'], ''),
             coalesce(triggerOutputs()?['body/<source>'], ''))),
  ...one line per column...
)
```

`coalesce(..., '')` on both sides matters: `null` and `''` are not equal in Power Automate, so
without it every row with a blank looks changed and the guard never fires.

## `Order Items - sync from Order`

Trigger list **`Order`** · **19 columns** · fan-out avg **3.1**, worst **29**

| Source column | → `Order Items` column | Internal name | Type |
|---|---|---|---|
| `Client Date Status` | `Order - Client Date Status` | `OrdClientDateStatus` | Text ⚠️ was Choice |
| `Engineering Required` | `Order - Engineering Required` | `OrdEngineeringRequired` | Boolean |
| `Indexing` | `Order - Indexing` | `OrdIndexing` | Text ⚠️ was Choice |
| `Initial Promised Date` | `Order - Initial Promised Date` | `OrdInitialPromisedDate` | DateTime |
| `LDs` | `Order - LDs` | `OrdLDs` | Boolean |
| `New model to be created` | `Order - New model to be created` | `OrdNewmodeltobecreated` | Text ⚠️ was Choice |
| `Note` | `Order - Note` | `OrdNote` | Note |
| `Order Date` | `Order - Order Date` | `OrdOrderDate` | DateTime |
| `Order Folder` | `Order - Order Folder` | `OrdOrderFolder` | URL |
| `Order Number` | `Order - Order Number` | `OrdOrderNumber` | Text |
| `Order Status` | `Order - Order Status` | `OrdOrderStatus` | Text ⚠️ was Choice |
| `Order Step` | `Order - Order Step` | `OrdOrderStep` | Text ⚠️ was Choice |
| `Order Type` | `Order - Order Type` | `OrdOrderType` | Text ⚠️ was Choice |
| `PO` | `Order - PO` | `OrdPO` | Text |
| `Price` | `Order - Price` | `OrdPrice` | Currency |
| `Province/State` | `Order - Province/State` | `OrdProvinceState` | Text |
| `Qty` | `Order - Qty` | `OrdQty` | Number |
| `Sales Notes` | `Order - Sales Notes` | `OrdSalesNotes` | Note |
| `WET-WETP` | `Order - WET-WETP` | `OrdWETWETP` | Text ⚠️ was Choice |

## `Order Items - sync from Models`

Trigger list **`Models`** · **5 columns** · fan-out avg **6.9**, worst **91**

| Source column | → `Order Items` column | Internal name | Type |
|---|---|---|---|
| `Estimated Effort` | `Model - Estimated Effort` | `MdlEstimatedEffort` | Number |
| `Latest Model Revision` | `Model - Latest Model Revision` | `MdlLatestModelRevision` | Text ⚠️ was Lookup |
| `Model_ID` | `Model - Model_ID` | `MdlModelID` | Text |
| `Modification_Status` | `Model - Modification_Status` | `MdlModificationStatus` | Text ⚠️ was Choice |
| `Parent Model` | `Model - Parent Model` | `MdlParentModel` | Text ⚠️ was Lookup |

## `Order Items - sync from Model Revisions`

Trigger list **`Model Revisions`** · **24 columns** · fan-out avg **2.6**

| Source column | → `Order Items` column | Internal name | Type |
|---|---|---|---|
| `Cable` | `Mod. Rev. - Cable` | `RevCable` | Text |
| `Client_Model_Code` | `Mod. Rev. - Client_Model_Code` | `RevClientModelCode` | Text |
| `Copper (LV)` | `Mod. Rev. - Copper (LV)` | `RevCopperLV` | Text |
| `Core Type` | `Mod. Rev. - Core Type` | `RevCoreType` | Text ⚠️ was Choice |
| `Duplicate Order` | `Mod. Rev. - Duplicate Order` | `RevDuplicateOrder` | Text ⚠️ was Lookup |
| `Family` | `Mod. Rev. - Family` | `RevFamily` | Text ⚠️ was Choice |
| `Form` | `Mod. Rev. - Form` | `RevForm` | Text |
| `JS #` | `Mod. Rev. - JS #` | `RevJS` | Text |
| `Model Description` | `Mod. Rev. - Model Description` | `RevModelDescription` | Note ⚠️ was MultiChoice |
| `Model Type` | `Mod. Rev. - Model Type` | `RevModelType` | Text ⚠️ was Choice |
| `Model_Revion_ID` | `Mod. Rev. - Model_Revion_ID` | `RevModelRevionID` | Text |
| `Notes` | `Mod. Rev. - Notes` | `RevNotes` | Note |
| `Oil Amount` | `Mod. Rev. - Oil Amount` | `RevOilAmount` | Number |
| `Oil Type` | `Mod. Rev. - Oil Type` | `RevOilType` | Text ⚠️ was Choice |
| `Overcoil` | `Mod. Rev. - Overcoil` | `RevOvercoil` | Number |
| `Phases` | `Mod. Rev. - Phases` | `RevPhases` | Number |
| `Pioneer Model Code` | `Mod. Rev. - Pioneer Model Code` | `RevPioneerModelCode` | Text ⚠️ was Lookup |
| `Primary Voltage` | `Mod. Rev. - Primary Voltage` | `RevPrimaryVoltage` | Number |
| `Secondary Voltage` | `Mod. Rev. - Secondary Voltage` | `RevSecondaryVoltage` | Number |
| `Spec_Date` | `Mod. Rev. - Spec_Date` | `RevSpecDate` | DateTime |
| `Spec_ID` | `Mod. Rev. - Spec_ID` | `RevSpecID` | Text |
| `Spec_Revision` | `Mod. Rev. - Spec_Revision` | `RevSpecRevision` | Text |
| `Wire (HV)` | `Mod. Rev. - Wire (HV)` | `RevWireHV` | Text |
| `kVA` | `Mod. Rev. - kVA` | `RevkVA` | Number |

## 🔴 The SA branch — `Model` and `Model Revision` are not in the tables above

Those two are **not** prefixed columns. They overwrite the existing `Order Items.Model` and
`Order Items.Model Revision` lookups, by decision: a model corrected on the `Order` must reach
every unit of that order. That makes them the one destructive write in this whole design.

Inside the `Apply to each`, before writing either:

```
Condition:  items('Apply_to_each')?['SAJob']  is equal to  false

  YES ->  write Order.Model straight through

  NO  ->  resolve the twin:
            Get items on Models
              Filter Query:  SA_x0020_Model eq 1
                         and Parent_x0020_Model eq '<new model's Model_Code>'
            if exactly one match  -> write it
            if zero matches       -> DO NOT WRITE. Flag for engineering.
```

Measured 2026-09-05, and this is why the branch exists:

| | |
|---|---|
| Orders holding both an SA and a non-SA unit, model known on both | **34** |
| …where the SA unit carries a **different** model | **32** |
| Orders where non-SA siblings disagree | **0** |
| SA models where `Parent Model` resolves correctly | **15 of 15** |
| Models that have a twin **at all** | **15 of 390** |

So the zero-match branch is not an edge case — **96% of models have no twin**. Writing a blank or
the main model there is exactly the failure this guard exists to prevent.

**Five SA units already sit on plain `M-` models** (`22098-1/1 SA`, `22099-1/1 SA`,
`22107-1/1 SA`, `22108-1/1 SA`, `22110-1/1 SA`) and one has no model at all
(`21499-1/3 SA`). Resolve those by hand *before* the flow runs, or they take the zero-match
branch on the first edit.

## `Models` → SA twin — the self-edge

A change to a model must also reach its SA twin, so this flow writes **`Models` → `Models`**.
Editing `M-HYQU-0092` fires it, it writes `MSA-HYQU-0092`, and that fires it again. It terminates
today only because no `MSA-` model has a twin of its own — luck, not design.

Two guards, both cheap:

1. The change-guard above — nothing is written when nothing differs, so the second hop stops.
2. **Skip outright when `SA Model` is already true.** A twin can then never trigger another hop,
   regardless of what the change-guard does.

## `Clients.Lead Time` → `Order Items`

One column, and it is the exception to *don't sync Clients*. Same shape as the flows above.

⚠️ **Fan-out is 27.5 average and 698 worst** — HYDRO QUEBEC is 68% of the list. That is fine
*after* A3 (~5 actions per trigger run, drains in minutes) and is the load shape that hit the
capacity cap *before* it. **Build it now, enable it after A3.**

`Pièce critique` and `Fournisseur` do **not** travel — reference data, one lookup away.

## Capacity — why A3 comes first

| Parent | Rows | Avg fan-out | Worst |
|---|---|---|---|
| `Order` | 445 | 3.1 | 29 |
| `Models` | 390 | 6.9 | 91 |
| `Model Revisions` | 391 | ~2.6 | not measured |
| `Clients` | 98 | 27.5 | **698** |

Each written row fires the `Order Items` trigger flow. At its current ~100 actions that is the
load that wedged 29+ instances on Sep 2. After A3 it is ~5 actions. **The change-guard and the
trigger condition together are what make this safe** — the guard stops unnecessary writes, the
condition stops the necessary ones from costing a run.

## Build order

1. Read the lookup internal names (top of this doc).
2. `Model Revisions` first — 24 columns, smallest fan-out, no SA branch. Proves the pattern.
3. `Models` — 4 columns, plus the self-edge guards.
4. `Order` — 19 columns, plus the SA branch. The riskiest, built last on a proven pattern.
5. `Clients.Lead Time` — after A3.

Test each on **one** parent row with a small fan-out before enabling. `Order` is the natural
choice: pick an order with 2–3 units and no SA.
