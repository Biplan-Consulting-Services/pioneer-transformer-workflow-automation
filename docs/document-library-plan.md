# Document Library / NC Storage Plan (seed doc)

**Status: early — problem and goal confirmed, seed data found, real design not started.**
**Blocked on Monday.com access (2026-08-21)**: user's account access to Monday.com is
pending approval — nothing that requires logging into Monday (the Formula column, the live
inline-preview test) can happen until that lands. The SharePoint-side work below (library
setup, the `Order Number`/`Order Item` folder structure, tagging drawings from the
spreadsheet) has no Monday dependency and can proceed in the meantime.
Same spirit as `order-items-build-plan.md`/`phase1-plan.md` when they began: capture what's
known, propose one direction, flag the real open questions rather than guessing a full
design. Part of Workstream 5 (`roadmap.md`) — production-tracking-only scope, alongside the
Monday.com move.

## Two distinct problems, both raised in the same 2026-08-21 meeting

### 1. Engineering design docs → the correct production step

**Today**: drawings live on a local file server. For a given order, the needed drawings get
printed in multiple physical copies and distributed in color-coded folders, one color per
department. Described by the user as archaic.

**Goal**: shop-floor tablets. When a unit's production step starts (in Monday), the person
working it should have direct access to exactly the drawings that step/department needs —
no printing, no physical folders.

### 2. NC (non-conformance) photos and notes

No existing tracking mechanism at all today — genuinely new. Need a place to attach photos
and notes about production defects/problems, tied to a specific unit (`Order Item`) and
production step.

## Seed data: `Utilisateurs dossier bleu V2.xlsx`

The user already ran a completed analysis of which drawing each department/step needs, added
to this repo at `docs/Utilisateurs dossier bleu V2.xlsx` (Git-LFS-tracked, same as other
binary Office files here). Inspected directly — actual structure, not guessed:

- One sheet, 56 drawing rows (`A4:N59`).
- Columns A/B: `TITRE DU DESSIN` (drawing title) / `NO. DESSIN` (drawing number).
- Column C: `exemplaires` — total copy count for that drawing (`SUM` across the department
  columns).
- Columns D–N: 11 department/production-step columns — `Essai`, `Qualité`, `Isolation`,
  `Ass + Stacking`, `Tanking`, `Test`, `Finition`, `Filerie`, `Cuve`, `Vente`, `Achats`.
  Several of these line up directly with the existing `Location` choice values already on
  `Order Items` (`Isolation`, `Tanking`, `Test`, `Finition`, ...) — a useful anchor for
  mapping drawings to production steps later.
- Each cell is `1` or blank, marking whether that specific drawing is needed by that
  department/step. Row 1 sums total drawings needed per department; each data row sums total
  copies needed across departments.
- Row 2 assigns a color per department column (`Rouge`, `Rose`, `Jaune`, `Gris`, `Bleu`,
  `Vert`, `Orange`, `Violet`, `Beige`) — mirrors the physical colored folders described above.

This is the existing document-to-step mapping to build from, not something to re-derive by
hand.

## Storage location — confirmed 2026-08-21: centralize in SharePoint, not Monday

The production team has been struggling with Monday's native file storage in practice.
User's call: centralize the documents (drawings + NC photos/notes) in one place rather than
leaving them scattered across Monday, and that place should be SharePoint — consistent with
the "SharePoint = database" shape Workstream 5 already settled on, and it's what the rest of
this system already runs on (Power Automate, the same tenant, the same Microsoft 365
license). Monday links out to / surfaces a filtered view of the SharePoint library rather
than storing the files itself.

**Considered and ruled out, for completeness**: a separate document-management/PLM system
(overkill at this scale and adds a fourth system to maintain), plain Azure Blob storage (no
native metadata/tagging or browsing UI, would need custom tooling for exactly what a
Document Library gives for free), and Monday's own storage (the thing already causing
problems). Nothing found beats a SharePoint Document Library for this — same recommendation
as before, now on firmer footing since the alternative (Monday storage) has a confirmed real
problem, not just a theoretical one.

## Proposed direction (recommendation — not yet confirmed with the user)

