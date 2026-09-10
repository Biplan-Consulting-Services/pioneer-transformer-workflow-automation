# N3 flow definitions — generated

`python scripts/gen_n3_flows.py`. Source internal names read from the platform 2026-09-08; read shapes follow the R22 lesson (`?['Value']` on every Choice and Lookup source).


## `Order Items - sync from Order`

Trigger list **Order** · fan-out filter `OrderNumberId` · **17** fields

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
| `OrdOrderStatus` | `OrderStatus` | choice | `triggerOutputs()?['body/OrderStatus']?['Value']` |
| `OrdOrderStep` | `Order_x0020_Step` | choice | `triggerOutputs()?['body/Order_x0020_Step']?['Value']` |
| `OrdOrderType` | `Order_x0020_Type1` | choice | `triggerOutputs()?['body/Order_x0020_Type1']?['Value']` |
| `OrdPO` | `PO` | plain | `triggerOutputs()?['body/PO']` |
| `OrdPrice` | `Price` | plain | `triggerOutputs()?['body/Price']` |
| `OrdProvinceState` | `Province_x002F_State` | plain | `triggerOutputs()?['body/Province_x002F_State']` |
| `OrdSalesNotes` | `SalesNotes` | plain | `triggerOutputs()?['body/SalesNotes']` |
| `OrdWETWETP` | `WET_x002d_WETP` | choice | `triggerOutputs()?['body/WET_x002d_WETP']?['Value']` |
| `OrdOrderFolder` | `Order_x0020_Folder` | url | `triggerOutputs()?['body/Order_x0020_Folder']` |

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
| `RevModelDescription` | `Description` | multichoice | `if(empty(coalesce(triggerOutputs()?['body/Description'], json('[]'))), null, join(select(coalesce(triggerOutputs()?['body/Description'], json('[]')), item()?['Value']), '; '))` |
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
