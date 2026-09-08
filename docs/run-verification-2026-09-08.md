# R3 run verification — 2026-09-08

Measured against the **live tenant** via the SharePoint REST API at ~06:15, after the user ran
`R3`. Nothing here is inferred from run status — a healthy run reports `Failed`, so status was
never consulted. Sources: `_api/web/lists(guid'd6468ec5…')/items` (paged, `odata=nometadata`),
plus `workflow-data/UpdateOrderItemRawInput.json` for one iteration's resolved inputs.

## R4 — the day-early dates: **PASS**

The whole project existed to fix ~4,711 date values rendering a day early. It worked.

| | |
|---|---|
| rows now on the list | **1,117** (was 1,052 → **+65**) |
| rows the run wrote | **1,013**, all stamped `Modified 2026-09-08` |
| rows the run never touched | **104** |

**Stored time-of-day, which is the actual test:**

| column | non-null | `04:00Z` | `05:00Z` | `00:00:00Z` |
|---|---|---|---|---|
| `Planned_x0020_Tanking_x0020_Date` | 1,028 | 552 | 416 | **60** |
| `CoilingDate` | 237 | 143 | 1 | **93** |
| `OrdOrderDate` | 1,011 | 782 | 229 | **0** |

The `04:00`/`05:00` split is the DST offset resolving per date — exactly the predicted signature.

🟢 **The crosstab is what closes it:**

| | rows |
|---|---|
| touched by the run **AND** still `00:00:00Z` | **0** |
| untouched **AND** still `00:00:00Z` | 93 |
| untouched and already clean | 11 |

**Zero.** Every row the run wrote carries a correct site-local instant. There is no mapping
defect. `OrdOrderDate`, written fresh into a new column, is 1,011 for 1,011 correct.

### The 93 that remain are orphans, not failures

They sit entirely inside the 104 rows the run never touched — which is **R15's 104 orphan rows**,
list rows with no workbook counterpart. Split by `Item Status`: **68 Active, 36 Delivered** — the
36 matching R15's "36 correctly Delivered" exactly.

⚠️ **`21408-1/1` is one of them**, which matters because risk card `R6` cites it as *the* proof of
the bug (`2026-04-23T00:00:00Z` showing as 4/22). It was last modified **2026-09-05**, before the
run. Its stale value is not a failure of the run — **the run cannot reach it.** Re-running will not
fix these 93; only the `X2` reconciliation pass can.

## R5 — new columns: **PASS**, with two findings

| column | predicted | measured | |
|---|---|---|---|
| `Info_x002b_` | ≈96 | **96** | exact |
| `Technical_x0020_Notes` | ≈6 | **6** | exact |
| `Section_x0020_Qty` | ≈112 | **112** | exact |
| `Configuration` | ≈491 | **500** | +9 |
| `Protector_x0020__x0026__x0020_Sw` | 0 | **0** | correct — blank at source |
| new rows created | +65 | **+65** | exact |

Three exact hits is strong evidence the `D1` mappings landed on the right internal names.

**Parent columns populated at scale** — `MdlModelID` 1,008 · `RevkVA` 1,006 · `OrdOrderNumber`
1,013. This retires the largest open unknown in v006: the fetch-once restructure changed every
parent read from `Get item` to a cached `Get items` filtered in memory, and the flattened key form
was *statically consistent but empirically unconfirmed*. **Now confirmed** — the raw inputs show
`MdlModelID` `M-MEEN-0002`, `MdlLatestModelRevision` `MR-MEEN-0002-V1`, `RevkVA` 2500,
`RevPhases` 3. Had it been wrong, 29 columns would have landed blank with no error.

### 🔴 Finding 1 — `RevModelDescription` stores a raw odata reference on 979 rows

```
[{"@odata.type":"#Microsoft.Azure.Connectors.SharePoint.SPListExpandedReference","Id":5,"Value":"MALT"}]
```

The intended value is `MALT`. The mapping passes the **whole expanded-lookup array** instead of its
`Value`, so 979 of 1,117 rows now hold ~110 characters of JSON as literal text. Confirmed at scale,
not a one-row fluke — and it is the *write*-side twin of the export-side trap already documented in
`R19` (`SUBWAY` vs `["SUBWAY"]`).

**Fix:** read `…?['ModelDescription']?['Value']` rather than the reference, then re-write that one
column. It is the only one of the 29 parent columns affected — every other sampled `Rev*`/`Mdl*`
value is a clean scalar.

