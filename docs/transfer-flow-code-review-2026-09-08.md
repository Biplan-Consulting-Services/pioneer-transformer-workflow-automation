# Code review — `Order Items - Excel Transfer Flow`

Reviewed 2026-09-08 against **v005** (v004 live + the 18 `Ord*` mappings staged). Read from the
definition, not from docs. Findings are ordered by what they cost if left alone.

---

## 🔴 1. A variable leaks across rows: SA units get the *previous* row's model

**This is the one to fix before the next run.** It writes a wrong, plausible-looking model onto
real units and reports nothing.

The two model variables are initialised **once, before the loop**:

```
InitialiseModelIDToWrite          ModelIDToWrite         = null   (top level)
InitializeModelRevisionIDToWrite  ModelRevisionIDToWrite = null   (top level)
```

Inside the loop they are set on two of three paths:

```
Condition:  IsSA == false
  TRUE  -> Set_variable    ModelIDToWrite         = GetResolvedOrder.Model/Id
           Set_variable_1  ModelRevisionIDToWrite = GetResolvedOrder.ModelRevision/Id
  ELSE  -> GetModels  (the SA twin: ParentModelId eq <order model> and SAModel eq 1)
           Condition_1:  length(GetModels) == 0
             TRUE  -> SAModelUnmatched = true          ← ⚠️ NEITHER VARIABLE IS SET
             ELSE  -> Set_variable_2  ModelIDToWrite         = first(GetModels).ID
                      Set_variable_3  ModelRevisionIDToWrite = first(GetModels).ModelRevision/Id
```

Both write actions then map:

```
item/Model/Id          @variables('ModelIDToWrite')
item/ModelRevision/Id  @variables('ModelRevisionIDToWrite')
```

**A Logic Apps variable is scoped to the run, not the iteration.** So on the `SAModelUnmatched`
path the write uses whatever the *previous* iteration left in the variable:

| iteration | unit | what happens |
|---|---|---|
| n | `21786-3/14` non-SA | `ModelIDToWrite` ← that order's model, say `M-HYQU-0092` |
| n+1 | `22110-1/1 SA`, no twin | variables **not set** → writes **`M-HYQU-0092`** |

The unit is silently attached to **another order's model**. And because `Apply_to_each` is
sequential (concurrency unset), it is deterministic rather than intermittent — which makes it
look like real data rather than a glitch.

**`SAModelUnmatched` does not save you.** It appears exactly **once** in the whole definition —
it is defined and never read. It stops nothing, flags nothing, and reaches no report. The
`Switch` still runs and the write still happens.

**Scale:** 42 SA units exist. `Parent Model` resolves for **15 of 15** SA models that have one,
but only **15 of 390 models have a twin at all** — so the no-twin path is the common case for SA
units, not the edge case. This is also precisely the failure R2 warned about, arriving by a
mechanism R2 did not describe.

### Fix

Set both variables to `null` at the **top of every iteration**, before `Condition`. Then the
no-twin path writes null — which leaves the lookup empty, visibly wrong and fixable, instead of
confidently wrong. Two `Set variable` actions, no logic change.

Better still, and cheap: give `Condition_1`'s TRUE branch an explicit null-set of its own, so the
intent is local and readable rather than depending on an initialisation twelve actions away.

---

## 🔴 2. Two `If` actions have no `else`, so rows vanish without a trace

| action | condition | what happens when false |
|---|---|---|
| `CheckOrderMatch` | `length(Get_Orders) == 1` | **the entire row is skipped** — no `Order Items` write at all |
| `CheckMatchCountModels` | `length(GetModels1) == 1` | the `Model Revisions` update is skipped |

Neither logs, neither counts, neither fails. A run reporting "982 iterations completed" is
therefore **not** a claim that 982 rows were written.

`CheckOrderMatch` is the serious one: any unit whose order number does not resolve to **exactly
one** `Order` row is dropped. That is a strong candidate for part of the missing-row diff — and
note the six named survivors (`P1_001-1/1`, `P20001-1/1`, `P20002-1/1`, `P20004-1/2`,
`P20004-2/2`, `20877R1-1/1`) look exactly like rows whose orders are absent from the `Order`
list. **This is testable against the exports and worth doing before blaming the run.**

**Fix:** add an `else` to each that appends the unit ID to an array variable, and surface the
array at the end. Cheap, and it converts "silently dropped" into a list you can act on.

---

## 🟡 3. Nine connector calls per row — ~9,171 per run

| when | action | operation |
|---|---|---|
| upfront | `List_rows_present_in_a_table` | Excel FRM10-12 |
| upfront | `List_rows_present_in_a_table_BO` | Excel BO Manager |
| **per row** | `Get_Orders` | Get items · Order |
| **per row** | `GetResolvedOrder` | Get item · Order |
| **per row** | `GetModels1` | Get items · Models |
| **per row** | `GetModels` | Get items · Models |
| **per row** | `Get_Order_items` | Get items · Order Items |
| **per row** | `UpdateOrder` | **write** · Order |
| **per row** | `Update_item` | **write** · Model Revisions |
| **per row** | `CreateOrderItem` / `UpdateOrderItem` | **write** · Order Items |

That is the shape behind the capacity ceiling, and it is why the plan treated the 24
`Mod. Rev. - X` columns as expensive: another `Get item` per row would have made it ten.

### 🟢 3a. `GetResolvedOrder` is redundant — 1,019 calls for nothing

```
Get_Orders        Get items on Order, $filter Order_x0020_Number1 eq <n>   → the full row
ResolvedOrderId   first(Get_Orders).ID
GetResolvedOrder  Get item on Order by that ID                             → the same row again
```

