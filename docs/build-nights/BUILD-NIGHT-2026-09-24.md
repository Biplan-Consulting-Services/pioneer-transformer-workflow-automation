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
- **Clients → unit:** ~~not measurable, flow reads the wrong field~~ **corrected 21:1x** — the flow is
  right (`CliLeadTimeWeeks` is the source name too); `Cli*` is blank because the 17 valued clients were
  seeded before the flow existed. Fixed by U5 (x22 `CLI_FILL`), not by a flow change.
- **`Order Items` mirrors (`*_TextField`)** — `x16`. Self-heal on each unit's next edit once v008 is on.
- **Stamps** — `x24` dry run. Optional now that the date is manual; what it still affects is that
  Livraison units not yet `Terminé`/`Delivered` get completed on their next edit.

### x25 results — run by the user 21:2x, read by `claude-43` (P2)
**1,127 units. 0 drift on any parent modified since midnight → the outage left NO parent→unit drift.**
818 older unit-field mismatches on 738 units. The known `MdlLatestModelRevision` drift shows up (sanity
check passes). Classified from the full `window.x25.report`:

| group | what the values show | route |
|---|---|---|
| `MdlLatestModelRevision`, unit `M-…` vs parent `MR-…-V1` (~670) | the 09-21 known stale value | **x22 OVERWRITE**, filtered list |
| unit **blank**, parent has value — SA units (`22098/22107/22108/22110-1/1 SA`: all Mdl*/Rev*, `21613/21661/21664/21665/21749 SA`: Ord*), `21792-3/5`,`4/5`, `22169-7..10/10`, `22175-1/2`, `22112-1/3` | never filled | **x22 blank-fill** (plain run; combine with U5 `CLI_FILL`) |
| `OrdInitialPromisedDate` 18 / `OrdOrderDate` 14 — parent `…T00:00:00Z`, unit `…T04:00/05:00Z` **one day earlier** | ~~app-created orders stored UTC-midnight during the site-UTC period~~ **corrected by E7 (21:42):** only these **6 of 457** orders carry the `T00Z` shape; the same authors' other orders in that window are stored T04/T05Z, so it is **not** the app pattern — cause unknown. Real one-day difference. **E7 reading: the Order's (later) date was meant** | **DO NOT WRITE** — which date is right is decision 5 below |
| `OrdLDs` / `OrdEngineeringRequired`, unit `true`/`false`, parent **blank** (~40) | ~~parent side went blank in the N4 conversion window~~ **corrected by E6 (21:40):** LDs/EngReq are plain Yes/No and N4 never touched them; the 0339 export is local time (taken after those edits). **E6 reading: the Orders were never set; the units match FRM10-12 and are right** | **DO NOT WRITE** — decision 4 (x22 lists, never clears) + decision 6 |
| `22001-2/8` `OrdEngineeringRequired` unit `false` parent `true` | genuine | x22 OVERWRITE (1 field) |
| `E21007-1/1` unit says model `M-MEEN-0001`, lookup points at `M-MEEN-0005` | lookup and copy disagree on WHICH model | **DO NOT WRITE** — decision 7 |
| Models 391/392 → parent value `MR-ENMA-0052` / `-0053` with **no `-V1`** | parent-side data smell (x17 rule) | overwrite is still closer; flag for x17 |

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
| P2 | Interpret U3; decide repair route per parent (touch vs E1 overwrite) | `claude-43` | no | **DONE 21:3x (x25 part)** — see *x25 results* in KEY FACTS. x16 / x24 still to come |
| E1 | **x22 overwrite mode** — repair stale non-blank parent values from an x25 report | `claude-5b` | yes | **DONE `d489f5a`** — regenerated + `node --check` OK; mock-harness 6/6 (see log) |
| E4 | **x25 rows carry the unit `id`** — so x22's OVERWRITE matches exactly instead of by Title. ⚠️ **Do before E2:** U3 has not run yet, so this is free now and costs a user re-run later. Files: `scripts/gen_x25_drift_scan.py` → regenerate. Add `id: u.Id` to every `report.push` and to `perParent[k].units` (keep Title for humans). Verify: regenerate, `node --check`, diff stat, and confirm x22's OVERWRITE accepts the new rows as-is | `claude-5b` | yes | **DEPRIORITISED 21:3x** — user is running x25 now, so it would not land in time; x22 already aborts on ambiguous Titles. Do after E2/E3 if at all |
| E5 | **Decision 7 evidence — `E21007-1/1`: M-MEEN-0001 vs M-MEEN-0005, same model or duplicate?** Spec below | `claude-5b` | yes | **DONE 21:36**, log entry. Two different models, Models rows 0001/0005 crossed |
| E6 | **Decision 6 evidence — LDs / Engineering Required blank on the Order but set on its units.** Spec below | `claude-5b` | yes | **DONE 21:40 (files)**. Units right, Orders never set (reading); live confirmation = `x26` (user) |
| E7 | **Decision 5 evidence — the one-day date table (UTC vs Eastern).** Spec below | `claude-5b` | yes | **DONE 21:42**, log entry. Raw (later) date meant (reading); only 6 of 457 orders have T00Z |
| E8 | **SharePoint mirror workbook: a local, refreshable copy of the live lists, so sessions can validate without the user.** Spec below | `claude-5b` | yes | UNCLAIMED (added by `claude-43`, 21:5x, user request) |
| E9 | **Console scripts print failures + a summary only.** User 21:5x: "just paste the fails in the terminal because it bloats the pastes". x22 APPLY printed a `wrote <id> Cli*` line per unit (1,053 lines) | `claude-5b` | yes | UNCLAIMED, **do before E8** because the user runs x22 again tonight (RUN2) |
| E2 | **Docs: record today** — Status Date manual decision, v006/v008, connection incident | `claude-5b` | yes | **DONE `ba41132` + `7f59469`** — diff stat and block text in the log |
| E3 | **Clients flow reads the wrong source field** — find the real field, author the fix | `claude-5b` | yes | **RE-SCOPED 21:1x by `claude-43`** — premise WRONG, flow is correct: confirmed independently, `Clients 2026-09-10 1734.csv` has exactly one lead-time field, `CliLeadTimeWeeks` (Number, "Lead Time (weeks)"). No flow change, nothing to stage. New scope: Cli* blank-fill via x22 (lift Cli from SKIP_GROUPS for one run) + correct the 09-21 doc's parked item 4. **UNBLOCKED 21:1x** — U4 back, go |
| U4 | Browser, signed in: `https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/lists(guid'3bcf7d97-0862-404d-ab3f-eeaa358c05d8')/items?$select=Id,Title,CliLeadTimeWeeks&$top=100` — read-only. Expect 200 with ~17 clients holding a value | **user** | no | **DONE 21:17** — 200, **17 of 97** clients hold `CliLeadTimeWeeks` (16×3, 18×5, 20×7, 24×1 CONED, 28×1 HYDRO QUEBEC = FRM13's value). 80 are null — their units correctly stay blank. Pasted Atom feed, counted by `claude-43` |

### E5 / E6 / E7 — shared ground rules
All three are **read-only analysis for a user decision**. Nothing writes to the tenant. The output is a
table posted on the board (event log) that the user can decide from, plus a one-line reading of it,
**labelled as a reading, not a verdict** — the user decides. The source files, all on disk:
- `sharepoint-lists/Order 2026-09-11 0339.csv` — ⚠️ **taken BEFORE the N4 choice conversion (04:20) and
  probably before every parent in E6 was modified (04:27–05:12Z — reconcile the timezones first)**:
  the likely pre-change state
- `sharepoint-lists/Models 2026-09-11 0340.csv`, `Model Revisions 2026-09-11 0340.csv`, `Order Items 2026-09-11 0410.csv`
- `sharepoint-lists/Models dedup worklist 2026-09-05.csv` — check it for MEEN first (E5)
- `workbooks/FRM10-12 final staff version pre-archive 2026-09-11 0522.xlsx` — the last Excel the staff used
- `workbooks/Archive active.xlsx` (09-16) and `workbooks/Archive active 2026-09-10 2231.xlsx` — `TableArchiveFRM10_12`
- **current live values** come from the user's x25 run, quoted per task below. Anything else live →
  write a read-only console snippet for the user rather than guessing.
- Read CLAUDE.md's export traps first (ListSchema first record; lookups absent; exports follow the view).
- ⚠️ Timezones: x25 `modified` stamps are **UTC** (Z). The CSV exports print in the **site** timezone at
  export time — decision 6 of 09-04 says the site was set to UTC then; confirm from the file, don't assume.

### E5 — `E21007-1/1`: which model is it?
Live (x25): the unit's **Model lookup → Models id 463 = `M-MEEN-0005`** (latest rev `MR-MEEN-0005-V1`),
but the unit's copied columns say `MdlModelID = M-MEEN-0001`, `MdlLatestModelRevision = MR-MEEN-0001-V1`.
Parent 463 last modified 2026-08-13T17:37:46Z.
**Produce:** a side-by-side of Models `M-MEEN-0001` vs `M-MEEN-0005` and Model Revisions `MR-MEEN-0001-V1`
vs `MR-MEEN-0005-V1` — every non-empty column, differences marked. Plus: which one the unit's
`ModelRevision` lookup points at (Order Items export), what FRM10-12 / Archive say the model is for
`E21007`, and whether either appears in the dedup worklist. Question the user needs answered:
**same transformer entered twice, or two genuinely different models?**

### E6 — LDs / Engineering Required: was the Order blanked, or cleared on purpose?
Live (x25): the Order is **blank**, the units hold a value. Every parent was last modified 2026-09-11
04:27–05:12Z (the cutover night, just after N4 at 04:20 local — ⚠️ reconcile local vs Z before claiming
order of events).
- `OrdLDs`, units `true`: orders 21982, 21665, 21661, 21981, 22022, 22023, 22024, 22025, 22026, 22027,
  22028, 22029, 22030, 21664, 21932
- `OrdLDs`, units `false`: 21499, 21523
- `OrdEngineeringRequired`, units `false`: 22111 (units 5/10, 6/10), 22088, 22046, 22047, 22048, 22049,
  22050, 22051, 22052, 22053
- (reverse, for completeness — unit blank, Order has a value: `21613` LDs true / EngReq false, `21749` LDs true)
**Produce, per order:** value in the 03:39 Order export · value in FRM10-12 final staff version ·
value in Archive active (both copies) · current live (blank) · did the order exist in Excel at all.
Also: how many Orders list-wide are blank on LDs / EngReq now vs in the 03:39 export — is this ~20
orders or the whole column? That number decides "the conversion wiped it" vs "someone cleared a few".

### E7 — the one-day date table
Live (x25), unit value vs Order value:
| order | field | unit | Order |
|---|---|---|---|
| 22140, 22141 | Initial Promised | 2027-03-25T04:00Z | 2027-03-26T00:00Z |
| 22156 | Initial Promised / Order Date | 2027-01-17T05:00Z / 2026-08-31T04:00Z | 2027-01-18T00:00Z / 2026-09-01T00:00Z |
| 22157 (10 units) | Initial Promised / Order Date | 2027-01-21T05:00Z / 2026-08-31T04:00Z | 2027-01-22T00:00Z / 2026-09-01T00:00Z |
| P00005 | Initial Promised / Order Date | 2025-12-30T05:00Z / 2026-09-02T04:00Z | 2025-12-31T00:00Z / 2026-09-03T00:00Z |
| P10003 | Initial Promised / Order Date | 2026-09-03T04:00Z / 2026-09-02T04:00Z | 2026-09-04T00:00Z / 2026-09-03T00:00Z |
**Produce one table**, per order, everything that helps the user tell which calendar date was *meant*:
Order `Created` + `Author` (app vs human), the Order value as the 03:39 export printed it, the unit value
as the 04:10 Order Items export printed it, the FRM10-12 final staff version value, the Archive value,
and the weekday of each candidate date (a promised date on a Sunday is a tell). Also list whether ANY
other order has the same `T00:00:00Z` shape — if every app-created order does and no hand-entered one
does, that is the pattern, and say so.
⚠️ `P00005` Initial Promised 2025-12-30/31 is **before** its Order Date — flag it, it is odd either way.

### E9 — quiet console output
**Rule for every console script the user pastes (x22 first, then x25, x24, x16, x26):**
- **Print by default:** the summary and counts; every FAILURE or ABORT with enough detail to act on;
  and anything that needs a human decision.
- **Do not print by default:** per-row success lines (`wrote 1179 Cli*`) or per-unit plan blocks (x22's
  `--- Id 1223 ---` sections). Put them behind `const VERBOSE = false;`.
- **Full detail:** keep it available on `window.<script>` for `copy(...)`, as x25 already does, so
  nothing is lost. Only the terminal gets shorter.
- A dry run still shows **a sample** (first ~10 planned writes) plus the totals. That sample is what
  makes a dry run checkable.
**Priority: x22 now.** The user's next paste is RUN2 (~740 writes). If x22 changes, tell `claude-43`
before the user pastes it.
**Verify:** `node --check`, re-run the mock harness, and diff the default-mode output line count
before and after on the harness.

### E8 — SharePoint mirror workbook (user request, 2026-09-24)
**Goal, in the user's words:** "that way you can always validate yourself". Sessions should read LIVE
list state from disk instead of asking the user for exports and console pastes.

**Approach agreed: Power Query, not the list's *Export to Excel* (.iqy).** The .iqy follows the current
VIEW (the 09-05 3-row BO Tracking trap) and gives lookups as display text with no id. Power Query
`SharePoint.Tables` reads the list itself, and returns lookup ids and values.

**Build:**
- `workbooks/SharePoint mirror.xlsx`: one query per list, loaded to a table. The lists are Order Items,
  Order, Models, Model Revisions, Clients, Index, plus Models SA if cheap.
  - Reuse FRM10-12's M (`FRM10-12/power-query/`: the `SharePoint.Tables` source,
    `FlattenSharePointLookupLists`) rather than writing new M.
  - Keep lookup **ids** as well as values (`<Field>Id`), because x22/x25 join on the id.
  - Keep `Id`, `Created`, `Modified`, `Author`, `Editor`.
  - Keep raw date values. Do **not** convert timezones in M; note what comes back.
  - Track the M under `power-query/SharePoint mirror/` with `Export-PowerQuery.ps1`.
