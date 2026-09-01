# Track C — sales-app fan-out, paste-ready Power Fx

Build night 2026-09-01. Companion to `cutover-runbook-2026-09-01.md` Track C.
Written by session `claude-02` assisting the user; Track D is owned by
`pioneer-transformer-build-night`.

---

## AS BUILT — 2026-09-01 06:19, reconciled against the live app

**Read this before the sections below.** Everything from `## C2` down was written from schema
exports, *not* the live app. It was walked into Power Apps Studio on build night and four things
came out differently. The app is the truth; this section records the deltas.

### 1. It is C2 (`Patch`). The `SubmitForm` in `OnSelect` is a decoy.

The Save button's `OnSelect` **does** contain `SubmitForm(Form2)` — but **Form2 is the Model
Revision form**, not the Order (`Set(SelectedModelRevision, Form2.LastSubmit)` on the next line).
The Order is created by an explicit `Patch(Order, Defaults(Order), {...})` further down.

**The C2-alt decision table below is too coarse and will mislead you.** "Does `OnSelect` contain
a `SubmitForm`?" is the wrong test. The right test is **"what statement creates the `Order`
record?"** Anyone applying the table literally would have put the fan-out on `Form2.OnSuccess`,
firing it on every Model Revision save, against the wrong record, silently.

### 2. The Order Patch had to be wrapped

It was a bare `Patch(...)` with its result discarded. Now `Set(varNewOrder, Patch(Order, ...))`.
The variable is **`varNewOrder`**, not `newOrder` — matches the app's `var`-prefix convention.

### 3. Short lookup shape, not `SPListExpandedReference`

The app's own working lookups use `{Id: ..., Value: ...}`. The `'@odata.type'` form written below
is unnecessary against this site. Short form shipped and works.

### 4. No create-only guard needed

There is **no Order form** — the Order is patched from loose controls with `Defaults(Order)`
hardcoded, so the Save button is create-only by construction. The `If(FormMode = FormMode.New,
...)` wrapper the runbook and the C2/C2-alt sections both demand is dead weight here.

---

## C1b — which `Models` row an SA unit points at

**This is the one C1 missed.** C1 settled the SA row *grain* (how many rows); it never addressed
*which model* those rows carry. The first build of C2 pointed SA units at the **main** model —
caught by the user in testing, 2026-09-01 ~06:00.

Two independent sources, no inference:

- **`FRM10-12_2026-08-31_09h41m.xlsx`, sheet `Orders`**: 43 of 43 SA rows carry
  `Modèle = <main model code> & " SA"`. Zero exceptions.
  (`21408-1/1` → `TMP9`, `21408-1/1 SA` → `TMP9 SA`.)
- **`models-sa-fusion-plan.md`** (migration completed 2026-08-13, live): `Models SA` was fused
  into `Models`. SA designs are ordinary `Models` rows with `SA Model = Yes` and a
  self-referencing **`Parent Model`** lookup at the main model. Every one already has its
  `Latest Model Revision` populated (fusion step 5).

**Resolve by the `Parent Model` FK, never by the `" SA"` suffix.** The fusion plan says so
explicitly, and proves why: `MSA-HYQU-0071`'s `Model_Code` is `4276269` with **no `" SA"`
suffix** — a confirmed data-entry omission. A suffix match silently misses it. The suffix is a
naming convention that mostly holds, not a key.

Inside `If(varNewOrder.SA, ...)`, before the `ForAll`:

```
Set(
    SelectedSAModel,
    LookUp(
        Models,
        'SA Model' = true && 'Parent Model'.Id = SelectedModel.ID
    )
);
```

Then, **in the SA loop only** — the main loop keeps the main model unchanged:

```
Model: If(
    !IsBlank(SelectedSAModel),
    { Id: SelectedSAModel.ID, Value: SelectedSAModel.Model_Code }
),
'Model Revision': If(
    !IsBlank(SelectedSAModel),
    {
        Id:    SelectedSAModel.'Latest Model Revision'.Id,
        Value: SelectedSAModel.'Latest Model Revision'.Value
    }
)
```

