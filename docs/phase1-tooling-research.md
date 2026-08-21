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

### 5. Third-party tools (monday.com, Smartsheet, etc.) — viable only as a synced presentation layer, not as the system of record

Looked at properly this round, not just waved off. Two real options surfaced:

**monday.com** — has a Power Automate connector, so a `Workflow Tasks` ↔ monday.com board
sync is genuinely buildable, the same way Planner Premium was considered as a synced *view*
above. But several real costs stack up:
- The connector is a **Premium** Power Automate connector
  ([apps-for-monday.com](https://apps-for-monday.com/apps/10000270/)) — extra cost beyond
  what's already licensed, on top of monday.com's own per-seat pricing.
- Microsoft's own listing shows the connector still in **(Preview)**
  ([learn.microsoft.com](https://learn.microsoft.com/nb-no/Connectors/monday)) — not
  GA, a real maturity/reliability flag for something this project would depend on daily.
- One integrator states plainly that "Power Automate integration is not natively offered by
  monday.com and requires third-party developer add-ons"
  ([dsapps.dev](https://www.dsapps.dev/compare/monday-sharepoint-vs-power-automate/)) — the
  sync path runs through an extra third-party layer (e.g. David Simpson Apps' SharePoint
  integration), not a first-party Microsoft-to-monday bridge.
- monday.com caps automations at 25,000/month even on its top plan
  ([monday.com blog](https://monday.com/blog/project-management/monday-com-vs-smartsheet-2026/)) —
  unlikely to matter at Pioneer's volume, but worth knowing it's not unlimited.

**Smartsheet** — a plausible alternative to monday.com in this comparison specifically
because reviewers repeatedly frame it as the better Microsoft-365-native fit: *"enterprise
teams already using... heavy Microsoft Office 365 workflows will find Smartsheet's
integrations more valuable"*, and its spreadsheet-grid model is called out as a good match
for *"manufacturing workflows... detailed scheduling and milestone tracking"* specifically
([tech.co](https://tech.co/project-management-software/smartsheet-vs-monday);
[monday.com blog](https://monday.com/blog/project-management/monday-com-vs-smartsheet-2026/)) —
plus unlimited automations on its Business plan, vs. monday.com's capped 25,000/month.

**Verdict**: real options if the actual want is a nicer Kanban/timeline board and the team
is willing to pay for extra seats + a Premium connector — but they'd solve a problem
(prettier visualization) that Adaptive Cards + a filtered SharePoint view already solve
inside licensing Pioneer already has, while adding a second synced system that can drift out
of step with `Order`/`Order Items` and a maintenance dependency on a third-party connector.
Not recommended as the system of record for the same reason Planner Premium isn't: it would
sit *beside* the native-Lookup architecture already proven in this tenant, not inside it.
Worth revisiting only if, after Phase 1 ships, staff specifically ask for board/timeline
visualization the SharePoint list view genuinely can't give them.

## What an Adaptive Card actually is, concretely

Since this is the specific mechanism being proposed for notifications, worth explaining
fully rather than just naming it.

**The technology**: an Adaptive Card is a small JSON document describing a UI — text,
images, input fields, and buttons — that gets rendered *natively* by whatever app displays
it (Teams, Outlook, even a bot), so the same JSON payload looks and behaves like a normal
Teams card in Teams, a normal Outlook card in Outlook, without writing app-specific UI code
([learn.microsoft.com](https://learn.microsoft.com/en-us/adaptive-cards/);
[imrizwan.com](https://imrizwan.com/blog/adaptive-cards-m365-developer-guide)). The JSON has
two main parts: a `body` array (the layout — `TextBlock` for text, `ColumnSet`/`Container`
for layout structure, `Image`) and an `actions` array (the buttons — `Action.Submit` sends
data back to whatever triggered the card, `Action.OpenUrl` opens a link).

**A concrete card for this project** — what a `Planning Schedule` task notification could
actually look like, sent to Scheduling when both Preliminary Review tasks complete (the
fan-out point, updated 2026-08-21 — see `phase1-plan.md`'s reorder section):

```json
{
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    { "type": "TextBlock", "text": "Planning Schedule needed", "weight": "Bolder", "size": "Medium" },
    { "type": "TextBlock", "text": "Order 21865-1/5", "isSubtle": true },
    {
      "type": "FactSet",
      "facts": [
        { "title": "Step", "value": "Planning Schedule" },
        { "title": "Department", "value": "Scheduling" },
        { "title": "Status", "value": "Not Started" }
      ]
    }
  ],
  "actions": [
    { "type": "Action.Submit", "title": "Mark as Started", "data": { "itemId": 4821, "newStatus": "In Progress" } },
    { "type": "Action.OpenUrl", "title": "Open in SharePoint", "url": "https://ermcopower.sharepoint.com/..." }
  ]
}
```

**How it plugs into the flow, mechanically**: Power Automate's action is literally called
**"Post an Adaptive Card to a Teams user (or channel) and wait for a response"**
([learn.microsoft.com](https://learn.microsoft.com/en-us/power-automate/create-adaptive-cards)).
The word "wait" is functional, not cosmetic — the flow run genuinely pauses at that step
until the recipient clicks a button in Teams. Once they click "Mark as Started," the
`data` payload from that button (`itemId: 4821, newStatus: "In Progress"`) becomes available
as dynamic content in every step *after* the wait action
([community.dynamics.com](https://community.dynamics.com/blogs/post/?postid=d055f96f-b8c5-4f89-8aab-cd895ac53cab)) —
so the very next flow step is just "Update item" on `Workflow Tasks`, setting `Status` to
whatever came back in `newStatus`. No polling, no separate "did they click it yet" check —
the flow is asleep until they act, then wakes up already holding what they clicked. Note the
`Action.Submit` buttons specifically **require** the "wait for a response" variant of the
action — a plain "Post message" card can't collect a response at all
([community.powerplatform.com](https://community.powerplatform.com/forums/thread/details/?threadid=e01ee0c2-21bd-ef11-b8e8-7c1e52025ab5)).

**Authoring**: hand-writing the JSON above works fine for something this size, but Microsoft
also ships a visual [Adaptive Cards
Designer](https://learn.microsoft.com/en-us/adaptive-cards/) (drag-and-drop, live preview
against the actual Teams/Outlook rendering) if a more complex card is wanted later — not
needed to get started.

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
