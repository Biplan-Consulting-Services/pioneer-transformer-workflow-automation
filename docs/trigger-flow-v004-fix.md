# Trigger flow v004 — fixing the 203, and how to know it worked

Written 2026-09-14. This is handover job 1: the `Order Items` create-or-update trigger
flow has been **disabled since 2026-09-11 07:1x** and this is what turns it back on.

`roadmap.md` (*FIRST daylight job*) says why the fix is shaped this way. This file is
deploy and test only.

---

## What v004 changes

| | v003 (live, disabled) | v004 |
|---|---|---|
| `Get_Client` / `Get_Model` | top-level, id read unguarded off the trigger | each wrapped in a guard condition on its own lookup id |
| `Condition_StatusDate` | `runAfter: Condition` — behind both gets | `runAfter: Initialize_vStatusDateValue` — parallel to them |
| `Condition`'s two lookup comparisons | `@outputs('Get_Client')?['body/Client_ID']` | same, wrapped in `coalesce(..., the mirror)` |
| `Update_item`'s two lookup writes | same bare read | same coalesce |
| trigger `recurrence.interval` | 5 | **5, deliberately unchanged** |

The resulting graph is a diamond — the stamp no longer descends from either get:

```
Initialize_variable
  └─ Initialize_vStatusDateValue
       ├─ Condition_StatusDate            (Step Status + Step Status Stamped only)
       └─ Guard_Client { Get_Client }
            └─ Guard_Model { Get_Model }
                 └─ Condition             (the four-mirror change guard)
                        ↓
       Condition_3  ← Condition, Condition_StatusDate  →  Update_item
```

**Why guards rather than a tolerant `runAfter`.** An `If` that evaluates false still
*succeeds*; only the nested action is skipped. So every downstream `runAfter` stays plain
`["Succeeded"]`. The roadmap sketch said downstream would need `Succeeded` **and**
`Skipped` — true of `runAfter: {Get_Client: [Succeeded, Skipped, Failed]}`, not of
wrapping the action. Wrapping also means a model-less unit never spends a connector call
on a get that cannot work.

**Why the write is coalesced too, and not only the comparison.** Both expressions appear
twice. Uncoalesced, the *comparison* is the real bug: on a model-less unit, `null` against
a populated mirror compares unequal, so `Condition` reports a change that has not happened
and rewrites the row on **every poll** — and the write never makes the two sides agree, so
it does not settle. The *write* is milder than it first looks: R14 established this
connector ignores a field passed `null` rather than clearing it, which is the same
behaviour v002's `item/StatusDate` already relies on. Both are coalesced anyway, because
R14 is an observed behaviour and not a documented contract, and a field we intend to leave
alone should say so. **Gate B below measures how much was riding on it.**

Regenerate at any time:

```bash
python scripts/apply_v004_lookup_guards.py \
  "workflow-data/Order Items - Create or Update Trigger flow/v003__2026-09-11T06-00__pulled__pasted-from-designer.json" \
  -o /tmp/v004.json
```

It refuses to run unless v003 is exactly the shape it expects, and re-checks afterwards
that no `runAfter` crosses a scope boundary, that no uncoalesced lookup read survives,
that the stamp no longer descends from a get, and that the interval is still 5.

---

## Part 0 · The gate — run this BEFORE anything is pasted

```
scripts/x10_trigger_flow_gate.js     read-only, paste into the browser console
```

**GATE A — `StepStatusStamped == StepStatus` on every row with a Step Status. Must be 0
drifted.** It was 262/262 at 2026-09-11 05:55 and nothing should have moved it, but this
is the one precondition whose failure cannot be undone by turning the flow off again: a
drifted mirror makes `Condition_StatusDate` fire on the next poll and re-stamp
`Status Date` to today, and **246 rows carry a historical date**.

Until now the only thing that ever printed that number was `n8_split_status.js`, whose
verification block sits *after* its early return on DRY RUN — so re-reading the gate meant
letting it write. x10 reads it and nothing else.

**GATE B — a lookup is empty but its mirror is not.** Informational, not blocking. It
counts the rows that were relying on R14, i.e. how load-bearing the coalesce on the write
turns out to be. Record the number here when it is first run.

