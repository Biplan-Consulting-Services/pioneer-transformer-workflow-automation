# Archive rebuild check

- baseline: `Archive active 2026-09-28 1152.xlsx`
- new: `Archive active LIVE COPY.xlsx`
- mirror: `C:\Users\solei\OneDrive\Documents\Biplan\claude\Clients\Pioneer Transformer\Workflow-Automation\sharepoint-lists\mirror\live`
- run: 2026-09-28 12:50 (strict)

| # | check | status |
|---|---|---|
| 1 | Shape | FAIL |
| 2 | FRM10-12 cells | FAIL |
| 3 | Date columns hold no text | FAIL |
| 4 | List tables vs mirror | PASS |
| 5 | Additivity | PASS |
| 6 | Readers | PASS |
| 7 | Nightly Sync replay | WARN |
| 8 | BO merge | WARN |

## 1. Shape: FAIL

- **FAIL** TableArchiveFRM11 cells changed (4024 rows differ); it must stay untouched
  - `row count 4250 -> 4253`
  - `row 229 (21706-5/6): NUMÉRO DE CUVE '21706-5/6'->'21993-7/8', Fournisseur CUVE 'CADORETTE'->'FRAMECO', Fournisseur Peinture 'SIXPRO'->'MORIN'`
  - `row 230 (21706-4/6): NUMÉRO DE CUVE '21706-4/6'->'21706-5/6', Original Tanking Date 2025-10-15->2025-10-22, Date encuvage 2025-10-15->2025-10-20`
  - `row 231 (21706-3/6): NUMÉRO DE CUVE '21706-3/6'->'21706-4/6', Date encuvage 2025-10-14->2025-10-15, Date Livraison client 2025-10-28->2025-10-29`
  - `row 232 (21706-1/6): NUMÉRO DE CUVE '21706-1/6'->'21706-3/6', Original Tanking Date 2025-10-09->2025-10-15, Date encuvage 2025-10-09->2025-10-14`
- **WARN** TableArchiveFRM11 ref A1:AM4251 -> A1:AM4254 although the cells are identical
- **FAIL** TableArchiveFRM13 cells changed (249 rows differ); it must stay untouched
  - `row 602 (21635): TCQ Progress Chande Date 2026-09-27 23:56->2026-09-28 12:45`
  - `row 603 (21637): TCQ Progress Chande Date 2026-09-27 23:56->2026-09-28 12:45`
  - `row 604 (21639): TCQ Progress Chande Date 2026-09-27 23:56->2026-09-28 12:45`
  - `row 605 (21640): TCQ Progress Chande Date 2026-09-27 23:56->2026-09-28 12:45`
  - `row 606 (21626): TCQ Progress Chande Date 2026-09-27 23:56->2026-09-28 12:45`
- **PASS** TableArchiveFRM10_12 headers = the pinned 93 then the 18 BO detail columns
- **FAIL** TableArchiveFRM10_12 table GUID (xr:uid) is {B99ABEF7-7D68-4DB0-808A-AA182D45011C}, must be {17014A43-5D94-47C6-982F-45D962DA4036}: table was recreated
- **WARN** TableArchiveFRM10_12 table xml id/part/sheet moved: ('2', 'xl/tables/table2.xml', 'Archive FRM10-12') -> ('15', 'xl/tables/table2.xml', 'Archive FRM10-12') (the GUID is what the connector uses)
- **WARN** TableArchiveFRM10_12 keeps 1 blank-Order row(s) carried from the baseline

## 2. FRM10-12 cells: FAIL

- **FAIL** 5321 Orders in both copies, 494853 cells: identical 438480, cleaner 53859, newer 1647, intended 866, REGRESSION 1
- **FAIL** Tanking Date: 1 REGRESSION
  - `20597-1/1: '1899-12-31 12:00:00 AM' -> datetime.time(0, 0)  (mirror: unit not on SharePoint)`
- **PASS** info: 14 cells identical to the baseline but not to the mirror (stale rows)

