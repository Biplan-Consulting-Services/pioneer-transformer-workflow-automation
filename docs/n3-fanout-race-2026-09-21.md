# The N3 fan-out race — order 22169, found 2026-09-21

Four of the ten units on order `22169` have no Order or Model parent data. They were not
erased and nothing is corrupt. **The sync flow's fan-out set is frozen at read time, and
those four units did not exist yet when it read.**

Measured with `scripts/x19_parent_history_probe.js` (every stored version over REST) and
`scripts/x20_resolve_identities.js` (who the stamped ids actually are). Both read-only.

## The evidence

Patrick Vaillancourt created the ten units one at a time through Power Apps
(`AppAuthor = Microsoft Power Platform`) over 41 seconds on 2026-09-17, 17:39:44–17:40:25 UTC
(13:39 local). All ten got all four lookups. Times below are each unit's version stamps.

| unit | Id | created | `Ord*` written | `Mdl*` written | `Rev*` written |
|---|---|---|---|---|---|
| 1/10 | 1217 | 17:39:44 | v2.0 17:40:13 | v3.0 17:40:18 | v4.0 17:40:38 |
| 2/10 | 1218 | 17:39:48 | v2.0 17:40:13 | v3.0 17:40:18 | v5.0 17:40:40 |
| 3/10 | 1219 | 17:39:52 | v2.0 17:40:13 | v3.0 17:40:19 | v5.0 17:40:40 |
| 4/10 | 1220 | 17:39:57 | v2.0 17:40:14 | v3.0 17:40:21 | v5.0 17:40:45 |
| 5/10 | 1221 | 17:40:03 | v2.0 17:40:16 | v3.0 17:40:22 | v5.0 17:40:46 |
| 6/10 | 1222 | 17:40:07 | v2.0 17:40:16 | v3.0 17:40:22 | v5.0 17:40:46 |
| 7/10 | 1223 | 17:40:12 | 🔴 **never** | 🔴 **never** | v6.0 **09-18** 17:04:30 |
| 8/10 | 1224 | 17:40:16 | 🔴 **never** | 🔴 **never** | v6.0 **09-18** 17:04:31 |
| 9/10 | 1225 | 17:40:20 | 🔴 **never** | 🔴 **never** | v6.0 **09-18** 17:04:32 |
| 10/10 | 1226 | 17:40:25 | 🔴 **never** | 🔴 **never** | v6.0 **09-18** 17:04:32 |

The cut falls between the unit created at **17:40:07** and the one created at **17:40:12**.

🔑 **The write times are not the cut — the read time is.** Unit 1223 already existed at
17:40:13 when the Order flow wrote to 1217, and it was still skipped. So the flow's
`Get items` ran somewhere in 17:40:07–17:40:12, returned six rows, and the `Apply to each`
then spent the next nine seconds writing to exactly those six. Everything created after that
read was outside the loop and was never revisited.

`Rev*` landing a day later on the four stragglers is the same mechanism seen from the other
side: the `Model Revisions` parent was edited on 09-18 at 17:04, the flow re-triggered,
re-read the children, and found all ten. **A later parent edit heals it.** `Order` and
`Models` have not been touched since, so those fields are still blank four days on.

## Why nothing ever fixes it

The four N3 flows trigger on the **parent** list. Nothing fills a child's parent columns when
the **child** is created — the create-or-update trigger flow does not do parent sync, and it
is off anyway. So the fan-out race is not a transient: a missed unit stays missed until
somebody happens to edit its Order or its Model.

This is the same structural gap that leaves any unit created after the 2026-09-08 R3 backfill
blank. The race just makes it reachable in under a minute instead of requiring a new order.

## The fix, in order of value

1. **Fill parent columns on child create.** The durable fix. A unit that resolves its own
   parents at creation cannot be raced, and it retires the backfill-gap class entirely.
   Belongs in the trigger flow, which already reads the lookups — but note it currently
   fails on model-less units (`HANDOVER-2026-09-11.md`), so the guards land first.
2. **Re-read inside the loop, or re-run the fan-out on a delay.** Cheaper, and still a race —
   only a narrower one. Treat as mitigation, not a fix.
