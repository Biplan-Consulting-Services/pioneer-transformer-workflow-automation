# Engineering document control for production

**Status: designed 2026-09-14, not built.** Supersedes `document-library-plan.md`, which was
a seed doc written 2026-08-21 before Monday access existed and before the vault was known.
That file stays for its dsapps.dev research; everything else here replaces it.

Part of Workstream 5 (`roadmap.md`).

---

## The problem

Today, drawings live on a local file server. For each order ~163 sheets get printed and split
into 11 colour-coded folders, one per department, and walked down the production line. The goal
is to remove the paper entirely: when a unit reaches a production step, whoever is working it
sees exactly the documents that step needs, at the revision that unit is being built to, on a
tablet.

Three constraints make this harder than "put the PDFs in SharePoint":

1. **Frozen sets.** A client change mid-production must not silently change what the floor is
   looking at — but the floor must keep access to the revision they started on. Every revision
   has to stay live and individually addressable.
2. **No duplication.** Copying each needed PDF into each order folder multiplies the same file
   across hundreds of folders and guarantees drift.
3. **Routing.** Each document goes to a specific subset of departments. That mapping exists
   already as a completed analysis and must not be re-derived by hand.

---

## Core idea

**Stop using the folder tree as the access mechanism.** Add an index layer on top, and the
storage layout becomes just storage — engineering keeps working the way it does today.

Two things carry all the weight:

- **Routing is derived from document *type*, not stored per file.** Each PDF is tagged once with
  its type (`Outline - Encombrement`, `Wiring - Shéma éléctrique`, …); which departments need it
  comes from the routing table. Changing who needs what is a one-row edit applying retroactively,
  not a re-tagging pass over thousands of files.
- **A pin is an explicit stored revision, never "whatever is newest".** A unit's document row
  stores the SharePoint `UniqueId` of one exact PDF. A new revision landing in the library cannot
  reach the floor by accident; only a deliberate re-pin does that.

### Resolution rule — most-specific-wins, per document type

```
Unit-specific  >  Order-specific  >  Model-revision baseline  >  Plant master
(Nameplate,       (order folder     (model code folder         (CB Master,
 M.P.L)            contents)         root PDFs)                 WB Master, PL-Master)
```

The 2026-08-21 doc assumed everything was order-item-specific and built `{Order Number}/{Order
Item}` folders on that basis. Confirmed 2026-09-14: most documents are **model-generic**, with
per-order deltas and a handful of true per-unit documents. Three levels, not one.

---

## Where the data lives

**The file server stops being in the path.** Forced by the tablet requirement — a Windows share
cannot be linked from a Monday item, will not open in a browser on a tablet, and is unreachable
for the outside tank fabricators who receive the `Cuve` package.

One thing must **not** move:

| Layer | Home | Why |
|---|---|---|
| CAD source (`.ipt`/`.iam`/`.idw`) + the Vault file store and SQL database | **Stays in Vault** — never SharePoint, never a OneDrive-synced folder | Inventor assemblies use file references that break under cloud sync; Autodesk requires Vault workspaces to be local. Moving them corrupts working files. |
| Published PDFs | **SharePoint** | The only layer the floor, Monday and suppliers consume |
| Routing table, baselines, pins, unit drawing lists | **SharePoint lists** | Consistent with the "SharePoint = database" shape the rest of the estate runs on |

Flow: **Vault → published PDF → SharePoint.** The drop folder in between holds files for
minutes, not as a home.

### Migration (scope: everything)

Use Microsoft's free **SharePoint Migration Tool (SPMT)** for the bulk file-share move — it
preserves Created/Modified timestamps, handles path and character problems, and runs
incrementally so cutover is not a big bang. Scripting is then only the *metadata tagging* pass,
which is the part SPMT cannot infer.

Measure before the first run:

1. **400-character URL limit.** `Client / ModelCode / OrderNumber / long filename.pdf` can
   exceed it. Worst case decides whether the folder depth survives as-is.
2. **Illegal characters** — `" * : < > ? / \ |`, leading/trailing spaces, reserved names. The
   naming culture in the seed sheet (`Base Mod./ Tank Mod.`, `Formulaire: Points a surveiller`,
   `N/P-Ext.`) says this will bite.
