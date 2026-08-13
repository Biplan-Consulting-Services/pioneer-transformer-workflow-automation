# Phase 1 tooling research: what's the best fit for `Workflow Tasks`?

**Why this doc exists:** before building the `Workflow Tasks` list/flow described in
`phase1-plan.md`, the user asked for a deliberate look at whether SharePoint + Power
Automate is still the right foundation, versus what else exists (Planner Premium, Power
Apps + Dataverse, Teams-native approvals, third-party tools) — weighed on usability,
efficiency, and compatibility with the `Order`/`Order Items`/`Model Revisions` lists
already being built. Researched 2026-08-12 via web search; sources linked per section.

## Short answer

**Yes — stay in SharePoint + Power Automate**, exactly as `phase1-plan.md` already
proposes. Nothing found in this research beats it for this project's actual shape (a few
hundred to ~1000 orders/year, already-built native Lookup relationships to `Order`/`Order
Items`, no dedicated Power Platform admin/budget). Two things *are* worth changing from the
current plan, both folded back into `phase1-plan.md`:
1. **Use Adaptive Cards from day one**, not plain Teams messages — this was flagged as a
   "later iteration" nice-to-have; research shows it's the standard, low-extra-effort
   pattern for exactly the "whose turn is it" problem this phase exists to fix.
