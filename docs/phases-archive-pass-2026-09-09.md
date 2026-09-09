# Can the archive fill the blank `Phases` values? No — and the reason is the finding

Asked 2026-09-09: *"for the blank phases i would like you to do a pass on the archive and
find the orders that have the PO Item #(client model code) that matches and see if wee can
fill them. i dont want to replace what is all ready filled only the empty ones."*

Done exactly that. **It fills nothing.** The reason is worth more than the result.

## The two numbers, side by side

| | |
|---|---|
| Where `Phases` **is** already populated (297 rows) | the archive agrees on **277 of 277** matchable rows — **zero** disagreements, **zero** conflicting values |
| Where `Phases` is **blank or `0`** (94 rows) | it fills **0** |

A method that is perfect where it can be tested and useless where it is needed is not a
method with a bug. It is a method measuring the wrong thing.

## What is actually going on

**The archive is a mirror of the same datum, not an independent source.** An archive order
row inherits `Phases` from its model revision, so when the revision is blank every one of
its order rows is blank too. Measured directly rather than inferred:

- Of the 94 blank-phase revisions, **23 do have a matching `PO Item #`** in the archive.
  Those 23 map to **81 archive rows**, and `Phases` is blank on **all 81**. Not one of the
  23 has any archive row carrying a `1` or a `3`.
- The other **71 were never ordered at all** — absent from the archive *and* from the live
  workbook. Which is also why they have no phase: nothing was ever built.

So the 100% agreement was never corroboration. **It was copying.** Reading it as
validation would have been the mistake — the same shape as trusting a `Bo Sort Date` that
a CSV export renders blank, or a run that reports `Failed` on success.

## Things ruled out along the way

- **Not a format mismatch.** Tried the raw code, the code with a `-22`-style suffix
  stripped, and the code with hyphens removed. All three give the same 23 matches.
- **Not a different column.** Only **1** of the 94 codes appears in the archive's `JS #`.
- **Not archive sparsity in general.** Archive-wide, `Phases` is populated on 3,155 of
  5,193 rows (`3` on 2,177, `1` on 978). It is well populated — just never for these.

## What the archive *is* good for here

It cannot answer the question, but it can help the person who has to. For each revision
needing validation it supplies **the client, the order numbers and the kVA** — enough for
the shop to recognise the physical transformer. That context is now in the validation
workbook: 20 of the 25 rows carry order numbers and 17 carry a kVA figure.

## Consequence

`Phases` cannot be back-filled from data. It can only be filled by someone who knows the
unit, which is why the workbook asks. And it is why `Phases` cannot be the *sole*
mechanism for resolving 1PH/3PH names: it is missing on 94 of 391 revisions (24%), so it
works as a **check on** a name rather than a **replacement for** one.

That check has already earned its place — used as a validator it caught three name-based
mappings that looked obvious and were wrong on some rows:

| value | rows | what `Phases` said |
|---|---|---|
| `PADMOUNT` | 33 | 28 at `3` — but **5 blank** |
| `VAULT-1PH` | 13 | 10 at `1`, 2 blank, and **1 at `3`** — a straight contradiction |
