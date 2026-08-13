# Order Items — Full Build Plan

**Status:** ready to build. Written 2026-08-12. **Priority elevated above/parallel to
`phase1-plan.md`** — user's explicit call: get staff off manually editing
`FRM10-12.xlsx`'s `TableOrders` as soon as possible, not deferred as a later phase. This
supersedes the earlier "just build a minimal identity-only Order Items list" scoping in
`phase1-plan.md` — since the full list is being built now anyway, Phase 1's fan-out logic
just consumes it once it exists, no separate minimal version needed.

## Goal — what "done" looks like

1. `Order Items` SharePoint list built with the **full** confirmed schema (not just
   identity fields) — every field from `infrastructure-overview.md`'s "Order Items list
   schema" section, which is the single source of truth for field names/types; this doc
   doesn't duplicate that table, just sequences the build around it.
2. Companion new columns added to `Order` (`Engineering Required`, `LDs`, `Client Date
   Status`, `Sales Notes`, `Order Status`) and `Model Revisions` (`Duplicate Order`,
   `Family` — decided 2026-08-12 to go on Model Revisions specifically, not Models, since
   both can change revision-to-revision) — not `Order Items` fields themselves, but part
   of the same "stop manually editing Excel" migration, since they're also currently
   manual `TableOrders` columns. (`Protector & Switchgear PO` was originally planned here
   too, but **moved to `Order Items` instead, 2026-08-13** — user's call: it's per-unit
   purchasing, not per-order, pairing with `Protector Status` which is per-unit for the
   same reason.)
