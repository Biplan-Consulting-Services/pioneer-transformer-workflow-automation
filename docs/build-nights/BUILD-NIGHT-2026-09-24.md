# BUILD NIGHT — 2026-09-24 (Thu) → 2026-09-25 (Fri)

> ### 📍 THIS FILE IS THE WORKING BOARD. A TRACKED SNAPSHOT LIVES IN GIT.
> **Tracked copy:** `Workflow-Automation/docs/build-nights/BUILD-NIGHT-2026-09-24.md`. This path
> sits above the repos and git cannot track it; `~/.claude/session-tracks.json`'s `_night`
> points here. **Do not delete either copy.** After appending, re-harvest:
> ```
> cd "Clients/Pioneer Transformer"
> cp BUILD-NIGHT-2026-09-24.md Workflow-Automation/docs/build-nights/
> # then commit + push from Workflow-Automation
> ```
> On a conflict THIS file is newer; the tracked copy is authoritative for what survived.

Project: **Pioneer Transformer — Workflow-Automation** (`Clients/Pioneer Transformer/Workflow-Automation`).
Start-of-session context for anyone joining: `docs/HANDOVER-2026-09-11.md` (status block),
then `docs/n3-fanout-race-2026-09-21.md` § *Status at close of 2026-09-21*.

## HOW TO USE THIS BOARD

- **Post before you act, not after.** Intent → do → result.
- **A claim is not evidence.** Every status says how it was verified — a count, a diff, a hash
  match, a read-back. "I pasted it" is not verification; an `intake` hash match is.
- **Targeted edits only.** Never rewrite this file wholesale — two sessions append to it.
- **Blocked? Post `BLOCKED (on what, who unblocks)`**, then take the next UNCLAIMED task.
- **Board = state, DMs = questions.** Anything that changes state goes here too.

### Task states
`UNCLAIMED` → `CLAIMED (who, time)` → `BLOCKED (on what)` → `DONE (evidence)`

### Roles
| Session | Role | Owns |
|---|---|---|
| `claude-43` | planning | this board's task table, flow versioning (`flow_version.py intake/stage`), interpreting the user's console-script output |
| `claude-5b` | code editing | claims tasks, edits, verifies, commits + pushes, posts the result |
| **the user** | tenant | the Power Automate designer, running console scripts against the live lists, enabling flows |

### Exclusive resources — NOT stealable
| Resource | Owner | Why |
|---|---|---|
| Power Automate designer / enabling flows | **user** | No session can drive it (see CLAUDE.md, *hand-off*); two authors in one flow fork it |
| `workflow-data/<flow>/` (history.json, versions, `_inbox`, `_outbox`) | `claude-43` | `intake`/`stage` rewrite history.json and clear folders; two writers corrupt the lineage |
| Writes to live SharePoint lists | **user** (via scripts we write) | Every write fires the trigger flows; no session writes the tenant directly tonight |
| Git in `Workflow-Automation` | shared | **Stage named paths only — never `git add -A` / `git add .`.** `git pull --rebase --autostash` before every push — plain `--rebase` refuses because of the modified `x14` below (hit 21:0x). The tree carries untracked files that are not ours (below) |

