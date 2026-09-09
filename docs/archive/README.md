# archive/ — superseded cutover documents

Moved here 2026-09-09. **The current runbook is `../CUTOVER-RUNBOOK.md`.**

These are kept, not deleted, because several carry decisions and measurements that are
still the only record of *why* something is the way it is. But none of them describes the
current plan, and between them they disagreed on what was done, what was decided, and what
happens next — which is what made a clean rewrite necessary.

Everything still load-bearing has been carried into `CUTOVER-RUNBOOK.md` and re-checked
against the repo or the tenant on the way. **Do not work from a file in this folder.**

| file | what it was | why it is here |
|---|---|---|
| `cutover-runbook-2026-09-01.md` | The five-track build-night plan for the 2026-09-01 presentation. The most detailed document ever written about this cutover, and the only one that carried real switchover mechanics. | Its own header, corrected 2026-09-03, says the block below it was wrong for two days. Written when `Order Items` had one writer; the app's fan-out makes two. **Carried forward:** the deploy-in-place decision (D5) and the three named refresh owners (D5b) — those live in Stage 3 of the current runbook. |
| `cutover-plan-2026-09-02.md` | A replacement plan written the day after. | Stamped `SUPERSEDED — do not work from this document` by its own author. Wrong premise, and it contains a mapping bug. |
| `handover-2026-09-08.md` | Session handover written 01:20, before the run. | Stamped superseded by the 07:25 handover. |
| `handover-2026-09-08-0725.md` | Its replacement. | Marked `CONTINUED` into the morning runbook below. |
| `RUNBOOK-2026-09-08-morning.md` | The most recent, and the narrowest: three scripts to run and a short open list. | Overtaken on two counts. It prescribes making the flow **create-only**, which the 2026-09-09 decision reverses — create-only would gut the update branch that is the entire purpose of the final run. And the R22 fix it points at was itself wrong (see `../r22-mapping-correction-2026-09-08.md`). Its three scripts and their figures are carried into Stage 1. |

## The status registers also disagreed

Worth recording, because it is the reason to distrust a tick:

- `../roadmap.md` — items 1–44, the master list.
- `../../artifacts/risk-register-tracker.html` `app-state` — 33 step ids.
- This folder's `RUNBOOK-2026-09-08-morning.md` — that morning's action list.

They conflicted in **both** directions. `P4` was ticked `done` and had never been taken.
`X1`/`X2`/`N8` read `todo` and were still `todo` — but only because they had not been run,
not because the register was tracking them.

The current board is `../../artifacts/cutover-state-board.html`
(https://claude.ai/code/artifact/3300b1d1-dc81-40a6-9d03-34a185649767), and it splits work
by **who can move it** rather than by phase.