- `scripts/Refresh-SharePointMirror.ps1`: opens the workbook via COM, runs `RefreshAll()`, waits for
  completion with a timeout, saves, and writes each table to
  `sharepoint-lists/{List} {YYYY-MM-DD} {HHMM}.csv` (existing convention; superseded files → `Archive/`).
  `RefreshAll` is fine on THIS workbook; the ban is FRM10-12-specific (CLAUDE.md, memory).
  - Abort on a zero-row table. A zero-row read is a failed read.
  - Print row counts per list.
  - ⚠️ Check `load_exports.py` still reads the output. These CSVs have no `ListSchema` first record,
    so either make the loader tolerate both shapes or write a separate folder. Say which.
**Acceptance (the dates are the test):**
1. Row counts match live: Order Items 1127, Order 470, Models 394, Model Revisions 395, Clients 99
   (x25 / U4 tonight).
2. Unit `22157-1/10` Order Date and Order 559's Order Date come back exactly as x25 saw them
   (`2026-08-31T04:00:00Z` vs `2026-09-01T00:00:00Z`), or the shift is explained and documented.
   If PQ silently normalises the timezone, the mirror cannot see the E7 defect. Find that out
   before anyone trusts it.
3. Lookup id present for Order Items → Order / Model / Model Revision / Client.
4. `Cli*` shows tonight's fill (e.g. any HYDRO QUEBEC unit = 28).
**Needs the user once:** the first refresh prompts for SharePoint credentials (Organizational
account). Post BLOCKED at that step with the exact prompt they will see.

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