2. **`Workflow Tasks` needs the same archiving treatment already planned for `Order`/`Order
   Items`** (see `archiving-plan.md`) — SharePoint Online has a hard, non-configurable
   5,000-item **List View Threshold** ([Microsoft
   Support](https://support.microsoft.com/en-us/sharepoint/lists/data-and-lists/list-view-threshold-for-large-lists-and-libraries)),
   and a task-per-step-per-order/unit design accumulates rows fast enough that this matters
   well before `Order`/`Order Items` themselves would hit it.

## Options considered

### 1. SharePoint list + Power Automate (the current plan) — recommended

**Pros:**
- Zero additional licensing — included in every Microsoft 365 plan Pioneer already has
  ([wrvishnu.com](https://www.wrvishnu.com/sharepoint-list-vs-dataverse/)), unlike Dataverse
  which needs Power Apps per-app/per-user licensing on top.
- **Already proven compatible** with this system's exact architecture: native Lookup
  columns (`Order Number`, `Order Item`) work the same way they already do between `Order`
  and `Model Revisions` in this tenant — confirmed directly this session, not assumed.
- Staff already know SharePoint list views from `Order`/`Models` — no new tool to learn.
- Power Automate supports the branching/fan-out/converge logic `phase1-plan.md` already
  designs (Switch on `Step Name`, "wait for sibling task" AND-gate patterns) natively via
  standard, non-premium connectors
  ([sharepointsupport.com](https://sharepointsupport.com/blog/sharepoint-power-automate-workflows-guide)).

**Cons:**
- SharePoint lists are flat — no enforced referential integrity or cascading deletes the
  way Dataverse offers
  ([aufaittechnologies.com](https://aufaittechnologies.com/blog/dataverse-vs-sharepoint-lists/)).
  Not a real problem at this project's scale/complexity, but a genuine limitation if the
  data model ever needs deep relational logic.
- **Hard 5,000-item List View Threshold, can't be raised in SharePoint Online**
  ([Microsoft Support](https://support.microsoft.com/en-us/sharepoint/lists/data-and-lists/list-view-threshold-for-large-lists-and-libraries);
  [sharemaster.io](https://www.sharemaster.io/tools/sharepoint-list-view-threshold-reference)) —
  the threshold counts items a query must *scan*, not just what it returns, so an
  unindexed filtered view can hit it even with few visible rows. Manageable with the
  archiving pattern this project already has planned for `Order`/`Order Items`, but must be
  applied to `Workflow Tasks` too, and probably sooner (a task-per-step design generates
  more rows per order than one `Order Items` row per unit does).
- Power Automate itself needs "ownership, testing, and governance"
  ([sharepointsupport.com](https://sharepointsupport.com/blog/sharepoint-workflow-automation-2026-guide)) —
  someone has to own the flow long-term, same as any other automation.

### 2. Microsoft Planner Premium (formerly Project for the web) — not recommended

**Key finding, and the deciding factor**: Planner Premium is **Dataverse-backed, not
SharePoint-backed**
([wellingtone.com](https://wellingtone.com/microsoft-planner-premium-licensing-plans-pricing-2026/)) —
this is a real architecture change from the old Project Online (which *was*
SharePoint-backed, but [is being retired September 30,
2026](https://techcommunity.microsoft.com/blog/plannerblog/microsoft-project-online-is-retiring-what-you-need-to-know/4450558),
so it's not a live option either way). Using Planner Premium would mean the task-tracking
layer lives in a completely separate data platform from `Order`/`Order Items`/`Model
Revisions` — no native Lookup relationship back to them, just loose title/text matching at
best. That directly undercuts the whole point of this migration project: consolidating
scattered manual tracking into one coherent system, not adding a second disconnected one.

Also found: **Power Automate's Planner connector actions don't support Planner Premium at
all** ([community forum
post](https://community.powerplatform.com/forums/thread/details/?threadid=36dfaec9-4f86-ef11-ac21-7c1e520da679)) —
so even the automation half of this project's needs (notify-on-handoff) would be harder to
build against it, not easier.

**Where it could still fit**: purely as an optional *visual* layer (a Kanban board someone
glances at) synced *from* the SharePoint list via Power Automate, never as the backing
store — same "nice-to-have presentation layer" `phase1-plan.md` already floats for Planner
generally, just now with the specific caveat that it can't be the source of truth.

### 3. Power Apps (canvas app) + Dataverse — not recommended at this scale

**Pros:** referential integrity, cascading deletes, richer security/role controls, business
process flows that enforce consistent step-by-step data entry
([aufaittechnologies.com](https://aufaittechnologies.com/blog/dataverse-vs-sharepoint-lists/);
[learn.microsoft.com](https://learn.microsoft.com/en-us/power-platform/guidance/architecture/real-world-examples/bpf-dataverse-powerautomate)).
Genuinely the right tool if this were an enterprise line-of-business app with complex
security needs and heavy data volume.

**Cons:** requires Power Apps per-app/per-user licensing on top of what Pioneer already
pays for ([wrvishnu.com](https://www.wrvishnu.com/sharepoint-list-vs-dataverse/)) — real
recurring cost for a workflow that's currently non-existent (pure upside case, not
replacing a paid tool). One source frames the decision almost exactly for this project's
size: *"Choose SharePoint Lists if you're building a lightweight internal tool... with less
than 5000 records that aren't related to each other. Use Dataverse when you're building an
enterprise line-of-business app"*
([wrvishnu.com](https://www.wrvishnu.com/sharepoint-list-vs-dataverse/)) — Pioneer's ~1000
orders/year, already inter-related via proven SharePoint Lookups, is squarely the former.
Migrating `Order`/`Order Items`/`Model Revisions` into Dataverse later isn't ruled out if
volume/complexity genuinely outgrows SharePoint, but nothing here suggests that's close.

**Where a canvas app *could* still add value**: purely as a nicer input form over the
existing SharePoint list (multi-step wizard, conditional fields, mobile-friendly) — Power
Apps custom forms/canvas apps can sit on top of a SharePoint list as the data source without
requiring Dataverse at all
([bulb.digital](https://www.bulb.digital/blog/power-apps-for-forms-which-option-is-right-for-you-customized-list-forms-or-standalone-canvas-apps);
[c-sharpcorner.com](https://www.c-sharpcorner.com/article/power-apps-vs-sharepoint-list-customization-vs-microsoft-forms-choosing-the-ri/)).
Same "nice-to-have presentation layer" category as Planner — worth revisiting once Phase 1
is live and staff have opinions about the raw list-view UI, not a blocker now.

### 4. Native Teams "Approvals" app alone — not recommended as the primary mechanism

Microsoft's built-in Teams Approvals app handles simple one-shot approvals with zero setup,
triggered from a chat or channel without needing a Power Automate flow at all
([learn.microsoft.com](https://learn.microsoft.com/en-us/power-automate/teams/native-approvals-in-teams)).
But it explicitly **doesn't support multi-stage routing logic** (waiting on multiple
approvers before advancing, sequential department handoffs)
([laurakokkarinen.com](https://laurakokkarinen.com/the-ultimate-guide-to-microsoft-teams-based-approvals/)) —
exactly the fan-out/converge/AND-gate logic this phase needs. It also has no
list-of-record behind it tied to `Order`/`Order Items` — an approval happens and is gone,
not queryable the way a `Workflow Tasks` row is. Could layer in later for a genuinely
simple single-person sign-off step, but not as the backbone.

### 5. Third-party tools (Monday.com, Smartsheet, Asana, etc.) — not researched in depth, not recommended

Not pursued beyond a sanity check: adopting one would mean abandoning the native Lookup
relationships to `Order`/`Order Items`/`Model Revisions` this session already confirmed work
natively in SharePoint, adding a new per-seat cost on top of Microsoft 365 licensing already
in place, and introducing a tool most of the team hasn't used before — three real costs for
no capability this project actually needs that SharePoint + Power Automate lacks.

## Two things worth changing in `phase1-plan.md`, based on this research

1. **Adaptive Cards, not plain Teams messages, from the start.** `phase1-plan.md` currently
   lists this under "Open decisions... for a later iteration." Research shows this is the
   established, well-documented pattern specifically for "whose turn is it"
   handoff-notification problems
   ([stoneridgesoftware.com](https://stoneridgesoftware.com/adaptive-cards-in-teams-and-outlook-keep-your-business-processes-moving-quickly/);
   [Microsoft Learn](https://learn.microsoft.com/en-us/power-automate/create-adaptive-cards)) —
   the card can show task title/owner/due date/status/next-action consistently and let the
   recipient act (e.g. flip Status to "In Progress") right from Teams, with the flow's
   "Post an adaptive card and wait for a response" action. Since this phase's whole reason
   for existing is fixing exactly this visibility gap, worth building it right the first
   time rather than a plain-text placeholder now and a rework later.
2. **`Workflow Tasks` needs an archiving plan from the start**, not deferred — add it as an
   explicit line item to the build-order checklist, reusing the same scheduled/verify-before-
   delete mechanism `archiving-plan.md` already designs for `Order`/`Order Items`, gated on
   `Status = Completed` (or `Blocked`+stale) rather than reinventing a separate mechanism.
