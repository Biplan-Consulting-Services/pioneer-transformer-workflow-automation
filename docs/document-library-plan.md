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

## Explicitly open — not decided, needs a real design pass

- Exact library/list structure for both the drawings and the NC entries.
- How a drawing's metadata tags actually get populated from the spreadsheet — manual tagging
  pass in the SharePoint UI, or a scripted import (blocked by the same PnP/tenant-consent
  wall as other schema work, if scripting is wanted — see `order-items-manual-build-checklist.md`
  for that constraint).
- How NC entries get created in practice — directly in Monday? A form? Who's expected to
  file one, and when?
- How Monday's per-task view actually surfaces the right filtered document set from
  SharePoint (confirmed 2026-08-21 as the storage location, see above) — a link/embed to a
  filtered library view, or something deeper via the connector? Not researched yet
  (`phase1-tooling-research.md` only evaluated monday.com as a task/automation layer, not
  its document-linking capabilities).
- Whether every one of the 56 drawings in the spreadsheet is still current, or whether the
  file-server migration is a good moment to prune stale ones.
