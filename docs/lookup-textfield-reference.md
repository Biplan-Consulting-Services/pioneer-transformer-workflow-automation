# Lookup → TextField Reference

> ## 🔴 The field names in this document are not reliable. Verified 2026-09-14.
>
> Three errors found in adjacent rows of the table below, while diagnosing a live data
> corruption. **Do not design a flow, script or query against a name taken from here** —
> read it off the live list first.
>
> | this doc says | the live list has |
> |---|---|
> | `Model_Revion_ID` on `Model Revisions` (with a note calling the missing "s" a deliberate pre-existing typo) | **no such field.** The revision id lives in **`ModelID`** |
> | `Client_ID_TextField` on `Model Revisions` | **`Client_ID_TextFiel`** — genuinely truncated, missing its final `d` |
> | `Model Revision` needs the **Get-item** pattern, pulling a separate id field | **Simple is correct.** The lookup's `ShowField` already resolves to `ModelID` |
>
> **Why it drifted:** the header says it was "pulled directly from the live schema exports
> in `sharepoint-lists/*.csv`". Per `CLAUDE.md`, a SharePoint CSV export **omits every
> Lookup column entirely — values *and* schema**; only the `_TextField` mirrors appear. So
> the source it was built from could not have contained the lookup facts it asserts. The
> table's *shape* (which lookup pairs with which mirror, which pattern each needs) is still
> the useful part; its *names* were reconstructed.
>
> ⚠️ **This cost real time.** On 2026-09-14 the `Model Revision` row led to two wrong
> diagnoses in a row — first "the flow writes the wrong field, fix the mapping", then "no
> field holds these values, stop writing the column". Both would have broken a mapping that
> works. The actual defect was 29 corrupt rows in `Model Revisions` itself. Reasoning about
> field *names* instead of reading field *values* is what produced both errors.
>
> **To verify a name**, probe it — `scripts/x16_audit_lookup_mirrors.js` and
> `x17_audit_revision_modelid.js` both try candidate names against the live list and abort
> rather than report a clean result they did not measure. Note that a bad `$select` returns
> 400, and the usual `j.value||[]` turns that into **zero rows**, which reads as "nothing
> wrong" rather than "broken query".

**What this is**: every Lookup column across the live SharePoint lists, its companion
`_TextField` (plain-text mirror, per the user's standing convention — every Lookup gets a
sibling `{Field}_TextField` for search/filtering), and which sync pattern it needs. Built
while constructing the Power Automate sync flows (`order-items-power-automate-flows.md`),
but kept as its own reference doc since it's useful beyond that — e.g. for diagramming the
list relationships, or auditing that every Lookup actually has its companion built.

Pulled directly from the live schema exports in `sharepoint-lists/*.csv` — re-check against
those (or fresher exports) if this goes stale, don't trust this table blindly forever.

## The two sync patterns

- **Simple**: the Lookup's own displayed value (its `ShowField`) already *is* the value the
  TextField wants — e.g. `Order Number`'s Lookup is configured to show the Order list's own
  `Order Number` field, so the TextField just mirrors that directly. Flow: condition
  compares `{Field} Value` to the TextField, update writes `{Field} Value` on mismatch.
- **Get-item**: the TextField wants a *different* field than what the Lookup displays —
  e.g. `Client` Lookups show the Clients list's `Client` (display name), but the TextField
  wants `Client_ID`. Flow needs an extra `Get item` action on the target list (using the
  Lookup's `Id`), then compares/writes that fetched field instead of the Lookup's own value.
- **Chained Get-item** (rare, one case so far): the field you need isn't even one hop away —
  see `ModelChanges`'s `Client_ID_TextField` below.

## Full table

| List | Lookup field | TextField companion | Pattern | Notes |
|---|---|---|---|---|
| Order Items | Order Number | `Order_Number_TextField` | Simple | ✅ Built & tested 2026-08-13 |
| Order Items | Regrouped Into | `Regrouped_Into_TextField` | Simple (multi-value) | Deferred — nice-to-have, nothing regrouped yet |
| Order Items | Client | `Client_ID_TextField` | **Get-item**, likely | ✅ Built 2026-08-14 (step 8 schema + sync flow both done, added into the existing merged flow). Direct Lookup to `Clients` (not chained through `Order`) — same shape as `Models`/`Order`'s own `Client` Lookup. |
| Order Items | Model | `Model_ID_TextField` | **Get-item**, likely | ✅ Built 2026-08-14. Same shape as `Order`'s `Model` Lookup. |
| Order Items | Model Revision | `Model_Revision_ID_TextField` | **Get-item**, likely | ✅ Built 2026-08-14. Same shape as `Order`'s `Model Revision` Lookup. |
| Model Revisions | Client | `Client_ID_TextField` | **Get-item** | ✅ Built 2026-08-13 (pending test confirmation). On `Clients`: pulls `Client_ID` |
| Model Revisions | Pioneer Model Code | `Pioneer_Model_Code_TextField` | Simple | ✅ Built 2026-08-13 (pending test confirmation). Points at `Models`. |
| Model Revisions | Duplicate Order | `Duplicate_Order_TextField` | Simple | ✅ Built 2026-08-13 (pending test confirmation). Same shape as Order Items' `Order Number`. |
| Models | Client | `Client_ID_TextField` | **Get-item** | ✅ Built 2026-08-13 |
| Models SA | Client | `Client_ID_TextField` | ~~Get-item~~ | **Superseded 2026-08-13** — `Models SA` is being fused into `Models` (see `models-sa-fusion-plan.md`), no dedicated flow built for it. |
| EngineeringChangeOrders | Client | `Client_ID_TextField` | **Get-item** | ✅ Built 2026-08-13 |
| ModelChanges | Model_ID | `Model_ID_TextField` | Simple | ✅ Built 2026-08-13, `ShowField` verified during build |
| ModelChanges | ECO_ID | `ECO_ID_TextField` | Simple | ✅ Built 2026-08-13, `ShowField` verified during build |
| ModelChanges | *(none directly)* | `Client_ID_TextField` | **Chained Get-item** | ✅ Built 2026-08-13. Path: `ModelChanges.Model_ID` → that `Models` item's `Client` lookup ID → that `Clients` item's `Client_ID`. |
| Order | Client | `Client_ID_TextField` | **Get-item** | ✅ Confirmed live 2026-08-13. On `Clients`: pulls `Client_ID` — same pattern as every other `Client` Lookup in this table. |
| Order | Model | `Model_ID_TextField` | **Get-item**, likely | ✅ Confirmed live 2026-08-13. Naming matches `ModelChanges`' `Model_ID_TextField` (which pulls `Models`' `Model_ID`) — near-certain same pattern, not independently re-verified against `ShowField`. |
| Order | Model Revision | `Model_Revision_ID_TextField` | **Get-item**, likely | ✅ Confirmed live 2026-08-13. Naming implies it pulls `Model Revisions`' `Model_Revion_ID` field (note: source field is spelled without the second "s" — a pre-existing typo on `Model Revisions`, not a naming mismatch to "fix" here). Not independently re-verified against `ShowField`. |

## To-do

**Only one thing remains** — the new `Client`/`Model`/`Model Revision` Lookups added
2026-08-14 (step 8) have their sync flow built too, added into the existing
`Order Items - created or updated trigger` flow alongside step 2b/2c, same merged-flow home
as the rest of `Order Items`'s Lookup syncs.

- [ ] `Regrouped Into` (`Order Items`) — deferred as a future nice-to-have, nothing
      regrouped yet. See the note in `order-items-power-automate-flows.md`.