| 5 | 32 order dates differ by one day between Order (UTC midnight) and its units (Eastern midnight, day before) on 22140/22141/22156/22157/P00005/P10003. Which is the intended date? Check one order in the app or with sales | open — nothing written |
| 6 | ~40 units hold `LDs`/`Engineering Required` = true/false where their Order is now blank (parents modified in the 09-11 N4 window). Was the Order blanked by the conversion (units right) or cleared on purpose (units stale)? | open — nothing written |
| 7 | `E21007-1/1`: its Model lookup is `M-MEEN-0005` but its copied model data is `M-MEEN-0001`. Which model is the unit? | open — nothing written |
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

**2026-09-24 21:18 (`date`) | `claude-5b` |** ⚠️ **Timestamp correction:** my entries above stamped
21:2x / 21:4x / 21:5x were estimated, not read from the clock. The machine clock says 21:18 now, so
they all fall between 21:06 and 21:18. Commit times in `git log` are the reliable record. From here
on, stamps come from `date`.
**E3 resumed (U4: 200, 17 of 97 clients hold a value).** Intent:
1. **x22:** add `CLI_FILL = false` (opt-in, off by default). `SKIP_GROUPS` is untouched. When it's on,
   the run ignores `UNITS`/`OVERWRITE` and blank-fills **only** the `Cli*` group across the whole list. It
   reads units with `$select=Id,Title,ClientId,<Cli targets>`, resolves each client by **lookup id**
   (never Title, because of the `§` titles), and writes only where the unit is blank AND the client has a value.
   The dry run asserts "skipped N units: parent CliLeadTimeWeeks null", prints a units-per-client table,
   aborts on zero-row reads, aborts if both CLI_FILL and OVERWRITE are set, and reads back after APPLY.
