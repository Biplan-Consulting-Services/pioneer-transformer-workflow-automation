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

---

## ✅ EXECUTED 2026-09-07 23:5x — all 48 created and verified

Run from the browser against the live list. Verified by **reading every field back**, not by
trusting the POST responses.

| check | result |
|---|---|
| columns on `Order Items` | 117 → **165** (+48) |
| stored in group `Parent Sync` | **48** |
| by prefix | `Ord` **19** · `Mdl` **5** · `Rev` **24** |
| internal names honoured exactly | ✅ all 48 — `Options: 8` worked, no truncation, no rename dance |
| any `Choice` or `Lookup` stored | ✅ **none** — the remapping held |
| `DateTime` fields | 3, **all `dateOnly`** |
| `Note` fields | 4, stored as text with `allowMultipleLines: true`, `linesForEditing: 4` |
| `OrdOrderFolder` | `TypeAsString: URL` ✅ |
| **leaked into the default view** | ✅ **0 of 48** — `Options` correctly omitted `16` |

All 48 are **empty**. Creating them changed no data and fired no flow.

### 🔴 Two script defects found before running — both would have mattered

The script's **read-back and its UNDO block** both used
`_api/web/lists/…/fields?$select=…&$filter=…`, which is **unavailable on this tenant**. So
verification would have reported nothing, and — worse — **the UNDO would have enumerated
nothing and deleted nothing while appearing to succeed.** A rollback that silently no-ops is
worse than no rollback at all. Both now use
`_api/v2.0/sites/root/lists/<id>/columns`, filtered on `columnGroup == 'Parent Sync'`, and the
UNDO reports per-field success.

### What actually works on this tenant, for the next person

| endpoint | works? |
|---|---|
| `_api/v2.0/sites/root/lists/<id>/columns` | ✅ the one to use for column metadata |
| `_api/v2.0/lists/<id>/columns` | ❌ `itemNotFound` — the `sites/root` segment is required |
| `_api/web/lists/…/fields/createfieldasxml` (POST) | ✅ |
| `_api/web/lists/…/fields/getbyinternalnameortitle('X')` | ✅ **single-field GET works** |
| `_api/web/lists/…/fields?$select=…&$filter=…` | ❌ hangs / `Failed to fetch` |
| `_api/web/lists/…/defaultview/viewfields` | ✅ |

So it is the **`/fields` collection query with `$select`/`$filter`** that is broken, not the
whole `/fields` family — a sharper statement than "`/fields` is unavailable".

⚠️ **One operational note.** Running this from a heavy SharePoint SPA page (`Home.aspx`) froze
the renderer mid-request — a 45-second CDP timeout with the write outcome unknown. I verified
nothing had been created before retrying; it had not. Running the same code from a lightweight
JSON endpoint page worked first time and every time after. **Do not run batch writes from a
SharePoint application page.**

