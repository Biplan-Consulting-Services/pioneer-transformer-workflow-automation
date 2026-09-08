# artifacts/

Local copies of published Artifact pages, kept so a corrupted or unreachable live page can be
recovered without rebuilding it.

## `risk-register-tracker-recovery-2026-09-08.html`

A clean copy of the **Order Items Migration Risks** tracker
(`https://claude.ai/code/artifact/a787ce02-c396-4626-ae79-67a27fe50130`), built 2026-09-08 from
the last version this session had read (`1788643514-a2b3`, captured 2026-09-07 14:07), with the
platform's frame wrapper stripped and the embedded `app-state` corrected to what is actually
true.

**Why it exists.** The user reported the live page rendering as text rather than the styled
page with the dependency graph, and the Artifact tool was disabled for this session (it went
away when the signed-in session changed), so it could be neither read nor republished from here.

**Integrity checked:** 1 `<!doctype>`, 1 `<html>`, 1 `app-state`, the graph container and the
`STEPS` definition all present. That matters because this page has a **history of a nesting
corruption** — saving from the page used to wrap the whole document inside itself, reaching 3
doctypes and 62 KB before it was fixed. Copies at `1788637426` and earlier show it; anything
from `1788640361` on is clean.

**To use it:** open it in a browser to read the tracker offline, or republish it from a session
where the Artifact tool is available, passing the URL above so it updates in place rather than
creating a second tracker.

⚠️ **It is a snapshot, not a merge.** Any tick made on the live page after 2026-09-07 14:07 is
not in it — the `app-state` here was set from what the work actually shows, which is the more
reliable source, but a genuine live edit could still be lost. Prefer fixing the live page if it
turns out to be readable.