3. **Do not OneDrive-sync the migrated library** for daily engineering use.

Volume is not a concern: a few thousand PDFs is trivial (30M items per library; the 5,000 figure
is a *view* threshold, not storage, and folder-per-model keeps any one folder small).

---

## Entities

| Name | Type | Grain | Purpose |
|---|---|---|---|
| `Engineering Drawings` | Document library | one row per **PDF revision** | The masters. Every revision immutable and permanent. |
| `Document Types` | List | 56 rows | The routing table. Type → recipients, colour, copies. |
| `Recipients` | List | ~15 rows | Departments/stations/suppliers, and how each maps to a Monday step. |
| `Model Doc Sets` | List | model revision × doc type | The reusable baseline. |
| `Unit Drawings` | List | **active** unit × doc type | Flat and filterable — what the floor reads. Generated at release, archived at delivery. |
| `Unit Drawings Archive` | List | same | As-built record, permanent. Keeps the live list small. |

`Unit Drawings` is denormalised deliberately: every floor query becomes a single indexed equality
filter, the only thing that works in a plain SharePoint view URL. Volume stays bounded because
rows exist only for units in production (~150 units × ~30 docs ≈ 4,500 rows), not all 1,189 units
ever created.

**Library rules that make the pin trustworthy:**

- Never move or rename a released file. Superseding sets `Status`, it does not relocate — a moved
  file breaks a path-based pin. Default views filter to `Status = Current`, so clutter is
  invisible to everyone but engineering.
- Rows store the SharePoint `UniqueId`, **never a path**.
- Apply a **retention label** to released revisions so a pinned revision cannot be deleted.

---

## The step vocabulary — four systems, none of which agree

| | Values |
|---|---|
| Blue folder (11) | Essai, Qualité, Isolation, Ass + Stacking, Tanking, Test, Finition, Filerie, Cuve, Vente, Achats |
| `Order Items.Location` (12) | Isolation, Bobinage, Stacking, Assemblage, Four, Tanking, Test, Finition, Livraison, Entrepôt, Extérieur, Réparation |
| `Order Items` stage columns (8) | Coiling, Stacking, Assembly, Drying, Tanking, Testing, Finishing, Delivery |
| **Monday groups (~26)** | En attente de production, Isolation, Bobinage, Enroulage, Assemblage, Test Ratio, Four, Sortie Four et Test DF, Encuvage, Inspection Mise en Cuve, Vaccum, Tests, Soudure, Montage Électrique, Finition, Inspection Finale, En attente de tests d'huiles, Vérification NC, Expédition, Reparation — plus a `Stockage <station>` buffer after most stations |

**Decision (2026-09-14): Monday's step list is the current truth, and every step is tracked.**
Not just the ones that consume documents — all of them — until production confirms otherwise.
Do not prune `Stockage *`, `Test Ratio`, `Vérification NC` or `Reparation` on the assumption
that a step with no drawings needs no tracking; a buffer step with no documents still has real
dwell time, and that is exactly what this system is meant to measure.

A step consuming **no documents is a normal, valid state** — `Unit Drawings` simply has no rows
for it. Routing and tracking are independent axes and must not be collapsed into one another.

### How to carry 26 steps in SharePoint — a child list, not 52 more columns

`Order Items` already has **141 columns**. Two date columns per step for 26 steps takes it to
~193, and that is the wrong shape:

- The step list is **still changing** — the board is under construction. Every added step would
  be a schema change plus an N3 flow change. A child list absorbs a new step as a *row*.
- The existing 8 stage pairs already carry a documented trap: every stage's END date is
  internally `<Stage>Date`, **not** `<Stage>EndDate`, while the Start Dates genuinely are
  `<Stage>StartDate` — the two halves of one pair follow different rules. Hand-making 52 more
  multiplies that risk.
- Monday already stores this as `Date_Depart_<Step>` / `Temps_<Step>` columns. A child list maps
  to those one row per step.

