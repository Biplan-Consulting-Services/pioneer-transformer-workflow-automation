# Demo cheat sheet — 09:00, 2026-09-01

For reading at 08:55 on no sleep. Click-path first, then the things that could surprise you.

---

## The click-path, in order

**1. Site home page**
Start here, not in a list. It's the thing staff will actually land on. Point at the links in
the left-hand nav — that's their way in from now on.

**2. Production Floor view** (`Order Items`)
The centrepiece. Show it grouped by `Location` with the colour chips. Say the line: *this is
the shop floor board — every unit, sorted by where it is right now.* Collapse a group to show
it's interactive. Note that delivered and cancelled units drop off automatically.

**3. Edit a unit, live**
Click a cell, change it, move on. No save, no refresh, no file lock. This is the whole pitch
in five seconds — say out loud that several people can do this at the same time, which was
impossible before.

**4. Planning view**
For the sceptics in the room who like the workbook. Same columns, same order, new home.

**5. Create an order in the sales Power App**
Hit Save and show the unit rows appearing in `Order Items` on their own. This is the piece
that didn't exist before tonight — previously nothing created Order Items for a new order at
all.

**6. The viewer workbook**
Close on familiarity: the Excel file staff know, showing the same data, now read-only and
rebuilding itself from SharePoint.

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
Nothing. It keeps working exactly as before. It finds FRM10-12 through the `Index` list rather
than a fixed path, and the new file was deployed to that same path — so it resolves to the new
one automatically, with no change to FRM09 at all. Same answer for BO Manager.

*(Worth knowing but don't volunteer it: this was the single biggest risk found in the audit.
Deploying anywhere else would have left both of them silently reading a frozen file — no
error, just data that quietly stops moving.)*

**"Who refreshes it now?"**
A named person, once each morning. Safe to do now in a way it never was before — the file is a
full rebuild from SharePoint with no hand-typed data to lose, and the corruption incident in
August came from people editing while a refresh ran, which can't happen once it's read-only.
Automating it is on the list.

**"What about Power BI?"**
Be careful here. The planning docs say Power BI reads the Excel Archive directly and needs no
repointing, and no Power BI files are tracked in the repo. **This was not verified against the
live tenant.** If someone in the room owns a report that reads FRM10-12 directly, that's worth
knowing — invite them to say so rather than asserting nothing is affected.

**"When does production tracking move to Monday.com?"**
That's the plan from the August meeting, and tonight's work supports it: SharePoint's
`Order Items` stays the authoritative database that reporting runs against, with Monday as the
working layer on top. The SharePoint stage-stamping automation was switched off tonight in
anticipation — and a disabled copy is parked, so if Monday doesn't work out it can be turned
back on in one click.

**"What's next / when does the rest arrive?"**
Phase 1 — the `Workflow Tasks` piece — automates the front of the order process and notifies
whoever's turn it is to act, which is the other big pain point today: nobody can see whose
turn it is on an order. Fully specified, not yet built.

---

## If it breaks in the room

- **The sales app misbehaves** → Power Apps keeps version history. Restore the previous version
  immediately. Sales being able to create orders matters more than the fan-out demo.
- **The viewer looks wrong** → the pre-overwrite snapshot is in `FRM10-12/live-workbook-data/`.
  Say you'll restore it after the meeting; don't try to fix a workbook live in front of people.
- **A view looks empty** → check the filter is `Item Status = Active` before assuming data loss.
  Delivered and cancelled units are meant to disappear.
- **Anything else** → say you'll look into it and move on. Don't debug in the room.
