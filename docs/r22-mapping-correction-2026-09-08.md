# R22 — the documented fix was wrong, and it would have failed silently

Found 2026-09-08 while preparing the mapping change. **The data is already repaired**
(979 rows, verified 979/979 against the parent). What was wrong is the *mapping fix*
every doc has been prescribing, including the risk register and the morning runbook.

## What the docs said to do

> Read `…?['ModelDescription']?['Value']` instead of the reference.

## What the mapping actually is

Read out of the live `v006` definition — present identically in **both**
`CreateOrderItem` and `UpdateOrderItem`:

```
@if(empty(first(body('Filter_ModelRevision'))?['Description']),
    null,
    string(first(body('Filter_ModelRevision'))?['Description']))
```

Three things follow, and each of them breaks the prescribed fix:

1. **The internal name is `Description`, not `ModelDescription`.** `Model Description`
   is the *display* name. `?['ModelDescription']` resolves to nothing on this list.
2. **`Description` is `MultiChoice`** — confirmed from the list's own schema XML
   (`<Field Name="Description" Type="MultiChoice" DisplayName="Model Description">`),
   not inferred. It is the **only** multi-value field on `Order`, `Models` and
   `Model Revisions` combined, which is why R22 has no siblings.
3. So the value arriving is an **array**, and the bug is `string()` serialising it.
   `?['Value']` is the shape for a *single* Choice or Lookup; on an array it yields
   nothing.

## Why the prescribed fix would have failed silently — twice over

`?['ModelDescription']?['Value']` evaluates to `null`. And **`null` does not clear a
field through the Power Automate connector** — the finding already recorded against
R14 and proven by the 844 stale `Pending` statuses that survived a full rewrite.

So the paste would have succeeded, the run would have reported success, and the blob
would still be sitting on every row. The natural conclusion would have been "the fix
didn't take" — and the actual cause, a wrong internal name, is invisible from the
outside. **That is the same failure mode as `Planned Delivery Date`**, which once wrote
nothing at all because its name was retyped instead of read from the platform.

## The correct expression

```
@if(empty(coalesce(first(body('Filter_ModelRevision'))?['Description'], json('[]'))),
    null,
    join(select(coalesce(first(body('Filter_ModelRevision'))?['Description'], json('[]')),
                item()?['Value']), '; '))
```

Apply to **both** write actions — `item/RevModelDescription` on `CreateOrderItem` and on
`UpdateOrderItem`. Two expressions, one paste.

⚠️ **`coalesce` appears twice on purpose.** Power Automate's `if()` evaluates *both*
branches rather than short-circuiting, so a bare `select(null, …)` can throw even when
the guard is true. Coalescing inside `select()` as well as in the guard is correct
either way and costs nothing. The same hardening has been applied to the N3 generator,
which was carrying the identical exposure.

## Consequences beyond this one column

- **`CreateOrderItem` carries the same defect.** Every doc discussed R22 as a
  *rewrite* problem, but the create branch has it too, so any newly-onboarded order
  would arrive with the blob. That matters more now, not less: the planned
  create-only change would have left this the *only* live path.
- **The `null`-on-empty idiom is retained** for consistency with the other 121
  mappings, which means a revision whose `Description` is genuinely empty keeps
  whatever the column already holds. Harmless today, because the repair script already
  set every one of the 979 rows correctly.

## The type question, answered with data

The 47 parent sync columns are **not** all Text — that assumption is worth retiring:

| type | count |
|---|---|
| Text | 29 |
| Number | 7 |
| Note | 4 |
| DateTime | 3 |
| Boolean | 2 |
| Currency | 1 |
| URL | 1 |

Of the 27 whose source field resolves straight out of the flow definition, **26 match
their parent's type exactly** — dates are `DateTime`, quantities are `Number`, `Price`
is `Currency`, `OrdOrderFolder` is `URL`, the notes are `Note`.

**Exactly one differs: `RevModelDescription` is `Note` against a `MultiChoice` parent** —
this column. And that is *why* the blob could be stored at all: a `Note` field accepts
any string, including 110 characters of JSON, without complaint.

The columns that *are* `Text` are the ones whose source is a **Choice** or **Lookup**,
and that is `N2`'s deliberate decision, not an oversight: a synced `Choice` **silently
rejects any value outside its option list, per row, inside the flow** — the `Family`
failure mode. `Text` cannot reject anything, which is the point. Keep them that way
(N3 spec, rule 5).

Whether `RevModelDescription` should become `Text` rather than `Note` is cosmetic — a
joined `A; B` string sorts and filters better as `Text` — and is not worth a schema
change on its own.