3. **Existing live orders' current data backfilled** from `TableOrders` into new `Order
   Items` rows — a one-time migration. Without this, staff can't actually stop touching
   Excel for orders already in flight; they'd have nowhere to see/edit that data until it's
   moved.
4. `ColumnMap.pq` + `TableOrders.pq` extended (same pattern as `Model Revisions`) so
   `TableOrders` becomes a **read-only mirror** of `Order Items` — Excel still shows the
   data (for anyone still glancing at it, and for the native formula columns/Power BI that
   depend on it), but staff no longer type into it.
5. Staff actually switch to editing in the SharePoint list view (or a future Power App)
   instead of Excel, and Excel stops being the edit surface for this data in practice.

## Build sequence

1. **Build the `Order Items` list schema in SharePoint** (empty, no data yet) — full field
   list from `infrastructure-overview.md`, sequenced as a click-through checklist in
   `docs/order-items-manual-build-checklist.md`.
2. **Add the companion new columns** to `Order`/`Model Revisions` (list above; also covered
   by the same manual checklist).
2b. **Build the TextField auto-sync Power Automate flow — elevated to a real task,
   2026-08-13** (previously just a passing "good later addition" comment in
   `order-items-manual-build-checklist.md`, not actually tracked anywhere — user flagged
   this while building: keeping `Order_Number_TextField`/`Regrouped_Into_TextField`/
   `Duplicate_Order_TextField` in sync by hand has been a real pain, not a hypothetical
   one). Not blocked by the PnP consent issue — Power Automate's first-party SharePoint
   connector is available now. Flow: on the source item (`Order`/`Order Items`) being
   created or having its lookup-target field change, write the looked-up value's text
   into the companion `_TextField` column on whichever list holds the Lookup
   (`Order Items`'s `Order Number`/`Regrouped Into`, `Model Revisions`'s `Duplicate
   Order`). Worth building **before or alongside step 3's backfill**, not after — the
   backfill will otherwise recreate the same manual-sync burden for every row it creates.
3. **One-time backfill**: export current `TableOrders` data (per the confirmed
   field-to-column mapping already worked out) into `Order Items` rows, one row per current
   `Order` value (e.g. `21865-1/5`). Needs a script or Power Query one-shot — given the
   scale (~1000 rows per the FRM10-12 migration's prior experience), don't do this by hand.
   **This step does the raw-value conversions**, not the schema build — e.g. `LDs`'
   `Y`/`N` text becomes real Yes/No, `Location`'s old short codes (`LI`, `IS`, ...) map to
   the new full-name Choice values, the old `'x'`/blank test markers become Yes/No. The
   schema decisions in `order-items-manual-build-checklist.md` don't have to be perfect
   before this step — field types/choice lists built in step 1 can still be adjusted (add a
   missed choice value, fix a type) any time before this backfill actually moves data, since
   nothing's been imported yet to conflict with a change.
4. **Extend `ColumnMap.pq`/`TableOrders.pq`** to pull `Order Items` back into Excel
   read-only, same differential-update pattern used for `Model Revisions`.
5. **Validate the round-trip** before cutting over — refresh `TableOrders`, confirm it
   matches the backfilled `Order Items` data exactly, no data loss. Treat this like the
   `Order`/`Models` migrations before it: verify with real data before trusting it, don't
   assume from the M code alone.
6. **Communicate the cutover to staff**: stop typing directly into `TableOrders`'s
   [Location, Status, Tank, Frame, dates, ...] columns, use the SharePoint list instead.
7. *(Optional hardening, not blocking)*: once `Order Items` is confirmed as the source of
   truth, consider protecting/locking those columns in `TableOrders` so a stray manual edit
   there goes nowhere silently rather than creating a conflicting value.

## Open items — don't block starting the build

- `Trimestrial Customer`'s per-unit granularity is still provisional (see
  `infrastructure-overview.md`) — build it per-unit as planned, revisit later per the
  standing future-review-point note.
- `Trimestrial Customer`'s **type/values are now actively pending clarification**, not just
  provisional: a full-history check (2026-08-13) found the field likely tracks a penalty
  date (`Pénalité Trimestrielle`), not a yes/no attribute — built as plain Text for now,
  **waiting on the business users who know this field to get back from holidays** before
  going further. Separate open item from the placement question above.

(`Tank`/`ISO Stack`/`ISO Coil`/`Lead Assembly`'s `R` = "Received" hypothesis is now
**confirmed** — 2026-08-12 — and stays Text/manually-filled by design, not converted to
Choice. No longer an open item.)

## PnP PowerShell route blocked — building manually instead

The original plan for step 1 below was a PnP PowerShell script. That's blocked: the
`ermcopower` tenant hasn't granted admin consent for the PnP Management Shell Azure AD app,
and this user doesn't hold a role that can grant it. **`docs/order-items-manual-build-checklist.md`**
has the full field-by-field list to build by hand in the SharePoint UI instead — same way
`Order`/`Models`/`Model Revisions` were originally built.

**Important scope correction (2026-08-13): this block is narrower than first framed.** It's
specific to PnP PowerShell — a third-party, multi-tenant Azure AD app that needs explicit
tenant admin consent before *anyone* in this tenant can use it at all. It does **not** extend
to **Power Automate cloud flows**, which use Microsoft's own first-party SharePoint
connector — already trusted under the existing Microsoft 365 license, no IT consent needed,
buildable directly in the browser today. So: **creating/modifying list schema (columns,
lists themselves)** stays manual for now (no scripting path). **Working with data once the
schema exists** — the one-time backfill's row creation, any future auto-sync flow (e.g.
keeping a Lookup's companion text field in sync), and all of Phase 1's `Workflow Tasks`
automation — is fully available via Power Automate, unaffected by this block. Don't treat
the whole migration as stuck on IT; only the schema-build step is.

## Relationship to `phase1-plan.md`

Two independent, parallel tracks — proceeding on one doesn't block the other:
- **This doc**: the production-tracking data layer (`Order Items` + the few companion
  columns) that shop-floor/production staff currently hand-type into Excel.
- **`phase1-plan.md`**: the front-of-process business workflow (Sales → Engineering →
  Planning → Client confirmation) and its `Workflow Tasks` automation/notifications.

Where they touch: `phase1-plan.md`'s fan-out logic (`Work Order`/`Planning Schedule` being
per-unit) needs `Order Items` rows to exist — once this build is done, that dependency is
fully satisfied (and then some), no separate minimal version needed on that side.
