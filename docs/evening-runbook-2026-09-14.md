# Evening runbook — 2026-09-14

Deploy v004 and turn the `Order Items` trigger flow back on. **After staff have gone**,
because enabling is the irreversible moment and the exposure window is where their work
gets caught.

---

## Where this stands — updated 2026-09-14 15:0x

| # | step | state |
|---|---|---|
| 2 | `n9` — eight columns | ✅ **done** ~14:20. All eight created, every `ResultType` stored as asked |
| 3 | confirm v004's parent | ✅ **done** 12:40. Reported a fork; it was our own stale hash, not a changed flow |
| 4 | paste v004 | ✅ **done** 14:48. `v004 CONFIRMED APPLIED`, verified in the tenant's own export |
| 1 | UTC trap test | ✅ **done 22:20** — `VERDICT: clean`, there is no trap |
| 5 | re-mirror | ✅ **done 22:22** — 80 rows, ok=80 fail=0, verification **0 / 0** |
| 6 | confirm the gate | ✅ **done 22:23** — Gate A `DRIFTED: 0`, 272/272 |
| 7 | **enable the flow** | ✅ **done ~22:23** — user flipped it |
| 8 | test on a model-less unit | ✅ **done 22:40** — 8.1-8.5 all pass; 8.6 outstanding |
| 9 | test on a healthy unit | ⬜ candidate `21386-2/2` (id 6), mirrors populated |
| 10 | watch two more polls | ⬜ |

**The flow was enabled at ~22:23 on 2026-09-14. It is now polling every 5 minutes.**

🔴 **Steps 5, 6 and 7 are one unbroken sitting.** Every minute between the re-mirror and
the enable is a minute of fresh staff drift that gets stamped with today's date. Step 1
is independent and can happen before or after.

If something goes wrong at any point: **turn the flow Off.** That undoes everything except
a `Status Date` already overwritten, which is why step 5 comes first and step 6 verifies it.

---

## Why this is an evening job at all

Measured today, twenty minutes apart, while we worked:

| | 11:2x | 11:4x |
|---|---|---|
| units | 1,193 | **1,195** |
| `Step Status` ≠ its mirror | 65 | **72** |

Staff are advancing units and typing dates right now. Every row they touch between the
re-mirror and the enable drifts again, and the flow's first poll stamps *those* with
today. The gap has to be seconds, not minutes — which is why the re-mirror comes **last**,
not first.

Precedent: the cutover itself ran 03:41–06:45 for this reason, and the 09-11
enable-then-fail landed at 07:1x, just as people arrived.

## The decision this runbook encodes

**Staff enter `Status Date` by hand today and want it auto-filled** (user, 2026-09-14).
So v004 ships unchanged.

⚠️ **Do not add a "only stamp when `Status Date` is blank" guard.** It was proposed here
this morning and it is wrong: a row already carrying a date from its previous step would
never stamp again, so the second transition and every one after would silently keep the
old date. The guard breaks the feature it looks like it protects.

The one behaviour to tell staff: *change the step and leave the date alone — it fills in
within 5 minutes. If the real date differs, correct it **after** the stamp lands and it
sticks*, because by then the mirror matches and the flow will not touch the row again.

---

## 1 · After 20:00 Eastern — the UTC trap test

Separate question, same evening, and it has to be after 8pm.

`calculated-columns-plan.md:528`: `TODAY()` in a SharePoint calculated column is widely
UTC-based rather than site-local, so a row edited between roughly **20:00 and midnight
Eastern** recomputes with UTC already on tomorrow and reads **a day ahead**.

```
scripts/x12_utc_trap_test.js       DRY RUN by default
```

It refuses to run before 20:00 Eastern, and refuses again if Eastern and UTC happen to be
on the same date — in which case the test cannot discriminate and a pass would mean
nothing.

🔴 **This cannot be a read-only test, and the original plan missed that.** A SharePoint
calculated column is **stored**, not evaluated on read: it recomputes when the **item** is
written and at no other time. Every row's `Estimated Delivery Date` was computed when the
column was created (~14:20 Eastern = 18:20Z), which is *before* 20:00 — so simply reading
at 21:00 returns this afternoon's answer and proves nothing. *"Check the test column after
8pm"* would have looked like a clean pass whatever the truth is.

So the script writes `Calc Refreshed` — our own column, read by nothing, and the exact
mechanism the nightly touch uses — then re-reads. One row per case:

| | | |
|---|---|---|
| **STALLED** | a unit on a `TODAY()` branch | should read **today + buffer + penalty** |
| **CONTROL** | a unit on branch 1 (`Planned Delivery Date` set) | that branch never calls `TODAY()`, so it **must not move at all** |

