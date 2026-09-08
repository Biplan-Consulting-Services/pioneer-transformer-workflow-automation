# N3 flow definitions — generated

`python scripts/gen_n3_flows.py`. Source internal names read from the platform 2026-09-08; read shapes follow the R22 lesson (`?['Value']` on every Choice and Lookup source).


## `Order Items - sync from Order`

Trigger list **Order** · fan-out filter `OrderNumberId` · **18** fields

| → `Order Items` | ← source internal | source kind | read expression |
|---|---|---|---|
| `OrdClientDateStatus` | `ClientDateStatus` | choice | `triggerOutputs()?['body/ClientDateStatus']?['Value']` |
| `OrdEngineeringRequired` | `EngineeringRequired` | plain | `triggerOutputs()?['body/EngineeringRequired']` |
| `OrdIndexing` | `Indexing` | choice | `triggerOutputs()?['body/Indexing']?['Value']` |
| `OrdInitialPromisedDate` | `Initial_x0020_Promised_x0020_Dat` | plain | `triggerOutputs()?['body/Initial_x0020_Promised_x0020_Dat']` |
| `OrdLDs` | `LDs` | plain | `triggerOutputs()?['body/LDs']` |
| `OrdNewmodeltobecreated` | `New_x0020_model_x0020_to_x0020_b` | choice | `triggerOutputs()?['body/New_x0020_model_x0020_to_x0020_b']?['Value']` |
| `OrdNote` | `Note` | plain | `triggerOutputs()?['body/Note']` |
| `OrdOrderDate` | `Order_x0020_Date` | plain | `triggerOutputs()?['body/Order_x0020_Date']` |
| `OrdOrderNumber` | `Order_x0020_Number1` | plain | `triggerOutputs()?['body/Order_x0020_Number1']` |
| `OrdOrderStatus` | `OrderStatus` | choice | `triggerOutputs()?['body/OrderStatus']?['Value']` |
| `OrdOrderStep` | `Order_x0020_Step` | choice | `triggerOutputs()?['body/Order_x0020_Step']?['Value']` |
| `OrdOrderType` | `Order_x0020_Type1` | choice | `triggerOutputs()?['body/Order_x0020_Type1']?['Value']` |
| `OrdPO` | `PO` | plain | `triggerOutputs()?['body/PO']` |
| `OrdPrice` | `Price` | plain | `triggerOutputs()?['body/Price']` |
| `OrdProvinceState` | `Province_x002F_State` | plain | `triggerOutputs()?['body/Province_x002F_State']` |
| `OrdQty` | `Qty` | plain | `triggerOutputs()?['body/Qty']` |
| `OrdSalesNotes` | `SalesNotes` | plain | `triggerOutputs()?['body/SalesNotes']` |
| `OrdWETWETP` | `WET_x002d_WETP` | choice | `triggerOutputs()?['body/WET_x002d_WETP']?['Value']` |

## `Order Items - sync from Models`

Trigger list **Models** · fan-out filter `ModelId` · **5** fields

| → `Order Items` | ← source internal | source kind | read expression |
|---|---|---|---|
| `MdlEstimatedEffort` | `Estimated_x0020_Effort` | plain | `triggerOutputs()?['body/Estimated_x0020_Effort']` |
| `MdlLatestModelRevision` | `ModelRevision` | lookup | `triggerOutputs()?['body/ModelRevision']?['Value']` |
| `MdlModelID` | `ModelID` | plain | `triggerOutputs()?['body/ModelID']` |
| `MdlModificationStatus` | `ModificationStatus` | choice | `triggerOutputs()?['body/ModificationStatus']?['Value']` |
| `MdlParentModel` | `ParentModel` | lookup | `triggerOutputs()?['body/ParentModel']?['Value']` |

## `Order Items - sync from Model Revisions`

Trigger list **Model Revisions** · fan-out filter `ModelRevisionId` · **24** fields