2. **`n3-fanout-race-2026-09-21.md`:** targeted correction notes on §*third bug* and parked item 4,
   with the original text kept.
3. x22's `SKIP_GROUPS` comment, then regenerate, `node --check`, a mock-harness run, and commit + push.

**2026-09-24 21:20 (`date`) | `claude-5b` |** **E3 authored and pushed, `f7a51eb`.** The live run is the
user's (dry run first).
- **Verification:** regenerated, `node --check` OK. The mock harness passed **15/15**: the 9 E1
  assertions, plus a check that a normal run never writes Cli, plus 5 new ones. A CLI dry run
  writes nothing. APPLY wrote exactly the 3 blank units whose client has a value (`18`, `18`, and
  `20` for the `LG§E` client, matched by id). Units that were already set, had a null parent, or
  pointed at a missing client were untouched. Only `CliLeadTimeWeeks` was written. CLI_FILL together
  with OVERWRITE aborts with 0 reads. Diff stat: gen/x22 81 lines each (identical), 09-21 doc +12, HANDOVER 5; 167+/12− in total.
- **Also corrected:** the 09-21 doc (a correction callout on §*third bug* and on parked item 4, with
  the original text kept) and **my own** HANDOVER 09-24 block, which repeated the wrong claim.
- **Still stale, not mine to edit:** the board's KEY FACTS "Clients → unit: not measurable" line
  (`claude-43`), and the `x25` header's "Clients is not scanned: its flow reads the wrong field". The
  x25 header is generated by `gen_x25_drift_scan.py`, so fix it at the next regenerate, not while
  x25 is in the user's hands.
