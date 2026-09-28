# Paste this back

## → `PASTE-ME.json`

**v009 — moving a unit out of Livraison sets Delivered back to Active (option C, user 2026-09-28); step status untouched**

That is the file, in the shape the extension takes. It includes the connection
bindings below, and pasting it applies them.

| connection | bound to |
|---|---|
| `shared_sharepointonline` | `new_sharedsharepointonline_89e9a` |

`alternate-shapes/` holds the same version in other shapes, **all with these bindings**.
There is deliberately no definition-only shape: it would keep the flow's current
connections instead of these.

## After pasting, check these in the editor

| | before | after |
|---|---|---|
| `CreateOrderItem` item/* fields | — | **—** |
| `UpdateOrderItem` item/* fields | — | **—** |
| `toLower(` occurrences | 0 | **0** |
| unguarded `'EC'` | 0 | **0** |

## Then close the loop

Save in Power Automate, copy the JSON back out into `_inbox/`, and tell me.
`flow_version.py intake` will confirm by hash — if it matches, v009 flips to
`applied`. Until then it stays `local`: I do not mark my own work as landed.

If it does **not** match, v009 is marked `forked` and I report exactly what
differs — which is the signal that something else changed underneath.