`Get_Orders` has **no `$select`**, so it already returns every field `GetResolvedOrder` returns.
Replacing `outputs('GetResolvedOrder')?['body/X']` with
`first(outputs('Get_Orders')?['body/value'])?['X']` deletes a call per row and changes nothing
else. **This is free and independent of everything below.**

---

## ✅ 4. Validating the fetch-once idea — it holds, with one caveat to decide

The proposal: fetch each list **once before the loop** and replace the per-row queries with
in-memory `Filter array`, exactly as `Filter_BO` already does for BO Manager.

Checked against the data rather than assumed:

| in-loop call | cacheable? | why |
|---|---|---|
| `Get_Orders` | ✅ | `Order` is 445 rows |
| `GetResolvedOrder` | ✅ | delete it outright (§3a) |
| `GetModels1` | ✅ | `Models` is 390 rows |
| `GetModels` | ✅ | same list, same snapshot |
| `Get_Order_items` | ✅ **verified safe** | see below |
| *(new)* Model Revisions | ✅ | 391 rows — this is what makes the 24 `Rev*` columns free |
| the 3 writes | ❌ | must stay per row |

**Result: 3 calls per row instead of 9.** 6 upfront + 3 × 1,019 = **~3,063 versus ~9,171 — a 67%
reduction** — *and* the 24 `Mod. Rev. - X` columns become free rather than costing 1,019 calls.

### The one thing that could have broken it, and did not

A snapshot is only equivalent to a live query if nothing the loop **writes** changes what a later
iteration would **read**. `Order Items` is written during the run, so:

> if two source rows shared a `Title`, iteration 1 would create the row, and iteration 2 —
> filtering a snapshot taken before it existed — would create a **duplicate** instead of
> updating.

Measured on the 2026-09-04 workbook: **1,019 source rows, 1,019 distinct `Order` values, zero
duplicates.** So no iteration can ever need to see a row an earlier one created. ✅

### ⚠️ The caveat: five fields on `Order` are both read and written by the loop

`UpdateOrder` writes `ClientDateStatus`, `EngineeringRequired`, `LDs`, `OrderStatus`,
`SalesNotes` — the "companion columns" — and v005 **reads those same five** to populate
`OrdClientDateStatus` and friends.

Today, with a live query, unit 2 of an order reads what unit 1's `UpdateOrder` just wrote. With a
snapshot it reads the pre-run value. **A real behaviour change, on 5 of 18 columns.**

Which is more correct is not obvious, and it is a judgement call rather than a bug:

- The **snapshot** gives every unit of an order the same value, independent of iteration order.
  That is more self-consistent.
- The **live query** propagates within the run, so later units see the freshest value.

**My recommendation: sidestep it entirely.** Those five originate in **Excel** — `UpdateOrder`
writes them Excel→`Order`. So have the five `Ord*` columns read `item()?['…']` from the Excel row
directly, the same source `UpdateOrder` uses. Then there is no ordering dependency, no staleness
question, and one less reason for the Excel→`Order`→`Order Items` round-trip that the risk
register already flags as backwards (and that R7 removes after the run).

### Paging is mandatory on every cached fetch

A SharePoint **`Get items` returns 100 rows by default.** All four lists exceed that (445 / 390 /
391 / 1,052). Every upfront fetch needs
`runtimeConfiguration.paginationPolicy.minimumItemCount: 5000`, matching the two Excel actions.

⚠️ **And this is already latent in the current flow:** `Get_Orders`, `Get_Order_items`,
`GetModels` and `GetModels1` have **neither `$top` nor pagination**. They are safe *only* because
each is filtered to an expected 0–1 rows. That is a correctness argument resting on a data
assumption, not on a setting — worth knowing before anyone loosens a filter.

---

## 🟡 5. `Update_item` writes `Family` unconditionally, so it erases as well as fills

Already logged as roadmap item 35, restated here because it is in the same action set: `Update_item`
maps `item/Family/Value: @item()?['Family']` with no blank guard, and **385 of 1,019** source rows
have a blank `Family`. Two units on one model, one blank, and the blank one clears the other's
value. The likely reason `Model Revisions.Family` is blank on 329 of 391 despite this mapping
having run for weeks.

---

## 🟢 6. What is right, and should not be "improved"

- **Sequential `Apply_to_each`** (concurrency unset). With writes to three lists and a run-scoped
  variable, parallelism would turn §1 from deterministic into a race. Leave it.
- **A failing row does not abort the run.** Confirmed by the Sep 1 run: 982 iterations completed
  and the run reported `Failed`. The iteration fails, the loop continues. So `Failed` means "at
  least one row" — never "nothing happened", and never "everything happened".
- **`Filter_BO` + one upfront Excel fetch** is exactly the pattern §4 generalises. It was the
  right call in D3 and it is the right call here.
- **The `Switch` default branch** (`DuplicateOrderItem`, a bare `Compose`) cannot throw, so a
  `Switch` failure is always one of the two write actions — which is what made the `int('ec')`
  diagnosis conclusive.

---

## Recommended sequencing

Splitting these matters, because combining a critical fix with a large restructure makes a failure
impossible to attribute.

| version | contents | size |
|---|---|---|
| **v006** | §1 the variable leak · §2 the two missing `else` branches · §3a delete `GetResolvedOrder` | small, surgical, all three are strict improvements |
| **v007** | §4 the fetch-once restructure · the 5 `Mdl*` and 24 `Rev*` columns · §4 caveat (five fields sourced from Excel) · §5 the `Family` guard | large but mechanical, and it is what makes the parent columns affordable |

v006 is worth pasting even if v007 waits: §1 is actively writing wrong models today, and §2 means
nobody currently knows how many rows the last run actually skipped.