| column | identical | cleaner | newer | intended | REGRESSION | stale* |
|---|---:|---:|---:|---:|---:|---:|
| Order | 5321 | 0 | 0 | 0 | 0 | 0 |
| Client | 5320 | 1 | 0 | 0 | 0 | 0 |
| KVA and KV | 128 | 5193 | 0 | 0 | 0 | 0 |
| Primary Voltage | 5321 | 0 | 0 | 0 | 0 | 0 |
| Secondary Voltage | 5321 | 0 | 0 | 0 | 0 | 0 |
| Phases | 2042 | 3279 | 0 | 0 | 0 | 0 |
| JS # | 5321 | 0 | 0 | 0 | 0 | 0 |
| Description | 5321 | 0 | 0 | 0 | 0 | 0 |
| Type | 5311 | 4 | 6 | 0 | 0 | 0 |
| PO | 5289 | 32 | 0 | 0 | 0 | 0 |
| Order Date | 5307 | 0 | 0 | 14 | 0 | 0 |
| Lead Time | 2566 | 2684 | 0 | 71 | 0 | 0 |
| Ing. Due Date | 5203 | 0 | 118 | 0 | 0 | 0 |
| Qty | 351 | 4970 | 0 | 0 | 0 | 0 |
| PO Item # | 5321 | 0 | 0 | 0 | 0 | 0 |
| Family | 5012 | 309 | 0 | 0 | 0 | 0 |
| Duplicate | 5321 | 0 | 0 | 0 | 0 | 2 |
| Engineering Required | 5319 | 0 | 2 | 0 | 0 | 0 |
| Duplicate Order | 5321 | 0 | 0 | 0 | 0 | 2 |
| Price | 0 | 5321 | 0 | 0 | 0 | 0 |
| Province/State | 5301 | 20 | 0 | 0 | 0 | 0 |
| WET-WETP | 5278 | 43 | 0 | 0 | 0 | 0 |
| Indexing | 5261 | 60 | 0 | 0 | 0 | 0 |
| LDs | 5321 | 0 | 0 | 0 | 0 | 0 |
| Initial Promised Date | 5303 | 0 | 0 | 18 | 0 | 0 |
| Trimestrial Customer | 5321 | 0 | 0 | 0 | 0 | 0 |
| Client Date Status | 4309 | 1012 | 0 | 0 | 0 | 0 |
| Info+ | 4265 | 1056 | 0 | 0 | 0 | 0 |
| Protector Status | 4195 | 1126 | 0 | 0 | 0 | 0 |
| Protector & Switchgear PO | 5321 | 0 | 0 | 0 | 0 | 0 |
| Protector & Switchgear Item # | 4195 | 1126 | 0 | 0 | 0 | 0 |
| Sales Notes | 4195 | 1126 | 0 | 0 | 0 | 0 |
| Technical Notes | 4176 | 1145 | 0 | 0 | 0 | 0 |
| Location | 4374 | 899 | 48 | 0 | 0 | 0 |
| Status | 4282 | 900 | 139 | 0 | 0 | 0 |
| Witness/Other | 4197 | 1124 | 0 | 0 | 0 | 0 |
| Temperature Rise | 5321 | 0 | 0 | 0 | 0 | 0 |
| Impulse | 5321 | 0 | 0 | 0 | 0 | 0 |
| DB | 5321 | 0 | 0 | 0 | 0 | 0 |
| Partial D | 5321 | 0 | 0 | 0 | 0 | 0 |
| Oil Analysis | 5321 | 0 | 0 | 0 | 0 | 0 |
| SFRA | 5321 | 0 | 0 | 0 | 0 | 0 |
| CSA | 5319 | 0 | 2 | 0 | 0 | 0 |
| Core | 4780 | 541 | 0 | 0 | 0 | 0 |
| Core Status | 4473 | 846 | 2 | 0 | 0 | 0 |
| Oil Type | 5246 | 75 | 0 | 0 | 0 | 0 |
| Oil Amount | 487 | 4834 | 0 | 0 | 0 | 0 |
| Production Line | 5321 | 0 | 0 | 0 | 0 | 0 |
| Configuration | 5319 | 0 | 2 | 0 | 0 | 0 |
| Section Qty | 3220 | 2101 | 0 | 0 | 0 | 0 |
| Cable | 5321 | 0 | 0 | 0 | 0 | 0 |
| Coil Winder | 5321 | 0 | 0 | 0 | 0 | 0 |
| Form | 5173 | 148 | 0 | 0 | 0 | 0 |
| Copper (LV) | 5158 | 163 | 0 | 0 | 0 | 0 |
| Wire (HV) | 5158 | 163 | 0 | 0 | 0 | 0 |
| Overcoil | 558 | 4728 | 35 | 0 | 0 | 0 |
| Winder | 4975 | 346 | 0 | 0 | 0 | 0 |
| Time (days) | 3810 | 1511 | 0 | 0 | 0 | 0 |
| Tank | 5318 | 0 | 3 | 0 | 0 | 0 |
| Tank Delivery Date | 5321 | 0 | 0 | 0 | 0 | 0 |
| Frame | 5321 | 0 | 0 | 0 | 0 | 0 |
| ISO Stack | 5318 | 0 | 3 | 0 | 0 | 0 |
| ISO Coil | 5295 | 0 | 26 | 0 | 0 | 0 |
| Lead Assembly | 5319 | 0 | 2 | 0 | 0 | 0 |
| Coiling Date | 5314 | 0 | 7 | 0 | 0 | 0 |
| Stacking Date | 5319 | 0 | 2 | 0 | 0 | 0 |
| Assembly Date | 5316 | 0 | 5 | 0 | 0 | 0 |
| Drying Date | 5313 | 0 | 8 | 0 | 0 | 0 |
| Tanking Date | 5314 | 0 | 6 | 0 | 1 | 0 |
| Testing Date | 5319 | 0 | 2 | 0 | 0 | 0 |
| Finishing Date | 5313 | 0 | 8 | 0 | 0 | 0 |
| Delivery Date | 5282 | 0 | 39 | 0 | 0 | 0 |
| Original Tanking Date | 5321 | 0 | 0 | 0 | 0 | 0 |
| Estimated Delivery Date | 5275 | 0 | 0 | 46 | 0 | 0 |
| Tanking date change justification | 4369 | 908 | 44 | 0 | 0 | 4 |
| Manual Estimated Delivery Date | 5318 | 0 | 3 | 0 | 0 | 0 |
| BO | 5310 | 0 | 3 | 8 | 0 | 6 |
| Price Value | 3731 | 1590 | 0 | 0 | 0 | 0 |
| Price CAD | 2699 | 2608 | 0 | 14 | 0 | 0 |
| Price USD | 2759 | 1867 | 0 | 695 | 0 | 0 |
| Navigation Order | 5321 | 0 | 0 | 0 | 0 | 0 |
| Navigation Model | 5317 | 0 | 4 | 0 | 0 | 0 |
| Archived | 5321 | 0 | 0 | 0 | 0 | 0 |
| Lot | 5321 | 0 | 0 | 0 | 0 | 0 |
| Tanking Date Status | 5321 | 0 | 0 | 0 | 0 | 0 |
| Planning Notes | 5321 | 0 | 0 | 0 | 0 | 0 |
| Production Complexity | 5321 | 0 | 0 | 0 | 0 | 0 |
| __PowerAppsId__ | 5321 | 0 | 0 | 0 | 0 | 0 |
| Client Desired Date | 5321 | 0 | 0 | 0 | 0 | 0 |
| FI | 5321 | 0 | 0 | 0 | 0 | 0 |
| Stack | 5321 | 0 | 0 | 0 | 0 | 0 |
| Production Status | 5321 | 0 | 0 | 0 | 0 | 0 |
| Last Synchronisation Date | 4193 | 0 | 1128 | 0 | 0 | 0 |

