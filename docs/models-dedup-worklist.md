# `Models` / `Model Revisions` dedup — the worklists

Generated 2026-09-05 from the exports (`scripts/gen_dedup.py`, re-runnable). Roadmap item 23
says remove the 14 spec columns duplicated on `Models` because the revision is authoritative.
This turns that into finite lists rather than a research task.

Full rows: **`sharepoint-lists/Models dedup worklist 2026-09-05.csv`** — sort by `Action`.

| Action | Rows | Meaning |
|---|---|---|
| **BACKFILL** | **373** | `Models` has a value, the revision is blank. Safe to write. |
| **REVIEW** | **117** | Both populated and genuinely different. Needs a human. |
| **AMBIGUOUS** | **0** | Same digits, `,` vs `.` — cannot tell decimal from thousands. |
| *(formatting)* | *405* | Same value, different serialisation. **Not listed** — nothing to do. |

## Most "disagreements" were formatting, not data

A naive comparison reports **522** conflicts. **405 of those are cosmetic**, from two causes:

- **Multi-choice columns export as a JSON array.** `Models.Description` holds `SUBWAY`;
  `Model Revisions.Model Description` holds `["SUBWAY"]`. Same value.
- **French vs English decimal separators, plus stray spaces.** `Models.Form` holds
  `7,875x13,25` where the revision holds `7.875x13.25`; also `9x12.5` vs `9x 12.5`.

⚠️ **Two corrections to earlier notes in this repo, both from over-reading raw counts:**

- `Description` vs `Model Description` was called *"probably not the same field at all"* on the
  strength of **zero agreements in 295 comparisons**. They *are* the same field — the zero was
  the JSON wrapper. Only **5** genuinely differ.
- `Form` was called the one *"where a wrong call silently attaches the wrong physical spec, so
  it deserves the closest look"* on 102 disagreements. **3** survive normalisation.

## Per column

| Column | Backfill | Review | Ambiguous | Formatting only | Agree |
|---|---|---|---|---|---|
| `Cable` | **6** | — | — | **1** | 61 |
| `Copper (LV)` | **6** | **8** | — | — | 164 |
| `Core Type` | **187** | **19** | — | — | 74 |
| `Form` | **3** | **3** | — | **99** | 75 |
| `JS #` | **12** | **3** | — | **6** | 259 |
| `Model Type` | **55** | **20** | — | **2** | 308 |
| `Oil Amount` | **3** | **11** | — | — | 202 |
| `Oil Type` | **86** | **5** | — | **6** | 232 |
| `Overcoil` | **3** | **9** | — | — | 166 |
| `Phases` | — | **7** | — | — | 230 |
| `Spec_ID` | **2** | — | — | — | 214 |
| `Wire (HV)` | **6** | **8** | — | **1** | 163 |
| `kVA and kV -> kVA` | **3** | **19** | — | — | 362 |
| `Description -> Model Description` | **1** | **5** | — | **290** | 0 |

## What the real conflicts look like

Two distinct shapes, and only one needs judgement:

- **`Models` holding a placeholder where the revision has real data** — `Core Type` `None` vs
  `Amorphe`, `Oil Type` `None` vs `Midel`, `Phases` `0` vs `3`, `Oil Amount` `0` vs a real
  figure. These support "the revision wins" rather than contradicting it, and can be cleared in
  bulk once someone confirms `None`/`0` are placeholders rather than meaningful.
- **Genuine differences** — `Model Type` `ZIG-ZAG` vs `MALT`, `kVA` `1,500` vs `7,500`,
  `Copper (LV)` `114*228` vs `152*430`. These need a person. They are the minority.

## How to run the backfill

**Write only where the revision's value is blank.** `Model Revisions` has been the source of
truth for weeks, so a populated cell is a deliberate edit and must survive — that is why this is
split into lists rather than run as one sync. `Proposed write` carries the value (JSON wrapper
already stripped) and is deliberately empty on REVIEW and AMBIGUOUS rows.

Join is `Model Revisions.Pioneer_Model_Code_TextField` → `Models.Model_ID`, effectively 1:1 —
385 of 391 revisions map cleanly, one model carries 6, and **6 revisions have no model key**
at all. Those 6 are excluded from every list above and deserve their own look.

Nothing gets **deleted** from `Models` until the lists are clear *and* FRM10-12's `.pq` queries
have been grepped for each column name — Power Query binds by name and breaks silently.