### Why blank, and not a fallback to the main model

The no-`else` `If` yields **blank** when a model has no SA twin — which happens on every
`varNewModel` save, since the app creates a main `Models` row and no SA counterpart.

That is deliberate. Pointing an SA unit at the main design **fabricates spec data**, and this
exact failure class already cost real time: the crossed `Latest Model Revision` links found on
2026-08-13, where `21611-1/1 SA` displayed `4261871 SA`'s `Form`/`Copper (LV)`/`Wire (HV)`/`kVA`.
It took a systemic check to establish it was a bad link rather than a cache artifact. **A blank
lookup is loud; a wrong lookup is silent.** Same principle as the runbook's A5b refusal to let
the transfer flow fabricate `Completed`.

Consequence to design around, not to paper over: **a brand-new model + SA ticked produces SA
units with no model.** They need a model assigned afterwards. Making the app create the SA twin
at model-creation time is the real fix and is not built.

### This closes `models-sa-fusion-plan.md` "Migration scope" step 5

> *"Build the order-item-generation logic that resolves the correct `Models` row (main vs. SA)
> for each unit — this is new logic, not just a repoint."*

Open since 2026-08-13; the last not-started item in that plan. It now lives in the sales app's
Save button. Note the scope limit: this implements it for **app-created** orders only. The
transfer flow and `phase1-plan.md`'s `Work Order` fan-out still need the same resolution logic.

---

## C1 — `Order.SA` grain: RESOLVED, per-unit

The runbook left this open ("does `Qty = 5` + `SA = true` mean five SA rows or one?") and told
you to answer it from live data. It is answerable **offline**, from the fan-out `TableOrders`
already performs today, and the answer is unambiguous.

Source: `FRM10-12/live-workbook-data/FRM10-12_2026-08-31_09h41m.xlsx`, sheet `Orders` —
980 unit rows across 354 orders.

- 43 SA rows across **34** orders.
- **34 of 34**: `main row count == SA row count == Qty`. No exceptions.
- SA rows are **additive**, not a replacement. Order `21499` (Qty 3) carries six rows:

```
21499-1/3      21499-1/3 SA
21499-2/3      21499-2/3 SA
21499-3/3      21499-3/3 SA
```

**Therefore**: the SA pass is a second `ForAll(Sequence(newOrder.Qty))`, not a single Patch.
An SA order with Qty 3 creates **6** `Order Items` rows.

Unit ID format, exactly: `{Order Number}-{n}/{Qty}` and `{Order Number}-{n}/{Qty} SA` — single
space before `SA`, same `n/Qty` numbering on both.

---

## C2 — the formula

Goes after the Patch that creates the Order, with that Patch's result captured as `newOrder`.