- **User run instructions (U5):**
  1. Open `…/PioneerPlanificatio/_api/web/currentuser`, signed in, then F12 → Console.
  2. Open `scripts/x22_repair_parent_sync.js` and change **`const CLI_FILL = false;` → `true`**. Leave
     `DRY = true` and `OVERWRITE = null`. Paste the whole file and press Enter. It writes nothing.
  3. Read the output:
     - The **units-per-client table** should have HYDRO QUEBEC largest.
     - `skipped N units: parent CliLeadTimeWeeks null` should be most units (80 of 97 clients are null).
     - `skipped N units: … already set` should be small (~2 on the 09-16 export).
     - `=== K writes planned ===`.
     - Any ⚠️ missing-client line.
     Paste it back for `claude-43`.
  4. If it looks right, set `DRY = false` and paste again. It writes and then reads back.
     Expect `✅ every written field verified` and a per-field tally of `written = verified = K`.
  5. **Set `CLI_FILL` back to `false`** afterwards (or just don't save the edit; the committed file stays `false`).
- ⚠️ Writing K units fires the Order Items trigger flow K times if it's enabled. It's OFF tonight,
  so that's fine now. Run U5 **before** enabling it, or accept K trigger runs.

**2026-09-24 21:3x | `claude-43` | P2 (x25) DONE.** Read the user's full `window.x25` paste (818 rows,
73 parents). Outage drift = 0. Classification and routes in KEY FACTS *x25 results*; three new
decisions (5–7) for anything where the right value is unknown. Corrected my own earlier stamps
(22:0x / 22:2x were guesses; the U4 feed is stamped 01:17Z = 21:17) and the stale KEY FACTS Clients line.

**2026-09-24 21:23 (`date`) | `claude-5b` |** **P2's x22 recipe checked. (b) FAILED, now fixed in `615b7f3`.**
- **(a) blank unit field written in OVERWRITE:** ✅. A listed field skips the blank test, so a blank
  unit value is written from the live parent.
- **(b) `const OVERWRITE = window.x25OV;` with a bare `[{unit, field}]`:** the array form works ✅.
  **But if `window.x25OV` was never assigned (a skipped step, or a fresh console tab), OVERWRITE was
  `undefined`, and x22 silently fell back to blank-fill over the hard-coded `UNITS`.** I reproduced
  that against HEAD in the harness: it started reading units 1223 onward. **Fix:** `undefined` now
  aborts ("the window variable it points at was never set"). Off is `null` only.
- **(c) Titles `21665-1/3 SA`, `P21911_A_bu-1/1`:** ✅. They match by exact raw string. A near-miss
  decoy `21665-1/3` was NOT matched.
- **Verification:** regenerated, `node --check` OK, mock harness **18/18**. New case J is the exact
  P2 recipe via a window variable: 2 PATCHes, `OrdPO` only, on the two odd-Title units. New case K is
  the unset variable: abort, 0 reads, 0 writes.
- **For the user:** the recipe is fine as written. Make sure it runs in the same console tab as
  `x25`, before x22 is pasted. If it isn't, x22 now stops with that message instead of doing the wrong run.

**2026-09-24 21:4x | `claude-43` |** Added **E5 / E6 / E7** at the user's request ("use the other claude
session to help"): read-only evidence tables for decisions 5–7. Assigned to `claude-5b`. Nothing in
x22's OVERWRITE list touches any of those rows — the filter excludes dates, blank-parent rows and E21007.