*stale = identical to the baseline but differs from the mirror's value (info: the row was not refreshed).
- Assembly Date / newer: 21387-5/6: None -> 2026-09-21; 21814-3/11: None -> 2026-09-25; 21996-10/10: 2026-09-23 -> None; 21996-8/10: 2026-09-23 -> None; 21996-9/10: 2026-09-23 -> None
- BO / intended: 21787-1/5: None -> 'OK'; 21803-1/8: None -> 'OK'; 21813-1/1: None -> 'OK'; 21818-10/10: None -> 'BO'; 21840-1/10: None -> 'OK'
- BO / newer: 21873-1/8: 'BO' -> 'OK'; 22069-1/10: 'BO' -> 'OK'; P20004-1/2: 'OK' -> 'BO'
- CSA / newer: 21792-3/5: None -> False; 21792-4/5: None -> False
- Client / cleaner: 20877R1-1/1: 'BEAVER ELECTRICAL' -> 'BEAVER ELECTRICAL '
- Client Date Status / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 20877R1-1/1: '' -> None; 21040W2-1/1: '' -> None
- Coiling Date / newer: 21875-1/5: 'EC' -> 2026-09-25; 21875-2/5: None -> 'EC'; 21876-1/5: 'EC' -> 2026-10-02; 21876-2/5: None -> 'EC'; 21913-3/7: 'EC' -> 2026-09-25
- Configuration / newer: 21792-3/5: 'HQ' -> None; 21792-4/5: 'HQ' -> None
- Copper (LV) / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 21522-1/3: '' -> None; 21522-2/3: '' -> None
- Core / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 21050W1-1/1: '' -> None; 21350-1/1: '' -> None
- Core Status / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20877R1-1/1: '' -> None; 21304-1/2: '' -> None; 21304-2/2: '' -> None
- Core Status / newer: P20004-1/2: '' -> 'Reçu'; P20004-2/2: '' -> 'Reçu'
- Delivery Date / newer: 21792-3/5: 2026-09-24 -> 2026-09-03; 21792-4/5: 2026-09-24 -> 2026-09-03; 21835-1/1: None -> 2026-09-30; 21840-10/10: 2026-10-30 -> 2026-09-30; 21854-1/2: None -> 2026-10-30
- Drying Date / newer: 21387-5/6: None -> 2026-09-21; 21980-1/1: None -> 2026-09-28; 21996-1/10: None -> 2026-09-25; 21996-2/10: None -> 2026-09-25; 21996-3/10: None -> 2026-09-25
- Engineering Required / newer: 21792-3/5: 'N' -> None; 21792-4/5: 'N' -> None
- Estimated Delivery Date / intended: 21792-3/5: 2026-09-24 -> 2026-09-03; 21792-4/5: 2026-09-24 -> 2026-09-03; 21835-1/1: 2026-09-15 -> 2026-09-30; 21840-10/10: 2026-10-30 -> 2026-09-30; 21854-1/2: 2026-10-29 -> 2026-10-30
- Family / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 21304-1/2: '' -> None; 21304-2/2: '' -> None
- Finishing Date / newer: 21387-4/6: None -> 2026-09-25; 21521-1/1: None -> 2026-09-25; 21657-1/1: None -> 2026-09-25; 21793-4/5: None -> 2026-09-25; 21911-6/7: None -> 2026-09-25
- Form / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 21664-1/1 SA: '' -> None; 21665-1/3 SA: '' -> None
- ISO Coil / newer: 21874-1/5: None -> 'R'; 21874-2/5: None -> 'R'; 21874-3/5: None -> 'R'; 21874-4/5: None -> 'R'; 21874-5/5: None -> 'R'
- ISO Stack / newer: 21387-5/6: None -> 'R'; 21387-6/6: None -> 'R'; 21916-1/1: None -> 'R'
- Indexing / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 20877R1-1/1: '' -> None; 21040W2-1/1: '' -> None
- Info+ / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 20877R1-1/1: '' -> None; 21040W2-1/1: '' -> None
- Ing. Due Date / newer: 20164W2-1/1: 2025-12-22 -> 2025-12-23; 21040W2-1/1: 2026-02-24 -> 2026-02-25; 21386-2/2: 2025-10-09 -> 2025-10-10; 21499-1/3: 2026-01-11 -> 2026-01-12; 21499-1/3 SA: 2026-01-11 -> 2026-01-12
- Initial Promised Date / intended: 22140-1/2: 2027-03-25 -> 2027-03-26; 22140-2/2: 2027-03-25 -> 2027-03-26; 22141-1/2: 2027-03-25 -> 2027-03-26; 22141-2/2: 2027-03-25 -> 2027-03-26; 22156-1/1: 2027-01-17 -> 2027-01-18
- KVA and KV / cleaner: 19394-1/2SA: '500' -> 500; 19394-2/2SA: '750' -> 750; 19515-1/1: '4889' -> 4889; 19515-W4-14: '4889' -> 4889; 19515-W4-39: '4889' -> 4889
- Last Synchronisation Date / newer: 19515-W4-39: 2026-09-27 -> 2026-09-28; 19515-W4-53: 2026-09-27 -> 2026-09-28; 20164W2-1/1: 2026-09-27 -> 2026-09-28; 20877R1-1/1: 2026-09-27 -> 2026-09-28; 21040W2-1/1: 2026-09-27 -> 2026-09-28
- Lead Assembly / newer: 21387-5/6: None -> 'R'; 21832-8/11: None -> 'R'
- Lead Time / cleaner: 19515-1/1: '26' -> 26; 19515-W4-14: '26' -> 26; 19515-W4-39: '26' -> 26; 19515-W4-53: '26' -> 26; 20162W2-1/1: '26' -> 26
- Lead Time / intended: 21657-1/1: '26' -> 18; 21847-1/1: '26' -> 20; 21848-1/3: '26' -> 20; 21848-2/3: '26' -> 20; 21848-3/3: '26' -> 20
- Location / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20877R1-1/1: '' -> None; 21304-1/2: '' -> None; 21304-2/2: '' -> None
- Location / newer: 21387-4/6: 'FI' -> 'XT'; 21387-5/6: 'BO' -> 'TA'; 21387-6/6: 'BO' -> 'ST'; 21521-1/1: 'FI' -> 'XT'; 21657-1/1: 'FI' -> 'XT'
- Manual Estimated Delivery Date / newer: 21792-3/5: None -> 2026-09-24; 21792-4/5: None -> 2026-09-24; 22179-1/1: None -> 2027-09-17
- Navigation Model / newer: 20877R1-1/1: 'Ouvrir modèle' -> None; P1_001-1/1: 'Ouvrir modèle' -> None; P20001-1/1: 'Ouvrir modèle' -> None; P20002-1/1: 'Ouvrir modèle' -> None
- Oil Amount / cleaner: 19394-1/2: '6240' -> 6240; 19394-2/2: '6240' -> 6240; 19515-1/1: '0' -> 0; 19515-W4-39: '0' -> 0; 19515-W4-53: '0' -> 0
- Oil Type / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 21499-1/3 SA: '' -> None; 21499-2/3 SA: '' -> None; 21499-3/3 SA: '' -> None
- Order Date / intended: 22156-1/1: 2026-08-31 -> 2026-09-01; 22157-1/10: 2026-08-31 -> 2026-09-01; 22157-10/10: 2026-08-31 -> 2026-09-01; 22157-2/10: 2026-08-31 -> 2026-09-01; 22157-3/10: 2026-08-31 -> 2026-09-01
- Overcoil / cleaner: 19394-1/2: '28125' -> 28125; 19394-1/2SA: '15,25' -> 15.25; 19394-2/2: '28125' -> 28125; 19394-2/2SA: '15,25' -> 15.25; 20162W2-1/1: '19' -> 19
- Overcoil / newer: 21382-1/2: '33625' -> 33.625; 21382-2/2: '33625' -> 33.625; 21386-2/2: '33625' -> 33.625; 21387-4/6: '33625' -> 33.625; 21387-5/6: '33625' -> 33.625
- PO / cleaner: 21943-8/8: '4513563161' -> '4513563161 '; 21946-1/5: '4513563162' -> '4513563162 '; 21946-2/5: '4513563162' -> '4513563162 '; 21946-3/5: '4513563162' -> '4513563162 '; 21946-4/5: '4513563162' -> '4513563162 '
- Phases / cleaner: 19515-1/1: '3' -> 3; 19515-W4-14: '3' -> 3; 19515-W4-39: '3' -> 3; 19515-W4-53: '3' -> 3; 20162W2-1/1: '1' -> 1
- Price / cleaner: 19394-1/2: '314124' -> 314124; 19394-1/2SA: '0' -> 0; 19394-2/2: '314124' -> 314124; 19394-2/2SA: '0' -> 0; 19515-1/1: '86017' -> 86017
- Price CAD / cleaner: 19515-1/1: '118703,46' -> 118703.46; 19515-W4-14: '86017' -> 86017; 19515-W4-39: '119563.63' -> 119563.63; 19515-W4-53: '119563.63' -> 119563.63; 20162W2-1/1: '0' -> 0
- Price CAD / intended: 21714-1/4: '230591.1' -> 225578.25; 21714-2/4: '230591.1' -> 225578.25; 21714-3/4: None -> 225578.25; 21714-4/4: None -> 225578.25; 21917-1/1: '122640.7242' -> 123529.4251
- Price USD / cleaner: 19515-1/1: '86017' -> 86017; 19515-W4-14: '6233115942' -> 6233115942; 19515-W4-39: '86017' -> 86017; 19515-W4-53: '86017' -> 86017; 20162W2-1/1: '0' -> 0
- Price USD / intended: 21304-1/2: '324467.2374' -> 324467.237410072; 21304-2/2: '324467.2374' -> 324467.237410072; 21350-1/1: '130490.1583' -> 126840.083916084; 21351-1/1: '131293.3237' -> 127620.783216783; 21352-1/1: '131435.7391' -> 131435.739130435
- Price Value / cleaner: 19515-1/1: '86017' -> 86017; 19515-W4-39: '86017' -> 86017; 19515-W4-53: '86017' -> 86017; 20162W2-1/1: '0' -> 0; 20163W2-1/1: '0' -> 0
- Protector & Switchgear Item # / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 20877R1-1/1: '' -> None; 21040W2-1/1: '' -> None
- Protector Status / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 20877R1-1/1: '' -> None; 21040W2-1/1: '' -> None
- Province/State / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 20877R1-1/1: '' -> None; 21040W2-1/1: '' -> None
- Qty / cleaner: 19394-1/2: '2' -> 2; 19394-2/2: '2' -> 2; 19515-1/1: '1' -> 1; 19515-W4-14: '1' -> 1; 19515-W4-39: '39' -> 39
- Sales Notes / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 20877R1-1/1: '' -> None; 21040W2-1/1: '' -> None
- Section Qty / cleaner: 20162W2-1/1: '0' -> 0; 20522-1/1: '0' -> 0; 20572R1-5: '0' -> 0; 20937-1/1: '0' -> 0; 20944-1/1: '0' -> 0
- Stacking Date / newer: 21387-5/6: None -> 2026-09-21; 21832-10/11: None -> 2026-09-25
- Status / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20877R1-1/1: '' -> None; 21304-1/2: '' -> None; 21304-2/2: '' -> None
- Status / newer: 21387-4/6: 'EC-Se-25' -> 'TE-Se-25'; 21387-5/6: 'TE-Se-25' -> 'TE-Se-28'; 21387-6/6: 'TE-Se-25' -> 'EC-Se-28'; 21521-1/1: 'EC-Se-25' -> 'TE-Se-25'; 21657-1/1: 'EC-Se-25' -> 'TE-Se-25'
- Tank / newer: 21387-5/6: None -> 'R'; 21841-10/10: None -> 'R'; 21841-8/10: None -> 'R'
- Tanking Date / newer: 21875-1/5: 2026-10-14 -> 2026-10-19; 21875-2/5: 2026-10-14 -> 2026-10-20; 21875-3/5: 2026-10-19 -> 2026-10-27; 21875-4/5: 2026-10-19 -> 2026-10-27; 21875-5/5: 2026-10-20 -> 2026-10-28
- Tanking date change justification / cleaner: 20877R1-1/1: '' -> None; 21364-1/1: '' -> None; 21365-1/1: '' -> None; 21371-1/1: '' -> None; 21382-1/2: '' -> None
- Tanking date change justification / newer: 21854-2/2: 'perte à vide' -> 'Perte à vide\n'; 21908-1/6: 'À expédier en Q4 / Rads arrivent début août / Pb STC' -> '28/09/2026 :  Pascal demande que les commandes de janvier 2027 soient tirées en dec 2026. \nÀ expédier en Q4 / Rads arrivent début août / Pb STC'; 21908-2/6: 'À expédier en Q4 / Rads arrivent début août / Pb STC' -> '28/09/2026 :  Pascal demande que les commandes de janvier 2027 soient tirées en dec 2026. \nÀ expédier en Q4 / Rads arrivent début août / Pb STC'; 21908-3/6: 'À expédier en Q4 / Rads arrivent début août / Pb STC' -> '28/09/2026 :  Pascal demande que les commandes de janvier 2027 soient tirées en dec 2026. \nÀ expédier en Q4 / Rads arrivent début août / Pb STC'; 21908-4/6: 'À expédier en Q4 / Rads arrivent début août / Pb STC' -> '28/09/2026 :  Pascal demande que les commandes de janvier 2027 soient tirées en dec 2026. \nÀ expédier en Q4 / Rads arrivent début août / Pb STC'
- Technical Notes / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 20877R1-1/1: '' -> None; 21040W2-1/1: '' -> None
- Testing Date / newer: 21841-4/10: None -> 2026-09-25; 21994-3/3: None -> 2026-09-25
- Time (days) / cleaner: 19394-1/2: '2,5' -> 2.5; 19394-1/2SA: '1779418627' -> 1779418627; 19394-2/2: '2,5' -> 2.5; 19394-2/2SA: '1779418627' -> 1779418627; 20293-1/1: '1486677914' -> 1486677914
- Type / cleaner: E21003R1-1/1: '' -> None; P21911_B-1/1: '' -> None; WRG3027-1/2: '' -> None; WRG3027-2/2: '' -> None
- Type / newer: 20164W2-1/1: 'Substation' -> 'SUBSTATION'; 21918-1/1: 'Substation' -> 'SUBSTATION'; 21937-1/1: 'Substation' -> 'SUBSTATION'; E21009-1/1: 'Substation' -> 'SUBSTATION'; E21015-1/1: 'Substation' -> 'SUBSTATION'
- WET-WETP / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 20877R1-1/1: '' -> None; 21040W2-1/1: '' -> None
- Winder / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 20877R1-1/1: '' -> None; 21522-1/3: '' -> None
- Wire (HV) / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 21522-1/3: '' -> None; 21522-2/3: '' -> None
- Witness/Other / cleaner: 19515-W4-39: '' -> None; 19515-W4-53: '' -> None; 20164W2-1/1: '' -> None; 20877R1-1/1: '' -> None; 21040W2-1/1: '' -> None

