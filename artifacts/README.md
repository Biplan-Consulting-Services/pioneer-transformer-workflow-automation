# artifacts/

Local sources for published Artifact pages, kept so a corrupted or unreachable live page can be
recovered without rebuilding it.

## `risk-register-tracker.html` — the canonical source

The **Order Items Migration Risks** tracker,
`https://claude.ai/code/artifact/a787ce02-c396-4626-ae79-67a27fe50130`.

**Edit this file, then republish passing that URL** so it updates in place rather than creating a
second tracker. It is a **body fragment** — no doctype, no `html`/`head`/`body` tags — because the
Artifact tool wraps what it is given in a document skeleton at publish time. Verified on every
publish: those tags must count **zero**.

## The bug this page had, and why it is not a mystery

The live page rendered as **unstyled text with the dependency graph collapsed into a column**.
Diagnosed 2026-09-08 by diffing the live version against the last good local copy:

- the live version had **zero `style` blocks**, no `title`, no font links and no `app-state`
  element — lines 2–259 of the good copy, one contiguous span, **13,339 bytes of CSS**;
- the surviving content was **byte-identical** to the good copy otherwise, so nothing else was
  lost and no live edit was at risk;
- with `app-state` gone, `STATE` parsed to `{}` and **every step read `todo`** regardless of the
  real progress.

**Root cause — two contracts that are opposites, which is the whole trap.**

| | takes |
|---|---|
| the **Artifact tool** (publishing this file) | a **body fragment** — it adds the skeleton |
| the in-page **`publish()`** runtime API | a **complete document, doctype first** |

The page's `serialize()` returned `document.body.innerHTML` — a fragment — and the runtime
contract also says *never serialize the live DOM*. Both were violated. The failure is silent and
cumulative: this page's `title`, font links and `style` are authored at the top of the body, a
fragment publish gets them **normalised up into the document head**, and the next save — reading
the body alone — no longer saw them. **Two clicks destroyed the styling.** Nothing errored.

The earlier "nesting corruption" in this page's history (3 doctypes, 62 KB) was the *same* root
error from the other direction: returning a whole document, which then nested on each save.
Fixing that by switching to body-only traded one failure for this one.

**The fix.** `serialize()` now assembles a complete document explicitly: it gathers this page's
own assets by their `data-asset` marks **wherever they currently sit** (head or body), places them
in the head, and captures the body without them. Two details are load-bearing:

- **the shell tags are built with `String.fromCharCode`, never written literally.** The guard that
  strips document-shell tags out of the body capture would otherwise match those literals in the
  script's own source — the body capture includes the script — and strip them from the published
  copy, disabling the shell and quietly publishing a fragment again.
- **both captures are trimmed.** Without it the round trip is stable in content but not in size,
  appending a few blank lines per save, unbounded.

**Verified, not assumed.** A jsdom harness ran four generations — load, click, save, reload — and
checked the result is a **fixed point**: identical structure each generation, CSS steady at 13,321
bytes, `title`/links/`app-state` present, 34 graph nodes and 34 list rows rendered, exactly one of
each shell tag, and a tick made in one generation still set in the next.

## `risk-register-tracker-recovery-2026-09-08.html`

The historical snapshot this recovery was built from (live version `1788643514-a2b3`, captured
2026-09-07 14:07), kept for provenance. It carries a minimal document wrapper so it opens directly
in a browser — which is **why it is not the publish source**. Prefer
`risk-register-tracker.html`.

## `cutover-state-board.html` — the state-and-decisions companion

The **Order Items Cutover State** board,
`https://claude.ai/code/artifact/3300b1d1-dc81-40a6-9d03-34a185649767`.

A companion to the risk tracker rather than a replacement: the tracker is the *risk register*
with its dependency graph, this is *where things stand and what has been settled*. Built
2026-09-09 the night before the Thursday cutover, because three status registers disagreed and
the only document with real switchover mechanics was stamped `SUPERSEDED`.

Same publish contract as the tracker — **a body fragment**, `data-asset` marks on the title,
font links and `style`, and the same explicitly-assembled `serialize()`. Read that file's notes
above before touching this one; the two-opposite-contracts trap applies identically. Verified
zero shell tags on publish.

It is deliberately **simpler than the tracker**: the content is static HTML and only the tick
state is dynamic, so `serialize()` has no JS-rendered regions to reset. Ticks live in
`app-state` and are re-applied on load, which is authoritative over whatever classes the
captured body carries.

Figures on it are measured, not carried forward — `FRM10-12_2026-09-04_23h08m.xlsx` for the
workbook side, the 2026-09-08 list exports for the SharePoint side, joined row-level on
`Unit ID` over the 1,013 units present in both.