### 🟡 Finding 2 — `BO` reached 84, not the predicted 76

`TableBO` holds 76 roll-up rows and the pre-run list had 73. **Hypothesis, not yet checked:** the
run wrote 76 and a further 8 pre-existing values survived untouched among the 104 orphans
(76 + 8 = 84). Worth one query before `R7` removes the mapping, because the alternative — the join
fanning out to unintended rows — would mean wrong BO data on 8 units.

## Answered along the way: what the `E` prefix means

`R15` flagged three `E`-prefixed orphans (`E21010-1/2`, `E21010-2/2`, `E21014-1/1`) with
"**ask what `E` means before assuming it is junk**".

**It means `Order Type = ETS`.** From the `Order` export: **all 12** orders with `Order Type = ETS`
start with `E`, and 12 of the 13 `E`-prefixed orders are ETS (the 13th is a `Repair`). The raw
input corroborates it — `E21006-2/2` carries `OrdOrderType` `ETS`.

So they are legitimate orders, not junk. `E21006-2/2` is also a **fourth** `E`-prefixed unit beyond
the three `R15` names.

## R6 — the two-directional re-diff: **PASS, with nothing unexpected**

Post-run export `Order Items 2026-09-08 0557.csv` against `TableOrders` read out of
`workbooks/FRM10-12 2026-09-08 0219.xlsx` (`Orders!B5:CE1024`, 82 columns, **1,019 unit keys**).
That workbook copy postdates `R2`'s refresh — verified by the presence of orders `22143`–`22155`
in it — so it is the right side of the comparison.

| direction | predicted | measured |
|---|---|---|
| workbook → list, missing | **exactly the 6 named** | **6, and exactly those 6** |
| unexpected extras | any = a NEW problem | **zero** |
| rows created by the run | 65 | **65**, across exactly the 13 orders `22143`–`22155` |
| rows removed | 0 | **0** |
| list → workbook, missing | ~104 | **104** |

The six are `20877R1-1/1`, `P1_001-1/1`, `P20001-1/1`, `P20002-1/1`, `P20004-1/2`, `P20004-2/2` —
the exact set named in advance. **Nothing else appeared**, which was the whole point of naming them.

🔑 **The 104 is the same 104 twice over.** REST found 104 rows with `Modified` ≠ 2026-09-08; the
workbook diff independently finds 104 list rows with no `TableOrders` counterpart. Two unrelated
routes, same set, `21408-1/1` and `21408-1/1 SA` in both. That is what turns the `R4` residue from
a hypothesis into a fact: those 93 stale dates are unreachable-by-design, not a mapping failure.


## The 4 skipped live units — created and verified 2026-09-08 06:45

`scripts/create_missing_units.js` then `scripts/fix_created_units.js`.

| unit | Id | Order | Location | verified |
|---|---|---|---|---|
| `P1_001-1/1` | 1128 | 562 (new) | Bobinage | ✅ |
| `P20001-1/1` | 1129 | 563 (new) | Tanking | ✅ |
| `P20004-1/2` | 1130 | 487 | — | ✅ |
| `P20004-2/2` | 1131 | 487 | — | ✅ |

Every date landed at `04:00:00Z`, so the bare-date rule holds for hand-written rows too, not only
flow-written ones.

**Two defects in my own create script, both caught by the read-back and both fixed:**

- `Frame` came back `"Plaspak"` on 1128/1130/1131. The payload builder dropped empty values, so it
  **omitted** the key and SharePoint applied the column **default**. *Omitting a field is not the
  same as sending null.* The flow never hits this because it sends every mapped field explicitly.
  Cleared; the create script now carries a `NULLS` list.
- `ClientId` was null on unit 1129 and order 563 — client ids were resolved from *existing Order
  rows* and no existing Order carries CONED. CONED does exist in `Clients` (Id **123**, matched on
  `Title`). Set on both.

🟢 **`null` DOES clear a field over raw REST** — no retry with `""` was needed. That confirms the
distinction rather than leaving it assumed: the "null does not clear" behaviour is the **Power
Automate connector**, which is what kept the 844 stale `Pending` statuses alive. Raw REST is a
different code path.

### The contamination report's two extra fields are calculated columns, not contamination

`Bo_x0020_Sort_x0020_Date` and `test_x0020_calculated_x0020_colu` showed values on the new rows
that no script set. Checked over REST on three rows — an untouched orphan (Id 4), a run-created row
(Id 1090) and a hand-created row (Id 1128):

