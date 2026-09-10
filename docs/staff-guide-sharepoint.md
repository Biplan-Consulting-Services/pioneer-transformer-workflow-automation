# Working in SharePoint: a short guide

> ### 📋 Draft for review, publish on cutover day, then delete this box
>
> Rewritten 2026-09-09 for the Thursday cutover. The old banner said the two "don't type in
> the Excel file" instructions were **backwards**, and it was right: during the parallel run
> FRM10-12 was the only live workbook. **At cutover they become correct**, so the warning is
> gone and both instructions now say precisely what is true, including the part the old
> draft did not cover, which is that the file stays *readable* and keeps its familiar
> layout.
>
> New since the last draft: the **"What looks different"** section. Staff are not just
> moving where they type, several fields have changed from a letter typed into a cell to a
> checkbox or a dropdown, and nobody had written that down.
>
> **Do not circulate before the cutover completes.** Until then,
> `views-guide-sharepoint.md` is what to tell staff.

## What changed

Production tracking has moved out of the FRM10-12 Excel file and into SharePoint. You now
update your units directly in a list on this site, instead of opening the workbook. That
means no more waiting for someone else to close the file, and no more lost changes.

The Excel file still exists, and it still looks the same, same columns, same order, same
values. It is now a **read-only copy** that rebuilds itself from SharePoint. Open it and
read it as much as you like. Your changes go in SharePoint.

## Finding your work

Open the **Production Floor** view (*affichage*).

It shows only what matters when you are tracking an order: the unit number, the order
number, where the unit is right now, who's winding it, and when it's due. Everything else is
hidden.

Units are **grouped by Location**: the production step: `Bobinage`, `Stacking`,
`Assemblage`, `Four`, `Tanking`, `Test`, `Finition`, `Livraison`, and the others you already
know. Every unit sitting at the same step appears together under one heading, and you can
collapse a group you don't care about. It reads like a board, not a spreadsheet.

Each Location has its **own colour**, so you can see at a glance where the work is piling
up.

Within each group, the most urgent unit is at the top, sorted by due date.

Only live work shows here. Units marked delivered or cancelled drop off the view
automatically.

## Updating a unit

Click the cell. Type. Move on.

That's the whole thing. There is:

- **No save button**: it saves as you go
- **No refresh**: everyone sees your change straight away
- **No "someone else has it open"**: several people can work at once

If you change a unit's Location, it jumps to its new group by itself.

## What looks different

Most columns work exactly as they did. A few now have a proper control instead of a cell you
typed a letter into, the same information, just no longer a convention you had to remember.

| you used to type | now |
|---|---|
| `R` in **Tank**, **ISO Stack**, **ISO Coil**, **Lead Assembly** | a **checkbox**, tick it |
| `x` in **Temperature Rise**, **Impulse**, **Partial D**, **Oil Analysis**, **DB** | a **checkbox**, tick it |
| `Y` in **SFRA** | a **checkbox**, tick it |
| `Reçu` or `Plaspak` in **Frame** | a **dropdown**, pick one |
| free text in **Order Type**, **Order Step**, **Order Status**, **Indexing**, **WET-WETP**, **Client Date Status**, **Core Type**, **Family**, **Model Type**, **Oil Type**, **Modification Status**, **New model to be created** | a **dropdown**, pick one |
| a code like `TE-Se-4` in **Status** | two fields: **Step Status** (pick the step) and **Status Date** (pick the date) |

Two things worth knowing about the checkboxes:

- **Unticked means "no".** There is no third option for "not decided yet". If that distinction matters for a unit, put it in **Technical Notes** rather than leaving the box
  as a hint.
- **A dropdown does not erase what is already there.** Values that predate the
  dropdown keep displaying exactly as they were, even the odd spellings. What the
  dropdown changes is only what you can pick from now on. So if a value you need is missing from the list, that is worth reporting rather than working around.
- **The Excel copy still shows the letters.** Tick the Tank box here and the read-only
  workbook shows `R`, exactly as before. The reports built off that file are unaffected.

## Columns that come from somewhere else

Some column names start with a prefix. The prefix tells you which list the value came
from:

| prefix | comes from | what lives there |
|---|---|---|
| **Order -** | the **Order** list | facts about the whole order: the PO, the promised date, the order type, the sales notes |
| **Model -** | the **Models** list | facts about the model, shared by every unit built to it |
| **Mod. Rev. -** | the **Model Revisions** list | the technical spec: voltages, core type, oil, kVA, the drawing revision |
| **Client -** | the **Clients** list | facts about the client, such as their lead time |

There are 48 of these. You will mostly meet them in **All Items**; the day-to-day views
show only a handful.

They are **copies, kept up to date automatically**. The unit shows them so you can see an
order's PO or a model's voltage without opening another list, but the real value lives on
the other list.

**Don't type into them.** A value you type into one of these is not wrong straight away,
which is what makes it worth warning about: it sits there looking correct until the next
time somebody edits that order or model, and then it is silently replaced by whatever the
other list says. If one of them is wrong, it needs fixing on the order, the model or the
revision. Come and ask if you are not sure which.

## If you want the old layout

Open the **Planning** view instead. It is the workbook's **collapsed** layout, the same
columns, in the same order, that you see in FRM10-12 when the column groups are closed. If
you need one of the detail columns you'd normally expand to reach, they are all still there
in the **All Items** view.

## Please don't

**Don't edit the Excel file any more.** It's a mirror now: it rebuilds itself from
SharePoint, so anything typed into it is wiped on the next rebuild and never reaches
SharePoint. You will most likely find you can't type in it at all, it is set to read-only,
but if you ever find yourself able to, that is a mistake to report, not an invitation.

**Don't work around a problem.** See below.

## Something look wrong?

**Come ask Soleil Anker-Baril**, on Teams, or at soleil.anker@ermco-eci.com.

If a unit is missing, a column looks empty, or something just doesn't seem right. Don't work around it and don't guess. Come and ask. It's a new system and finding the rough edges
early is genuinely helpful.