## 3. Date columns hold no text: FAIL

- **WARN** TableArchiveBO: 7 legacy text value(s) kept exactly as in the baseline
  - `21914-1/2 BO1 Date='TBD'`
  - `21407-2/3 BO1 Date='TBD'`
  - `21838-1/5 BO1 Date='TBD'`
  - `21840-1/10 BO1 Date='TBD'`
  - `21385-1/2 BO2 Date='TBD'`
- **FAIL** TableArchiveFRM10_12: 7 text value(s) in date columns
  - `21407-2/3 BO1 Date='TBD'`
  - `21838-1/5 BO1 Date='TBD'`
  - `21840-1/10 BO1 Date='TBD'`
  - `21914-1/2 BO1 Date='TBD'`
  - `21385-1/2 BO2 Date='TBD'`
- **WARN** TableArchiveFRM10_12: 124 legacy text value(s) kept exactly as in the baseline
  - `20481-1/1 Tank Delivery Date='.'`
  - `20930-1/1 Tank Delivery Date='.'`
  - `20932-1/2 Tank Delivery Date='.'`
  - `20932-2/2 Tank Delivery Date='.'`
  - `20933-1/1 Tank Delivery Date='.'`
- **WARN** TableArchiveFRM11: 111 legacy text value(s) kept exactly as in the baseline
  - `20572R1-5 Date encuvage='re'`
  - `21465-3/5 Date encuvage='2024-1125'`
  - `21447-1/4 RAD Shipping Date to Paint='(3/12/2025)'`
  - `21447-2/4 RAD Shipping Date to Paint='(3/12/2025)'`
  - `21447-3/4 RAD Shipping Date to Paint='(3/12/2025)'`