| Id | Planned Tanking | Bo Sort Date | test calculated column |
|---|---|---|---|
| 4 | `2026-04-23T00:00:00Z` | `2026-04-23T00:00:00Z` | `2026-09-11T04:00:00Z` |
| 1090 | `2027-01-29T05:00:00Z` | `2027-01-29T05:00:00Z` | `2026-09-15T04:00:00Z` |
| 1128 | `2026-08-28T04:00:00Z` | `2026-08-28T04:00:00Z` | `2026-09-15T04:00:00Z` |

`Bo Sort Date` mirrors `Planned Tanking Date` on every row. **Nothing was contaminated** — and the
CSV export is simply blind to calculated columns (now recorded in `CLAUDE.md`).

🔑 **`test calculated column` is live evidence for `R12`.** Id 4 reads **2026-09-11** while Ids 1090
and 1128 read **2026-09-15**. Id 4 was last written 2026-09-05; the other two today. So the value is
**frozen at each row's last write** and is already days stale — exactly the freeze `R12` predicts
and exactly why `N6` cannot rely on `TODAY()` without the `N7` nightly touch. This is no longer a
theoretical concern; it is measurable on the list right now.

⚠️ **Remove or hide `test calculated column` before staff arrive.** It is a probe from `N4`, it is
populated on all 1,117 rows, it carries a stale date, and it is named "test". If it appears on any
staff view it will be asked about on day one.


## R22 FIXED — 2026-09-08 08:35, verified against the source

979 rows now hold the real value instead of the raw expanded-lookup array. **0 failures, and 0
blobs remain on the live list** (re-read after: 1,121 rows, `stillHoldingABlob: 0`, longest value
14 chars vs ~110 before).

| value | rows | | value | rows |
|---|---|---|---|---|
| SUBWAY | 314 | | ANNEX | 35 |
| NETWORK | 243 | | VAULT-1PH | 34 |
| PADMOUNT | 165 | | LTC | 28 |
| MALT + SA | 75 | | MALT | 24 |
| MINPAD-1HP | 40 | | SUBSTATION | 11 |
| | | | SUBSTATION LTC / PARTS / FLAT FRONT | 4 / 4 / 1 |

**No lookup table was needed, and that is the point:** the correct value was already inside the
broken one — the flow wrote the whole reference instead of its `Value`, so `Value` *is* the
parent's value as of the run. Extraction is lossless, not a guess. **Zero rows were multi-valued**,
so the join logic never had to choose between alternatives.

🟢 **Verified against the authoritative source anyway**, not just against that reasoning: joined
each unit to its parent via `Mod. Rev. - Model_Revion_ID` and compared with
`Model Revisions.Model Description`. **979 of 979 match exactly** — 0 differing, 0 case-only
differences, 0 units whose parent revision could not be found.

⚠️ **My first verification pass reported 979 MISMATCHES and was wrong.** `lib.norm` lowercases text
and only unwraps *expanded-reference* arrays, so it left the parent side as the literal string
`["padmount"]`. That is the **`R19` wrapper trap for the second time in one session**, in the
opposite direction — the export wraps multi-choice values as a plain string array, and any
comparison has to unwrap **both** shapes. Recorded here because it will happen again otherwise.

⚠️ Still outstanding: **the v006 mapping is unchanged.** It will re-write the blob on any future
run. It needs `…?['ModelDescription']?['Value']`. Safe for now only because the flow is
manual-trigger and heading to create-only — see the `N3` build rules, which now warn about exactly
this.

## Still open

- **`R6`** — the two-directional re-diff has not been run.
- **`R7`** — 🔴 the `BO` mapping and the 5 `Order` companion writes are **still in the flow**. It is
  re-runnable, so until they come out, any future run overwrites SharePoint-native BO edits with
  stale Excel values.
- **`SkippedUnits`** — v006 records which rows it dropped and why. Not yet read; it would confirm
  the 104 directly rather than by inference.
- The `RevModelDescription` fix above.

## Method notes worth keeping

- `_api/web/lists(guid'…')/items` with `$select` + `$top=500` and `odata.nextLink` paging **works
  fine** from a plain browser tab, contradicting nothing but usefully extending the record: it is
  the `…/fields` endpoint that hangs on this tenant, not `…/items`.
- Ask for `Accept: application/json;odata=nometadata` — the default returns Atom XML.
- A CSV export **cannot** verify `R4`: it carries the rendered date, not the stored instant. This
  check is only possible over REST.
