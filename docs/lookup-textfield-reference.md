# Lookup → TextField Reference

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
| Model Revisions | Client | `Client_ID_TextField` | **Get-item** | ✅ Built 2026-08-13 (pending test confirmation). On `Clients`: pulls `Client_ID` |
| Model Revisions | Pioneer Model Code | `Pioneer_Model_Code_TextField` | Simple | ✅ Built 2026-08-13 (pending test confirmation). Points at `Models`. |
| Model Revisions | Duplicate Order | `Duplicate_Order_TextField` | Simple | ✅ Built 2026-08-13 (pending test confirmation). Same shape as Order Items' `Order Number`. |
| Models | Client | `Client_ID_TextField` | **Get-item** | ✅ Built 2026-08-13 |
| Models SA | Client | `Client_ID_TextField` | ~~Get-item~~ | **Superseded 2026-08-13** — `Models SA` is being fused into `Models` (see `models-sa-fusion-plan.md`), no dedicated flow built for it. |
| EngineeringChangeOrders | Client | `Client_ID_TextField` | **Get-item** | ✅ Built 2026-08-13 |
| ModelChanges | Model_ID | `Model_ID_TextField` | Simple | ✅ Built 2026-08-13, `ShowField` verified during build |
| ModelChanges | ECO_ID | `ECO_ID_TextField` | Simple | ✅ Built 2026-08-13, `ShowField` verified during build |
| ModelChanges | *(none directly)* | `Client_ID_TextField` | **Chained Get-item** | ✅ Built 2026-08-13. Path: `ModelChanges.Model_ID` → that `Models` item's `Client` lookup ID → that `Clients` item's `Client_ID`. |
| Order | Client | *(missing — to add)* | **Get-item**, likely | User's call, 2026-08-13: this needs a `Client_ID_TextField` too, currently missing. Verify `ShowField`, but almost certainly the same Get-item shape as every other `Client` Lookup here. |
| Order | Model | *(missing — to add)* | *(verify)* | Needs a TextField companion. Confirm what `ShowField` currently displays (likely `Model_Code`) before deciding Simple vs. Get-item. |
| Order | Model Revision | *(missing — to add)* | *(verify)* | Needs a TextField companion. Confirm `ShowField` (likely something identifying the specific revision, e.g. `Spec_ID` or `Model_Revion_ID`) before deciding pattern. |

## To-do

**All TextField sync flows built as of 2026-08-13** for every Lookup that currently has a
TextField column to sync into — `Order Items`/`Order Number`, `Model Revisions` (all
three), `Models`, `EngineeringChangeOrders`, and `ModelChanges` (all three, including the
chained one). Only two things remain, both already known/deferred, not new gaps:

- [ ] `Regrouped Into` (`Order Items`) — deferred as a future nice-to-have, nothing
      regrouped yet. See the note in `order-items-power-automate-flows.md`.
- [ ] The three `Order` fields (`Client`, `Model`, `Model Revision`) — still **missing
      their TextField columns entirely** in SharePoint (a schema step, manual, same
      PnP-blocked situation as the rest of this migration). Can't build sync flows for
      these until the columns exist. See rows above for what each likely needs
      (`Client_ID_TextField` almost certainly Get-item; `Model`/`Model Revision`'s pattern
      still needs `ShowField` verification once their columns are added).