| result | meaning |
|---|---|
| stalled = today + buffer | no trap — `Estimated Delivery Date` stays a calculated column |
| stalled = tomorrow + buffer | **the trap is real** — decide whether evening-only staleness is tolerable; the fallback is the column formatting already built |
| **control moved** | stop. Branch 1 has no `TODAY()` in it, so the cause is something else entirely — do not redesign around a trap that is not the problem |

The dry run also prints **how many units are on a `TODAY()` branch right now**, which is
the honest count for stage B's nightly touch — the number the ~21 estimate needs replacing
with. If it fails, the fallback is already built — column formatting's `@now` is
browser-evaluated and has neither the freeze nor the UTC trap
(`sharepoint-lists/formatting/EstimatedDeliveryDate.format.json`).

> ### ✅ Done 2026-09-14 22:20 — VERDICT: clean, there is no UTC trap
>
> Run at **22:20 ET**, with Eastern on 09-14 and UTC already on 09-15 — the script
> confirmed the two dates differ before testing anything, which is the precondition that
> makes the result mean something.
>
> | | before | after the `Calc Refreshed` write |
> |---|---|---|
> | **STALLED** `21611-1/1` (id 7) | 2026-09-24 | **2026-09-24** — Eastern-today + 10 |
> | **CONTROL** `21408-1/1` (id 4) | 2026-08-31 | 2026-08-31 — unchanged, as required |
>
> The stalled row genuinely recomputed at 02:20**Z**, with UTC on tomorrow, and still
> resolved `TODAY()` to the **Eastern** date. So `TODAY()` here is site-local, not UTC.
>
> **Consequences:** `Estimated Delivery Date` stays a calculated column, and the
> `EstimatedDeliveryDate.format.json` `@now` fallback is not needed. The
> `calculated-columns-plan.md:528` warning does not hold on this tenant — it should be
> annotated rather than deleted, since the claim is widely made and the next person will
> re-raise it.
>
> ⚠️ The write mattered exactly as the script argued: reading without writing would have
> returned the 14:20 value and looked like a pass no matter what the truth was.
>
> **Also measured: 20 units are on a `TODAY()` branch right now** — that is the real
> number for stage B's nightly touch, replacing the ~21 estimate.

## 2 · `n9` — the eight columns (seven calculated, plus `Calc Refreshed`)

```
scripts/n9_create_calc_columns.js        DRY RUN by default
```

Independent of the flow work; nothing below depends on it. Creates columns, writes no
items. `Options: 8` is `AddFieldInternalNameHint`, so they do **not** land in the default
view and staff will not see them until someone adds them.

> ### ✅ Done 2026-09-14 ~14:20 — all eight created, nothing downgraded
>
> Run **before** step 1 deliberately, reversing this file's original order: it means the
> UTC test tonight reads the **real `Estimated Delivery Date` column** rather than the old
> hidden `test calculated column` proxy, which the cutover runbook says was hidden and may
> not be usable anyway.
>
> Eight POSTs, eight `200`s — and the read-back is what matters, since a `200` is not proof
> of the stored `ResultType`. Decoding `OutputType` (SP.FieldType):
>
> | column | TypeAsString | OutputType | |
> |---|---|---|---|
> | `CalcRefreshed` | DateTime | — | plain column, correct |
> | `BoPenalty` | Calculated | 9 = Number | ✓ |
> | `EstimatedDeliveryDate` | Calculated | **4 = DateTime** | ✓ |
> | `IsCanadian` | Calculated | 8 = Boolean | ✓ |
> | `FxYear` · `FxRate` | Calculated | 9 = Number | ✓ |
> | `PriceCAD` · `PriceUSD` | Calculated | **10 = Currency** | ✓ |
>
> The two Currency columns were the likeliest to be silently coerced to Number. They were
> not. The 828-character `Estimated Delivery Date` formula was also accepted whole, so the
> 1024 limit held with room to spare.

## 3 · Confirm v004's parent is still current

```bash
python scripts/flow_version.py --flow "Order Items - Create or Update Trigger flow" intake
python scripts/flow_version.py --flow "Order Items - Create or Update Trigger flow" status
```

Export the live definition from the designer into `_inbox/` first.

- **Matches v003** → v004 is good, continue.
- **Does not match** → the designer has been touched since 09-11 06:00 and v004 was built
  on a stale parent. Re-run `apply_v004_lookup_guards.py` against the newer pull. **Do not
  paste v004 as it stands** — that is the silent-fork case the whole versioning system
  exists to catch.