x10 also prints the thing the handover asks for and nothing supplied: **which units are
the 203**, and which of them are usable as a test row.

---

## Part 1 · Deploy

The flow already exists, so this is the v002 → v003 route, not the N3 shell dance:
overwrite the definition in the designer with the browser extension that exposes raw JSON.

1. Confirm the flow is still **Off**.
2. **Export the current definition first and intake it.** Nothing modifies a flow until
   what is live has been snapshotted. If the designer has been touched since 2026-09-11
   06:00 the export will not match v003, and `apply_v004_lookup_guards.py` must be re-run
   against the newer pull rather than pasting a v004 built on a stale parent.

   ```bash
   python scripts/flow_version.py --flow "Order Items - Create or Update Trigger flow" intake
   ```

3. Paste the **definition object**, not the full export document:

   ```
   workflow-data/Order Items - Create or Update Trigger flow/
     v004__2026-09-14T09-34__local__guard-both-lookup-gets-decouple-the-Status-Date-.definition-only.json
   ```

4. **Save, then export again and snapshot it.** The paste does not prove itself; only a
   pull carrying the same sha marks v004 `applied`.

   ```bash
   python scripts/flow_version.py --flow "Order Items - Create or Update Trigger flow" intake
   python scripts/flow_version.py --flow "Order Items - Create or Update Trigger flow" status
   ```

   ⚠️ Expect `recurrence.interval` to survive at 5. If a pull reports FORKED on **only**
   that key, that is the designer rewriting it on save — the known 2026-09-11 behaviour,
   not a bad paste.

5. Only then turn the flow **On**.

---

## Part 2 · Test — on one of the 203, not on a healthy unit

Testing the happy path is how this flow reached production broken. x10 prints candidates:
model-less units whose Step Status already equals its mirror, so a deliberate change
produces one clean, attributable stamp.

1. Change **Step Status** on one candidate unit.
2. Wait one poll — **5 minutes**, not 1.
3. Check, in this order:

| # | expect | if not |
|---|---|---|
| 2.1 | the run **succeeded** | read the error; if it is still `WorkflowOperationParametersRuntimeMissingValue` a guard did not match the empty shape SharePoint sends — see below |
| 2.2 | `Get_Client` and `Get_Model` show **Skipped**, not Failed | the guard evaluated true on an empty lookup; widen `nonempty()` in the generator |
| 2.3 | `Status Date` = today | the stamp is still coupled to something — check `Condition_StatusDate`'s `runAfter` in the saved definition, not in the file we pasted |
| 2.4 | `Step Status Stamped` follows the new value | `Update_item` did not run; `vUpdateOrderItem` never went true |
| 2.5 | the **four `_TextField` mirrors are unchanged** | the coalesce did not take — this is the Gate B failure mode, and on a model-less unit with populated mirrors it means data was just cleared |
| 2.6 | the next poll writes **nothing** | termination is broken; one of the coalesced comparisons is not settling |

4. Then repeat 1–3 on a **healthy** unit — one with all three lookups — to confirm the
   guards did not break the path that already worked.

**On the empty shape.** The guard tests both `''` and `0` because the run died at the
connector, which is downstream of the trigger body, so the failure said "null or empty"
and nothing more precise. If 2.2 shows a guard evaluating true on an empty lookup, read
the actual trigger body out of the run history, note the shape **here**, and narrow the
guard to it rather than adding a third speculative clause.

---

## Part 3 · After it is on

- `Order Items`' four `_TextField` mirrors start being maintained again. They were
  confirmed unused on 2026-09-11, so nothing downstream should move.
- The **parent** mirrors remain unmaintained — that is a separate job (handover item 3,
  design in `roadmap.md`), and N3 is strictly parent → child so this flow does not touch
  them.
- The N3 test preconditions in `n3-deploy-and-test.md` §0.1 assume this flow is **off**.
  With it on, every N3 write fires it once. That is correct behaviour, not noise — but a
  future N3 test run will read differently than the 2026-09-10 ones did.
