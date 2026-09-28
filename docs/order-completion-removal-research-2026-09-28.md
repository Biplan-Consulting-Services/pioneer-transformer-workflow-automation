# Removing completed Orders from the `Order` list: research

Written 2026-09-28 (afternoon). This is design only. Nothing in the tenant, the lists, the flows or the workbooks was changed.
It answers the user's question: now that `TableArchiveOrder` exists, can COMPLETED orders leave the SharePoint `Order`
list, and how does the system know that all of an order's units are done? The user suggested having the Order Items
trigger flow update the parent Order when its last unit completes.

Sources: the mirror at `sharepoint-lists/mirror/live/` (refresh 2026-09-28 12:50), the go-live copy
`workbooks/upload/Archive active.xlsx` (`TableArchiveOrder`, `TableArchiveOrderItems`, `TableArchiveFRM10_12`, read
with openpyxl, no COM), the flow definitions in `workflow-data/`, and the docs cited inline. The measurement scripts are
in the session scratchpad (`order_completion.py`, `rule_eval.py`). They are throwaway, but everything below can be
re-derived from the mirror plus the archive.

It also answers two questions left open in `archiving-plan.md` (lines 148–155): "`Order` needs an archive before it
can have a cleanup" (done 09-28) and "does the Order row need the same grace + reconfirm rigor?" (yes, §5).

---

## 0. Short answer

- **Yes, it can be done safely.** The deciding rule is **"all of this order's units have already left SharePoint
  through the unit stage, and the archive proves every unit ended terminal."** It is not "the last unit was just
  delivered".
- **Recommended: B + C.** The Nightly Sync computes completion in its batch and writes a completion **date** to a
  **new, unsynced** Order column (`Units Completed`). On a *later* night, a separate, gated delete stage removes the
  order. The completion evidence comes from a small derived table in Archive active, because the archive is the only
  place where departed and pre-cutover units still exist.
