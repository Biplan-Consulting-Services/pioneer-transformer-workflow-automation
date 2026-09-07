# _outbox — you copy back from here

When I have authored a change, this folder holds exactly one thing to paste:

    PASTE-ME.definition.json     the bare `definition` object, ready for the JSON editor
    PASTE-ME.md                  which version it is, what changed, what to check after

Anything older is cleared when a new one is staged, so there is never a question about
which file is current.

After pasting: **save in Power Automate, then copy the JSON back out into `_inbox/`** (or
export the `.zip` there). I ingest it and confirm the change landed by hash. Until that
happens the authored version stays `local` — I do not mark my own work as applied.
