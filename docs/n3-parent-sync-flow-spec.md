# N3 — the parent sync flows, build spec

Generated 2026-09-05 (`scripts/gen_n3.py`). Mapping tables come straight from the N2 field
definitions, so every target name here is exactly what `n2_create_columns.js` creates.

**Prerequisites:** N2 (the 48 columns exist) and **A3** (2c stage-stamping stripped out of the
`Order Items` trigger flow). A3 is not optional — see *Capacity* below.

## ✅ The lookup internal names — RESOLVED 2026-09-07

Read from the platform, not guessed. `Order Items` has **117 columns**; these are its lookups:

| lookup | **internal name** | → list | list GUID | show field |
|---|---|---|---|---|
| `Order Number` | **`OrderNumber`** | `Order` | `6fe35dfe-2b7d-455a-abe3-056abb386733` | `Order_x0020_Number1` |
| `Model` | **`Model`** | `Models` | `b43a5140-0f9d-4ac1-9019-43b897074224` | `ModelName` |
| `Model Revision` | **`ModelRevision`** | `Model Revisions` | `e2ff8703-b590-4648-b181-9b47cf3883ba` | `ModelID` |
| `Client` | `Client` | `Clients` | `3bcf7d97-…` | `Title` |
| `Regrouped Into` | `RegroupedInto` | *self* | `d6468ec5-…` | `Title` ⚠️ multi-value |

So the fan-out filters are:

```
Order            OrderNumberId    eq @{triggerOutputs()?['body/ID']}
Models           ModelId          eq @{triggerOutputs()?['body/ID']}
Model Revisions  ModelRevisionId  eq @{triggerOutputs()?['body/ID']}
```

The list GUIDs match the `table` parameters the transfer flow already uses, which is an
independent confirmation that these are the right lists.

### How to read them, because the obvious route does not work here

⚠️ **`_api/web/lists/…/fields` is unavailable on this tenant.** Two 45-second
`document_idle` timeouts on 2026-09-05, two more on 2026-09-07, and `Failed to fetch` when
called as a `fetch` rather than a navigation. Not flakiness.

⚠️ **An export cannot supply them either.** Its `ListSchema` record carries 90 fields and
**not one of type `Lookup`** — SharePoint omits lookup columns from an export's schema as well
as its data.

✅ **What works:**

```js
fetch("/sites/PioneerPlanificatio/_api/v2.0/sites/root/lists/<listId>/columns")
  // each entry: {name, displayName, lookup:{listId, columnName, allowMultipleValues}}
```

Note `_api/v2.0/**sites/root**/lists/…` — the shorter `_api/v2.0/lists/…` returns
`itemNotFound`. Or, without any API: list settings → click the column → the `Field=`
parameter in the URL.

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

---

## 🔴 Five things the R3 run proved, that N3 must get right

Added 2026-09-08 after measuring the backfill against both source workbooks. Every one of these
is a mistake **already made once** in the transfer flow, or a behaviour of SharePoint that is not
what you would assume. Read this before writing a single mapping.

### 1 · Unwrap `.Value` — a parent lookup does NOT come back as a string

This is the one that already bit us. `RevModelDescription` on **979 of 1,117 rows** now holds:

```
[{"@odata.type":"#Microsoft.Azure.Connectors.SharePoint.SPListExpandedReference","Id":5,"Value":"MALT"}]
```

The intended value was `MALT`. The mapping passed the **whole expanded-reference array** instead
of its `Value`. It is the *write*-side twin of the export-side trap in `R19`
(`SUBWAY` vs `["SUBWAY"]`) — same mistake, opposite direction.

**Every** N3 mapping reads a Lookup or Choice off a parent list, so **every** N3 mapping is
exposed to this:

```
✅  first(body('Filter_Revisions'))?['ModelDescription']?['Value']
🔴  first(body('Filter_Revisions'))?['ModelDescription']
```

