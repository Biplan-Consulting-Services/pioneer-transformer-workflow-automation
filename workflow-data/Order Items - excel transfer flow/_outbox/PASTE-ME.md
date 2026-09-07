# Paste this back

**v004 — D3 BO transfer**

File: `PASTE-ME.definition.json` — the bare `definition` object.

Authored from **v003** (D1D2 six columns), which is what the flow was at 2026-09-07 16:06.

## After pasting, check these in the editor

| | before | after |
|---|---|---|
| `CreateOrderItem` item/* fields | 56 | **75** |
| `UpdateOrderItem` item/* fields | 64 | **83** |
| `toLower(` occurrences | 28 | **34** |
| unguarded `'EC'` | 0 | **0** |

## Then close the loop

Save in Power Automate, copy the JSON back out into `_inbox/`, and tell me.
`flow_version.py intake` will confirm by hash — if it matches, v004 flips to
`applied`. Until then it stays `local`: I do not mark my own work as landed.

If it does **not** match, v004 is marked `forked` and I report exactly what
differs — which is the signal that something else changed underneath.