A **SharePoint Document Library** for the drawings, consistent with "SharePoint = database"
(Workstream 5's confirmed shape) and the user's own "document library sync" phrasing:
- Library holds the actual drawing files (migrated from the local file server), organized
  into `{Order Number}/{Order Item}` subfolders — human-navigable on its own, see below.
- A `Production Step(s)` metadata column on each file records which department(s) need it —
  seeded from the spreadsheet's matrix above, either as a one-time tagging pass or an
  import script.
- Monday surfaces the relevant filtered subset (this specific unit's folder, further
  narrowed to one department) for a given production-step task, rather than staff hunting
  for the right file — see the mechanism below.

**NC photos/notes — capture mechanism found, 2026-08-21**: the same dsapps.dev app named
below (already recommended as a *viewing* fallback) turns out to directly do what the user
guessed for *capture* too. Checked its feature list directly:
- **"Copy assets to SharePoint"**: *"Automatically copy files attached to monday.com item
  updates into the configured SharePoint folder for that item."* — a worker attaches a
  photo to a Monday Update on their current task (a normal, lightweight thing to do in
  monday, not the heavier Files-column browsing experience that's apparently been causing
  trouble) and the app copies it out into that item's SharePoint folder automatically. This
  is the confirmed answer to "where does an NC photo actually land."
- It also does **"folder generation on item creation"** and **"templated folder generation
  on status change"** — meaning this same app might be able to auto-create the
  `{Order Number}/{Order Item}` folder structure itself when a task item is created, rather
  than needing a separate Power Automate step for that.
- **Real limitation, confirmed by the same check**: no conditional file routing based on
  other column values — it copies into *one* folder configured per item, it doesn't branch
  by department on its own. Not a problem as long as the monday item this is configured
  against is already at the right granularity (one item per `Order Item` + production step,
  which this system already uses) — the item's *own* configured folder just needs to already
  point at the right place; the app doesn't need to compute that itself.
- **Not yet confirmed**: whether that per-item "configured folder" can be a *template*
  built from the item's own column values (so it resolves to that item's actual
  `Order Item`, not a fixed folder typed in by hand) — the fetch found the feature names but
  not the exact templating syntax. Needs checking once there's actual access to the app
  (which needs Monday.com access first, and the same org-wide M365 admin consent flagged
  below).

Given this, NC photos/notes likely don't need a separate SharePoint list of their own —
they can land as files inside the same `Order Number`/`Order Item` folder structure already
designed for drawings, with the Update's text serving as the note. Still open: whether a
short, structured NC record (who logged it, when, which stage) also needs a real SharePoint
list entry alongside the photo file, or whether the monday Update itself (with its
timestamp/author already built in) is enough of a record on its own.

## How Monday surfaces the filtered SharePoint view (researched + revised 2026-08-21)

**First pass of this design was incomplete** — it only filtered by department/step, not by
*which order/unit*. Since drawings turn out to be mostly **order-item-specific, not generic**
(confirmed by the user — engineering redraws things like nameplates per unit, with real
variation even between units in the same order), a department-only filter would mix every
order's drawings together — useless on the shop floor. The corrected design filters on
**both** dimensions at once, and folds in the user's separate ask for human-navigable
folders rather than treating that as a competing idea:

1. **One SharePoint Document Library** ("Engineering Drawings"), populated from the local
   file server migration.
2. **Folder structure: `{Order Number} / {Order Item}`** — e.g. `21865/21865-1_5/` —
   mirroring the Order → Order Item hierarchy already used everywhere else in this system.
   This is what makes the library human-browsable directly (useful on its own, and
   especially right now while Monday access is pending) — someone can navigate straight to
   a specific unit's folder without going through Monday at all.
   - **Real gotcha to handle**: `Order Item` IDs contain a literal `/` (e.g. `21865-1/5`),
     which isn't safe as a folder name or URL path segment as-is — needs a sanitized variant
     (e.g. `21865-1_5`) wherever a folder gets created or a link gets built. Flagging this
     now, same category of surprise as the `EC`-in-a-date-column gotcha found earlier in
     this project — don't let it get discovered mid-build instead.