A MultiChoice returns several entries — join them, do not take `first()` blindly. And note it
fails **silently and legibly**: the row is populated, nothing errors, and it looks fine until
someone reads the column. Check one real row's raw inputs per mapping, not the run status.

### 2 · `null` does not clear a field — it leaves the old value

Proven, not assumed: the flow writes `null` for a stage whose source date is blank, the run
rewrote all 1,013 comparable rows, and **844 stale `Pending` statuses survived anyway**
(Testing 813, Stacking 26, Finishing 4, Drying 1).

So for N3:

- a change-guard that "clears" a field by writing `null` **does nothing at all**;
- **no re-run will ever remove a stale value** — if N3 writes something wrong, re-running the
  corrected flow will not undo it, and you need a one-off pass that writes an explicit value;
- the flip side is load-bearing and must not be "fixed": it is exactly what preserves the blank
  `{Stage} Start Date` marker that `X1`/`R14` key on. All eight start-date columns are still
  0-populated because of it.

### 3 · Dates: write a **bare** `yyyy-mm-dd`, never a full instant

A bare date into a Date-Only column stores site-local midnight — `04:00Z` or `05:00Z` split by
DST. A full instant stores UTC midnight, which renders as **the previous day**: the exact bug the
whole backfill existed to fix. Verified after the run: `Planned Tanking Date` 552 at `04:00Z` +
416 at `05:00Z`, `OrdOrderDate` 1,011 of 1,011 correct, and **zero** touched rows left at
`00:00:00Z`.

### 4 · Resolve-by-key must handle an **ambiguous** parent, not just a missing one

✅ **The instance is fixed — the rule stays.** `P20004` used to appear **twice** in `Order`,
Id 487 (`PIONEER TRANSFORMERS`) and Id 488 (`ERMCO`), the only duplicated order number in all
445 rows, and its two units were **exactly** the two the transfer flow could not explain
skipping. The user deleted **487** on 2026-09-08; verified over REST that one `P20004` row
remains (488, ERMCO) and both units point at it. `Order` has no duplicate order number today.

**Build the guard anyway.** Nothing prevents a second `P20004` from being typed tomorrow — the
column has no uniqueness constraint, and this one survived undetected long enough to silently
skip two units on every run. So do not take `first(…)`: count the matches and **flag anything
other than exactly one** rather than guessing between two different clients. Same discipline
`R2` already demands for the SA twin.

### 5 · The synced columns are `Text` on purpose — keep them that way

`N2` deliberately remapped `Choice` → `Text` and `Lookup` → `Text` when creating the 48 columns,
because a synced `Choice` **silently rejects any value outside its option list, per row, inside
the flow** — the `Family` failure mode. That decision is what makes mapping 1 above safe to do as
a plain string. Do not "tidy" these back into Choice columns later.

⚠️ **But "the sync columns are all Text" is not true, and it is worth retiring as an assumption**
(asked 2026-09-08, measured from the list's own schema). The 47 parent columns are **Text 29 ·
Number 7 · Note 4 · DateTime 3 · Boolean 2 · Currency 1 · URL 1**. Of the 27 whose source field
resolves straight out of the flow definition, **26 match their parent's type exactly** — dates are
`DateTime`, quantities are `Number`, `Price` is `Currency`, `OrdOrderFolder` is `URL`. Only the
**Choice and Lookup** sources were flattened to `Text`, which is exactly the rule above and no
broader.

**Exactly one column's type disagrees with its parent: `RevModelDescription` is `Note` against a
`MultiChoice` source** — and that is *why* R22 could happen at all. A `Note` field accepts any
string, including 110 characters of JSON, without complaint. See
`docs/r22-mapping-correction-2026-09-08.md`.

### Sanity numbers to build against

The run already populated these, so N3's first job is to *keep them right*, not to fill them:
`MdlModelID` **1,008** · `RevkVA` **1,006** · `OrdOrderNumber` **1,013** of 1,117 rows. If an N3
test run moves those counts down, it is clearing values it should have left alone — see 2 above.