3. **A detector.** `x19` already answers "which units have lookups set but synced columns
   blank" across the whole list. Run it as a periodic check until (1) ships; the nightly
   cleanup flow is the natural home.

⚠️ Per the N3 spec's finding 2, a re-run of a corrected flow will **not** repair the existing
four — writing `null` through the connector leaves the old value, and these are blank rather
than wrong. They need an explicit write.

## 🔴 The second cause, same symptom: Save Conflict

Found the same day, from a failed `Order Items - sync from Order` run writing unit **1245**
(order 22175). The payload was well-formed — choices as `/Value`, `OrdInitialPromisedDate` as
a bare `2027-03-25`, so the `N4` conversion and the date rule are both holding:

```
{"status":400,"message":"Save Conflict\n\nYour changes conflict with those made
 concurrently by another user. ..."}
```

**All four N3 flows write to the same `Order Items` row.** One new order can change `Order`,
`Models`, `Model Revisions` and `Clients` at once; four flows then fan out onto the same
children and collide on `Update item`.

🔑 **The write is lost permanently, and this is a configuration gap, not bad luck.** Checked
across all four definitions in `workflow-data/n3-flows/`:

| | |
|---|---|
| `retryPolicy` on `Update_unit` | **absent in all four** |
| `concurrency` on `Apply_to_each_unit` | **absent in all four** |

With no explicit policy, Logic Apps applies its default — which retries **408, 429 and 5xx
only**. A Save Conflict arrives as **400**, a client error, so it is never retried. The run is
marked `Failed`, the row keeps its blank parent columns, and the flow does not fire again
because the parent is not edited again.

⚠️ And run status is not a usable alarm here: the handover already records *"a healthy
transfer-flow run reported `Failed`"*, so Failed runs are not being treated as real. This is
the inverse case — a `Failed` that genuinely is data loss. Nobody is watching either way.

### Fixing this one

1. **Add an explicit `retryPolicy` that covers 400 Save Conflict.** Logic Apps' policy cannot
   select status codes, so this needs a `Scope` around `Update_unit` plus a second attempt
   with `runAfter: ["Failed"]`, or a bounded `Do until` on the status code. Two attempts
   clears almost all conflicts.
2. **Serialise the writers.** Setting `Apply_to_each_unit` concurrency to 1 does *not* fix
   this — each iteration touches a different unit, so the collision is across flows, not
   within one. Trigger concurrency 1 per flow narrows the window without closing it.
3. **The structural fix is the same one the race calls for**: one writer per child. If the
   child resolves all its parents in a single `Update item` at create/update time, there is no
   second writer to conflict with, and no read to race.

## The measured damage — and a third cause that is not a bug

`x21_parent_sync_gaps.js` over all 1,102 units. **The blast radius is small**, and the gaps
are not all the same thing:

| group | units with no synced data | orders |
|---|---|---|
| `Mdl*` | 11 | 21792, 22098, 22107, 22108, 22110, 22169, 22175 |
| `Rev*` | 4 | 22098, 22107, 22108, 22175 |
| `Cli*` | 1 | 22167 |
| `Ord*` | **not yet known** — see the correction below |

Sorted by actual cause:

- 🟢 **4 units are the documented SA zero-match branch, not a defect.** `22098-1/1 SA`,
  `22107-1/1 SA`, `22108-1/1 SA`, `22110-1/1 SA`, all created 2026-08-21. The N3 spec named
  these in August: *"Five SA units already sit on plain `M-` models … Resolve those by hand
  before the flow runs, or they take the zero-match branch on the first edit."* They did. The
  guard worked as designed — writing nothing was the correct behaviour. `22099-1/1 SA`, the
  fifth, is **not** in the gap list, so it was resolved at some point; worth confirming how,
  because that is the repair recipe for the other four.
- 🔴 **7 units are the race / Save Conflict**: `22169` (1223–1226, 09-17), `22175` (1245 lost
  `Mdl*`, 1246 lost `Rev*`, 09-17), `22167` (1204 lost `Cli*`, 09-11). Note 22175's two units
  lost *different* groups — two flows colliding on two rows at two moments, which is the
  Save Conflict signature rather than the race's clean cut line.
