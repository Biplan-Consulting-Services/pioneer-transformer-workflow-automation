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

## What happens to the Excel file

It is still there, and it still looks the same: same columns, same order, same values. It
is now a **read-only copy** that rebuilds itself from SharePoint, so open it and read it as
much as you like.

**The data only travels one way, from SharePoint into the file.** Nothing typed into the
file reaches SharePoint, and the next rebuild overwrites it. If you want to make changes,
you need to make them in the SharePoint lists.

## Finding your work

The list opens in the **`FRM10-12 Layout`** view (*affichage*), which is the workbook's
layout: the same columns, in the same order you are used to. You should find your way
around it straight away, and there is nothing to pick or set up first.

**Then make one of your own.** `FRM10-12 Layout` has everything, which means it also has a
lot you personally never look at. You can build a view with just the columns you need,
sorted and grouped the way you think about the work, and it will be there every time you
open the list.

🔑 **Come and do it with me the first time.** It takes about two minutes, and there is one
setting worth getting right at the start: a view you make is **public by default**, so it
turns up in everyone's menu. That is not a disaster, but it is easier to decide up front
than to tidy up later. After the first one you will not need me.

**The other views**

All three FRM10-12 views have the same columns in the same order. Only the filter differs:

| view | shows |
|---|---|
| **`FRM10-12 Layout`** | live work: everything not yet delivered |
| **`FRM10-12 Completed`** | units that have been delivered |
| **`FRM10-12 All`** | everything, delivered or not |

**`FRM10-12 All`** is the one to check when a unit seems to have vanished. Nine times out
of ten it has simply been delivered and dropped out of `FRM10-12 Layout`.

**`BO Tracking`** shows the same units grouped by BO status, so what is waiting on a
part is together in one place.

You will also see views colleagues have built for themselves. Opening one changes nothing
for them, so look if it is useful. It is the same list either way.

## Updating a unit

Click the cell. Type. Move on.

That's the whole thing. There is:

- **No save button**: it saves as you go
- **No refresh**: everyone sees your change straight away
- **No "someone else has it open"**: several people can work at once

## What looks different

Most columns work exactly as they did. A few now have a proper control instead of a cell you
typed a letter into, the same information, just no longer a convention you had to remember.

| you used to type | now |
|---|---|
| `R` in **Tank**, **ISO Stack**, **ISO Coil**, **Lead Assembly** | a **checkbox** |
| `x` in **Temperature Rise**, **Impulse**, **Partial D**, **Oil Analysis**, **DB** | a **checkbox** |
| `Y` in **SFRA** | a **checkbox** |
| `Reçu` or `Plaspak` in **Frame** | a **dropdown** |
| free text in **Order Type**, **Order Step**, **Order Status**, **Indexing**, **WET-WETP**, **Client Date Status**, **Core Type**, **Family**, **Model Type**, **Oil Type**, **Modification Status**, **New model to be created** | a **dropdown** |
| a code like `TE-Se-4` in **Status** | two fields: **Step Status** (pick the step) and **Status Date** (pick the date) |

A few things worth knowing:

- **Unticked means "no".** There is no third option for "not decided yet". If you need
  that option, come and see me.
- **A dropdown does not erase what is already there.** Values that predate the
  dropdown keep displaying exactly as they were, even the odd spellings. What the
  dropdown changes is only what you can pick from now on. So if a value you need is missing from the list, that is worth reporting rather than working around.
- **The Excel copy still shows the letters.** Tick the Tank box here and the read-only
  workbook shows `R`, exactly as before. The reports built off that file are unaffected.
- **If a column doesn't work the way your job needs it to, come and tell me.** These
  choices were made column by column, from how the workbook was being used, and some of
  them will turn out to be wrong for work I didn't see. A checkbox that needs a third
  state, a dropdown missing an option, a field that should accept free text: all of that
  can be changed. It is a settings change, not a rebuild. **Don't work around it** by
  putting the real answer somewhere else, because then nobody knows the column is wrong.

## Columns that come from somewhere else

Some column names start with a prefix. The prefix tells you which list the value came
from:

| prefix | comes from | what lives there |
|---|---|---|
| **Order -** | the **Order** list | facts about the whole order: the PO, the promised date, the order type, the sales notes |
| **Model -** | the **Models** list | facts about the model, shared by every unit built to it |
| **Mod. Rev. -** | the **Model Revisions** list | the technical spec: voltages, core type, oil, kVA, the drawing revision |
| **Client -** | the **Clients** list | facts about the client, such as their lead time |

There are 48 of these. Most of them are hidden in the views you work in day to day; you meet the whole set
only if you go looking.

They are **copies, kept up to date automatically**. The unit shows them so you can see an
order's PO or a model's voltage without opening another list, but the real value lives on
the other list.

**Don't type into them.** This is not where the data lives. Anything entered here is
replaced by the value from the source list as soon as that list changes. If one of them is
wrong, it needs fixing on the order, the model or the revision. Come and ask if you are not
sure which.

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
