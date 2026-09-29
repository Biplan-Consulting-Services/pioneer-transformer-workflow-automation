# Duke Energy RFP: Pioneer OTD 2024-2026

Built overnight 2026-09-29 for the request in `../Project Context - Duke Energy RFP - Pioneer On-Time Delivery (OTD)`.

| File | What it is |
|---|---|
| `Pioneer OTD 2024-2026 - quarterly v2.pptx` (+ `preview.png`) | The slide, quarterly chart. ERMCO dashboard look: red header/footer, logo, white cards with red title strips. Native editable chart; speaker notes carry the extra figures |
| `Pioneer OTD 2024-2026 - monthly v2.pptx` (+ `preview.png`) | Same slide with a monthly chart (33 months), highlights in a 2 × 2 grid |
| `Email draft - OTD slides.md` | Draft email presenting both slides to Michael / Lyn |
| `ERMCO-Pioneer-Transformers.png` | Logo used on the slides (added by the user) |
| `Archive/` | v1 slides (blue design, 03:17 and 09:14), superseded by v2 |
| `Pioneer OTD 2024-2026 - backup data.xlsx` | Method, Yearly, Quarterly, Monthly, Sensitivity, every counted unit, 2026 reconciliation, exclusions |

Rebuild: `python scripts/duke_otd/build_otd.py` then `node scripts/duke_otd/build_slide.js "<out.pptx>" [monthly]`
(needs `pptxgenjs` on the node path; `build_slide.js` reads the `otd.json` the Python step writes next to itself).

## The numbers

| | 2024 | 2025 | 2026 YTD (to Sep 25) |
|---|---|---|---|
| **OTD, 8-day grace** | **63.2%** (766 / 1,212) | **86.7%** (1,079 / 1,244) | **89.8%** (799 / 890) |
| No grace (strict) | 57.5% | 84.6% | 86.9% |
| Order level (every unit of the order on time) | 53.3% | 74.3% | 75.6% |
| Median delay of late units | 77 days | 35 days | 30 days |

## Method: which source for what, and why

- **Unit** = one transformer (`21150-3`). Excluded: sub-assemblies (SA), repairs (WRG), service lines (`OS-`),
  `E`/`P`/`W` orders: the same exclusions as Jose's shipments query.
- **Delivery date**
  - **2024-2025: FRM10-12 archive** `Delivery Date`, only units with `Location = LI` (delivered). Jobscope
    shipments only start in Jan 2026, so the archive is the only source for these years.
  - **2026: Jobscope shipment date** (the actual ship record). Plus 9 archive units marked LI that are
    missing from Jobscope, kept with the archive date.
  - **Why the archive can be trusted for 2024-2025:** on the 866 units in both sources in 2026,
    **803 have the same date and 55 are within 3 days**. So the archive's delivery dates are accurate.
- **Promised date: archive `Initial Promised Date`**, per unit. Jobscope's DATE PROMISED is used only
  where the archive has none (15 units in total).
  - **Why not Jobscope's promised date:** Jose's `qry_JOBS` keeps a single date per job, and it is the first
    item's. On orders shipped in releases (e.g. Kortick 21040: four monthly items, Jan-Apr 2025), that
    makes every later release look late. Matching units to Jobscope's *item* dates gives
    63.9% / 86.2% / 85.3%, close to the archive's figures.
- **On time** = delivered ≤ promised + 8 days (the Power BI grace period).

## Check before sending

1. **Compare against Power BI.** If the report shows a different 2025/2026 figure, the likely causes are
   (a) it counts orders, not units (order-level row above), or (b) it uses Jobscope's job-level promised date.
2. **2026 uses the archive's promised date, which is kinder than Jobscope's.** Using Jobscope's job-level
   promised date gives **85.4%** instead of 89.8%. The gap comes from about 50 units where Jobscope's promise is earlier
   (mostly Hydro-Québec and Kortick release orders). If Duke could ever audit against the ERP date, 85% is the
   safer headline. Every alternative is in the `Sensitivity` sheet.
3. **The 2024 → 2025 jump is real, not a data artifact.** Jobscope's promised dates give the same 2024 result
   (64.5% vs 63.1%). The late 2024 units are spread over 187 orders and many clients, with a median delay of 77 days. The
   step change is between Q1 2025 (65%) and Q2 2025 (95%). Sales may want one line on *why* (what changed then).
4. **2026 Q3 is partial** (Jul 1 - Sep 25). The footnote says so.
5. **No Duke Energy orders in the data**, so the slide covers all customers.

## Data problems found (not fixed; nothing was changed in SharePoint or the workbooks)

- **Archive `Client` differs from Jobscope's customer on most 2025 units.** 1,001 of 1,244 units read `KORTICK`,
  but Jobscope bills them to Hydro-Québec (497), Georgia Power (85), Toronto Hydro (68), Austin Energy, Xcel, Enmax
  and others. 2026 shows the same pattern on a smaller scale. User, 09-29: Kortick may be a supplier or a contact for some
  sub-companies, so the archive may be recording the intermediary rather than the end customer. Not an error for this work
  either way: the slide does not break down by client, and the dates on those rows check out against Jobscope. The
  backup workbook uses Jobscope's customer name and keeps the archive's in `archive_client`.
- ✅ **Corrected 09-29 (user):** the column called "Planned Delivery Date" in Order Items *is* the Delivery Date,
  the truck delivery date Caroline maintains. "Planned" is a naming error. So the archive date after the cutover
  is the right date, and this was never a missing actual date. What remains is a few units where Caroline's date and
  Jobscope's ship date differ (Punch List `fix-actual-delivery-date`). Original note, kept for the record:
- **Since the 09-11 cutover, the archive's `Delivery Date` holds the *planned* date for units not yet shipped.**
  126 units have a 2026 date with Location XT/BO/TA/FI/…, several of them dated 2026-09-28 while still at XT.
  `Order Items.DeliveryDate` (actual) is empty on all 54 `Delivered` units.
  ✅ **Power BI is safe from the big version of this** (user, 09-29): it only counts units that are `LI` *and*
  have a planned delivery date, so an unshipped unit is never counted. Residual: on LI units the date is still the
  planned one. In Sep 2026, 6 LI units differ from Jobscope's ship date, 3 of them by more than 3 days (21792-3/4:
  shipped 09-03, archive 09-24). This is small, and it only grows if planned dates aren't corrected when a unit ships.
- 14 cancelled (AN) units carry a 2026 delivery date. They are excluded here.
- 2023 in the archive has no Initial Promised Date on 276 of 278 deliveries, so it can't be used for OTD.
- 38 duplicate unit keys in `TableArchiveFRM10_12`. The delivered row was kept.
- Archive copy used: `workbooks/Archive active 2026-09-28 1152.xlsx`. The live file was refreshed at 02:47 on 09-29, but
  2024-2025 are historical and 2026 comes from Jobscope, so this does not change the result.