- **WARN** TableArchiveFRM13: 1 legacy text value(s) kept exactly as in the baseline
  - `20990 Order Date='2023-02.09'`
- **PASS** TableArchiveModelRevisions: 1 date columns clean
- **PASS** TableArchiveModels: 1 date columns clean
- **PASS** TableArchiveOrder: 2 date columns clean
- **PASS** TableArchiveOrderItems: 29 date columns clean

## 4. List tables vs mirror: PASS

- **PASS** TableArchiveOrderItems: 1128 Ids match the mirror's 1128
- **PASS** TableArchiveOrderItems: 29 date-only + 5 lookup columns equal the mirror
- **PASS** TableArchiveOrder: 473 Ids match the mirror's 473
- **PASS** TableArchiveOrder: 2 date-only + 3 lookup columns equal the mirror
- **PASS** TableArchiveModels: 396 Ids match the mirror's 396
- **PASS** TableArchiveModels: 1 date-only + 3 lookup columns equal the mirror
- **PASS** TableArchiveModelRevisions: 396 Ids match the mirror's 396
- **PASS** TableArchiveModelRevisions: 1 date-only + 3 lookup columns equal the mirror
- **PASS** TableArchiveClients: 99 Ids match the mirror's 99
- **PASS** TableArchiveClients: 0 date-only + 0 lookup columns equal the mirror

