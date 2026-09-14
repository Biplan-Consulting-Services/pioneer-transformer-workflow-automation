# Evening runbook — 2026-09-14

Deploy v004 and turn the `Order Items` trigger flow back on. **After staff have gone**,
because enabling is the irreversible moment and the exposure window is where their work
gets caught.

Steps 1–3 are safe with staff still in. **Step 5 onward must be one unbroken sitting.**

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

**Step 2 ran first, so test the real column rather than the proxy:** open a few units and
read **`Estimated Delivery Date`** itself. The old hidden `test calculated column` is the
fallback if that is somehow unreadable.

- **If it shows tomorrow's date, the trap is real.**

Read at least one unit from each branch — one delivered (branch 1, no `TODAY()`, so it
must NOT move), and one stalled in production (a `TODAY()` branch). If the non-`TODAY()`
branch also reads a day ahead, the problem is not the trap and is something else entirely.

This decides whether `Estimated Delivery Date` survives as a calculated column. If it fails, the fallback is already built — column formatting's `@now` is
browser-evaluated and has neither the freeze nor the UTC trap
(`sharepoint-lists/formatting/EstimatedDeliveryDate.format.json`).

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