**Proposed: a `Unit Step History` list** — `Unit ID` (lookup to `Order Items`), `Step` (choice,
the Monday vocabulary), `Sequence`, `Start`, `End`, `Duration`, `Operator`, `Step Status`. One
row per unit per step.

**Keep the existing 8 stage columns as a denormalised summary**, rolled up from the child list.
They cannot be retired — FRM10-12, FRM11 and FRM13 all read them. Specifically:

- 🔴 FRM11's purge rule reads `Location` in **two-letter codes** (`{XT,TE,FI,LI}`, or `TA` plus
  `Status` containing `TE`). Extending the `Location` choice to 26 Monday values would break it.
- 🔴 FRM11 parses the **composite `Status` format**, so that format cannot be retired either.

So: **leave `Location` at its 12 coarse values** and add a separate `Current Step` column
carrying the Monday vocabulary. Full fidelity for the new system, nothing broken in the old one.

---

## The Monday board as observed (2026-09-14)

Account `powerpartners.monday.com`, workspace *Pioneer Production Control*, board
**`Transformers Production`** (`18416970916`). **Still under construction** — its shape can still
be influenced, which is why the vocabulary work is cheap now and expensive later.

| | |
|---|---|
| Item grain | **`Numéro de série`** — one item per physical unit. IDs read `G21458-1/12`, `G21714-1/3`: the `Order Items` unit ID with a `G` prefix. Mixed with throwaway test data (`Kdjddjd`, `465`, `1253`). |
| Steps | **Board groups**, not subitems and not a column |
| Advance | A **"Prochaine Étape" button column**, backed by some of the board's **55 automations** |
| Columns | 44. Relevant: **`Code Produit`** (empty), `Client`, `Type`, `KVA`, `Prototype`, `Statut Production`, `Priorité`, **`QR Fichier`**, `NC Ouverte`, connect-columns to `NC_Pioneer_Transformers` and `Tableau de BO`, plus ~24 `Date_Depart_<Step>` / `Temps_<Step>` telemetry columns |
| Views | `Main table`, **`Triggerly - QR Print View`**, **`Vue Opérateurs`** |

Three consequences that change the build:

**🔴 Steps are groups, and a Monday formula column cannot read an item's group.** The filtered
link cannot be derived from where the item sits. Fix: extend the existing "Prochaine Étape"
automation to also write an **`Étape actuelle`** status column alongside the group move. Small
change to automation already running, and nothing else here works until it exists.

**🔴 `Code Produit` is empty**, and it is the join key from a unit to its model document set.
Populating it (from `Order Items.Model` / `Client_Model_Code`) is a prerequisite.

**🟢 QR is already in play** (`QR Fichier` + a QR print view), implying scanners or tablets on the
floor already. A unit's QR can open its own drawing list — a cheap win on existing infrastructure.

### How the floor gets its documents

Monday item → one link → a pre-filtered SharePoint view of `Unit Drawings`:

```
…/Lists/UnitDrawings/AllItems.aspx?useFiltersInViewXml=1
  &FilterField1=UnitID&FilterValue1=21865-1_5
  &FilterField2=Recipient&FilterValue2=Tanking
```

Built by a Monday formula column from `Numéro de série` + `Étape actuelle`. Stacked URL filters
are confirmed working (up to 10, AND-combined). No third-party app, no admin consent, no custom
code.

**dsapps.dev stays available as a nicer last mile.** Not an alternative architecture — the
library, routing table, baseline and pin are identical either way; it only changes how the final
list reaches the screen (embedded in the Monday item rather than a SharePoint tab). The deciding
test, still unanswered from public docs: **does the folder embed show a folder's full contents,
or only a single linked file?** Full contents makes it an upgrade; single-file makes it useless
for a drawing packet. Build on the URL filter so nothing is blocked, then swap if it proves out.
Its folder-generation feature is a second, independent reason to evaluate it.

---

## The publishing boundary — Inventor → SharePoint

Engineering runs **Inventor with the bundled Vault**, and is interested in automating the PDF
publish. The rule that makes everything downstream trustworthy: **the revision must come from
the CAD iProperty, never be typed by a human.**

