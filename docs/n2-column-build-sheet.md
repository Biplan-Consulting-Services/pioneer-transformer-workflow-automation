# N2 — the columns to create on `Order Items`

Generated 2026-09-05 from the returned picker (`scripts/gen_build.py`, re-runnable).
Full rows: **`sharepoint-lists/N2 column build list 2026-09-05.csv`**.

The picker came back **55 Yes** (an earlier note in this repo said 57 — that was counted before
`Model - Spec ID` and `Model - Model_Code` were switched to No). Ten of those were then overridden
by decisions taken *after* it
was filled in, so the real build is **48 new columns** — listed here rather than silently
dropped, because a future reader comparing the workbook to the list will otherwise think rows
went missing.

| Action | Count | Meaning |
|---|---|---|
| **CREATE** | 46 | New prefixed column, straight from the picker. |
| **KEEP** | 2 | Create it, with a caveat attached. |
| **RENAME** | 2 | **Not** prefixed — overwrites an existing lookup. |
| **REPLACE** | 1 | Superseded by a different source. |
| **BACKFILL** | 1 | One-time fill of an existing column, not a synced column. |
| **DROP** | 3 | Decided against after the picker was returned. |

## The ten overrides

| Proposed name | Action | Why |
|---|---|---|
| `Order - Model` | **RENAME** | NOT prefixed — overwrites the existing Order Items.Model lookup. SA units RE-RESOLVE, never copy. |
| `Order - Model Revision` | **RENAME** | NOT prefixed — overwrites the existing Order Items.Model Revision lookup. Same SA rule. |
| `Order - Lead Time` | **REPLACE** | Superseded: the client lead time comes from FRM13 via Clients.Lead Time, not Order.Lead Time (306 of 342 disagree). |
| `Client - Client_ID` | **BACKFILL** | One-time backfill into the existing Client_ID_TextField, not a synced column. |
| `Order - Client` | **DROP** | Client stays client — the existing Order Items.Client lookup is the only one. |
| `Model - Client` | **DROP** | Same decision. Reachable through the Client lookup. |
| `Mod. Rev. - Client` | **DROP** | Same decision. |
| `Model - Latest Model Revision` | **KEEP** | Name it so it reads as 'the newest design', NOT 'this unit's revision'. They are different facts. |
| `Mod. Rev. - Duplicate Order` | **KEEP** | Create it, but it stays empty — 0 of 391 populated. Future engineering-completion logic fills it. |

## Creating them

**Create each with a short name, then rename to the display name.** SharePoint derives the
internal name from whatever the column is called at creation and never changes it afterwards, so
creating `Order - Order Number` directly bakes in
`Order_x0020__x002d__x0020_Order_`. Creating `OrderOrderNumber` and renaming gives a clean
internal name and the display name you want.

⚠️ Internal names are escaped **and truncated at 32 characters**. `Protector & Switchgear Item #`
on this same list already became `Protector_x0020__x0026__x0020_Sw` — stopping mid-word. Anything
writing an expression against a new column must read the internal name back from
`_api/…/fields` (or an export's `ListSchema` record) rather than deriving it. See
`a5-d1-d2-paste-sheet.md` for what that mistake costs.

## By source list

| Source | Columns to create |
|---|---|
| `Model Revisions` | 24 |
| `Models` | 5 |
| `Order` | 19 |

## Sequencing

Creating the columns is safe on its own — an empty column changes nothing. **The sync flows
(N3) wait for A3**, stripping 2c stage-stamping out of the trigger flow: before that, every
synced write re-fires a ~100-action flow per row, which is the load shape that hit the capacity
cap. Change-guard every write.