- **Design A (the trigger flow marks the parent) is workable, but not as the authority.** With a new unsynced column
  it causes **no N3 loop** (the coordinator's verified finding holds: see §3.A). Its race can be closed too. But it
  sees only SharePoint, so it cannot check Qty coverage for the 6 of 18 done orders whose other units predate the
  cutover. It also does nothing while the trigger flow is OFF (today), and it needs a nightly reconcile anyway. It is
  an optional real-time add-on later, not the mechanism.
- **Design D (views only) gets most of the day-to-day benefit with zero risk**, and it uses the same marker. Order
  growth is about 30 per month, so the list's 5,000-item threshold is about a decade away. Deletion is about tidiness,
  not performance. Suggested order: marker + views first, deletion behind its own switch.

---

## 1. Today's numbers

Mirror 2026-09-28 12:50, archive = go-live copy.

| fact | value |
|---|---|
| Orders | **473** (max Id 590, so ~117 Ids were deleted or never used earlier; `Lists.csv` lastItemDeleted 2026-09-08). **0 units point at a missing order** today. |
| `OrderStatus` | Active 379 · blank 94 (all created 04/05, the backfill) · **Cancelled 0** |
| `TaskStatus` | has a `Completed` choice, but is 0.4% filled. Unused, do not repurpose it. |
| `Order Entry Status` | In Progress / Done, **0% filled** |
| Units (Order Items) | 1,128: **Active 1,074 · Delivered 54** (all 54 at Livraison, and all 54 Livraison units are Delivered). **No `Cancelled`/`Regrouped` on SharePoint**, and `RegroupedInto` is empty on every unit |
| SA twins on SharePoint | 42 units on 33 orders. **No order has its regular units done while an SA twin is still Active** |
| `TableArchiveOrder` | 473 rows. **`Modified` equals the live `Modified` on 473/473** (ISO text, as §3 of the archive design intended) |
| Order `Modified` | 335 on 09-11 and 111 on 09-10 (bulk backfills), the rest scattered. Only 6 edited since 09-21 |
| New orders per month | Jun 29 · Jul 28 · Aug 25 · Sep 33 |

### Orders classified by the rule in §2

| class | orders | examples |
|---|---:|---|
| **OPEN**: at least one Active unit on SharePoint | **332** | 21900, 21999, E21016 |
| **COMPLETE, all units already off SharePoint** | **123** | 112 all delivered (`LI`), e.g. **21865 (Id 4, Qty 5: 21865-1/5…5/5 all `LI`, left the viewer 2026-05-04)**, 21589, WRG3025. 11 include cancelled/regrouped units (`AN`/`GR`): 21728, 21729, 22065, 20853R1, 21884 (all `AN` = annulé); **21820** (Qty 40 → 10: x/40 rows `GR`, x/10 rows `LI`); E21010, E21004, 21819, 21882, 21881 |
| **COMPLETE, units still on SharePoint (all Delivered)** | **18** | 12 have every unit on SharePoint (21991, 21967, 21795, 22017…). **6 have only some units on SharePoint, and the rest were delivered before the cutover** so they never existed on Order Items: **21971** (1 of 8 on SP, 7 `LI` in the archive), 21943 (1 of 8), 21803 (4 of 8), 21793 (3 of 5), 21792 (2 of 5), 21969 (1 of 2) |
| **HOLD** (evidence incomplete or contradictory) | **0 today** | see the edge cases below; they will show up |

**The 123 unit-less orders are verified against the archive, not assumed.** Every one of them has its units in
`TableArchiveFRM10_12` at a terminal code (`LI`, `AN` or `GR`) covering 1..Qty. The brief's "likely completed before
the migration" is right for 117. The other **6 were cancelled, not delivered** (`AN`), so "completed" has to mean
"closed", not "delivered".

### Edge cases found in the data (all OPEN today, all HOLD when they finish)

| order | what is wrong | why a naive rule gets it wrong |
|---|---|---|
| **21387** | `Qty` = 4, but the live units are `4/6`, `5/6`, `6/6`. The archive has old x/4 rows at `GR` plus x/6 at `LI` | Qty and the titles disagree. A "1..Qty covered" check against Qty = 4 would pass on the old regrouped rows |
| **21522** | `Qty` = 1, three live units `1/3…3/3`. The archive has `21522-1/1` at `GR` | same: stale Qty |
| **19515** | units titled `19515-W4-39`, `19515-W4-53` (no n/m), Qty 1 | titles cannot be parsed into an index |
| **21840** | Qty 10: 9 units `LI` in the archive (pre-cutover), 1 Active on SP | a SharePoint-only count sees "1 unit" |

### Unit stage (v007 gate) today

54 Delivered units. **34 of them already have their exact `Modified` in `TableArchiveOrderItems`, and 0 have been
untouched for 7 days** (Modified 09-25 ×31, 09-28 ×22, 09-23 ×1). So no unit can be deleted before about **10-02**, and
no order that still has units can be deleted before about **10-09**. The 123 unit-less orders are the only immediate
candidates.

---

## 2. What "order completed" means

Call it **closed**: every unit the order ever had has ended in a terminal state, and there is evidence for each one.
Evidence comes from three places, and a rule that uses only one of them is wrong on today's data:

| evidence | holds | key |
|---|---|---|
| units on SharePoint now | post-cutover units not yet deleted | `Order Items.OrderNumberId` = `Order.Id` |
| `TableArchiveOrderItems` | every post-cutover unit, **including those the unit stage deletes**, kept forever | `Id`, with `OrderNumberId` |
| `TableArchiveFRM10_12` | pre-cutover history (units never created on Order Items) | `Order` = unit title `21865-1/5`, joined by order number text |

Terminal states: SharePoint `ItemStatus` ∈ {Delivered, Cancelled, Regrouped}. Legacy `Location` code ∈ {`LI`, `AN`, `GR`}.

**The rule.** An order is **COMPLETE** when all of these hold. Otherwise it is **OPEN**, or **HOLD** with a reason:

1. **No open unit on SharePoint.** No unit with this `OrderNumberId` has `ItemStatus = Active`. SA twins count like
   any other unit. *(fails → OPEN)*
2. **At least one unit is known** (on SP or in either archive table), **unless `OrderStatus = Cancelled`**. A
   cancelled order with no units at all is closed. *(fails → HOLD "no unit anywhere")*. This is what stops a brand-new
   order from being completed during the Power App's fan-out window (Qty × ~4.5 s, `n3-fanout-race-2026-09-21.md`),
   and an order whose unit creation failed partway (the save has no error handling).
3. **No archived unit left SharePoint in a non-terminal state.** Any archived unit of this order that is no longer on
   SP must be terminal. *(fails → HOLD "unit vanished while open")*. Catches a unit someone deleted by hand.
4. **Qty is covered.** For the regular (non-SA) units whose title denominator equals the current `Order.Qty`, the
   indexes 1..Qty each have a terminal record (SP or archive). *(fails → HOLD "Qty not covered")*. This catches 21387,
   21522 and a partial save. Titles that don't parse (19515-W4-39) also HOLD. **A HOLD is a data-quality report for
   a person, never a delete.**

The completion date is the latest terminal date of its units: the delivery date, or the date the unit left the
viewer/SharePoint (`Last Synchronisation Date`). It goes onto the order.

How the candidate rules score on today's data:

| rule | says complete | verdict |
|---|---:|---|
| "has units on SP and none Active" | 18 | misses the 123 already-empty orders |
| "no Active unit on SP" (vacuous when empty) | 141 | right today **by luck**. It would complete a new order before its units exist, or one whose units were never created |
| "SP count of Delivered = Qty" | 12 | misses 21971 & co. (pre-cutover units), and breaks on Qty drift |
| **§2 rule (1–4)** | **141, 0 HOLD** | right today, and fails safe on every edge case above |

---

## 3. Designs compared

| | A. Trigger flow marks the parent | B. Nightly Sync computes and acts | C. Status marker + separate delete stage | D. Never delete, hide with views |
|---|---|---|---|---|
| **when** | within ~5 min of the last unit's edit | nightly, 01:30 | mark night N, delete night ≥ N+7 | as soon as there is a marker |
| **sees** | SharePoint only | SharePoint + archive (via the derived table, §6) | as B | the marker |
| **Qty coverage / pre-cutover units** | ❌ cannot see them (6 of 18 done orders) | ✅ | ✅ | n/a |
| **race** | concurrent runs; closable (below) | none (one batch) | none | none |
| **N3 loop** | none if a new unsynced column; ❌ if `OrderStatus` | same | same | none |
| **works while the trigger flow is OFF** | ❌ (OFF today) | ✅ | ✅ | ✅ |
| **silent failure** | a failed run (Save Conflict 400, never retried) leaves the order unmarked forever | a failed night retries the next night | same as B | none |
| **reversal** (unit reopened) | must also clear, on every run | recomputed nightly | recomputed; delete only after grace | recomputed |
| **risk** | low (writes one column) | low | low with the §5 gates | none |

### A, evaluated fairly

**Loops: none, provided the marker is a new column.** Verified against the live `Order - Create or Update Trigger` v005
(coordinator; `workflow-data/n3-flows/Order_Items__sync_from_Order.definition.json` is the same). The Order sync has
**no trigger condition**, so every Order write costs one run. That run reads the order's units and compares 17 synced
fields in `needsUpdate`, then writes a unit only if one differs. A new unsynced `Units Completed` column costs **one
cheap run and zero unit writes**, so the Order Items trigger flow never fires and there is no loop.

- ❌ **Never use a `Completed` value in `OrderStatus`.** `OrderStatus` → `OrdOrderStatus` is synced, so marking one
  order would rewrite every unit, and each rewrite fires the trigger flow. It is also a human (sales) column, and a
  flow should not share a column with people.
- ⚠️ This stays true only while nobody adds the marker to the N3 mapping. If someone ever does, give A an "only
  write when the value differs" guard so the echo stops after one round.

**The race, and how to close it.** The trigger flow polls every **5 min** with `splitOn`, so each changed unit is its
own run. No concurrency limit is set, so the runs start together. If units X and Y of one order are both set to
Livraison in the same poll window and each run checks "are my siblings Delivered?", each can read the other before
the other's `Update_item` lands. Then neither marks the order. Two things fix this:

1. **Check the user-written state, not the flow-written one.** Count a sibling as open when
   `ItemStatus = Active AND Location ≠ Livraison`. People set `Location`, and it is on the row before the poll that
   starts either run. So the last edit's run always sees every earlier edit, and the race is gone.
2. **Echo runs heal whatever remains.** Each `Update_item` modifies the unit, so the next poll starts an echo run
   (stamps equal, `CompletOrder` false). If the sibling check runs on every run of a terminal unit, and not only
   inside the `CompletOrder` branch, the echo runs 5 min later see the final state.

**Why A still is not the authority:**

- It cannot tell "the rest of the units were delivered in May" (21971) from "the rest were never created"
  (a failed partial save). Both look like "no open sibling on SharePoint". Only the archive can tell them apart, and
  a per-unit flow reading a 5,322-row Excel table is the v001 mistake (`nightly-sync-review-2026-09-25.md` §2).
- The trigger flow is **OFF** pending tests. Every order completed while it is off would need B anyway.
- Failed runs are silent and unretried (`n3-fanout-race` §Save Conflict). Again, B has to reconcile.
- Unmarking needs a Get on the Order in every run of the flow. That is extra load on the flow closest to the
  request allowance.

So A only adds same-day marking on top of B. Since deletion waits ≥ 7 days anyway, that is worth little. **If the
user still wants it, it is safe as designed above**: new column, Location-based predicate, differs-guard, and B
reconciling nightly.

### D, honestly

At ~30 orders/month the Order list is not a performance problem, and `archiving-architecture-2026-09-16.md` §3/§5
already argued "G1 is not urgent, and deletion is not the only lever". Once the marker exists, a default view
`Units Completed is empty` (plus the same filter in the Power App's order pickers, if it has any) gives staff a clean
list today. Deletion then becomes the user's choice, not a prerequisite.

---

## 4. Recommendation

1. **Add one column to `Order`:** `Units Completed` (Date only, internal `UnitsCompleted`). Do not add it to the N3
   mapping, and do not reuse `OrderStatus`, `TaskStatus` or `Order Entry Status`. It is date-only, so write a **bare
   `yyyy-mm-dd`** (E7 rule). Optionally add a `Completion Hold` text column holding the HOLD reason, so a person sees
   it in a view.
2. **Compute completion in Archive active**: a derived table `TableOrderCompletion`, rebuilt each refresh (not
   accumulated), one row per `TableArchiveOrder` Id: `Id`, order number, Qty, `Class` (OPEN/COMPLETE/HOLD), `Reason`,
   `UnitsKnown`, `UnitsOnSharePoint`, `CompletedOn`, `LastUnitLeftOn`, `OrderModified`. It uses §2's rule over the three
   evidence sources. Keep a Python replica of the rule in the repo (the `check_archive_rebuild.py` pattern) and check
   one against the other on every refresh.
3. **Nightly Sync stage E (v008):** E1 marks/unmarks (write the date, report HOLDs), E2 deletes with §5's gates behind
   its own `DeleteOrdersEnabled` switch.
4. **Views** filter on `Units Completed` as soon as E1 runs (design D). Deletion is enabled later, separately.
5. A is not built. Revisit only if same-day marking is ever asked for.

---

## 5. Safety gates for deleting an Order

These mirror the unit gate (`archive-all-lists-design-2026-09-27.md` §5, v007). **All must hold**, checked in the
flow against live SharePoint, not only against the archive:

| # | gate | why |
|---|---|---|
| G1 | `TableOrderCompletion.Class = COMPLETE` | the §2 rule, with archive evidence |
| G2 | **0 units on SharePoint** with this `OrderNumberId` (live `Get items` in the flow, `$top 1`) | units leave first, through their own gate. With no relationship enforcement (§7), deleting an order that still has units orphans them |
| G3 | `TableArchiveOrder` has this `Id` with **the same `Modified` text** as the live order | the archive holds the order's final state, including the `Units Completed` date written by E1 |
| G4 | the order is untouched for 7 days (`Modified` ≤ now − 7 d, as ticks) | grace for corrections. E1's own write starts this clock, so marking and deleting can never happen on the same night |
| G5 | its **last unit left SharePoint ≥ 7 days ago** (`LastUnitLeftOn` from the archive's `Last Synchronisation Date`) | lets a wrongly deleted unit be restored while its order still exists |
| G6 | `Units Completed` is set, and no HOLD | a person has been able to see the marker in a view for a week |
| G7 | cap **20 orders/night**; over the cap, delete nothing and report | same pattern as C5. The 123-order backlog clears in ~7 nights |
| G8 | `DeleteOrdersEnabled = false` to start (dry run: "would delete order 21865 (Id 4)") | compare one or more nights' list with the mirror and `TableOrderCompletion` before enabling |
| G9 | recycle bin only (the connector's Delete item). No purge step anywhere | 93-day undo |
| G10 | a delete that **fails** (e.g. a Restrict-delete refusal) is reported as held back, and never retried in a loop | fails safe |

**Order of operations.** Units first, then orders, on different nights:

```
night N    C: unit deleted (its own v007 gate)
N+1        archive refresh: unit row kept, Last Synchronisation Date = N; TableOrderCompletion recomputed
N+1..      E1: order COMPLETE → Units Completed = date   (Order.Modified changes)
next       archive refresh captures the new Modified (G3)
≥ +7 d     E2: G1–G10 → recycle the Order
```

**Rollback runbook: restore the Order before its units.** A unit restored while its Order is in the recycle bin comes
back with a dangling `OrderNumber` lookup. Restoring keeps the item `Id`, so the lookups resolve again.

---

## 6. Proposed build steps (a Nightly Sync stage, v008)

1. **Check relationship behaviour (§7).** It takes 30 s and decides whether G2 is the only line of defence.
2. **User decisions (§10)**, then create `Units Completed` (and optionally `Completion Hold`) on `Order`. That is a
   SharePoint change: mirror refresh right before it.
3. **Archive active: `TableOrderCompletion`**, authored in the repo (`power-query/Archive-active/`), applied with
   `Apply-ArchivePowerQuery.ps1` to a copy first. Its inputs are `TableArchiveOrder`, `TableArchiveOrderItems` and
   `TableArchiveFRM10_12`, all local, with no extra SharePoint read.
4. **Python replica + checker**: add the rule to `check_archive_rebuild.py`. It must reproduce today's **332 / 141 /
   0**, and mutation tests (a Qty change, a hand-deleted Active unit, a new order with 0 units, a cancelled order with
   0 units, an SA twin left Active) must each move an order to the right class. At the same time change check 4 so the
   archive is a **superset** of the mirror for Order (and Order Items). Today it tests equality, and it would FAIL the
   morning after the first delete.
5. **`gen_nightly_sync.py` → v008**, parent = v007 once v007 is pulled:
   - `E0` List rows `TableOrderCompletion` (by name, ≤ 473 rows, filter `Class ne 'OPEN'`) + `TableArchiveOrder`
     (`Id`, `Modified`)
   - `E1` mark: COMPLETE and marker blank → `Update item` `UnitsCompleted = CompletedOn`. OPEN and marker set →
     clear it (report as "reopened"). Cap 50, same `DeleteEnabled`-style switch `MarkEnabled`
   - `E2` delete: G1–G10. `Get items` Order Items `OrderNumberId eq <Id>` `$top 1` per candidate (≤ 20 calls), Delete
     item at concurrency 1–5, no variables
   - summary fields `E_marked`, `E_unmarked`, `E_holds[{Id, number, reason}]`, `E_deleteCandidates`,
     `E_deletedOrWouldDelete`, `E_heldBack[{Id, reason}]`, `E_capExceeded`
   - mutation tests in `test_gen_nightly_sync.py`, like C/D: delete outside the switch, cap removed, G2 or G3
     dropped, grace via date truncation instead of ticks
6. **Mirror health:** a `deleted` event is red today (`mirror_health.py` line 16). Downgrade a deletion to "expected"
   when the id is in the archive with the same `Modified` and the night's summary lists it. Keep everything else red.
   Unit deletions need the same change.
7. **Dry run ≥ 1 week**, then views (D), then `MarkEnabled`, then, on the user's word, `DeleteOrdersEnabled`.

Effort: about one build session (the PQ table, checker and generator are the pattern already used for v005–v007),
plus the usual paste loop.

---

## 7. 🔴 Relationship behaviour of `Order Items.Order Number` → `Order`

**The repo cannot prove it, but it points strongly to "not enforced".** The mirror catalog (`Columns.csv`, read from
`_api/v2.0` columns) reports the `OrderNumber` lookup as **`indexed = False`**. SharePoint only enforces relationship
behaviour on an **indexed** lookup: ticking "Enforce relationship behavior" creates the index, and the index cannot be
removed while enforcement is on. (The catalog does report `indexed = True` where it should, e.g. `Models.ModelID`, so
the flag is populated.) None of the exports or docs mention `RelationshipDeleteBehavior`, and the catalog query does
not read it.

**How the user confirms it (30 s):** Order Items → ⚙ → List settings → Columns → **Order Number** → the **Relationship**
section at the bottom: *Enforce relationship behavior* ☐/☑, then *Restrict delete* / *Cascade delete*. Also look at
**Model Revisions → Duplicate Order**, the only other lookup to `Order` among the mirrored lists (0% filled). Lists
outside the mirror (`ModelChanges`, `EngineeringChangeOrders`) are not in the catalog. Check them for lookups to
`Order` too.

**Why it matters:**

| setting | deleting an Order that still has units |
|---|---|
| **none** (likely) | succeeds. The units keep a dangling lookup and show a blank Order Number. N3 can never reach them. The **trigger flow's next run** sees `OrderNumber/Value ≠ Order_Number_TextField` and **writes the blank into `Order_Number_TextField`**, erasing the unit's order number. The archive adapter joins by lookup id, so it would overwrite the unit's archived FRM10-12 row with null order fields. **G2 is the only guard.** |
| **Cascade delete** | succeeds and **recycles every unit with it**, bypassing the unit gate. Dangerous. Turn it off before any order stage runs. |
| **Restrict delete** | fails with an error while any unit references the order. This is the ideal backstop: a gate bug or a person deleting in the UI cannot orphan units. |

**Suggestion:** turn on **Restrict delete** (a SharePoint column setting, 1,128 items is well under the threshold). It
costs nothing and turns G2 into a database rule. G10 handles the refusal. It is the user's call, since it also stops a
person deleting an order that still has units (which is the point).

---

## 8. What else is affected when an Order row disappears

With G2 holding (no units left):

| consumer | effect |
|---|---|
| **N3 `Order` sync** | none. A delete does not fire "created or modified", and there are no units to sync |
| **Order Items trigger flow** | none. It reads Clients/Models, not Order. Only a unit with a dangling lookup would be harmed (§7) |
| **Viewer `TableOrders`** | none. It starts from Order Items and left-joins Orders by `Order Number Id`, so an order with no units is never read |
| **Archive `TableArchiveOrder`** | the row stays forever (`AccumulateIntoLocal`). `Last Synchronisation Date` becomes the day it left |
| **Archive FRM10-12 adapter** (`ArchiveFrm1012Joined`) | none. It starts from live units, and the departed units' rows are kept by accumulate. ⚠️ If an order were deleted while units remain, it would overwrite their archived rows with null order fields (another reason for G2) |
| **`check_archive_rebuild.py`** | check 4 ("TableArchiveOrder: 473 Ids match the mirror") **fails** the first morning. Change it to a superset (§6.4) |
| **Mirror health** | every deletion is red. Needs the expected-deletion rule (§6.6) |
| **Power BI** (`PriceReg.pq`) | none. It reads the archive's FRM10-12 table, not the Order list (`archiving-architecture` §2). The order's price is frozen in the archive once its units left the viewer |
| **FRM09 / FRM11 / FRM13 / BO Manager** | none. They read the viewer and archive tables through `Index`, not the Order list (FRM13 reads only Models) |
| **Power App** | ❓ it **creates** orders (`Patch(Order, Defaults(Order))`, no edit form: `fanout-powerfx-c2.md`). Unknown whether any screen lists or reopens old orders, or checks order-number uniqueness against `Order`. If it does, a deleted order's number could be reused. Question 3 |
| **`TableNextOrder`** (Archive active) | ❓ the formula was not found in the go-live copy's XML. Confirm it does not derive from the Order list |
| **Order Folder links** | 130 orders have one. The URL survives in `TableArchiveOrder`, and the folder itself is untouched |
| **Attachments** | none on any Order (473/473 `Attachments = False`) |

**N3 loop risk if design A writes the Order:** covered in §3.A. None with a new unsynced column. With `OrderStatus`
it would be a fan-out to every unit plus one trigger run per unit.

---

## 9. How this fits the long-term KPI archive

(The punch-list item `ar-long-term-archive` is not in the repo. It presumably lives on the state board or artifact
DB, so this goes by `archiving-architecture-2026-09-16.md` §5 and `analytics-history-options.md`.)

- `TableArchiveOrder` is already the **order-level completion record**: latest state, kept forever, keyed on `Id`.
  With `Units Completed` stamped before deletion, it carries the KPI fields the model lacks today: **order cycle time**
  (`Order Date` → `Units Completed`) and on-time vs `Initial Promised Date`, per order rather than per unit.
- The long-term design's "Layer 2 — completion records, append-only" is the natural home for a **frozen copy at
  deletion time**. When that layer exists, add a gate G11: *the order's final row is in the long-term store*. Then an
  editable workbook is never the only copy of a deleted order.
- Completed-order removal does **not** reduce what KPIs can see, because the order is already out of the viewer once
  its units are. It only removes the live row. The one thing lost is the live list's version history (50 versions),
  which goes to the recycle bin with the item. The mirror's monthly snapshots and journal keep the rest.

---

## 10. Questions for the user

1. **Decision N4 changes.** On 09-27 you chose "keep the Order row" for orders whose units are gone
   (`nightly-sync-review` §6d). Is removal now wanted, or would **marker + views (D)** be enough for now, with deletion
   left for later?
2. **Relationship behaviour (§7):** what does Order Items → Order Number → *Enforce relationship behavior* show? And
   may Restrict delete be turned on?
3. **Power App:** does any screen list, search or reopen existing orders, or check that an order number is unique
   against `Order`? Can a completed order ever get new units (add-on, rework, Qty increase)? If yes, does it reuse the
   same order row?
4. **Cancelled orders:** "closed" includes all-cancelled orders (6 today, `AN`). Should those be deleted like
   delivered ones, or kept longer?
5. **Grace and cap:** 7 days after the last unit left, 7 days after marking, 20 orders/night. OK?
6. **HOLDs** (Qty drift like 21387/21522, unparseable titles like 19515): who fixes the Order's Qty when the report
   flags one?
7. **Design A:** now that the loop concern is resolved, do you still want same-day marking from the trigger flow? The
   recommendation is no (§3.A), since the nightly marker is enough for views and deletion waits a week anyway.