```
Set(newOrder, Patch('Order', Defaults('Order'), { ...your existing form fields... }));

// main units
ForAll(
    Sequence(newOrder.Qty) As Unit,
    If(
        IsBlank(
            LookUp('Order Items',
                   'Unit ID' = newOrder.'Order Number' & "-" & Unit.Value & "/" & newOrder.Qty)
        ),
        Patch('Order Items', Defaults('Order Items'),
            {
                'Unit ID':      newOrder.'Order Number' & "-" & Unit.Value & "/" & newOrder.Qty,
                'Unit #':       Unit.Value,
                Qty:            newOrder.Qty,
                'SA Job':       false,
                'Item Status':  { Value: "Active" },
                'Order Number': {
                    '@odata.type': "#Microsoft.Azure.Connectors.SharePoint.SPListExpandedReference",
                    Id:    newOrder.ID,
                    Value: newOrder.'Order Number'
                },
                Order_Number_TextField: newOrder.'Order Number',
                Client:           newOrder.Client,
                Model:            newOrder.Model,
                'Model Revision': newOrder.'Model Revision'
            }
        )
    )
);

// SA units — same grain, per C1
If(newOrder.SA,
    ForAll(
        Sequence(newOrder.Qty) As Unit,
        If(
            IsBlank(
                LookUp('Order Items',
                       'Unit ID' = newOrder.'Order Number' & "-" & Unit.Value & "/" & newOrder.Qty & " SA")
            ),
            Patch('Order Items', Defaults('Order Items'),
                {
                    'Unit ID':      newOrder.'Order Number' & "-" & Unit.Value & "/" & newOrder.Qty & " SA",
                    'Unit #':       Unit.Value,
                    Qty:            newOrder.Qty,
                    'SA Job':       true,
                    'Item Status':  { Value: "Active" },
                    'Order Number': {
                        '@odata.type': "#Microsoft.Azure.Connectors.SharePoint.SPListExpandedReference",
                        Id:    newOrder.ID,
                        Value: newOrder.'Order Number'
                    },
                    Order_Number_TextField: newOrder.'Order Number',
                    Client:           newOrder.Client,
                    Model:            newOrder.Model,
                    'Model Revision': newOrder.'Model Revision'
                }
            )
        )
    )
);
```

### Five deliberate changes from the runbook's draft

1. **`As Unit` scoping instead of bare `Value`.** `Sequence()` returns a single-column table
   whose column is named `Value`, which collides with the `Value()` function inside a nested
   `Patch` scope. `As Unit` / `Unit.Value` removes the ambiguity outright. Cheap insurance at
   03:00.

2. **`'Unit ID'`, not `Title`.** The column's internal name is `Title` but its DisplayName is
   `Unit ID` (confirmed in the `Order Items` schema export), and Power Apps addresses SharePoint
   columns by **display name**. *Verify against Studio's intellisense as you type* — if the app
   predates the rename it may still offer `Title`.

3. **Lookups written in `SPListExpandedReference` shape.** A bare record assigned to a SharePoint
   Lookup is the most common cause of a silently-failing Patch. `Order Number` is written
   explicitly. `Client` / `Model` / `Model Revision` are copied straight off `newOrder`, where
   they are *already* expanded references of the same shape — so a direct copy should work.
   **Test those three first**; if any lands blank, expand it like `Order Number` using
   `newOrder.Client.Id` / `.Value`.

4. **`Order_Number_TextField` written inline.** See the hazard below — this is the one the
   Production Floor view puts on screen.

5. **The SA branch is a full `ForAll`**, resolved by C1.

### Guards, as the runbook requires

- **Create-only.** If the Save button is shared between new and edit, wrap the whole thing in
  `If(FormMode = FormMode.New, ...)`. Editing an order must never re-fan-out.
- **Idempotency.** The `IsBlank(LookUp(...))` around each Patch makes a double-tap on Save a
  no-op rather than a double-create. `LookUp` on a text column with `=` is delegable, so this is
  safe against the ~1000-row list.
- **Qty changes after the fact** are out of scope tonight, per the runbook. No mechanism exists
  today either.

---

## C2-alt — if the Save button is `SubmitForm`, not `Patch`

> **SUPERSEDED 2026-09-01 — see AS BUILT §1.** This table's test is wrong: Pioneer's Save
> button contains a `SubmitForm` that belongs to the *Model Revision* form, and an `Order`
> `Patch` further down. Ask **"what creates the Order record?"**, not "is there a
> `SubmitForm` anywhere?". Kept below because the `OnSuccess`/`LastSubmit` reasoning is still
> correct for an app whose Order *is* a form.

**Check this first, it decides where the code goes.** Select the Save button and read `OnSelect`:

| `OnSelect` reads | Which variant | Where the fan-out goes |
|---|---|---|
| `Patch('Order', ...)` | C2 above | Straight after the Patch, same `OnSelect` |
| `SubmitForm(FormName)` | **C2-alt, below** | The **form's `OnSuccess`** — *not* `OnSelect` |

