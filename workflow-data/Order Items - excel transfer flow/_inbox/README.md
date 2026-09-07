# _inbox — you paste here

Drop the JSON you copied out of Power Automate into this folder. **Any filename**, any of
these shapes — it is detected, not configured:

- the bare `definition` object (`$schema` / `parameters` / `triggers` / `actions`) — what a
  JSON editor extension usually shows you
- the full export document (`name` / `id` / `type` / `properties`)
- an exported `.zip` package

Then tell me, and I run:

    python scripts/flow_version.py intake

which snapshots it as a **`pulled`** version — the record of what the flow actually was at
that moment — reports its fingerprint, and **removes the file from here** so a stale paste
can never be ingested twice. The version file is the record; this folder is a doorway.

If the paste matches a version I authored and was waiting on, intake flips that version to
`applied` automatically. That is the only thing that ever proves a paste landed.