- ⚠️ **`21792` is neither.** 2 of 2 units, created 2026-08-17, a **whole** order. Nothing
  partial about it, and it predates the N3 flows being enabled at the 09-11 cutover — so this
  one should have been covered by the R3 backfill of 09-08 and was not. Separate question.

### 🔴 Correction: the first `Ord*` and `Cli*` numbers were wrong

The first run reported `Ord* 0` and `Cli* 1`. Both were artefacts of this script, not facts
about the list, and the script's own column listing showed why:

> `Ord* (Order): 19   OrderNumber, Order_Number_TextField, OrdOrderType, …`
> `Cli* (Clients): 3   Client_ID_TextField, Client, CliLeadTimeWeeks`

`OrderNumber` and `Order_Number_TextField` begin with `Ord`; `Client` and
`Client_ID_TextField` begin with `Cli`. They are the **lookup and its mirror**, not N3 synced
columns, and they are populated on essentially every row — so "every column in this group is
blank" could never be true and the test could never fire. Units 1223–1226 are known from
`x19` to be missing `OrdOrderDate`, `OrdOrderStatus` and `OrdPO`, and `Ord*` still reported
zero.

Two fixes, both now in the script:

- The four names are **excluded outright**. The tempting general rule — require an uppercase
  letter after the prefix — is also wrong: `RevkVA` has a lowercase `k`.
- **Boolean columns no longer count as evidence.** SharePoint returns `false` whether a
  Boolean was written false or never written at all, so `OrdEngineeringRequired` and `OrdLDs`
  would mark an untouched row as populated. Same class of false negative.

A **sentinel check** was added alongside the strict test — one key column per group
(`OrdOrderDate`, `MdlModelID`, `RevkVA`, `CliLeadTimeWeeks`) — because the strict test also
misses any unit that received *part* of its group. It over-reports where a parent genuinely
has no value, so both numbers are printed rather than one replacing the other.

**Re-run `x21` before acting on any `Ord*` or `Cli*` figure.**

## Confirmed 2026-09-21: the three flagged orders are TWO different failures

`x19` with sibling divergence, over the orders the client flagged. All three were created by
Patrick Vaillancourt through Power Apps on 2026-09-17.

### 22169 — the fan-out race

A clean contiguous tail. Units created 17:39:44–17:40:07 got everything; the four created
17:40:12–17:40:25 got nothing from `Order` or `Models`. Thirteen `Ord*` fields diverge between
the six good siblings and the four bad ones, all the same way.

### 22172 and 22175 — Save Conflict, and the timestamps prove it is not the race

**This is the important distinction, and 22172 is what makes it visible.**

| | |
|---|---|
| `1235` 22172-1/2 | created **17:57:20** — lost `Ord*` |
| `1236` 22172-2/2 | created **17:57:24** — has everything |

The damaged unit was created **first**. Both existed well before the flows ran at 17:57:51.
So the fan-out read them both, and the write to 1235 simply failed. Its own history shows why:
`v2.0` (`Mdl*`) and `v3.0` (`Rev*`) are both stamped **17:57:51** — two flows writing the same
row in the same second. The Order flow was the third, and it lost.

22175 is the same thing, scattered further:

| | |
|---|---|
| `1245` 22175-1/2 | lost `Ord*` **and** `Mdl*` — this is the unit whose run threw the 400 |
| `1246` 22175-2/2 | lost `Rev*` |

Two siblings, **different groups lost on each**. No race produces that. And on 1236 the version
labels are not in timestamp order — `v4.0` is stamped 17:57:52 against `v3.0` at 17:57:53 —
which is concurrency visible in the version numbering itself.

🔑 **So the race is the smaller problem.** It needs a burst of creates to bite. The Save
Conflict needs only two flows and one row, which is every single order.

### 🔴 And a third, unrelated bug: the `Clients` sync flow reads a field that is not there

`Cli*` came back `0/1` on **all 14 units across all three orders**. The flow definition says
why — its one mapping is:

