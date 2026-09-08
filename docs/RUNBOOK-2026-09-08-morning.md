# Runbook — what to do when you wake up

Written 2026-09-08 ~10:00 while you slept. Everything below is ready; nothing here
needs thinking, only running and reading. **Total hands-on time: about 20 minutes**,
plus two decisions only you can make.

## Already done and verified — no action needed

| | |
|---|---|
| **R22** — `RevModelDescription` | ✅ **979 rows fixed, 0 blobs remain.** Verified against the parent `Model Revisions`: **979/979 match exactly**, 0 differing, 0 case-only differences. |
| **4 skipped live units** | ✅ created and verified (Ids 1128–1131), all dates at `04:00:00Z` |
| **`P20004` → ERMCO** | ✅ units 1130/1131 repointed to Order 488, Client ERMCO |
| **N5 — version history** | ✅ already capped: versioning on, `MajorVersionLimit` **50** |

## Run these three, in this order

⚠️ **Order matters for the first two.** X2 corrects the stale `Location` on 104 units;
X1 keys on `Location`. Run X1 first and it clears the delivery of 68 genuinely-shipped
units. X1 has a guard that refuses to run if it detects X2 hasn't — but don't rely on it.

Each one: open
`https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser`,
`F12` → Console, paste, Enter. If Chrome refuses the paste, type `allow pasting` once.
**All three are DRY RUN by default** — read the summary, then set `APPLY = true` and paste again.

### 1 · `scripts/x2_set_delivered.js` — 66 rows

Marks the archived-and-delivered units `Delivered`, per your rule (Location `LI` + a
delivery date). All 104 orphans meet it; 36 already read Delivered.

- **excluded, for you:** `21792-3/5`, `21792-4/5` — archive delivery date **2026-09-24, in the future**
- **flagged, included:** 9 still read archive `Status = EC` — `21803-4/8` plus eight `22021-*`
- 🔑 those eight `22021-*` are **exactly R15's "genuinely unexplained" eight**. Delivered and archived. R15 is closed.

### 2 · `scripts/x1_clear_fabricated_stages.js` — 1,120 stage-clears

Clears the fabricated Tanking/Delivery completions. Keeps 203. **Holds back 52.**

Fabrication is proven three independent ways, so this isn't a judgement call:
- `Tanking End Date` is a **byte-copy of `Planned Tanking Date` on 921 of 975** rows
- **811 of 975** "completed" Tanking dates are **in the future** — a completed stage cannot complete in the future
- `Delivery = Completed` appears with `Location = Bobinage` on 29 rows — delivered while still in the winding shop

Clears to **blank, not `Pending`** — R10 records that `Pending` destroys the very marker the cleanup depends on.

### 3 · `scripts/n8_split_status.js` — creates 2 columns + fills 247 rows

Creates `Step Status` (Text) and `Status Date` (Date Only), then splits the composite
`Status` (`TE-Se-4` → `Terminé` + `2026-09-04`).

- code table read from **FRM10-12's own `List` sheet** (`TableValidationStatusCode`), not inferred
- **all 247 parse; all 19 ambiguous `Jui` rows resolve to *juillet*** from each unit's own real stage dates — most landing on the *exact* same day. **None need a human**, against the roadmap's plan to flag 9

## Two decisions only you can make

**1 · The 52 held-back rows are all one question.** Every single one is `Location = Extérieur`
— the only location outside the production sequence
(`IS→BO→ST→AS→FO→TA→TE→FI→LI`). A unit could be outside waiting for a supplier to
fabricate its tank (**before** tanking, per FRM11) or finished and stored outside (**after**).

> **Is `Extérieur` before or after tanking?** One word settles all 52.

**2 · `P20004` still has two Order rows** — 487 (Pioneer Transformers) and 488 (ERMCO). It's
the only duplicated order number in all 445. Until one goes, the flow will keep skipping
those two units, and **N3 inherits the same problem** since it resolves parents by key.
Id **487** is the candidate: wrong client, and now zero units attached. Say the word and I'll retire it.

## N3 — ready to paste and validate

`workflow-data/n3-flows/` — three definitions plus `MAPPING.md`.