| → `Order Items` | ← source internal | source kind | read expression |
|---|---|---|---|
| `RevCable` | `Cable` | plain | `triggerOutputs()?['body/Cable']` |
| `RevClientModelCode` | `ModelName` | plain | `triggerOutputs()?['body/ModelName']` |
| `RevCopperLV` | `Copper_x0028_LV_x0029_` | plain | `triggerOutputs()?['body/Copper_x0028_LV_x0029_']` |
| `RevCoreType` | `Core_x0020_Type` | choice | `triggerOutputs()?['body/Core_x0020_Type']?['Value']` |
| `RevDuplicateOrder` | `DuplicateOrder` | lookup | `triggerOutputs()?['body/DuplicateOrder']?['Value']` |
| `RevFamily` | `Family` | choice | `triggerOutputs()?['body/Family']?['Value']` |
| `RevForm` | `Form` | plain | `triggerOutputs()?['body/Form']` |
| `RevJS` | `JS_x0020__x0023_` | plain | `triggerOutputs()?['body/JS_x0020__x0023_']` |
| `RevModelDescription` | `Description` | multichoice | `if(empty(coalesce(triggerOutputs()?['body/Description'], json('[]'))), null, join(select(triggerOutputs()?['body/Description'], item()?['Value']), '; '))` |
| `RevModelType` | `Model_x0020_Type` | choice | `triggerOutputs()?['body/Model_x0020_Type']?['Value']` |
| `RevModelRevionID` | `ModelID` | plain | `triggerOutputs()?['body/ModelID']` |
| `RevNotes` | `Notes` | plain | `triggerOutputs()?['body/Notes']` |
| `RevOilAmount` | `OilAmount` | plain | `triggerOutputs()?['body/OilAmount']` |
| `RevOilType` | `Oil_x0020_Type` | choice | `triggerOutputs()?['body/Oil_x0020_Type']?['Value']` |
| `RevOvercoil` | `Overcoil` | plain | `triggerOutputs()?['body/Overcoil']` |
| `RevPhases` | `Phases` | plain | `triggerOutputs()?['body/Phases']` |
| `RevPioneerModelCode` | `Model` | lookup | `triggerOutputs()?['body/Model']?['Value']` |
| `RevPrimaryVoltage` | `PrimaryVoltage` | plain | `triggerOutputs()?['body/PrimaryVoltage']` |
| `RevSecondaryVoltage` | `SecondaryVoltage` | plain | `triggerOutputs()?['body/SecondaryVoltage']` |
| `RevSpecDate` | `Spec_Date` | plain | `triggerOutputs()?['body/Spec_Date']` |
| `RevSpecID` | `SpecID` | plain | `triggerOutputs()?['body/SpecID']` |
| `RevSpecRevision` | `Spec_Revision` | plain | `triggerOutputs()?['body/Spec_Revision']` |
| `RevWireHV` | `Wire_x0028_HV_x0029_` | plain | `triggerOutputs()?['body/Wire_x0028_HV_x0029_']` |
| `RevkVA` | `kVA_x0020_and_x0020_kV` | plain | `triggerOutputs()?['body/kVA_x0020_and_x0020_kV']` |

## Deliberately excluded

`OrdOrderFolder` (`Order_x0020_Folder`, URL). Roadmap 38 is an open decision — a hyperlink is an object on both read and write, the shape was never sourced, and a wrong one either fails every row or writes nothing. Confirm the shape from one real trigger payload, then add it.

## Validate these four things on the first run — I could not check them without the tenant

Everything above was read from the platform. These four are structural choices that only a
real run can confirm, so check them on one parent row with a small fan-out before enabling
(the spec suggests an `Order` with 2–3 units and no SA):

1. **`splitOn` + `triggerOutputs()`.** The trigger is `GetOnUpdatedItems` with
   `splitOn: @triggerOutputs()?['body/value']`, so each changed parent becomes its own run and
   `triggerOutputs()?['body/<field>']` refers to that single item. If the payload turns out not
   to be split, every `triggerOutputs()?['body/...']` would need `first(...)` instead — check
   one raw trigger output first.
2. **`ID` vs `Id`.** The fan-out uses `triggerOutputs()?['body/ID']` and the update uses
   `items('Apply_to_each_unit')?['ID']`. The connector emits both spellings; `ID` is the one the
   transfer flow already uses. Confirm in the raw inputs rather than assuming.
3. **`needsUpdate` returns a real boolean.** `@or(...)` in a Compose should yield `true`/`false`,
   which is what the following `If` compares against. If it ever arrives as the string `"true"`
   the condition silently never fires and nothing syncs — so on the smoke test, confirm the
   Compose output is boolean and that an actual change does trigger an update.
4. **The change-guard fires the right way round.** Edit one field on one parent and confirm
   exactly the units of that parent update, and that a second identical run updates **nothing**.
   A guard that never fires and a guard that always fires look identical from the run history —
   only the second, no-op run distinguishes them.

⚠️ **No trigger condition is set on these three flows, deliberately.** Writing to `Order Items`
cannot re-trigger a flow that watches `Order`, `Models` or `Model Revisions`. The trigger
condition the spec calls for belongs on the **`Order Items`** flow, so a sync-only write never
creates a run there — that is `X3`'s territory, not this one's.

⚠️ **`X3` is a hard prerequisite**, not a preference. Per the spec's capacity section, these
flows must not be enabled until the 2c stage-stamping is out of the `Order Items` trigger flow.
`Models` has a worst-case fan-out of **91** units from a single edit; each of those writes fires
the trigger flow, and at 100+ actions per run that is the shape of load that hit the capacity cap
and wedged 29 instances for six days.
