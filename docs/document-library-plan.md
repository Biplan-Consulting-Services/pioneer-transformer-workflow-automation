# Document Library / NC Storage Plan (seed doc)

**Status: early — problem and goal confirmed, seed data found, real design not started.**
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
- Library holds the actual drawing files (migrated from the local file server).
- Metadata columns on each file record which department(s)/production step(s) need it —
  seeded from the spreadsheet's matrix above, either as a one-time tagging pass or an
  import script.
- Monday surfaces the relevant filtered subset of the library for a given production-step
  task, rather than staff hunting for the right file.

**NC photos/notes**: a second, separate library or list (needs attachment/photo support,
which either a SharePoint list or a document library provides) keyed to `Order Item` +
production step — structurally simple, but the actual schema isn't designed yet.

## How Monday surfaces the filtered SharePoint view (researched 2026-08-21)

**Recommended mechanism — native, no extra cost:** monday.com's item view natively renders
an inline preview of an Office/SharePoint document when a **Link column** on that item holds
a link to it — no third-party app or per-seat cost needed for this part. Design:

1. **One SharePoint Document Library** for all drawings (e.g. "Engineering Drawings"),
   populated from the local file server migration.
2. **One multi-select Choice metadata column** on that library, `Production Step(s)`, using
   the same ~11 values as the spreadsheet's department/step columns (`Isolation`, `Ass +
   Stacking`, `Tanking`, `Test`, `Finition`, `Filerie`, `Cuve`, `Vente`, `Achats`, `Essai`,
   `Qualité`) — tag each drawing per the spreadsheet's existing matrix. A single file needed
   by multiple departments (common in the matrix) just gets multiple tags — no duplicate
   copies, unlike the current colored-folder system.
3. **One saved/filtered view per department/step** on that library (filter: `Production
   Step(s)` contains `X`) — 11 fixed views, each with a stable URL. Built once, not
   per-order/per-unit.
4. **On the Monday side**: each production-step task item already has a Step/Department
   value. Because there are only ~11 fixed target URLs (one per step, not one per task), a
   plain **native monday automation** ("when Production Step is set to X → set Link column
   to [that step's fixed view URL]") populates the Link column — no Power Automate, no
   third-party connector, no per-automation cost, and nothing to build/maintain beyond the
   11 recipes.
5. The populated Link column then shows the inline document preview directly in the item
   view — this is what a shop-floor tablet operator sees when opening their task.

**What's confirmed by research vs. still needs a hands-on test**: monday.com's own docs
confirm a link column holding an Office/SharePoint **file** link renders an inline preview
in the item view. What's *not* confirmed is whether that same inline-preview behavior
extends to a SharePoint **filtered library view URL** (multiple files, not one document) —
that specific case wasn't found documented either way. **Do a quick live test before
committing to this design**: create one filtered view, drop its URL into a monday Link
column, and check whether it renders inline or just as a clickable link.

**Safe fallback either way**: if the inline multi-file preview doesn't render, the Link
column still works as a plain clickable link that opens the filtered SharePoint view in the
tablet's browser — one tap to the exact right document set, still a large improvement over
the current printed/color-folder process, just not embedded in-page.

**Paid alternative, if the native approach falls short in testing**: the "Microsoft 365
SharePoint & Outlook integration" marketplace app (dsapps.dev) does purpose-built
SharePoint↔monday linking — confirmed (via its own docs) to link/embed files in place rather
than duplicating them into monday's storage, consistent with the centralize-in-SharePoint
decision above. Seat-based pricing from $15/month (3 users) scaling up; **requires a
Microsoft 365 admin to grant one-time org-wide consent** — worth flagging given this tenant
(`ermcopower`) has a history of withheld admin consent blocking similar app installs (see
the PnP PowerShell block noted throughout this repo). Keep as a fallback, not the default
plan, given the native approach above should be free and simpler if the inline-preview test
passes.

**This mechanism only covers *viewing* existing drawings** — it doesn't address how NC
photos/notes get *created* (see below), which is a write path, not a read/link path.

## Explicitly open — not decided, needs a real design pass

- Exact library/list structure for both the drawings and the NC entries.
- How a drawing's metadata tags actually get populated from the spreadsheet — manual tagging
  pass in the SharePoint UI, or a scripted import (blocked by the same PnP/tenant-consent
  wall as other schema work, if scripting is wanted — see `order-items-manual-build-checklist.md`
  for that constraint).
- How NC entries get created in practice — directly in Monday? A form? Who's expected to
  file one, and when?
- Whether every one of the 56 drawings in the spreadsheet is still current, or whether the
  file-server migration is a good moment to prune stale ones.