3. **Still keep the `Production Step(s)` multi-select tag** on each file, from the
   spreadsheet's type mapping — the folder narrows to *whose unit*, the tag narrows to
   *which department* within that unit's own folder.
4. **The Monday link — one formula, not 11 automations.** A production-step task item
   already has both an `Order Item` value and a `Step` value on itself. A native monday
   **Formula column** can concatenate: the library's fixed base URL + `/{Order Number
   from the task}/{sanitized Order Item from the task}/` + a SharePoint view-filter query
   string built from that same task's own `Step` value — e.g. (illustrative, not exact
   syntax): `CONCATENATE(baseUrl, "/", {Order Item}, "/Drawings.aspx?useFiltersInViewXml=1&FilterField1=Production_Step&FilterValue1=", {Step})`.
   No per-department automation rules to build or maintain — a future new department just
   works, since the formula references the task's own columns rather than a fixed lookup
   table. **Requires**: the text used for `Step` on the Monday task and the Choice values
   used to tag drawings in SharePoint match exactly (same spelling/casing) — a data-
   consistency detail to get right when building, not a design risk.
5. **Both technical pieces behind this are confirmed by documentation, not assumed**:
   - SharePoint modern list/library views accept stacked URL filters —
     `?useFiltersInViewXml=1&FilterField1=<field>&FilterValue1=<value>&FilterField2=...`
     (up to 10, AND-combined) — confirmed via
     [Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-365/community/query-string-url-tricks-sharepoint-m365)
     and the [PnP community docs](https://pnp.github.io/community-docs/articles/query-string-url-tricks-sharepoint-m365.html).
   - monday's Formula column supports nested `IF`/`CONCATENATE` referencing other columns on
     the same item — confirmed via [monday's own Formula Column support docs](https://support.monday.com/hc/en-us/articles/360001235445-The-Formula-Column)
     and its [available-functions reference](https://support.monday.com/hc/en-us/articles/360001276465-Available-functions-in-the-Formula-Column).
6. **Still an open, not-yet-tested question**: whether monday renders that resulting
   SharePoint view URL as an **inline preview** in the item view (confirmed behavior for a
   single Office file link) or only as a **clickable link** (multi-file filtered views
   weren't found documented either way). Either outcome is fine functionally — a clickable
   link is still one tap to exactly the right document set — but worth a live test once
   Monday access lands, before assuming the inline-preview version.

**Paid alternative, if the native approach falls short in testing**: the "Microsoft 365
SharePoint & Outlook integration" marketplace app (dsapps.dev) does purpose-built
SharePoint↔monday linking — confirmed (via its own docs) to link/embed files in place rather
than duplicating them into monday's storage, consistent with the centralize-in-SharePoint
decision above. Seat-based pricing from $15/month (3 users) scaling up; **requires a
Microsoft 365 admin to grant one-time org-wide consent** — worth flagging given this tenant
(`ermcopower`) has a history of withheld admin consent blocking similar app installs (see
the PnP PowerShell block noted throughout this repo). Keep as a fallback, not the default
plan.

**This mechanism only covers *viewing* existing drawings** — it doesn't address how NC
photos/notes get *created* (see below), which is a write path, not a read/link path.

## Explicitly open — not decided, needs a real design pass

- Exact library/list structure for the NC entries (the drawings side now has a concrete
  shape — folders + tag — see above).
- Who/what creates each `{Order Number}/{Order Item}` folder and when (at `Order Item`
  creation, automatically? manually by whoever uploads the first drawing for that unit?),
  and where the `/`-to-`_` ID sanitization actually happens.
- How a drawing's metadata tags actually get populated from the spreadsheet — manual tagging
  pass in the SharePoint UI, or a scripted import (blocked by the same PnP/tenant-consent
  wall as other schema work, if scripting is wanted — see `order-items-manual-build-checklist.md`
  for that constraint).
- Keeping the monday `Step` column's text values and the SharePoint `Production Step(s)`
  Choice values in exact sync (same spelling/casing) — not hard, but a real thing to get
  right once, not an afterthought.
- How NC entries get created in practice — directly in Monday? A form? Who's expected to
  file one, and when?
- Whether every one of the 56 drawings in the spreadsheet is still current, or whether the
  file-server migration is a good moment to prune stale ones.