Confirm the edition first — it decides what is possible:

| Edition | Revisions & lifecycle | Job Processor (auto-publish) |
|---|---|---|
| **Vault Basic** (bundled free with Inventor — the likely one) | Version history only; no controlled revision scheme or lifecycle states | **No** |
| Vault Workgroup / Professional | Yes | Yes |

**Path with no new licence:**

1. An **iLogic rule** on the drawing template exports the PDF on release, named deterministically
   from iProperties — `<DrawingNumber>_<Rev>.pdf` — into a watched drop folder.
2. A **watcher script** indexes that folder into the library: parses the name, writes metadata,
   marks the previous revision `Superseded`, leaves it in place. Needed regardless of what feeds it.
3. **Inventor Task Scheduler** ("Publish PDF") batches the same export across a folder — how the
   historical catalogue gets published in one pass.

**Upgrade worth pricing:** Vault Workgroup/Professional adds the Job Processor, publishing the PDF
automatically on a lifecycle transition to *Released* — fully hands-off, with real revision control
and change orders in the vault. The iLogic route delivers the same shop-floor outcome without
waiting on it.

---

## How a mid-production change is handled

The pin alone is not enough; propagation must be deliberate and visible.

1. Engineering publishes a new revision. **Nothing on the floor changes.**
2. A scheduled check flags every **active** unit whose pinned revision is behind, writing
   `Revision Status = Behind`.
3. Engineering decides **per order**: hold (record why) or re-pin.
4. A re-pin rewrites the pinned `UniqueId`, stamps `Re-pinned On`, and raises a visible flag on the
   Monday item so the station stops and re-reads. Steps already complete get a rework-check flag.

This is the part paper can never do, and it is the direct answer to the original concern.

---

## Findings from the seed data

`scripts/parse_dossier_bleu.py` parses `workflow-data/Utilisateurs dossier bleu V2.csv` into
`reports/dossier-bleu.json` and `reports/dossier-bleu-routing.csv` (159 routing rows). The
cross-foot is the test: column C and row 1 are independent sums of the same 163 sheets, and all
11 departments plus both grand totals agree. Five traps are documented in the script's docstring.

**1. The 11 "departments" are three different kinds of thing** — and only one kind can hang off a
Monday step:

| Kind | Members | Maps to a Monday step? |
|---|---|---|
| Shop-floor station | Isolation, Ass + Stacking, Tanking, Test, Finition, Filerie, Essai | Yes |
| Office function | Qualité, Vente, Achats | No — needs a different surface |
| **External supplier** | **Cuve** (26 copies — the highest of all) | No — the tank fabricator package (CADORETTE/METELEC/FRAMECO) |

`Cuve` routes documents *out of the building*. Materially different from shop-floor tablets, and
it should not be quietly folded in.

**2. Bobinage receives no documents in the matrix at all** — despite being a real station with its
own workbook (FRM09). Either winding works from something else, or the analysis is incomplete.
More likely a gap than a fact. **Confirm with production.**

**3. Two of the 56 rows are input forms, not output documents.** `Formulaire: Points à surveiller`
("Copie sur des feuilles oranges") and `Order Check List` (C1120/C1122/C1115/C1116) get filled in
by the floor. Going 100% digital means these become a Monday form or list entry, not a PDF to
view. Separate scope — call it out rather than absorb it.

**4. Seven rows have no drawing number at all** — `Com. atelier`, `Estampes`, `Flange Network`,
`HV busbar`, `X0 Bar support`, `X0 Connection`, `LY Layout`. Each needs a source before it can be
tagged. `X0 Bar support` is also a dead row (0 copies, no marks) and is a prune candidate.

**5. One row carries a physical-workflow instruction with no digital equivalent** — `Nameplate -
Plaque signalet.` (avec +), Essai column: *"placer dans chemise sur la table à dessins"*. Needs a
decision on what replaces it.

---

## Explicitly out of scope

**NC (non-conformance) photos and notes** — the second half of `document-library-plan.md`. The
`NC_Pioneer_Transformers` and `NC_Rapport_TEMPLATE` boards already exist and `NC Ouverte` is live
on the production board. Being solved elsewhere.

