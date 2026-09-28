# Paste this back

## → `PASTE-ME.json`

**v005 — v005: v003 logic unchanged, both connections on solution references (SharePoint new_sharedsharepointonline_89e9a, Excel new_sharedexcelonlinebusiness_452b5); drops the user's test Excel action**

That is the file, in the shape the extension takes. It includes the connection
bindings below, and pasting it applies them.

| connection | bound to |
|---|---|
| `shared_excelonlinebusiness` | `new_sharedexcelonlinebusiness_452b5` |
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
`flow_version.py intake` will confirm by hash — if it matches, v005 flips to
`applied`. Until then it stays `local`: I do not mark my own work as landed.

If it does **not** match, v005 is marked `forked` and I report exactly what
differs — which is the signal that something else changed underneath.

