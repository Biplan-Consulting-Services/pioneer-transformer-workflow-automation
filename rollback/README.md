# rollback/

Every "keep this" block from a live write, in one place, so recovering does not depend on
finding a console scrollback or a chat log.

**One file per write.** Named `YYYY-MM-DD <script> <what>.json`. Each carries the state
*before* the write, or the ids the write created — whichever is what an undo needs.

## Why this exists

The bulk scripts print an UNDO block to the console and nothing else. That is fine for the
five minutes after a run and useless the next morning. These writes are against production
SharePoint with no version history at the item level worth relying on, so the printed block
is genuinely the only route back.

## What each file is for

| file | undo by |
|---|---|
| `… X4 orders created.json` | **deleting** the listed Order ids — they did not exist before |
| `… X2 delivered.undo.json` | **restoring** the listed previous values onto those item ids |

Read the direction from the file's own `undo` field rather than assuming — creates and
updates reverse differently, and getting it backwards on a create makes 66 new rows.

## Running an undo

Each source script carries its own UNDO block, commented out at the bottom:

- `scripts/x4_create_missing_orders.js` — paste the `made` array, it DELETEs
- `scripts/x2_set_delivered.js` — paste the `PREV` array, it MERGEs the old values back

Paste the `data` array from the JSON file here into that block.

⚠️ **An undo is a write too.** Same rules: read it before running it, and expect it to need
the same `APPLY`-style care as the thing it is reversing.
