# _inbox — you paste here

Drop the JSON or the exported `.zip` from Power Automate into this folder. **Any filename**,
any of these shapes — it is detected, not configured:

- the bare `definition` object (`$schema` / `parameters` / `triggers` / `actions`) — what a
  JSON editor extension usually shows you
- the full export document (`name` / `id` / `type` / `properties`)
- an exported `.zip` package

Then tell me, and I run:

    python scripts/flow_version.py intake

which snapshots it as a **`pulled`** version — the record of what the flow actually was at
that moment — reports its fingerprint, and **moves the file into `_archive/`** stamped with
its arrival time.

If the drop matches a version I authored and was waiting on, intake flips that version to
`applied`. That is the only thing that ever proves a paste landed, and the `.zip` that proved
it is kept beside the version, because the package is the only artifact that re-imports.

## `_archive/` — nothing is ever deleted

Every consumed drop is archived as `YYYY-MM-DDTHH-MM__<original filename>`. It is not a
duplicate of the version record: it is the exact bytes you handed over, under the name Power
Automate gave them, at the moment they arrived. A version record is a normalised derivative
of that.

**This was learned the hard way.** Intake used to delete the file, on the reasoning that the
version record was the record. But when a drop *matches* an existing version, intake stores
nothing — so the v004 milestone package was destroyed at the exact moment it proved itself
correct, and had to be recovered from `~/Downloads`.
