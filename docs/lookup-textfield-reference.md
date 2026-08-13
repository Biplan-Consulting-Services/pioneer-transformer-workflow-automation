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
| Order | Client | `Client_ID_TextField` (exact name pending fresh export) | **Get-item**, likely | ✅ Column added + flow built 2026-08-13, per user. Exact field name/pattern to be confirmed against a fresh `sharepoint-lists/Order.csv` export. |
| Order | Model | *(exact name pending fresh export)* | *(pending confirmation)* | ✅ Column added + flow built 2026-08-13, per user. Details to confirm against a fresh export. |
| Order | Model Revision | *(exact name pending fresh export)* | *(pending confirmation)* | ✅ Column added + flow built 2026-08-13, per user. Details to confirm against a fresh export. |

## To-do

**All TextField sync flows built as of 2026-08-13** — every Lookup across every list now
has its companion built, including all three `Order` fields (columns added + flows built
in the same session, per user). Only one thing remains, already known, not a new gap:

- [ ] `Regrouped Into` (`Order Items`) — deferred as a future nice-to-have, nothing
      regrouped yet. See the note in `order-items-power-automate-flows.md`.
- [ ] **Verify the three `Order` rows above** against a fresh `sharepoint-lists/*.csv`
      export once the user re-exports — the table currently just trusts "done," the exact
      field names/patterns were placeholders and haven't been confirmed against live data
      the way every other row in this table was.
