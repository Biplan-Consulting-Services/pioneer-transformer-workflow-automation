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
3. **Existing live orders' current data transferred** from `TableOrders` into new `Order
   Items` rows (and the new `Order`/`Model Revisions` columns) — via a re-runnable Power
   Automate flow, run an initial time now and again right before go-live (not a one-shot
   script — see step 3 below). Without this, staff can't actually stop touching Excel for
   orders already in flight; they'd have nowhere to see/edit that data until it's moved.
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
   **Build-ready spec**: `docs/order-items-power-automate-flows.md`.
2c. **Build the production-sequence auto-stamp Power Automate flow, added 2026-08-13**:
   when any of the 8 `{Stage} Status` fields (Coiling/Stacking/Assembly/Drying/Tanking/
   Testing/Finishing/Delivery Status) is set to `Completed`, automatically stamp the
   matching `{Stage} Date` field with the current date **and time** — not left for staff
   to type in by hand. **Resolved 2026-08-13**: the 8 `{Stage} Date` fields are being
   changed from Date-only to **Date and Time** in SharePoint (manual schema tweak on the
   already-built list) — user's call, useful later for finer-grained production-time
   analytics (e.g. actual duration between stages, not just which day). Update
   `order-items-manual-build-checklist.md`'s Production-sequence dates section to say
   Date+Time once that change is made there too, so the two docs don't drift.
   **Expanded further, 2026-08-13**: for real time-*spent* tracking (not just completion
   timestamps), each stage also needs a `{Stage} Start Date` field (Date and Time, NEW —
   confirmed live in SharePoint as of the 2026-08-13 17:17 export), stamped when `Status`
   first becomes `In Progress`. The original `{Stage} Date` field was renamed to
   `{Stage} End Date` for symmetry. This is more accurate than inferring a start time from
   the previous stage's finish time, which would wrongly count any idle/waiting time
   between stages as work time. The flow now stamps two things per stage, not one — see
   `order-items-power-automate-flows.md`'s step 2c for the updated spec.
3. **Re-runnable transfer flow, not a one-shot script — changed 2026-08-13.** User's call:
   build this as a **Power Automate flow** (Excel connector reading `TableOrders` → 
   SharePoint connector upserting into `Order Items`/the `Order`/`Model Revisions`
   companion columns), triggered manually/on-demand, rather than a throwaway script run
   once. This lets the transfer happen **twice**: once now (an initial transfer, so there's
   real data in SharePoint to develop/test the rest of this system against), and once again
   right before go-live (to catch up on whatever staff kept editing in Excel during the
   rest of development — since Excel stays the live edit surface until cutover actually
   happens). Re-running must be an **upsert** (match on `Order`/`Title`, update if the row
   already exists, create if not) so running it twice doesn't create duplicates.
   - **Scope: only the columns that moved** — the ~40 `Order Items` fields plus the
     handful of new `Order`/`Model Revisions` companion columns. Don't touch fields
     already sourced from SharePoint the other way (`Client`, `Order Date`, etc.) — this
     flow only ever reads those columns from Excel, never writes them there.
   - **Direction note**: this is Excel → SharePoint, the *opposite* of the permanent
     architecture (SharePoint → Excel, read-only mirror, decided throughout this doc and
     `infrastructure-overview.md`). That's fine — it's explicitly a transitional tool for
     getting real data into SharePoint before cutover, not a standing bidirectional sync.
     Once go-live happens (step 6), this flow's job is done and step 4's SharePoint → Excel
     direction becomes the only one that matters going forward.
   - **This step does the raw-value conversions**, not the schema build — e.g. `LDs`'
     `Y`/`N` text becomes real Yes/No, `Location`'s old short codes (`LI`, `IS`, ...) map to
     the new full-name Choice values, the old `'x'`/blank test markers become Yes/No. The
     schema decisions in `order-items-manual-build-checklist.md` don't have to be perfect
     before this step — field types/choice lists built in step 1 can still be adjusted (add
     a missed choice value, fix a type) any time before a transfer run actually moves data.
4. **Extend `ColumnMap.pq`/`TableOrders.pq`** to pull `Order Items` back into Excel
   read-only, same differential-update pattern used for `Model Revisions`.
5. **Validate the round-trip** before cutting over — refresh `TableOrders`, confirm it
   matches the `Order Items` data exactly, no data loss. Do this against the **final**
   pre-go-live transfer run (step 3's second run), not the initial one — the initial
   transfer is for developing/testing against, not the data staff will actually see at
   cutover. Treat this like the `Order`/`Models` migrations before it: verify with real
   data before trusting it, don't assume from the M code alone.
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

Where they touch: `phase1-plan.md`'s fan-out logic (`Planning Schedule`/`Work Order` being
per-unit) needs `Order Items` rows to exist — once this build is done, that dependency is
fully satisfied (and then some), no separate minimal version needed on that side.