## 5. Additivity: PASS

- **PASS** TableArchiveBO: 1955 -> 1955 rows, every baseline Order kept
- **PASS** TableArchiveFRM10_12: 5322 -> 5322 rows, every baseline Order kept
- **PASS** TableArchiveFRM11: 4250 -> 4253 rows, every baseline NUMÉRO DE CUVE kept
- **PASS** TableArchiveFRM13: 1352 -> 1352 rows, every baseline Order kept

## 6. Readers: PASS

- **PASS** FRM11 Rows to purge: Order, Location, Status present
- **PASS** FRM13: Order, Location present
- **PASS** viewer purge: Order, Location, Delivery Date present
- **PASS** Query2: PO Item #, Order, Client, Order Date present
- **PASS** Power BI PriceReg: Price, Price Value present
- **PASS** Location values are codes (12 from LocationCodes.pq + baseline legacy ['AN', 'GR'])
- **PASS** Status prefixes are step codes

## 7. Nightly Sync replay: WARN

- **PASS** today 2026-09-28, cutoff 2026-09-21: 54 candidates, 21 confirmed on the new copy (baseline replay: 18)
- **WARN** 3 unit(s) confirmed now but not on the baseline replay: review before deletes
  - `21792-3/5`
  - `21792-4/5`
  - `E21011-1/1`

