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

## Three things the raw version dump surfaced on the way past

Each one is independent of the above and independently checkable.

- 🔴 **`Model Revisions.ModelID` is corrupt again, or was never fully repaired.** Revision
  `LookupId 387` resolves to `M-HYQU-0093` — a *model* code where a revision id belongs, and
  all ten units mirror it into `RevModelRevionID`. That is exactly the defect
  `model-revision-modelid-repair-2026-09-14.md` fixed on 29 rows a week ago. Revision 387 was
  either missed or created afterwards, which means **the repair addressed instances, not the
  cause.** Re-run `x17_audit_revision_modelid.js`.
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
