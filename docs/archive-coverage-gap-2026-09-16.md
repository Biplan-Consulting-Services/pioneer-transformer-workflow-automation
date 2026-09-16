# What the Excel archive does NOT carry — measured 2026-09-16

**This questions the premise `archiving-plan.md` is built on.** That plan opens with "**No
SharePoint-side archive list at all** — Excel's Archive workbook (`Archive active.xlsx`)
already *is* the permanent historical record", and concludes its only job is deleting rows,
not preserving them a second time.

That was true when `Order Items` was a copy of `TableOrders`. It is no longer true. The
list has grown columns the workbook never had, and lost its claim on others.

Measured against `Order Items` at 151 columns / 1085 rows (the full All-Items export of
2026-09-16 10:37) and `Archive active.xlsx`'s `Archive FRM10-12` at 93 columns.

**92 of the list's 151 columns have no counterpart on `Archive FRM10-12`.** Raw, that
number misleads — most of those columns do not need one. Split by what they are:

| group | columns | carry data | lost on delete? |
|---|---|---|---|
| **Unit data** | 32 | 22 | 🔴 **yes — no other home** |
| **BO1/BO2/BO3** | 18 | 18 | ⚠️ on the `Archive BO` sheet today; see below |
| Parent lookups | 24 | 21 | no — live on `Order`/`Models`/`Model Revisions`/`Clients` |
| Internals & mirrors | 18 | 16 | no — ids, `_TextField` mirrors, `Modified`, stamps |

---

## 🔴 The 22 unit-data columns that vanish

Deleting a row destroys these. Nothing else records them.

**The step grain the migration created.** The workbook kept ONE date per step — `Coiling
Date`, `Stacking Date`, … The list splits each into `Status` + `Start Date` + `End Date`
(the `n8_split_status` work). The End dates correspond to the workbook's single date; the
**`Status` values do not exist in the workbook at all**:

| | rows filled |
|---|---|
| `Testing Status` | 839 |
| `Coiling Status` | 174 |
| `Stacking Status` | 114 |
| `Assembly Status` | 89 |
| `Drying Status` | 83 |
| `Tanking Status` | 30 |
| `Finishing Status` | 27 |
| `Delivery Status` | 11 |

**SharePoint-native workflow state**, with no workbook equivalent:

| | rows filled | |
|---|---|---|
| `Item Status` | 1085 | the Active/Delivered/Cancelled/Regrouped state the whole archiving design keys on |
| `SA Job` | 1085 | |
| `Planned Tanking Date` | 1030 | |
| `Planned Delivery Date` | 304 | maps to the workbook's `Delivery Date`, but only where the workbook still has the unit |
| `Step Status` | 174 | |
| `Status Date` | 174 | **hand-entered by staff** — the column the v006 bug erases |

🔑 `Status Date` is the sharpest case. Staff type it by hand, three days of it were entered
manually during the cutover, and `status-date-null-write-2026-09-14.md` is an entire
document about not losing it. Deleting an archived row deletes it with no trace.

**Empty on every row today** — no data at risk yet, but they are part of the shape:
all eight `* Start Date` columns, `Protector & Switchgear Item #`, `Planned Tanking Sort Date`.

## ⚠️ BO — not lost yet, and the reason matters

The concern raised was that BO columns are no longer maintained in the workbook, so they
are now untracked. **Checked, and today they still agree exactly:** 29 units carry a `BO1
Date` on the list; all 29 exist on `Archive BO`; all 29 hold the *same* date. `Archive
BO`'s own `Last Synchronisation Date` reads 2026-09-14.

That is not evidence the path still works — it is the migration baseline. Both sides were
seeded from the same source, so of course they match. `Archive BO` is fed **from the
workbook**. If BO data is now entered in SharePoint, it has no route into the archive, and
the first divergence will be a *new* BO entry, not a changed one.

**So the loss is pending, not realised, and there is a clean test for it:** enter a BO date
on the list for a unit that has none, and see whether it ever reaches `Archive BO`. Worth
running before deciding how much to build — if the sync is genuinely dead, 18 populated
columns join the 22 above.

## What this does to the plan

The three open questions in `archiving-plan.md` all assumed deletion is safe because Excel
already holds everything. Two are now answered (7-day grace, delivery-date clock) and both
sharpen the exposure rather than reduce it: rows now become deletable **7 days** after
delivery instead of a month after their last touch.

The plan needs a fourth question answered before its delete is ever wired:

> **Where do the 22 unit-data columns go when the row is deleted?**

Three shapes, not yet chosen:

1. **A SharePoint archive list** — what the plan explicitly ruled out. Reconsider: the
   ruling-out was correct when the list was a mirror, and is not obviously correct now.
2. **Widen the Excel archive** — add the missing columns to `Archive FRM10-12` and extend
   whatever feeds it. Keeps one historical record; means writing to Excel, which the plan
   forbids in the flow ("**No flow writes to Excel, at all**").
3. **Accept the loss deliberately**, column by column, and write down which ones. Defensible
   for `Delivery Status`; much harder for `Status Date`.

Same question, separately, for `Order` — which has **no archive at all**, on any sheet, and
now needs both an archive and a cleanup of its own. Order `22021` is the first live case:
every one of its units was deleted from `Order Items` on 2026-09-16, leaving the order row
with nothing under it.

## Reproducing these numbers

```bash
python scripts/verify_archive_done_not_in_list.py --list "sharepoint-lists/Order Items (1).csv"
```

The column comparison itself was ad-hoc, not a script. If it is going to be re-run as the
schema moves — and it should be, before the delete is wired — it belongs in one.
