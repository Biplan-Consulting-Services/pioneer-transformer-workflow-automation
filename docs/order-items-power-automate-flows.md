# Order Items — Power Automate Flows to Build

Build-ready specs for the flows tracked in `order-items-build-plan.md`'s build sequence
(steps 2b, 2c, 3). Not blocked by the PnP consent issue — Power Automate's first-party
SharePoint connector is available now, buildable directly at make.powerautomate.com.

**Scope note (2026-08-13)**: the TextField auto-sync work (2b) turned out to span every
Lookup column across the whole system, not just `Order Items`/`Model Revisions` — see
`docs/lookup-textfield-reference.md` for the complete list-by-list table (which fields need
the Simple pattern vs. the Get-item pattern vs. the one chained case), kept there as a
standalone reference rather than duplicated here.

## Progress

- [x] 2b. TextField auto-sync — `Order Items`/`Order Number` piece built and tested
      2026-08-13 (single run per change, confirmed no loop). `Model Revisions`' three-field
      flow (`Duplicate Order`, `Client`, `Pioneer Model Code`) **built 2026-08-13** —
      pending test confirmation (see below). `Regrouped Into` piece **deferred as a future
      nice-to-have** — user's call, not needed now, revisit once regrouping is actually
      used. Remaining lists (`Models`, `Models SA`, `EngineeringChangeOrders`,
      `ModelChanges`, `Order`) still queued — see `lookup-textfield-reference.md`'s to-do.
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

**Built and tested 2026-08-13** (the `Order Number` piece):
- **Trigger**: SharePoint *"When an item is created or modified"* — Site:
  `https://ermcopower.sharepoint.com/sites/PioneerPlanificatio`, List: `Order Items`.
- **Condition**: `Order Number Value` (the dynamic-content variant that holds the
  looked-up item's display text — not `Order Number` or `Order Number Id`) **is equal to**
  `Order_Number_TextField`.
  - **If yes**: nothing (already in sync).
  - **If no**: Update item (Id = trigger's `ID`, only `Order_Number_TextField` set = `Order
    Number Value`) — this is the loop-prevention guard, structured around "equal" instead
    of "not equal" but same effect.
- **Tested**: changing `Order Number` on a row produces exactly one flow run and updates
  the TextField correctly — confirmed no loop.

**`Regrouped Into` piece — deferred, 2026-08-13.** Not needed now, user's call — nothing's
been regrouped yet and it's a nice-to-have, not blocking. If picked up later: same
condition/update structure as `Order Number`, but `Regrouped Into` is multi-value, so its
dynamic content is an array, not a plain string — needs a `join(select(...), ', ')`-style
expression to flatten it to text first. Check the actual dynamic-content picker output for
this field before trusting any specific expression syntax.

### Flow B — `Model Revisions` Lookup sync

**Built 2026-08-13** — three Lookups synced (`Duplicate Order`, `Client`, `Pioneer Model
Code`, not just `Duplicate Order` as originally scoped — see `lookup-textfield-reference.md`).
`Client` used the **Get-item** pattern (fetch `Client_ID` from `Clients`); the other two are
Simple. Built using the consolidated-update shape (variables per field, one boolean flag
flipped on any mismatch, one final `Update item` gated on that flag) rather than three
separate update actions.

### Testing before trusting this

1. ✅ **Done 2026-08-13** (`Order Items`/`Order Number`): changed `Order Number` on one
   `Order Items` row, confirmed `Order_Number_TextField` updated and exactly **one** flow
   run in the run history — no loop.
2. **`Model Revisions` — confirm before moving on**: test each of the three fields
   independently (change `Duplicate Order` alone, `Client` alone, `Pioneer Model Code`
   alone) and check the run history shows exactly one run per change, all three TextFields
   land correctly, and no loop. Also worth one test changing more than one field at once,
   to confirm the consolidated update still fires exactly once and gets all of them right.
3. `Regrouped Into` — deferred, see note above. Test whenever it's picked up.
