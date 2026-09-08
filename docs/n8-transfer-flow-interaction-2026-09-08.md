# N8 vs the transfer flow — is the flow adapted for `Status Date`?

Asked 2026-09-08. **Short answer: no, and it should not be.** Parsing the composite
does not belong in the flow. What it needs instead is a **run-order constraint**.

## What the flow does today

Read out of the live `v006` definition, identical on **both** write actions:

```
item/Status   =   @item()?['Status']
```

That is the raw composite (`TE-Se-4`) copied straight from the workbook. **Nothing
writes `StepStatus` or `StatusDate`** — and neither column exists on the list yet;
`scripts/n8_split_status.js` creates them.

## The create branch needs no adaptation — measured, not assumed

**A brand-new order has no status**, because `Status` is a progress marker staff type
as work happens:

| check | result |
|---|---|
| Rows the run created (orders `22143`–`22155`) | **65** |
| …of those carrying a composite `Status` | **0** |
| Workbook orders numbered ≥ `22143` with any `Status` | **none** |
| Workbook rows with a `Status` at all | 156 of 1,019, across 60 of 373 orders |

So on the create path there is nothing to split. Leaving `StepStatus`/`StatusDate`
unmapped is the correct behaviour, not an omission.

## The update branch is the whole problem — and it is the branch create-only deletes

While `One_Item_Found` → `UpdateOrderItem` is live, every run rewrites `Status` from
Excel and **does not touch the two split columns**. They do not get cleared; they go
**stale**, silently, on whichever of the 156 live status rows a staff member edits
between N8 running and the last transfer run.

Nothing reports this. `Status` and `Step Status`/`Status Date` simply stop agreeing.

## So the answer is an ordering constraint, not a mapping

Either order is safe. Pick one:

1. **Create-only first, then N8.** No divergence window exists at all. Cleanest.
2. **N8 first, then re-run N8 after the final transfer run.** Also fine —
   `n8_split_status.js` is **idempotent**: column creation skips columns that already
   exist, and the populate pass recomputes both values from the current `Status` and
   overwrites them. Re-running is a re-sync, not a duplicate.

What is **not** safe is running N8, treating the split columns as authoritative, and
leaving the update branch live indefinitely.

## Why the parse must not go into the flow

Three properties of the composite make a per-row flow expression the wrong tool, and
each one is a silent-wrong-answer risk rather than an error:

1. **There is no year in the value.** `TE-Se-4` carries a month and a day only. N8
   assumes 2026 and *checks the assumption for coherence* — every resolved date lands
   in `2026-07-06 … 2026-09-04`, which is what a current-production status should look
   like against a 2026-09-08 today. A flow expression cannot sanity-check itself.
2. **The month abbreviations are ambiguous.** `Jui` is juin or juillet. N8 resolves all
   19 rows from **each unit's own stage dates**, landing 0–1 days from the July reading
   and several times on the exact day. That is cross-column context a single-row
   mapping expression does not have.
3. **The status prefixes collide with the Location codes.** `BO` is *Manque Pièces* in
   `Status` but *Bobinage* in `Location`; `TE` is *Terminé* here and *Test* there. Only
   the column tells you which table applies. A mis-wired lookup produces a plausible
   wrong word, not a failure.

After cutover the question dissolves: staff type into `Step Status` and `Status Date`
natively in SharePoint, and the flow — create-only by then — has no business writing
either.

## ⚠️ Do not retire the composite `Status` column

`power-query/FRM11/Rows to purge.pq` parses that exact format:

```
"Already Tanked" = List.Contains({"XT","TE","FI","LI"}, [Location.1])
                   or ([Location.1] = "TA" and Text.Contains([Status.1], "TE"))
```

It reads `Status` via the **Archive active** workbook rather than from Order Items
directly, so retiring the list column would not break FRM11 *today*. But the
**format** is depended on outside this project, and a SharePoint-sourced `TableOrders`
would have to keep producing it — so keep `Status` as the legacy mirror and treat
`Step Status` + `Status Date` as additive. See `CLAUDE.md`.

Reconstructing the composite from the split pair is possible but lossy: `Step Status`
stores the display name (`Terminé`), not the code (`TE`), so it needs the reverse
lookup plus a French month abbreviation. Not worth it — keep the original.
