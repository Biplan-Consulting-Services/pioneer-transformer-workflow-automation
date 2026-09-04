# Build-night records

Coordination boards and handovers from the multi-session build nights, harvested here on
2026-09-04 because **they were in no git repo at all** — 232 KB of the only record of two
nights' decisions, living on one disk with no history and no backup.

That was not an oversight so much as a gap nobody owned: the boards are written at
`Clients/Pioneer Transformer/`, which is a plain folder above three separate repos. Every
session read them, no session could commit them.

| File | What it is |
|---|---|
| `BUILD-NIGHT-STATUS.md` | 2026-09-01, night 1. Archived — **do not append.** |
| `BUILD-NIGHT-2026-09-03.md` | 2026-09-03/04, night 2. The **evidence**: every claim with how it was verified, in an append-only event log. |
| `BUILD-NIGHT-2026-09-03-SUMMARY.md` | Night 2's handover — the read-in-the-morning version. The board stays the evidence. |

## Why keep the boards and not just the summaries

Both nights turned on the same failure: something reported as fact without being checked. Night
1's board says `A6 LAUNCHED BY THE USER`; it had not been, and the whole of night 2 existed to
undo the consequences. The boards are where the corrections live, including the ones where a
session retracted its own reported result. That is the part worth keeping — a clean summary of
outcomes loses exactly the information that would stop it happening again.

Night 2's log records three claims reported as fact and later found wrong, deliberately, with
who found each and how.

## Where these are the authority, and where they are not

**The boards outrank the repo docs on live state**, and by a wide margin on 2026-09-04. The docs
were written ahead of steps that were then cut, so several describe an intended end state as
though it had happened. Night 2 corrected the load-bearing ones in place — see the
`cutover-runbook-2026-09-01.md` header, `FRM10-12/CLAUDE.md`'s `viewer/` entry, and the
do-not-circulate banners on both staff guides — but treat any uncorrected doc as a plan, not a
status report.

**They are a snapshot, not a live feed.** They stopped being updated when the sessions ended.
Anything about the tenant should be re-read from the tenant.

## Two copies, on purpose — do not delete either

Each of these files exists in **two** places:

| | Path | Role |
|---|---|---|
| **Working** | `Clients/Pioneer Transformer/BUILD-NIGHT-*.md` | What sessions open and append to |
| **Tracked** | `Workflow-Automation/docs/build-nights/` *(here)* | What survives the machine |

**This is structural, not an oversight.** The working path sits at `Clients/Pioneer Transformer/`,
a plain folder *above* all three repo roots, and git cannot track files outside a repo root. It
also cannot simply be moved: `~/.claude/session-tracks.json`'s `_night` field points at it, and
it is the path every session opens at registration. Delete it and that pointer breaks.

So the arrangement is a working file plus a committed snapshot, which is a normal shape. **The
bug was never the duplication — it was that the sync obligation was undocumented.** It is now
written at the top of each working copy:

```
cd "Clients/Pioneer Transformer"
cp BUILD-NIGHT-*.md Workflow-Automation/docs/build-nights/
# then commit + push from Workflow-Automation
```

**Which wins on a conflict:** the working copy is newer by definition; the tracked copy is
authoritative for *what actually survived*. If they disagree, the working copy has unharvested
appends — re-harvest rather than reconciling by hand. They also differ in line endings (working
LF, tracked CRLF after commit), so a raw `diff` reports every line as changed. **Compare
sections, not whole files.**