> ### ✅ Done 2026-09-14 12:40 — and it reported a fork that was not one
>
> The export came in as **v005** and `intake` marked v004 FORKED. A structural diff of
> v003 against v005 found **zero** differing lines — byte-identical, same actions, same
> recurrence. The tenant had not moved.
>
> **The stale thing was our own hash.** `content_sha` gained its second
> `authentication`-stripping rule at 06:0x on 09-11, minutes *after* v003 was captured at
> 06:00, so v003's stored sha was computed by an older canonicaliser and no longer matched
> what the same file hashes to today. `rehash_flow_versions.py` exists for exactly this
> and fixed it: `v003 8952f0112e1b -> 26d75bd9e1cc`, which is v005's sha.
>
> Then the real check: regenerating v004 from **v005** produces `558b95e86850` — identical
> to the stored v004. **v004 is valid and paste-ready.**
>
> ⚠️ v004 still shows `forked` in `status`, and that is now cosmetic: the rule is "a later
> pull did not match", and v005 is a later pull of the *parent*, not of v004. Do not
> re-author on the strength of that label alone — diff first. A fork report is a prompt to
> investigate, not a verdict.

## 4 · Paste v004

Confirm the flow is still **Off**. Paste the definition object — not the full export
document:

```
workflow-data/Order Items - Create or Update Trigger flow/
  v004__2026-09-14T09-34__local__guard-both-lookup-gets-decouple-the-Status-Date-.definition-only.json
```

Save. Export again, intake, and confirm `status` flips v004 to `applied`.

⚠️ Expect `recurrence.interval` to survive at **5**. A FORKED report on **only** that key
is the designer rewriting it on save — known 09-11 behaviour, not a bad paste.

> ### ✅ Done 2026-09-14 14:48 — `v004 CONFIRMED APPLIED`
>
> **Paste the editor wrapper, not the bare definition.** Two attempts vanished silently
> before this was spotted — pasted, saved, re-exported, and the export still hashed as
> v003. The extension takes a flow-editor wrapper, `{connectionReferences, definition}`;
> a bare definition drops `connectionReferences`, which is the object carrying the real
> connection id, so the editor has nothing to bind and discards it. Saving then just
> re-saves what was already there. `n3-deploy-and-test.md` documents this and this
> runbook pointed at `definition-only.json` anyway.
>
> **The file that worked:** `_outbox/alternate-shapes/definition-plus-connections.json`,
> written by `flow_version.py stage`. Note that `stage`'s default `PASTE-ME.json` is the
> `properties` shape, chosen because it suited a *different* flow — for this one, use the
> alternate.
>
> Verified in the tenant's own export afterwards, not just by hash: both guards present,
> both gets nested inside them, `Condition_StatusDate` on `Initialize_vStatusDateValue`,
> 4 coalesces, interval still 5.
>
> **Two defects in `flow_version.py` surfaced and were fixed:**
> - A version already labelled `forked` could never afterwards be confirmed `applied`, so
>   v004 — demonstrably live — kept reading `forked`. Both labels are inferences; a pull
>   carrying the exact definition is direct evidence and outranks the earlier guess.
> - `live()` ordered by version NUMBER, so it reported v005 (captured 12:40) over v004
>   (applied 14:49). A local version is authored before it is pasted, so its number can be
>   lower than a pull that happened in between. Now ordered by when the proof arrived.

---

## 🔴 5 onward — one sitting, no breaks

### 5 · Re-mirror

```
scripts/x11_remirror_step_status.js      set APPLY = true
```

Run the DRY RUN first and read the list. It writes **one field** — `StepStatusStamped` —
and never `StatusDate`.

Two numbers at the end, and the second matters more:

| | expect | proves |
|---|---|---|
| mirror still drifted | 0 | the write landed |
| **StatusDate CHANGED** | **0** | it landed on the **right field** |

**Anything but 0 / 0 → stop. Do not enable.**

### 6 · Confirm the gate

```
scripts/x10_trigger_flow_gate.js
```

Gate A must now read `DRIFTED: 0`. Note the count of model-less units — see the footnote
below, it is not 203.

### 7 · Enable the flow

Immediately. Every minute here is a minute of fresh drift that will be stamped with today.

### 8 · Test on a unit with NO model

Not a healthy one — testing the happy path is how this reached production broken.
Candidates from x10's last run: **`22021-14/20`** (id 21), `21881-1/2` (id 22),
`22032-1/20` (id 25).

Change **Step Status**, wait one poll — **5 minutes, not 1**.

| # | expect | if not |
|---|---|---|
| 8.1 | run **succeeded** | still `WorkflowOperationParametersRuntimeMissingValue`? a guard missed the empty shape — read the trigger body and widen it |
| 8.2 | `Get_Client`, `Get_Model` show **Skipped**, not Failed | the guard evaluated true on an empty lookup |
| 8.3 | `Status Date` = today | the stamp is still coupled to something — check `Condition_StatusDate`'s `runAfter` in the **saved** definition, not the file we pasted |
| 8.4 | `Step Status Stamped` follows the new value | `Update_item` never ran |
| 8.5 | the four `_TextField` mirrors **unchanged** | the coalesce did not take |
| 8.6 | the **next** poll writes nothing | termination is broken |

