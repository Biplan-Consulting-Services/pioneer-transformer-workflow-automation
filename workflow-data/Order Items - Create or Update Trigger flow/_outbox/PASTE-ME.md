# Paste this back

## → `PASTE-ME.json`

**v008 — connection reference only; flow no longer writes Status Date (manual, user decision 2026-09-24); supersedes v007**

That is the file. It is the export's `properties` object — the shape the
extension accepted for v004 — and `connectionReferences` inside it is carried
through unchanged from what is live, so pasting it never rebinds a connection.

`alternate-shapes/` holds the same version in three other shapes. Ignore it unless
the editor rejects the file above; then try `definition-only.json` first.

## After pasting, check these in the editor

| | before | after |
|---|---|---|
| `CreateOrderItem` item/* fields | — | **—** |
| `UpdateOrderItem` item/* fields | — | **—** |
| `toLower(` occurrences | 0 | **0** |
| unguarded `'EC'` | 0 | **0** |

## Then close the loop

Save in Power Automate, copy the JSON back out into `_inbox/`, and tell me.
`flow_version.py intake` will confirm by hash — if it matches, v008 flips to
`applied`. Until then it stays `local`: I do not mark my own work as landed.

If it does **not** match, v008 is marked `forked` and I report exactly what
differs — which is the signal that something else changed underneath.