| flow | trigger list | fan-out filter | fields |
|---|---|---|---|
| `Order Items - sync from Order` | `Order` | `OrderNumberId eq <ID>` | 18 |
| `Order Items - sync from Models` | `Models` | `ModelId eq <ID>` | 5 |
| `Order Items - sync from Model Revisions` | `Model Revisions` | `ModelRevisionId eq <ID>` | 24 |

Each has the five blocks from the spec: trigger → fan-out (filtered on the lookup's `Id`,
paginated at 5000) → apply to each → `needsUpdate` change-guard → conditional single
`Update item`. Guard line counts match field counts exactly (18/5/24).

**Source internal names were read from the platform, never guessed** — and several are
actively misleading. These would each have failed silently:

| list | display | **internal** |
|---|---|---|
| Model Revisions | `Pioneer Model Code` | **`Model`** |
| Model Revisions | `Model_Revion_ID` | **`ModelID`** |
| Model Revisions | `Client_Model_Code` | **`ModelName`** |
| Model Revisions | `Model Description` | **`Description`** |
| Model Revisions | `kVA` | `kVA_x0020_and_x0020_kV` |
| Models | `Model_ID` | `ModelID` |
| Order | `Order Number` | `Order_x0020_Number1` |
| Order | `New model to be created` | `New_x0020_model_x0020_to_x0020_b` |

⚠️ **And they collide across lists.** `ModelID` is `Model_ID` on Models but `Model_Revion_ID`
on Model Revisions. `Model` is a lookup on Order but the Pioneer Model Code on Model
Revisions. `ModelName` is `Model_Code` on Models but `Client_Model_Code` on Model Revisions.

**Every Choice and Lookup source is read with `?['Value']`** — that is the R22 lesson encoded.
Without it you store the raw expanded reference, which is exactly what put 110 characters of
JSON into 979 rows. `Model Description` is MultiChoice and is joined, never stored raw.

🔴 **`OrdOrderFolder` is deliberately excluded** — roadmap 38 is still open. A hyperlink is an
object on both read and write, the shape was never sourced, and a wrong one either fails every
row or writes nothing. Confirm from one real trigger payload, then add it.

⚠️ **N3 still needs `X3` first** (strip 2c stage-stamping from the Order Items trigger flow) —
that is a capacity prerequisite from the spec, not optional. And N3 is **not** needed for
cutover: the 48 parent columns are already populated (`MdlModelID` 1,008 · `RevkVA` 1,006 ·
`OrdOrderNumber` 1,013). N3 keeps them fresh; it doesn't fill them.

## Still open for cutover

- 🔴 **No read-only viewer copy of FRM10-12 exists.** The `Index` list has 24 entries and none
  is a viewer. Your cutover email promises one. There *are* `(new)` entries for FRM11 and all
  seven supplier reports — someone is preparing a parallel set. **What is that?**
- 🔴 **FRM11 / FRM13 / FRM09** still read FRM10-12's `TableOrders`. Nobody sends a supplier
  report from FRM11 after cutover until it is repointed via `Index`.
- ⚠️ **`Order Items` has no unique permissions** (`HasUniqueRoleAssignments: false`) — staff edit
  rights must be confirmed at **site** level, not on the list.
- ⚠️ **Remove or hide `test calculated column`** — an N4 probe, populated on all 1,121 rows,
  carrying a stale date, named "test".
- **Make the flow create-only** before cutover (gut the `One_Item_Found` branch).
- **The v006 `RevModelDescription` mapping is still wrong** — it needs `?['Value']`. The data is
  fixed; the mapping will re-break it on any future run.

## Reports to read if you want the evidence

| file | rows |
|---|---|
| `reports/X1 tanking-delivery 2026-09-08.csv` | 1,375 stage-rows, tiered with reasons |
| `reports/X2 reconciliation 2026-09-08.csv` | all 104 orphans, with the archive columns |
| `reports/N8 status split 2026-09-08.csv` | all 247 parses, including the `Jui` resolutions |
| `docs/source-vs-list-comparison-2026-09-08.md` | MISSING = 0 across all 68 mapped fields |
| `docs/run-verification-2026-09-08.md` | R4/R5/R6 verification and R22 |