**2026-09-24 21:36 (`date`) | `claude-5b` |** **E5 DONE: `E21007-1/1`, M-MEEN-0001 vs M-MEEN-0005.** Read-only.
Sources: `Models`/`Model Revisions 2026-09-11 0340.csv`, `Order Items 0410.csv`, dedup worklist 09-05,
FRM10-12 final staff 0522, `Archive active` (09-16) and `Archive active 2026-09-10 2231`. The CSV
stamps carry `Z`, so they're UTC as printed. Scripts are in my scratchpad (`e5_explore.py`, `e5_meen.py`).

**The two MODEL rows (Models 0340)**. Every other non-empty column is identical: MEG Energy, Substation,
3 ph, SFRA Y, Up to Date, created 05-04 by soleil.anker, modified 2026-08-13T17:37:46Z (all five MEEN
models share that stamp, a bulk edit).
| | M-MEEN-0001 (id 459) | M-MEEN-0005 (id 463) |
|---|---|---|
| **Model_Code** | 1147005 | **1147005** ⚠️ same |
| **kVA and kV** | **1,500** | **7,500** |
| Latest rev | MR-MEEN-0001-V1 | MR-MEEN-0005-V1 |

**The two REVISION rows (Model Revisions 0340)**. Otherwise identical (Substation, ["SUBSTATION"], 3 ph).
| | MR-MEEN-0001-V1 (id 100) | MR-MEEN-0005-V1 (id 104) |
|---|---|---|
| **Client_Model_Code** | 1147005 | **1147012** |
| **kVA** | **7,500** | **1,500** |

➡️ **The lists contradict each other on this pair.** Revisions show two distinct transformers: 1147005 at 7,500
and 1147012 at 1,500. Models give both the code 1147005, with the kVA **swapped** against their own revisions.
The other three MEEN pairs (0002 = 1147006/2,500, 0003 = 1147007/2,500, 0004 = 1147011/7,500) agree
across both lists. **The 09-05 dedup worklist already flags exactly this pair**: `REVIEW`, "kVA and kV →
kVA", 0001 Models 1,500 vs Revisions 7,500, and 0005 Models 7,500 vs Revisions 1,500.

**What the staff's Excel says** (FRM10-12 final 0522 and both Archive copies agree). Every MEG Energy row:
| unit | PO Item # | kVA | PO |
|---|---|---|---|
| **E21007-1/1** | **1147005** | **7500** | MEG-10027 |
| E21005-1/1 | 1147005 | 7500 | MEG-10027 |
| **E21012-1/1** | **1147012** | **1500** | MEG-10012 |
| E21005A-1/1 | **1147005** ⚠️ | **1500** ⚠️ | MEG-10012 |
| E21006-1/1, 1/2, 2/2 | 1147006 | 2500 | MEG-10027 |
| E21011-1/1 | 1147011 | 7500 | MEG-10012 |

`E21005A` is the only row where 1147005 comes with 1,500 kVA. It sits on the 1147012 PO (MEG-10012) with the
1147012 rating, so it looks like a mistyped item number. **It reproduces exactly the Models list's
"1147005 at 1,500" entry.** Reading: that typo is probably where M-MEEN-0001's crossed values came from.

**The unit itself (Order Items 0410)** is split three ways:
| column | says |
|---|---|
| `Model` **lookup** (displays Model_Code) | 1147005 → `Model_ID_TextField` **M-MEEN-0005** (id 463, as live x25) |
| `Model Revision` **lookup** | **MR-MEEN-0001-V1** (1147005, 7,500) |
| copied `MdlModelID` / `MdlLatestModelRevision` | **M-MEEN-0001** / MR-MEEN-0001-V1 |
The other 3 live MEEN units are all consistent (E21006 ×2 → 0002, E21011 → 0004). E21005, E21005A and
E21012 are not in Order Items 0410.