```
'item/CliLeadTimeWeeks' = "@triggerOutputs()?['body/CliLeadTimeWeeks']"
```

`CliLeadTimeWeeks` is the **destination** column on `Order Items`. The source, per the N3 spec,
is `Clients.Lead Time`. The destination name was pasted into the source expression, so the
flow reads a field the `Clients` list does not have, gets null, and writes null — which the
connector turns into "leave it alone". It has been enabled since the cutover doing nothing at
all, on every unit, silently.

⚠️ Confirm the real internal name off the `Clients` list before fixing it — this repo's record
on reasoning about field names is bad enough that the rule is now read-values-only.

## ✅ ROOT CAUSE FOUND — the Power Apps order-creation save

Supplied by the user 2026-09-21. The save button's Power Fx does this, in this order:

```
 4  SubmitForm(Form2)                    -> creates the Model Revision   ⚡ fires Rev sync
 6  Patch(Models, SelectedModel, {...})  -> sets Latest Model Revision   ⚡ fires Mdl sync
 7  Patch(Order, Defaults(Order), {...}) -> creates the Order            ⚡ fires Ord sync
 8  ForAll(Sequence(varNewOrder.Qty),
        Patch('Order Items', Defaults(...), {...}))   <- the units, ONE AT A TIME
```

**Both defects fall straight out of that ordering.**

### The race: the Order exists before its units do

Step 7 creates the `Order` row, which fires the Order sync flow immediately. Step 8 then
creates the units one at a time — measured at **4–5 seconds each**, because each iteration
does a server round-trip for its `LookUp('Order Items', 'Unit ID' = …)` duplicate check. So
for a Qty-10 order the flow fans out into a list that is still being written for **~45
seconds** after it was triggered.

That is 22169 exactly: Order created ~17:39:4x, units trickling in until 17:40:25, the flow's
`Get items` landing at 17:40:07–12 and seeing six.

🔑 **The race window is Qty × ~4.5s.** It is not a fluke of that afternoon — it is a property
of every order, and it scales with quantity. Small orders escape it; big ones cannot.

### The conflicts: three flows fired within one second of each other

Steps 4, 6 and 7 are three writes to three different parent lists inside one save, a second or
so apart. Each fires its own sync flow, and all three fan out onto **the same** `Order Items`
rows. That is the collision — and it needs no burst of creates at all, which is why the
two-unit orders 22172 and 22175 were hit while being far too small to race.

### 🔑 The fix that removes both, and needs no flow change at all

**The app already holds every value the sync flows would write.** At step 8 it has
`varNewOrder` (order number, qty, PO, price, province, WET-WETP, indexing, order date, initial
promised date, order step, order type, note, order folder), `SelectedModel`,
`SelectedModelRevision` and `SelectedClient` — all in scope, all already fetched.

So populate `Ord*` / `Mdl*` / `Rev*` **in the same `Patch` that creates the unit**. One write,
by one writer, at a moment when no other writer exists:

- no read to race, because the child is born complete;
- no second writer, so no Save Conflict;
- and it retires the post-backfill gap as well — a unit created at any time is correct.

The N3 flows then keep their real job, which is propagating *later* parent edits, and the
damage they can do shrinks to that.

⚠️ This does not make the flows safe on its own. A parent edit still fans out and two flows
can still collide, so the retry scope is still worth adding. But it takes the common path —
order creation — off the collision course entirely.

### Three other things in that save worth a look

- 🔴 **`SelectedModel` is only `Set` inside `If(varNewModel, …)`.** On the existing-model path
  nothing in this code assigns it, so it carries whatever the *previous* save left in it
  unless some other control sets it. Step 6 then patches that model's `Latest Model Revision`,
  and steps 7–8 stamp it onto the Order and every unit. Confirm a picker sets it; if not, this
  is a live cross-order contamination bug and a much worse one than the sync gaps.
- 🔴 **No error handling anywhere.** Every `Patch` is unchecked — no `IfError`, no `Errors()`.
  If one unit's create fails, `ForAll` carries on and nothing reports it. Given that Save
  Conflicts are already landing on this list, silent partial saves are not hypothetical.