⚠️ **Untracked files in the tree that nobody should commit blindly:** `sharepoint-lists/Order Items.csv`,
`sharepoint-lists/Order Items (1).csv` (09-16 exports, unstamped names), `workbooks/Archive active.xlsx`,
and a modified `scripts/x14_step9_healthy_unit.js` (PHASE flipped to verify — pre-existing, not tonight's).

---

## KEY FACTS — read before doing anything

### Order Items trigger flow — where it stands (verified by `flow_version.py status`)
| v | what | state |
|---|---|---|
| v006 | **the user's own edit**, pulled 20:12 from their zip: Livraison auto-complete (`CompletOrder` → `Terminé`/`Delivered`), `LocationStamped`, Status Date initialised from the row | `pulled`, replaced by v008 21:10 |
| v007 | Status Date keep-a-typed-date design (`StatusDateStamped`) | `local`, **superseded, never pasted** |
| v008 | v006 + back on the connection reference + **flow no longer reads or writes Status Date** | **`applied` 21:10 = LIVE** (hash-confirmed by `intake`); flow still OFF |

- 🔑 **User decision 2026-09-24: Status Date stays MANUAL.** The flow does not stamp it. Do not
  reintroduce a Status Date write without the user asking; the design is kept in
  `scripts/apply_v007_connref_statusdate.py` if they do.
- The trigger flow is **OFF**. Order: paste v008 → user copies it back → `intake` must report the
  v008 hash → tests → enable. Not before.
- ⚠️ `scripts/apply_v006_status_date_preserve.py` (untracked) is **moot** — never run, fixed by the
  user's v006 by another route. Its "v006" name is unrelated to the pulled v006.

### Connections — verified 20:55 from fresh extension pulls
The 2026-09 password reset made the user reconnect. That moved **only the Order Items trigger's
trigger** onto a plain connection (`shared_sharepointonline_1`) → the designer's *"uses a connection
instead of a connection reference"* warning. **All four N3 flows are clean:** definitions unchanged
since 09-11 (hash-identical), every trigger and action on `shared_sharepointonline` =
solution reference `new_sharedsharepointonline_89e9a`, connection `…98111a58…`. v008 carries that
same reference.

**Unknown:** whether the N3 flows actually *ran* today. A clean definition does not prove the
reference's connection was authenticated all day. Needs the user to read one flow's run history.

### Drift after a day down
- **Parent → unit** (Order / Models / Model Revisions → `Order Items`): measured by **`x25`** (new,
  whole-list, generated from x7's 46-field map, **never yet run live**). Expect
  `MdlLatestModelRevision` to show list-wide as *older* drift — that is known (09-21 parked item 2)
  and is the sanity check that x25 works: if it does not appear, x25 is wrong, not the data.
- **Clients → unit:** not measurable. The Clients flow reads `body/CliLeadTimeWeeks` — its own
  destination name — so `Cli*` is blank everywhere regardless of the outage (task E3).
- **`Order Items` mirrors (`*_TextField`)** — `x16`. Self-heal on each unit's next edit once v008 is on.
- **Stamps** — `x24` dry run. Optional now that the date is manual; what it still affects is that
  Livraison units not yet `Terminé`/`Delivered` get completed on their next edit.

### Verified-hard lessons that apply tonight (from CLAUDE.md / past nights)
- A zero-row read is a **failed** read, not "nothing to do". Every script aborts on it.
- Never conclude a column is empty from a CSV export — lookups are absent and calculated columns read blank.
- `_api/web/lists/…/fields` **hangs** on this tenant. Probe by `$select` instead.
- Lookups are **absent** from a plain item read; use `FieldValuesAsText`.
- A 200 means accepted, not correct. Read back.
- `node --check` every generated JS; bash heredocs eat backslashes — author with Write/Edit.

---

## TASK TABLE

| # | Task | Owner | Stealable | State |
|---|---|---|---|---|
| 0.1 | Create board + KEY FACTS, register in `session-tracks.json` | `claude-43` | no | **DONE 21:0x** — this file; registry entry re-read after write |
| U1 | Paste v008 into the Order Items trigger (extension, `_outbox/PASTE-ME.json`), save, confirm the connection warning is gone, copy JSON back to `_inbox` | **user** | no | **DONE 21:10** (user-reported; verified by P1) |
| U2 | Read run history of one N3 flow: did it fail today, and from when to when? | **user** | no | UNCLAIMED — sets x25's `SINCE` |
| U3 | Run `x25`, `x16`, `x24` (dry), `x17`; paste output (`copy(window.x25)` for x25) | **user** | no | UNCLAIMED — after U2 + 10–15 min of healthy polls |
| P1 | Intake U1's pull; confirm v008 `applied` by hash | `claude-43` | no | **DONE 21:10** — `intake`: *v008 CONFIRMED APPLIED* (hash match), v007 → `forked`, package `.zip` attached. Export holds ONE connection reference (`shared_sharepointonline` → `…98111a58…`, same as the N3 flows); `_1` gone. Flow still OFF |
| P2 | Interpret U3; decide repair route per parent (touch vs E1 overwrite) | `claude-43` | no | BLOCKED on U3 |
| E1 | **x22 overwrite mode** — repair stale non-blank parent values from an x25 report | `claude-5b` | yes | **DONE `d489f5a`** — regenerated + `node --check` OK; mock-harness 6/6 (see log) |
| E4 | **x25 rows carry the unit `id`** — so x22's OVERWRITE matches exactly instead of by Title. ⚠️ **Do before E2:** U3 has not run yet, so this is free now and costs a user re-run later. Files: `scripts/gen_x25_drift_scan.py` → regenerate. Add `id: u.Id` to every `report.push` and to `perParent[k].units` (keep Title for humans). Verify: regenerate, `node --check`, diff stat, and confirm x22's OVERWRITE accepts the new rows as-is | `claude-5b` | yes | **DEPRIORITISED 21:3x** — user is running x25 now, so it would not land in time; x22 already aborts on ambiguous Titles. Do after E2/E3 if at all |
| E2 | **Docs: record today** — Status Date manual decision, v006/v008, connection incident | `claude-5b` | yes | **DONE `ba41132` + `7f59469`** — diff stat and block text in the log |
| E3 | **Clients flow reads the wrong source field** — find the real field, author the fix | `claude-5b` | yes | **RE-SCOPED 22:0x by `claude-43`** — premise WRONG, flow is correct: confirmed independently, `Clients 2026-09-10 1734.csv` has exactly one lead-time field, `CliLeadTimeWeeks` (Number, "Lead Time (weeks)"). No flow change, nothing to stage. New scope: Cli* blank-fill via x22 (lift Cli from SKIP_GROUPS for one run) + correct the 09-21 doc's parked item 4. **UNBLOCKED 22:2x** — U4 back, go |
| U4 | Browser, signed in: `https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/lists(guid'3bcf7d97-0862-404d-ab3f-eeaa358c05d8')/items?$select=Id,Title,CliLeadTimeWeeks&$top=100` — read-only. Expect 200 with ~17 clients holding a value | **user** | no | **DONE 22:2x** — 200, **17 of 97** clients hold `CliLeadTimeWeeks` (16×3, 18×5, 20×7, 24×1 CONED, 28×1 HYDRO QUEBEC = FRM13's value). 80 are null — their units correctly stay blank. Pasted Atom feed, counted by `claude-43` |

### E1 — x22 overwrite mode
**Why:** x22 fills only BLANK fields. After a day with the N3 flows down, units hold OLD values —
x22 skips them by design. x25 finds them; nothing repairs them.
**Files:** `scripts/gen_x22_repair.py` (generator — edit here), regenerate `scripts/x22_repair_parent_sync.js`.
Read `scripts/x25_parent_drift_scan.js` for the report shape (`window.x25.report`: `{unit, list, field, unitV, parentV, modified, recent}`).
**Acceptance:**
- New mode, **off by default**, that takes a pasted x25 report (or a list of `{unit, field}`) and
  overwrites exactly those unit-fields with the live parent value — nothing outside the list.
- Parent value resolved the way x22 already does (through the unit's own lookup, FieldValuesAsText
  for lookups, bare `yyyy-mm-dd` dates, Choice `.Value` not the object — R22). **Never** from the x25
  report's `parentV`, which is truncated to 40 chars.
- Dry run prints before/after per field; APPLY re-reads every written unit and reports per field.
- Blank-fill behaviour unchanged when the new mode is off (regenerate and diff the JS: only the new
  mode's code moves).
**Verify:** `python scripts/gen_x22_repair.py`, `node --check` on the output, diff the regenerated JS
against the committed one and post the diff stat + a summary of what moved.

### E2 — docs for today
**Files:** `docs/HANDOVER-2026-09-11.md` (add a *Status, updated 2026-09-24* block above the 09-14 one —
same format), `docs/roadmap.md` (the trigger-flow / Status Date item: mark the auto-stamp **dropped by
user decision 2026-09-24, date stays manual**), header comment of `scripts/apply_v006_status_date_preserve.py`
(one line: superseded, never run, see v006/v008) then commit it so it stops sitting untracked.
**Content source:** this board's KEY FACTS — do not re-derive.
**Acceptance:** targeted edits, no rewrites; the handover block names v006/v007/v008 with states, the
connection-reference incident and its fix, the Status Date decision, and x24/x25 as the drift tools.
**Verify:** `git diff --stat` + post the handover block text here.
⚠️ Do **not** edit CLAUDE.md for this — if something belongs there, post it under DECISIONS NEEDED.

### E3 — Clients flow source field
**Evidence:** `workflow-data/Client - Create or Update Trigger/_inbox/_archive/2026-09-24T20-54__inbox.json`
compares and writes `triggerOutputs()?['body/CliLeadTimeWeeks']` — `CliLeadTimeWeeks` is the
**destination** column on Order Items. The source column on `Clients` has some other internal name.
**Step 1 (read-only):** find it in the newest `sharepoint-lists/Client*.csv` ListSchema record
(first record, not first line — see CLAUDE.md). Also check every other `Cli*` mapping in that flow
for the same mistake — post the full source→target table here before authoring anything.
**Step 2:** `scripts/apply_clients_<fix>.py` in the `apply_v004_lookup_guards.py` pattern: load the
newest pulled version (v002), assert the exact old expressions, change only those, assert the leaf
diff, write the output file. Hand the output path to `claude-43` to `snapshot --local` + `stage`.
**Acceptance:** diff is exactly the source-key changes; nothing else in the definition moves.
⚠️ Also watch for the connection: the wrapper must keep `new_sharedsharepointonline_89e9a`.

---

## DECISIONS NEEDED (user only)

| # | Question | Status |
|---|---|---|
| 1 | Livraison auto-complete tests **current** Location, so any later step change on a Livraison unit is forced back to `Terminé`/`Delivered` (incl. setting it Cancelled). Intended as "delivered is final", or only on the move INTO Livraison? | open — v008 keeps current behaviour |
| 2 | Run `x24` (level stamps) before enabling, or let the ~8 Livraison-but-Active units complete on their next edit? | open — decide from x24's dry run |
| 3 | Delete the stray connection `…5348ae66…` once v008 is confirmed live (check its "used by" first) | after P1 |
| 4 | x22 overwrite: if the parent field is now **blank** but the unit still holds a value, clear the unit? (Whether the flow itself would clear it depends on the column: R14 "connector ignores null" was measured false for DateTime on 09-15.) | open. E1 lists these and doesn't clear them |

---

## EVENT LOG

*(newest last)*

**2026-09-24 21:0x | `claude-43` (planning) |** Board created from the 09-03 layout; registered in
`session-tracks.json` as `claude-43` / planning and pointed `_night` here. State above is carried from
this session's work since ~19:45, all committed and pushed to `Workflow-Automation`:
`cdbb401` (v006 pulled), `875be0e` (v007 + x24), `7aebe13` (v008, x24 trimmed, x25), `0bc13dd`
(four N3 pulls). How verified: v006/N3 by `intake` hash; v008 by its authoring script's leaf-diff
assertions (13 leaves removed, all Status Date, plus two runAfter rewires) and by counting the
user's constructs in the staged PASTE-ME (`CompletOrder` ×5, `Livraison`, `Delivered`,
`LocationStamped` present; the only `StatusDate` strings are an action name). x24/x25 by
`node --check` only — **neither has run live yet.**

**2026-09-24 21:06 | `claude-5b` (editing) |** Registered in `session-tracks.json` as `claude-5b` / EDIT
(JSON re-parsed OK after the edit). **Claiming E1** (x22 overwrite mode). Plan: read
`gen_x22_repair.py` and the x25 report shape, add an overwrite mode that is off by default, regenerate,
`node --check` it, diff it against the committed JS, then commit and push those named paths only.
Tree at start: HEAD `a251cc8`; the only dirty items are the pre-existing x14 and untracked files listed above.

**2026-09-24 21:2x | `claude-5b` |** **E1 DONE, pushed `d489f5a`** (only `gen_x22_repair.py` and
`x22_repair_parent_sync.js` staged). **How to use:** in x22, set `const OVERWRITE =` to the
`copy(window.x25)` paste, or to `[{id|unit, field}]`. `null` = off = blank-fill over `UNITS`, as before.
- **Semantics:** it overwrites exactly the listed unit-fields with the value resolved live through the
  unit's lookup, using the same code path as blank-fill (never `parentV`). A listed field that already
  matches is skipped. **A parent that is now blank is listed, not cleared.** Clearing is a decision
  (below). *(Corrected 21:3x: I first wrote "the flow can't clear either". R14 says that, but it was
  measured false for DateTime on 09-15. Header wording fixed in the E2 commit.)* Any of these abort before the first parent read:
  a Title matching 0 or several units, a field x22 doesn't write, a `Cli*` field, a `list` that
  disagrees with x22's map, or 0 rows. x25's `(parent N missing)` rows are listed and skipped.
- **Dry run** prints `before -> after` per field. **APPLY** reads back every written unit, prints a
  per-field `written/verified/failed` table, and prints 🔴 lines for anything that failed.
- **Verification:** (1) baseline: regenerating from the untouched generator gave 0 diff against HEAD.
  (2) after the change, `node --check` OK. Diff stat is `163 +++---` on each file (272+/54−); the
  JS moved exactly as much as the generator. The only moved blank-fill code is `flat`/`same`, hoisted
  out of the read-back loop unchanged, plus `UNITS.length` → `RUN.length` in the summary line.
  (3) Ran the generated JS in Node against a mock SharePoint, 6/6 pass. Overwrite apply sent one PATCH
  of exactly `{OrdOrderDate:"2026-09-20", OrdPO:"NEW-PO"}` and did not touch a blank unlisted field,
  a stale unlisted field, a field that already matched, or a field with a blank parent. Duplicate
  Title, Cli field and empty paste each aborted with 0 parent reads. Blank-fill still wrote only the
  blank field. **Not verified:** a live run. The mock doesn't exercise lookup fields through v2.0 `/columns`.
- **For P2 (`claude-43`):** filter the x25 paste before handing it over. `recent` only leaves out the
  known list-wide `MdlLatestModelRevision` drift. **x25 names units by Title only.** Adding `id` to its
  report rows (`gen_x25_drift_scan.py`) would remove the Title lookup and its ambiguity abort. I'll do it
  if you want, but it only helps a re-run, so not before U3.
- **Question for the user (DECISIONS):** when the parent field is now blank but the unit still holds a
  value, should overwrite clear it? Current answer: no, list it.
- Next: **claiming E2.**

**2026-09-24 21:4x | `claude-5b` |** **E2 DONE**, pushed `ba41132`, then `7f59469` after `claude-43`
reported v008 live at 21:10.
- **Diff stat (`ba41132`):** HANDOVER +32, roadmap +9, `apply_v006_status_date_preserve.py` +182 (new to
  git, header line added), `gen_x22`/`x22` ±8 (E1's corrected blank-parent rationale, comment only,
  regenerated + `node --check` OK). **`7f59469`:** HANDOVER ±9, roadmap ±1, "staged" → "live 21:10".
  Both docs changes are additions or in-place line swaps inside the new blocks. No existing prose was rewritten.
- **roadmap:** a dated 🔑 callout at the top of *FIRST daylight job*. Auto-stamp dropped by user
  decision; fix part 2 and the `StepStatusStamped` gate no longer apply to the date; part 1 (guard the
  gets) still does; v007 design is kept in its script.
- **HANDOVER block, as committed:**

> ## Status, updated 2026-09-24
> - **1. Trigger flow**: **v008 is LIVE** (hash-confirmed by `intake` at 21:10), but the flow is
>   still **OFF**. v006 = user's own edit, pulled 20:12, replaced by v008 at 21:10. v007 = keep-a-typed-date
>   design, **superseded, never pasted** (`forked` in history.json). v008 = v006 + connection reference +
>   no Status Date read/write, `applied` 21:10, one connection reference in the export, `_1` gone.
>   Order from here: tests, then enable.
> - 🔑 **Status Date stays MANUAL**, user decision 2026-09-24. `apply_v006_status_date_preserve.py` is moot.
> - **Connection-reference incident:** the password reset moved only the trigger flow's trigger onto
>   `shared_sharepointonline_1`. Fixed: v008 is on `new_sharedsharepointonline_89e9a`, confirmed live
>   21:10. The four N3 flows are clean. Unknown: whether they *ran* on 09-24.
> - **Drift tools:** x25 (find), x22 overwrite mode (repair), x24 (optional), x16 (mirrors). Clients →
>   unit can't be measured (E3).

  *(Condensed here; the file has the full wording.)* **Not edited:** CLAUDE.md. Nothing for DECISIONS.
- Next: **claiming E3.** Step 1 is read-only: find the source column, then post the full `Cli*`
  source→target table here before authoring anything.

**2026-09-24 21:5x | `claude-5b` |** **E3 step 1 done. The evidence says the flow reads the RIGHT
field. Nothing authored; raising this before anyone acts on it.**
- **Source→target table** (the whole Cli map, 1 field, from `gen_n3_flows.py:194` and the 20:54 pull):

  | Clients (source, internal) | type | display | → Order Items (target) |
  |---|---|---|---|
  | `CliLeadTimeWeeks` | Number | Lead Time (weeks) | `CliLeadTimeWeeks` (display "Client - Lead Time (weeks)") |

- **How verified:** I parsed the `ListSchema` record of `sharepoint-lists/Clients 2026-09-10 1734.csv`
  (12 `<Field>` entries; parser in the scratchpad, since `load_exports.py` drops the schema rather than
  parsing it). It contains `Name="CliLeadTimeWeeks" Type="Number" DisplayName="Lead Time (weeks)"` and
  **no `Lead Time` column at all**. The same internal name on both lists is by design: `n5_clients_lead_time.js:257`
  (Clients) and `:268` (Order Items) both create `CliLeadTimeWeeks`. The export (17:34) postdates n5's
  internal-name fix `786c01f` (17:27) and the 17:36 "17 of 17 live" commit `d0712db`. 17 of 99 clients
  hold a value.
- **Why 09-21 parked item 4 is probably wrong:** `n3-fanout-race-2026-09-21.md:220` takes the source
  as `Clients.Lead Time` "per the N3 spec". `Lead Time` is on **Order** (`Order.Lead Time`, roadmap
  #45), not on Clients. That doc's own ⚠️ asked for exactly this check before fixing.
- **What explains "Cli* blank everywhere" instead (hypothesis, not verified):** the 17 clients were
  seeded 09-10 ~17:3x, and the Clients flow was built at 17:44 (v001/v002 timestamps). A
  created-or-modified trigger never saw the seed, and no backfill copied it to the units. Supporting
  evidence: the 09-16 `Order Items (1).csv` has **2 of 1,085** units with `Client - Lead Time (weeks) = 18`.
  That looks like the flow writing on a later client edit.
- **Proposed next steps, for `claude-43`/user to decide:** (a) a live read-only confirmation, run
  signed in: `_api/web/lists(guid'3bcf7d97-0862-404d-ab3f-eeaa358c05d8')/items?$select=Id,Title,CliLeadTimeWeeks&$top=100`.
  A 200 with ~17 values confirms it; a 400 means I'm wrong. Optionally, one client's run history
  after an edit. (b) If confirmed, **E3 becomes a backfill, not a flow fix**: lift `Cli` out of x22's
  `SKIP_GROUPS` for one blank-fill run over units of the 17 clients (or touch the 17 clients once
  now that the N3 flows are healthy). Also correct `n3-fanout-race-2026-09-21.md` §*third bug* and
  parked item 4, the board's KEY FACTS "Clients → unit" line, and x22's `SKIP_GROUPS` comment.
  **No apply script is needed**, so there's nothing to hand over for `stage`.