**Reading, not a verdict:** **two genuinely different transformers, not a duplicate.** 1147005 is 7,500
kVA (E21005, E21007). 1147012 is 1,500 kVA (E21012). E21007 matches **MR-MEEN-0001-V1** on code and kVA.
Its Model lookup → 0005 looks like a consequence of the Models list's crossed 0001/0005 rows: on the
Models list, 0005 "looks like" 1147005 at 7,500, which is E21007's spec. If the user agrees, the fix is
**data on the Models list** (0005 → 1147012 / 1,500, 0001 → 7,500; the worklist's REVIEW item), then
repoint E21007's Model lookup to 0001. That's their decision, and nothing has been written. **Open question
for someone who knows the job:** E21005A's PO Item # 1147005. Should it read 1147012?

**2026-09-24 21:40 (`date`) | `claude-5b` |** **E6: file evidence DONE. One live number needs the user
(`x26`, read-only, pushed `bd3d09d`).**

⚠️ **Two premises in the E6 spec are wrong. The timeline, reconciled:**
| when (UTC) | = EDT | event | evidence |
|---|---|---|---|
| 04:27–05:12Z | 00:27–01:12 | the E6 Orders' last `Modified` (soleil.anker) | same stamps in the 0339 export and in live x25 |
| ≥05:16:32Z (07:39Z) | 03:39 | **`Order 0339` export taken** | its latest `Modified` is 05:16:32Z, so "0339" is local time |
| 08:09Z → 08:20Z | 04:09 → 04:20 | N4 schema saved, Choice conversion | commits `136db9e`, `bca550c` (−0400) |
- The export is **after** the parents' edits, not before them. The edits happened **~3 h before N4**, not "just after".
- **N4 never touched LDs or Engineering Required.** Both are plain Yes/No (`column-reference.md`: Boolean).
  They aren't in N4's targets, and `gen_n3_flows.py` maps them as `plain`. So the "N4 window" link doesn't hold.
- The E6 Orders have **not been modified since the export** (same `Modified` stamps), yet x25 reads them blank today.

**Why the 0339 export can't answer "blank then?"** A Yes/No that was never set is **NULL** over REST
(x25 reports that as blank). The export shows LDs 416 False / 41 True / **0 blank** and EngReq 353 / 104 / **0**.
So it renders NULL as False. "False at 03:39" and "blank now" are very likely **the same NULL**, with
nothing changed in between.

**Per order.** Excel columns show the distinct values across the order's unit rows. `None` is an empty cell;
the `… SA` rows are always empty.
| order | x25 group | 0339 Order LDs / EngReq | FRM10-12 final (0522) | Archive 09-10 | Archive 09-16 |
|---|---|---|---|---|---|
| 21982 21665 21661 21981 21664 21932 | LDs, units true | False / True | **LDs Y** on each main unit row | LDs Y | LDs **None** |
| 22022 22023 22024 22025 22026 22027 22028 22029 22030 | LDs, units true | False / False | **LDs Y** | LDs Y | LDs **None** |
| 21499 21523 | LDs, units false | False / True | **LDs N** | LDs N | None |
| 22111 | EngReq, units 5/10, 6/10 false | False / False | **EngReq N on exactly 5/10 and 6/10**, None on the other 8 | same | None |
| 22088 22046–22053 | EngReq, units false | False / False | **EngReq N** | N | None |
| 21613 21749 (reverse) | unit blank, Order has a value | **True** / False, True | LDs Y | Y | Y |
All 29 orders exist in FRM10-12 final and in both Archives.

**Reading, not a verdict:** **the units are right, and the Orders were never set, not wiped.** The units
match the staff's final Excel value for value and unit for unit. The strongest signal is 22111: only 5/10
and 6/10 carry `N`, exactly as in Excel. So the units were filled from Excel per unit. The Order-level Yes/No
disagreed with Excel **already at 03:39** (False where Excel says Y), which fits a NULL that was never
populated at Order level. It is not a whole-column wipe: 41 True / 104 True survived in the export, and x25
flags only ~27 orders. **The 09-16 Archive has lost most LDs values**, so don't use it as evidence (that's a
separate post-cutover sync question).
**Needs the user:** run `scripts/x26_order_flag_history.js` and `copy(window.x26)`. It gives the **live
true / false / NULL counts** list-wide, which is the "20 orders or the whole column" number, and **each E6
order's version history**. NULL in every version = never set, which confirms the reading. true → NULL by a
person = cleared on purpose, which overturns it.

