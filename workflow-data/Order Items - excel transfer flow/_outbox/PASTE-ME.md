# Paste this back

**v006 — v006 fetch-once + review fixes + Mdl-Rev columns**

## Which file

Editors disagree about which level they take. Try in this order:

| file | shape | use when |
|---|---|---|
| `PASTE-ME.properties.json` | `{apiId, displayName, definition, connectionReferences}` | the editor says **missing `definition` flow property** — it wants a wrapper |
| `PASTE-ME.definition.json` | the bare `definition` (`$schema` / `triggers` / `actions`) | the editor shows `triggers` and `actions` at its top level |
| `PASTE-ME.minimal.json` | just `{definition, connectionReferences}` | the wrapper is rejected for having extra keys |
| `PASTE-ME.full.json` | the whole export document | last resort |

`connectionReferences` is carried through **unchanged from what is live**, so none
of these rebinds a connection.

Authored from **v005** (v005 Order-X columns populated), which is what the flow was at 2026-09-08 00:04.

## After pasting, check these in the editor

| | before | after |
|---|---|---|
| `CreateOrderItem` item/* fields | 93 | **122** |
| `UpdateOrderItem` item/* fields | 101 | **130** |
| `toLower(` occurrences | 34 | **34** |
| unguarded `'EC'` | 0 | **0** |

## Then close the loop

Save in Power Automate, copy the JSON back out into `_inbox/`, and tell me.
`flow_version.py intake` will confirm by hash — if it matches, v006 flips to
`applied`. Until then it stays `local`: I do not mark my own work as landed.

If it does **not** match, v006 is marked `forked` and I report exactly what
differs — which is the signal that something else changed underneath.