- ⚠️ **The duplicate-check `LookUp` inside `ForAll`** is what makes each iteration cost 4–5
  seconds, and therefore what sets the width of the race window. If the parent fields move
  into the create, this stops mattering; if they do not, hoisting the check out of the loop
  shrinks the exposure.

## Three things the raw version dump surfaced on the way past

Each one is independent of the above and independently checkable.

- ✅ **`Model Revisions.ModelID` — cause found and closed 2026-09-21.** Revisions `387` and
  `106` resolve to `M-HYQU-0093` / `M-HYQU-0037` — *model* codes where a revision id belongs,
  and the units mirror them into `RevModelRevionID`. Same defect
  `model-revision-modelid-repair-2026-09-14.md` fixed on 29 rows, recurring because that
  repair fixed instances and never found the source.

  **The source was the Power App**, which carried the old model id through on creation. The
  user fixed it 2026-09-21. So the open question at the bottom of that repair doc — *"what
  corrupted them: unknown"* — is now answered, and `EditorId 106` was a red herring: it is
  simply the account the bulk scripts run as.

  🔑 **Sequencing:** the source is closed, so a repair now holds. Run
  `x17_audit_revision_modelid.js` for the current count, then `x18_repair_revision_modelid.js`
  — and only then `x22`, which **refuses** to write a `RevModelRevionID` that is not
  `MR-…-V1` / `MRSA-…-V1` rather than spreading a model code under cover of a repair.
- ⚠️ **`Frame = Plaspak` on v1.0 of all ten units.** `fix_created_units.js` documented this
  exact trap: a create payload that omits `Frame` gets the column's **default** applied
  silently, and blank is the normal state on 735 of 1,117 rows. The Power Apps create path
  appears to hit it. Confirm whether Plaspak is real for 22169 or contamination.
- ⚠️ **Three calculated columns are in an error state on every row** — `PriceCAD`, `FxRate`
  and `FxYear` all return `{"ErrorMessage":"256"}`. Also, the `test calculated column` is
  still on the list.

## The identity question, closed

The version history pane showed a modification by **Christine Dalpe**, dated 2023 or 2024, on
rows created last month. Resolved:

- **She is a real account** — `cdalpe@pioneertransformers.com`, site user id **26**, UIL row
  created **2023-08-28**. Not a current colleague, but not fabricated either; the UIL keeps an
  identity long after the account stops being used, and that 2023 stamp is when it first
  touched this site.
- **She has authored or edited nothing.** Across `Order Items` (1,102), `Order` (467),
  `Models` (393) and `Model Revisions` (394) — **4 lists, 2,356 rows** — id 26 does not appear
  in a single `AuthorId` or `EditorId`.
- Every stored version of all ten 22169 units is September 2026, by Patrick Vaillancourt,
  Soleil Anker or Angelique Tiago.

So whatever that pane was showing was not a version of any item in these lists. The likely
culprit is the details-pane **Activity** feed, which is not item version history and surfaces
events belonging to other things.

🔑 **And `EditorId 106` — left open in the Model Revisions repair as "accounts for 43 of 45
corrupt rows" — is `soleil.anker@ermco-eci.com`.** The account this project's own bulk
scripts run as. That open question should be closed as *our own tooling*, not an outside
actor, and the next bulk operation on that list planned accordingly.

## Read this before trusting a version history again

- `Order Items` has `EnableVersioning = true`, `MajorVersionLimit = 50`. History is kept, so
  "one entry" is a fact about the row — but past 50 writes the **oldest** versions are trimmed
  and v1.0 goes first.
- The pane diffs **rendered** values. A lookup it cannot resolve renders blank, so a version
  that cleared a lookup can display as "nothing changed".
- The details-pane **Activity** feed is not version history.
- `x19`'s `ERASED` verdict on units 7–10 is a false positive from a hand test at
  2026-09-21 04:59 UTC (`OrdPO` blank → `5` → blank, twenty minutes before the run). The
  original loss has no version at all, which is the whole point.
