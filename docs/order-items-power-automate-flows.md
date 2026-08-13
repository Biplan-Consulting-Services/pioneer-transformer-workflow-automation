# Order Items — Power Automate Flows to Build

Build-ready specs for the flows tracked in `order-items-build-plan.md`'s build sequence
(steps 2b, 2c, 3). Not blocked by the PnP consent issue — Power Automate's first-party
SharePoint connector is available now, buildable directly at make.powerautomate.com.

## Progress

- [ ] 2b. TextField auto-sync (this doc, below)
- [ ] 2c. Production-sequence auto-stamp
- [ ] 3. Excel → SharePoint transfer flow (re-runnable)

## Step 2b — TextField auto-sync

**Why**: every Lookup field (`Order Number`, `Regrouped Into` on `Order Items`;
`Duplicate Order` on `Model Revisions`) has a companion `_TextField` holding a plain-text
copy, for search/filtering. Keeping these in sync by hand has been a real pain point —
this automates it.

**⚠ Infinite-loop risk — read before building.** Both flows below update the *same item*
that triggered them. A naive "when item created or modified → update item" flow can
re-trigger itself forever. **Guard every flow with a condition that skips the update if
the TextField already matches the looked-up value** — the self-triggered re-run then finds
nothing to change and exits without looping.

### Flow A — `Order Items` Lookup sync

- **Trigger**: SharePoint *"When an item is created or modified"* — Site:
  `https://ermcopower.sharepoint.com/sites/PioneerPlanificatio`, List: `Order Items`.
- **Action 1 — Get item** (or use trigger outputs directly if the connector exposes lookup
  display values on the trigger — check `Order Number` and `Regrouped Into`'s available
  dynamic content fields first; Lookup columns typically expose both an ID and a
  Value/display-text output).
- **Condition 1**: `Order Number` (lookup display value) **is not equal to**
  `Order_Number_TextField` (current stored text).
  - **If yes**: Update item — set `Order_Number_TextField` = `Order Number`'s display
    value.
  - **If no**: do nothing (this is the loop-prevention guard).
- **Condition 2** (separate, for the multi-value lookup): `Regrouped Into` values, joined
  with a comma (`join(outputs('Get_item')?['body/RegroupedInto']?['value'], ', ')` or
  equivalent — the exact expression depends on how the connector surfaces a multi-value
  lookup; test this against a real multi-value row before trusting it) **is not equal to**
  `Regrouped_Into_TextField`.
  - **If yes**: Update item — set `Regrouped_Into_TextField` = the joined text.
  - **If no**: do nothing.

### Flow B — `Model Revisions` Lookup sync

- **Trigger**: SharePoint *"When an item is created or modified"* — same site, List:
  `Model Revisions`.
- **Condition**: `Duplicate Order` (lookup display value) **is not equal to**
  `Duplicate_Order_TextField`.
  - **If yes**: Update item — set `Duplicate_Order_TextField` = `Duplicate Order`'s
    display value.
  - **If no**: do nothing.

### Testing before trusting this

1. Change `Order Number` on one `Order Items` row → confirm `Order_Number_TextField`
   updates within a few seconds, and confirm the flow run history shows exactly **one**
   run per change, not a runaway loop.
2. Repeat for `Duplicate Order` on one `Model Revisions` row.
3. `Regrouped Into` can't be tested yet — nothing has been regrouped, and building the
   actual `Regrouped Into` UX (which items are legal targets, etc.) is separate future
   work. Test this one once a real regroup happens, or fabricate a test row/value first —
   don't skip testing it just because it's inconvenient right now, the multi-value join
   expression is the most likely part of this flow to be wrong.