With `SubmitForm` the record does not exist yet when `OnSelect` finishes, so a fan-out placed
there fans out against nothing — silently, with no error. `SubmitForm` is asynchronous; the
created record only becomes available in the form's `OnSuccess`, as `FormName.LastSubmit`.

Leave `OnSelect` as `SubmitForm(FormName)`. Put this on the **form's `OnSuccess`**:

```
Set(newOrder, FormName.LastSubmit);

// ...then the two ForAll blocks from C2 above, verbatim and unchanged.
```

Everything else is identical — the `Set` is the only line that differs. Substitute your form's
real name for `FormName`.

Two things to know about this route:

- **`OnSuccess` fires on edit too**, not just create. The create-only guard stops being optional
  here: wrap the fan-out in `If(FormName.Mode = FormMode.New, ...)`. Without it, every edit to an
  existing order re-runs the fan-out — the idempotency `LookUp` would absorb it for unchanged
  Qty, but an edited Qty would generate a second, differently-numbered set of units.
- **`LastSubmit` carries the server's response**, so `newOrder.ID` and any server-computed
  defaults are populated. That is exactly what the `Order Number` lookup needs.

---

## Hazard for Track A — the TextFields the demo actually shows

**`Order_Number_TextField` is written by `Order Items - created or updated trigger`**
(`lookup-textfield-reference.md`: Simple pattern, built & tested 2026-08-13). Two consequences
Track A needs:

1. **A4 moves TextField sync into the transfer flow — but the fan-out does not use the transfer
   flow.** App-created rows fire the *trigger* flow. The runbook already says keep the trigger
   flow alive for manual edits; that same requirement now covers **every order sales creates from
   tomorrow**. If A3's stripping damages the TextField branch, every new order shows a blank
   Order Number in the Production Floor view — on screen, permanently, on the primary staff view.

2. **The trigger flow is OFF during A6's run.** Fan-out test rows created in that window get
   blank TextFields and would read as a fan-out bug when they are not. Writing
   `Order_Number_TextField` inline (change 4) removes the dependency for the field that matters,
   and costs nothing — the app already holds the value it just wrote.

The three ID TextFields (`Client_ID_TextField`, `Model_ID_TextField`,
`Model_Revision_ID_TextField`) are **deliberately left to the trigger flow**. `Order` carries its
own copies, but they are written by *its* trigger flow, so on an order created in the same Save
they may still be blank at fan-out time — a race. The Order Items trigger flow resolves them via
the Get-item pattern already built and tested. Don't copy those three off `newOrder`.

---

## C3 — test plan

1. Confirm `Order Items - created or updated trigger` is **ON** before testing, or step 4's
   TextField check is meaningless.
2. Throwaway order, `Qty = 3`, `SA = false`. Expect exactly 3 rows: `{n}-1/3`, `{n}-2/3`, `{n}-3/3`.
3. Throwaway order, `Qty = 2`, `SA = true`. Expect exactly **4** rows — 2 main + 2 SA.
4. On one row confirm: `Item Status = Active`; `Order Number` lookup resolves;
   `Order_Number_TextField` populated *immediately*, before the flow runs; `Client` / `Model` /
   `Model Revision` resolved.
5. Tap Save twice on a new order — confirm no duplicate rows (idempotency guard).
6. **Write down every Unit ID created**, then delete all test rows before the demo.

**Rollback**: Power Apps keeps version history. If Save misbehaves, restore the previous version
immediately — sales creating orders tomorrow matters more than fan-out.

---

## Not done here

- The app is **not exported** — `FRM10-12/power-apps/` is empty but for `.gitkeep`. Runbook D6
  calls for exporting it, and it is about to carry business-critical logic with no backup
  anywhere. Track D owns that.
- This formula is written against the schema exports and the runbook, **not against the live
  app**. Control names, the Save button's existing Patch, and whether the form is shared between
  new and edit are all unverified. Reconcile in Studio.
