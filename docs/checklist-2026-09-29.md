# Restart checklist — written 2026-09-28 14:20, for the next session

**Start here.** It supersedes `checklist-2026-09-25.md` for current state. The live to-do list is the
**Punch List** artifact (https://claude.ai/artifact/R3Pvo8aimdFqCuFRJNQgdj, db collection `items`).
Update items there with ArtifactData; never rebuild it.

## First thing, every session
1. Refresh the mirror: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Refresh-SharePointMirror.ps1`.
   Exit 1 only means health has red items.
   - Expected reds after 09-28: the deleted `test calculated column` (it shows as a schema change, a bulk change
     and an erased value on 1,128 rows) and the 3 deleted test clients. All are intentional, done by the user.
   - Models 503's whitespace amber should be gone (fixed 09-28).
2. Ask the user for the Nightly Sync `C7_Summary` from the 01:30 run.

## Live state (confirmed 2026-09-28)
| thing | version | state |
|---|---|---|
| Nightly Sync | v007 | live, hash-confirmed; `DeleteEnabled=false`; gates on `TableArchiveOrderItems`; stage D recycles empty rows |
| Trigger flow | v009 | live 14:10, hash-confirmed. A move **out** of Livraison sets Delivered back to Active (step status untouched). Livraison still forces Terminé + Delivered. Live-tested on 21777-1/1 in both directions |
| Archive active | viewer-free | reads SharePoint directly. `TableArchiveFRM10_12` is loaded to the sheet (not the Data Model), 111 cols (93 + 18 BO). Archive BO sheet and query deleted |
| Trigger flow checks | done | no loop (max 2 flow writes in a row, 236 writes checked), never writes Status Date, model-less units OK, stray connection deleted |

Dry run 09-28: 54 candidates, 0 confirmed, all "edited within 7 days". This matches the replay, and the Modified text forms match.
First eligible nights: **10-02** 20 units (21777-1/1 moved there by the 09-28 test), 10-03 12, 10-06 22.

## User's request for the next session (2026-09-28)
**Plan a workspace organisation and cleanup, with mechanisms to keep it clean.** Present the plan first and
build nothing until the user approves it. Punch List item `ws-cleanup-plan` has the sizing: 73 top-level docs,
129 scripts, 14 uncommitted or untracked paths. Put it next to the Nightly Sync summary review.

## Next steps, in order
1. **Review tonight's `C7_Summary`.** Expect 0 confirmed.
2. **09-30:** refresh the mirror, then the user refreshes Archive active, then sets `DeleteEnabled=true`
   (one value in Settings). The first real deletions come 10-02. Watch that run's summary and the recycle bin.
   ⚠️ Nothing refreshes Archive active automatically. v007 only deletes units whose archived row is current,
   so deletes stall (safely) until someone refreshes it.
3. **Save Conflict retry** on the four N3 sync flows' Update_unit actions. The user deferred it on 09-28. Author it
   locally, snapshot, stage and paste, as usual.
4. Other Claude-side work that needs only the mirror: tune the bulk-change alert (`h-bulk-alert`), add the
   invalid-choice and stamp-drift checks (`h-more-checks`), measure the parent `_TextField` drift (`h-parent-mirror-drift`).
   Record in HANDOVER and roadmap that the trigger flow is ON, v009 (`tf-docs-state`).

## Waiting on the user or staff
- The **completed-Orders removal** design: `docs/order-completion-removal-research-2026-09-28.md`, 6 open questions.
  Q2 is answered: the Order Number lookup has **no enforced relationship**, so "0 units left" is a hard gate.
- **Angelique / Status Date:** all 410 changes since 09-24 were made by her directly in SharePoint, with no app stamp;
  the flow made none. Ask her what the date is meant to record.
- **The app must require a Model** (user decision), handled in the Power App clean-up. 4 units are model-less:
  P1_001, P20001, P20002, 20877R1.
- Power App export into the repo (`pa-export`) unblocks several app items.

## Done on 09-28 (details in git log)
Archive go-live (option 2); units 1256/1257 recycled; red items fixed (30 edits, revision 417 recycled);
Archive BO retired; version limit 500 on Order Items and Order; test column and test clients deleted;
Models 503 line break fixed (rollback file in `rollback/`).