confirmed: 21777-1/1, 21792-3/5, 21792-4/5, 21793-3/5, 21803-6/8, 21803-7/8, 21803-8/8, 21851-1/2, 21851-2/2, 21943-8/8, 21967-1/5, 21969-2/2, 21970-1/2, 21970-2/2, 21971-7/8, 21972-1/1, 21991-1/3, 21991-2/3, 21991-3/3, 22017-1/3, E21011-1/1

## 8. BO merge: WARN

- **WARN** 9 conflict(s): Order Items value wins over TableArchiveBO (list for the user)
  - `P20004-1/2 BO: Order Items 'BO', TableArchiveBO 'OK'`
  - `22105-1/1 BO1 Part Numbre: Order Items 'KDM KIT', TableArchiveBO 'PLAQUE '`
  - `22105-1/1 BO1 Description: Order Items 'KDM KIT', TableArchiveBO 'PLAQUE'`
  - `22105-1/1 BO1 PO Intern: Order Items '141376', TableArchiveBO 141548`
  - `22105-1/1 BO1 Date: Order Items datetime.date(2026, 9, 12), TableArchiveBO 2026-09-30`
- **PASS** 1382 TableArchiveBO values present in TableArchiveFRM10_12 (BO, BO1 Part Numbre, BO1 Description, BO1 PO Intern, BO1 Date, BO1 Fournisseur Interne, BO1 OK, BO2 Part Numbre, BO2 Description, BO2 PO Intern, BO2 Date, BO2 Fournisseur Interne, BO2 OK, BO3 Part Numbre, BO3 Description, BO3 PO Intern, BO3 Date, BO3 Fournisseur Interne, BO3 OK)

- P20004-1/2 BO: Order Items 'BO', TableArchiveBO 'OK'
- 22105-1/1 BO1 Part Numbre: Order Items 'KDM KIT', TableArchiveBO 'PLAQUE '
- 22105-1/1 BO1 Description: Order Items 'KDM KIT', TableArchiveBO 'PLAQUE'
- 22105-1/1 BO1 PO Intern: Order Items '141376', TableArchiveBO 141548
- 22105-1/1 BO1 Date: Order Items datetime.date(2026, 9, 12), TableArchiveBO 2026-09-30
- 22105-1/1 BO1 Fournisseur Interne: Order Items 'JEUX01', TableArchiveBO 'IDEN01'
- 21980-1/1 BO1 Part Numbre: Order Items '35Z9020', TableArchiveBO '35z9283'
- 22069-1/10 BO: Order Items 'OK', TableArchiveBO 'BO'
- 21873-1/8 BO: Order Items 'OK', TableArchiveBO 'BO'