**2026-09-24 21:42 (`date`) | `claude-5b` |** **E7 DONE: the one-day date table.** Read-only. Sources:
`Order 0339` (taken 07:39Z; stamps printed in `Z`), `Order Items 0410`, FRM10-12 final 0522, Archive 09-10
and 09-16. **All three Excel sources agree with each other, and with the units, on every row.**
| order | created (UTC) · author | field | **Order raw (0339)** | units (0410) = FRM final = both Archives |
|---|---|---|---|---|
| 22140, 22141 | 08-25 14:05 / 14:13 · patrick.vaillancourt | IPD | **2027-03-26 Fri** `T00:00Z` | 2027-03-25 Thu |
| | | OD | 2026-08-03 Mon `T04:00Z` (fine) | 2026-08-03 Mon |
| 22156 | **09-01** 15:46 · patrick.vaillancourt | IPD | **2027-01-18 Mon** | 2027-01-17 **Sun** ⚠️ |
| | | OD | **2026-09-01 Tue** = creation day | 2026-08-31 Mon (a day *before* creation) |
| 22157 (10 u) | **09-02** 13:40 · patrick.vaillancourt | IPD | **2027-01-22 Fri** | 2027-01-21 Thu |
| | | OD | **2026-09-01 Tue** | 2026-08-31 Mon |
| P00005 | **09-03** 17:21 · dominic.lague | IPD | **2025-12-31 Wed** ⚠️ | 2025-12-30 Tue ⚠️ |
| | | OD | **2026-09-03 Thu** = creation day | 2026-09-02 Wed (a day before creation) |
| P10003 (2 u) | **09-03** 19:00 · patrick.vaillancourt | IPD | **2026-09-04 Fri** | 2026-09-03 Thu |
| | | OD | **2026-09-03 Thu** = creation day | 2026-09-02 Wed (a day before creation) |

**Is the `T00:00:00Z` shape the app-created pattern? No. It's exactly these six orders, 6 of 457.** The
same two people created 22138–22155 and 22158–22166 in the same window (08-21 → 09-10), and every one of
those is stored as proper Eastern midnight (`T04`/`T05Z`). Author doesn't separate them, and all are human
accounts, since the app writes as the user. The creation time doesn't cleanly separate them either:
22142 was created 26 min after 22141 and is `T05Z`. **Cause unknown**; the version history of one of the six
would show which edit wrote `T00Z`.

**What the difference really is:** `…T00:00Z` on a Date-Only column is UTC midnight. On the now-Eastern site
it's the **previous evening**, so **SharePoint currently DISPLAYS the Order as the earlier date too**
(22156 shows 08-31). The units and Excel hold that displayed date as proper Eastern midnight. So "one day"
is real in raw storage, but on screen both lists show the earlier date today. Anything that slices the raw
UTC string gets the later date: `x22`'s `asDate` would, and so would a flow `formatDateTime` without a timezone.

**Reading, not a verdict: the LATER date (the Order's raw calendar date) is the one that was meant.** Units,
Excel, and today's SharePoint display are all one day early.
- **Order Date equals the creation day in 3 of 3 checkable cases:** 22156 created 09-01 → 09-01, P00005 and
  P10003 created 09-03 → 09-03. The earlier copies put the order date a day *before* the order existed.
  The 34 correctly stored orders in the window also carry OD = their creation day (e.g. 22144–22155
  created 08-31 → 08-31).
- **Weekday:** 22156's earlier IPD is a **Sunday**; the raw one is a Monday. The others are weekday either way.
- If the user agrees, the fix is on the **Order**: rewrite the six rows' dates as bare `yyyy-mm-dd` of the
  raw date, so they store as Eastern midnight and display correctly. Then the units follow. **Not** an x22
  overwrite in either direction. Nothing has been written.
⚠️ **P00005:** its Initial Promised Date (2025-12-31 raw, 12-30 displayed) is **~8 months before its own
Order Date** (2026-09-03) under either reading. Possibly a year typo (2026-12-31?). It's a question for
whoever entered it (dominic.lague).

**2026-09-24 21:4x | `claude-43` |** Corrected my two KEY FACTS *x25 results* rows that E6/E7 contradicted
(the "site-UTC period / app pattern" and "N4 conversion window" claims were both wrong — mine, not the
data's). Relayed E5–E7 readings to the user; decisions 5–7 stay open for them.

**2026-09-24 21:5x | `claude-43` | U5 / E3 DONE: Clients lead-time fill APPLIED by the user.** x22 `CLI_FILL = true`, `DRY = false`. Read-back: `CliLeadTimeWeeks` **1053 written / 1053 verified / 0 failed**, matching the dry run exactly (17 clients; 70 units parent-null, 2 already set, 2 no Client lookup). The Order Items trigger flow was OFF throughout. The four sync flows stayed on: they trigger on parent lists, and x22 writes only Order Items.

**2026-09-24 21:5x | `claude-43` |** Added **E8** (SharePoint mirror workbook) at the user's request, so
sessions can validate live state themselves. I chose Power Query over the .iqy Export-to-Excel because
the .iqy is bound to a view and loses lookup ids. The user can overrule that choice.

**2026-09-24 21:5x | `claude-43` |** Added **E9** (quiet console output) at the user's request, ahead of E8,
because the user pastes x22 again tonight for RUN2.