---

## Phases

| # | Phase | Depends on |
|---|---|---|
| 0 | **Discovery** — Vault edition + whether a `Revision Number` iProperty is maintained; then run the server survey below | — |
| 1 | **Routing table** — ✅ parser done; reconcile the vocabularies with production; build `Document Types` + `Recipients` | production session |
| 2 | **Library + metadata** — create `Engineering Drawings`, SPMT bulk move, tagging pass, stand up the publishing pipeline | 0 |
| 3 | **Baseline + pin** — `Model Doc Sets`, `Unit Drawings` | 2 |
| 4 | **Monday surface** — `Étape actuelle`, populate `Code Produit`, formula column, clean test items, pilot one step / one unit; dsapps.dev embed test in parallel | 3 |
| 5 | **Change control** — pinned-vs-latest check, hold/re-pin, floor notification | 3 |
| 6 | **Retire paper**, department by department | 4, 5 |

`Unit Step History` (see above) is production-tracking scope rather than document scope, but it
shares the step vocabulary from Phase 1 and should be designed in the same session.

### Running Phase 0

The drawing share is on Pioneer's network and is not reachable from the Biplan machine, so the
survey runs where it is:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Survey-DrawingServer.ps1 -Root "\\fileserver\Engineering"
```

Read-only — it never writes to, renames, moves or opens anything on the source. It writes
`reports/drawing-server-survey.md` and `reports/drawing-server-inventory.csv`, and answers the
four questions that decide the migration design:

| Question | Why it decides something |
|---|---|
| How big is it | Sets the SPMT schedule |
| Do the paths fit | It projects the **post-migration URL**, not today's UNC path — which is usually *longer*. Anything over 400 is rejected by SharePoint, so the folder depth may have to flatten. |
| Do the names fit | `~$` Office lock files are real, common, and not drawings — exclude them. Reserved device names and trailing spaces/periods are the other genuine hits. |
| Is there a convention | Scores names against the version schemes seen in the wild and reports the match rate. The dominant scheme is what the indexer parses; the rest is the exception list to fix by hand. |

It also counts, per document stem, how many versions sit in one folder — the check on whether any
history survived. A low number confirms baselines can only start from now.

Verified 2026-09-14 against a synthetic tree exercising every branch: a 453-character projected
URL, a `~$` lock file, a reserved `AUX` folder, four version schemes, an unparseable name, and a
stem with two versions. All six detected.

---

## Where this stopped — 2026-09-14

Paused here deliberately. Three things are ready and waiting on somebody else:

| Waiting on | What to do | Artifact |
|---|---|---|
| **Engineering** | Confirm the Vault edition (Basic / Workgroup / Professional) and whether drawing `Revision Number` iProperties are actually maintained | — |
| **A machine on Pioneer's network** | Run the server survey | `scripts/Survey-DrawingServer.ps1` |
| **A session with production** | Settle the step vocabulary | `reports/step-mapping-worksheet.xlsx` (regenerate with `scripts/gen_step_mapping_workbook.py`) |

Nothing else can start until at least the third lands — the routing table is built and verified,
but it cannot be pointed at a step until the 11 → 26 mapping exists.

**First thing to do on resuming:** re-read the Monday board's group list against the worksheet.
The 24 steps in it were read off the live board by eye, and two stretches scrolled past too fast
to capture — between `Inspection Mise en Cuve` and `Vaccum`, and between `Montage Électrique` and
`Finition`. A missing step is a missing row, and the worksheet cannot know it.

## Open questions

- Vault edition, and whether drawing `Revision Number` iProperties are actually maintained.
- The 11 → 26 vocabulary mapping, plus the Bobinage gap and `Cuve` as an external recipient.
- Where the `/` in unit IDs gets sanitised (`21865-1/5` → `21865-1_5`) — flagged 2026-08-21, still open.
- Whether all 56 document types are still current, or whether migration is the moment to prune.
- What replaces the two input forms, and the one physical-workflow instruction.
- Who owns the re-pin decision, and what the floor notification actually looks like.
