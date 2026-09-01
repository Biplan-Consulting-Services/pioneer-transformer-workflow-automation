# Demo cheat sheet — 09:00, 2026-09-01

**REWRITTEN 05:52 against what actually exists.** The first version assumed the cutover
completed. It did not — both build sessions were cut off by a usage limit at ~02:31. Three of
its six demo steps described things that were never built. This version only contains things
you can actually click.

For reading at 08:55 on no sleep.

---

## Say this first, in your own words

> Nothing has switched over yet. Everyone keeps working in Excel exactly as they do today.
> What I'm showing you is the new system built and working — I want your reaction before we
> move anyone onto it.

That framing is true, it costs you nothing, and it turns every "but it's not finished" into
"good, we're asking you first." **Do not describe today as a cutover.** The live FRM10-12 is
untouched and staff are unaffected — that is a feature, not an apology.

---

## The click-path, in order — ONLY these

**1. `Production Floor` view** (`Order Items`) — the centrepiece
Grouped by `Location` with colour chips. Say: *this is the live production board — every unit,
sorted by where it is right now.* Collapse a group to show it's interactive. This runs on the
real 1,038 rows, so it is not a mock-up.

**2. Edit a unit, live** — the whole pitch in five seconds
Click a cell, change it, move on. No save, no refresh, no file lock. Say out loud that several
people can do this simultaneously, which is impossible in the workbook today. **This is your
strongest moment — spend time here, not on the tour.**

**3. `Planning` view** — for the workbook loyalists
Built from the Orders sheet's own outline level 1, so it is the collapsed column set they
already work in, in the same order. Same columns, new home.

**4. The staff guides** (EN + FR)
Show that the guide exists in French as well as English, using the words already on their
screens — `Bobinage`, `En cours`, `Reçu`. Signals this is planned, not improvised.

---

## DO NOT DEMO THESE — they do not exist yet

- **The sales-app fan-out.** Never opened in Studio. The formula is written and reviewed, not
  installed. If asked: *"written, not yet wired in — it's the next piece."*
- **The viewer workbook.** Not deployed. Worse, a refresh right now would blank
  `Tanking Date` and `Delivery Date`, because those columns were repointed to new fields that
  the transfer run has not populated yet. **Do not open and refresh it in the room.**
- **The site home page.** Started, not finished. Navigate to the views from the list itself.

---

## The two honest facts, if pressed

1. **The 7 new columns are empty.** They were created at 02:20 and the run that fills them
   never happened. They are 7 of ~68 columns — if nobody points at them, don't raise it.
2. **`Planning` sorts by `Planned Delivery Date`, which is one of those empty columns**, so
   that sort currently does nothing. Sort by another column live if it looks odd.

---

## What's next — have a date, not a vague answer

The remaining work is one flow fix and one 45-minute transfer run, both understood and
specified. Give a week, not a day, and don't commit to a date in the room without checking the
usage limit that stopped tonight.

---

## Known gaps — so nothing surprises you on screen

**Blank by design. Don't apologise for these, explain them.**

- **`Duplicate`** — never migrated anywhere. Superseded by the EngineeringChangeOrders /
  ModelChanges tracker.
- **`Duplicate Order`** — deliberately frozen. Live data showed it self-referencing
  `PO Item #`, which contradicts what the field was designed to mean. It needs a requirements
  decision, not a data patch.

**Mapped but empty in the live data** — these read blank because nobody has filled them in,
not because anything is broken:

- `Sales Notes` — confirmed 100% blank as of the 2026-08-18 check
- `Primary Voltage` / `Secondary Voltage` — existing rows are blank; the field type was never
  confirmed against a populated value

**Tier 2 items that didn't land tonight:**

> _Fill this in before you leave. If everything landed, delete this block._
>
> - [ ] Reconciliation — if not done, some units showing as `Active` are actually delivered or
>       cancelled. If asked about row counts, say the cleanup pass runs this week
> - [ ] ______________________________________________
> - [ ] ______________________________________________

---

## Likely questions

**"What happens to FRM09 / the Winding workbook?"**
**Right now: absolutely nothing has changed.** FRM10-12 is untouched, so FRM09 is untouched.

When the switch does happen, it still won't change: FRM09 finds FRM10-12 through the `Index`
list rather than a fixed path, and the replacement goes to that exact same path — so it
resolves automatically with no edit to FRM09 at all. Same for BO Manager.

*(Worth knowing, don't volunteer it: this was the single biggest risk the audit found.
Deploying anywhere else would have left both silently reading a frozen file — no error, just
data that quietly stops moving. Now designed out.)*

**"Who will refresh it?"**
Three owners, so it doesn't die when one person is away: you, Angelique, and an automated bot.
Safe in a way it never was before — the file becomes a full rebuild from SharePoint with no
hand-typed data to lose, and the August corruption came from people editing *while* a refresh
ran, which can't happen once it's read-only to staff. **Future tense — none of this is live.**

**"What about Power BI?"**
Be careful here. The planning docs say Power BI reads the Excel Archive directly and needs no
repointing, and no Power BI files are tracked in the repo. **This was not verified against the
live tenant.** If someone in the room owns a report that reads FRM10-12 directly, that's worth
knowing — invite them to say so rather than asserting nothing is affected.

**"When does production tracking move to Monday.com?"**
That's the plan from the August meeting, and this work supports it: SharePoint's `Order Items`
stays the authoritative database that reporting runs against, with Monday as the working layer
on top. **The SharePoint stage-stamping automation is still running as normal** — switching it
off is part of the remaining work, not something already done. Say "when we move, we'll park a
disabled copy so it's one click to come back" — future tense.

**"What's next / when does the rest arrive?"**
Phase 1 — the `Workflow Tasks` piece — automates the front of the order process and notifies
whoever's turn it is to act, which is the other big pain point today: nobody can see whose
turn it is on an order. Fully specified, not yet built.

---

## If it breaks in the room

**The good news: almost nothing can break, because almost nothing changed.** No flow ran, no
data was written, the workbook is untouched and the sales app was never edited. The blast
radius this morning is a SharePoint list and two views.

- **A view looks empty** → check the filter is `Item Status = Active` before assuming data
  loss. Delivered and cancelled units are meant to disappear.
- **A column reads blank** → most likely one of the 7 created at 02:20 and not yet populated.
  Say "that fills on the migration run" and move on.
- **Someone asks to see the Excel side** → decline politely. *"It's mid-change, I don't want to
  show you something half-done."* True, and better than a blank column on screen.
- **Anything else** → say you'll look into it and move on. Don't debug in the room.
- **Anything else** → say you'll look into it and move on. Don't debug in the room.