> ### ✅ Done 2026-09-14 22:40 — v004 works on the shape that broke it
>
> **But it took two edits, and the first one taught us more than the second.**
>
> The flow was enabled ~22:23 and the test edit went in at 22:24:16. For sixteen minutes
> it produced **no runs at all** and wrote nothing to any of 1,196 rows. That is not a
> v004 defect and not a bad paste: `GetOnUpdatedItems` sets its watermark on the first
> poll **after** being enabled, and a poll that finds nothing logs no run — which is
> exactly the no-runs-at-all signature. The 22:24:16 edit fell inside that blind spot and
> was never eligible to be seen.
>
> 🔴 **Carry this forward: after enabling any `GetOnUpdatedItems` flow, the first edit you
> make may be silently ignored. Touch the test row a second time, several minutes later,
> before concluding anything about the flow's logic.** Sixteen minutes were spent here
> suspecting the guards, which were never the problem.
>
> Re-touching at 02:39:47Z produced the flow's write at **02:40:20Z**, 33 seconds later:
>
> | ver | | |
> |---|---|---|
> | 17.0 | 02:39:47Z | the re-touch — `step=En cours stamped=Terminé date=2026-08-11` |
> | 18.0 | **02:40:20Z** | **the flow** — `stamped=En cours date=2026-09-14` |
>
> | check | result |
> |---|---|
> | 8.1 run succeeded | ✅ green |
> | 8.2 `Get_Client` / `Get_Model` | ✅ **Skipped** — both guards evaluated `false` |
> | 8.3 `Status Date` = today | ✅ 2026-09-14 |
> | 8.4 `Step Status Stamped` follows | ✅ `En cours` |
> | 8.5 no mirror cleared | ✅ nothing wiped |
> | 8.6 next poll writes nothing | see below |
>
> `Condition StatusDate` returned **true** on its own branch — the decoupling holds — and
> `Condition` returned **false**, routing to `Set variable 16`, the null-lookup fallback.
> Only **1** row of 1,196 was modified, and drift returned to **0**.
>
> #### ⚠️ Undocumented side effect: the flow repopulates the `_TextField` mirrors
>
> `Order_Number_TextField` on the test unit went from `null` to **`22021`** — correct, it
> matches the unit's own title. Nothing was cleared; an empty field was filled. The
> `OrderNumber` lookup is not guarded (only Client and Model are), so the flow reads it
> and writes the mirror.
>
> **This matters well beyond this row.** The footnote below rests on the `*_TextField`
> mirrors being unreliable because that sync died on **2026-08-21** — which is why every
> "203" count was wrong. With the flow on, that is no longer static: every row staff touch
> gets its mirrors refreshed, so the mirrors slowly become accurate again, row by row, at
> different times. **"The mirrors are stale, don't trust them" quietly stops being true**,
> and anyone re-deriving lookup coverage from them in a few weeks gets a half-migrated
> picture with nothing to warn them. Read the lookups directly — `x10` does — and treat
> any mirror-derived count as unsafe regardless of which direction it now errs in.
>
> (The first version of `x13`'s 8.5 check called this a FAILURE, because it tested
> "differs from baseline" rather than the direction that is actually dangerous — a
> *populated* mirror wiped by a null from a skipped Get. Corrected; the check now
> distinguishes wiped from refreshed.)

### 9 · Then a healthy unit

One with all three lookups, to confirm the guards did not break the path that already
worked.

### 10 · Watch two more polls

Confirm no runaway writes. The failure mode to watch for is a row being rewritten every
poll because a comparison never settles.

---

## Footnote — the "203" is wrong, and it is ~20

`x10` measured it directly on 2026-09-14:

```
all three lookups empty : 16
some but not all        : 4      <- a shape nobody had counted
```

Not 203. `x6_check_lookup_coverage.js` says why in its own header: every earlier count
came from `*_TextField` mirrors in a CSV export, and that sync has been off since
**2026-08-21**, so those mirrors say nothing reliable about the lookups the flow actually
reads. Gate B is consistent — **0** rows have a populated mirror over an empty lookup, and
the reverse case is invisible to it.

The fix does not change; 20 rows still break the flow. But `roadmap.md`'s *"203 of
1,189"* and *"about 17% of units would silently stop stamping"* are measuring stale
mirrors. Real figure: **~20 units, ~1.7%.** Three documents need correcting once the
deploy is done.

The 4 partial rows — `P1_001-1/1`, `P20001-1/1`, `20877R1-1/1`, `P20002-1/1` — have a
Client but no Model or Revision. They would fail v003 at `Get_Model`; v004 guards each get
separately, so they are handled.
