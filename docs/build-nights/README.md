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
