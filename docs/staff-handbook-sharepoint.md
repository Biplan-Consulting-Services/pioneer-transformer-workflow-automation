# Order Items in SharePoint: staff handbook

Everything you need for day-to-day unit tracking now that production tracking has
moved out of FRM10-12. Two parts: **doing the work**, then **the views** you do it in.

Questions, anything that looks wrong, anything at all: **Soleil Anker-Baril**, on Teams
or at soleil.anker@ermco-eci.com. Asking is always better than guessing.

---

# Part 1 · Doing the work

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

---

# Part 2 · The views

## 1. What is a view?

In SharePoint there is **one single list** of units. Everybody is looking at the same data.

A **view** (*affichage*) is a **way of looking** at that list: which columns are shown, in what
order, grouped how, sorted how, and which ones are hidden.

The picture to keep in mind: the list is the whole workbook. A view is a **pair of glasses**.
Changing glasses doesn't change what's written, only what you see.

**What follows from that, and this is the part that matters:**

- Switching views **changes nothing**. You cannot break data by clicking on a view.
- If you edit a unit in one view, **the change is in the list**, so everyone sees it, whichever
  view they happen to be using.
- If a unit "disappears" when you switch views, it has **not** been deleted. It's just filtered
  out by the glasses you're wearing.

## 2. Switching views

At the top of the list you'll see the **name of the current view** with a small arrow next to it.
Click it and the available views drop down. Click the one you want.

That's it. No saving, no confirmation.

SharePoint **remembers** the last view you opened. If you come back tomorrow and the list doesn't
look the way you expect, that's usually why: you're still on a different view. Just switch back.

## 3. The views that exist

The four you'll use day to day:

| View | Columns | What it's for |
|---|---|---|
| **Production Floor** | 6 | The main shop-floor view: where every unit is right now. Grouped by `Location`, with a colour per step. Sorted by estimated delivery date. Active units only. |
| **Planning** | 24 | The workbook's **collapsed** layout, the same columns, in the same order you see in FRM10-12 when the column groups are closed. Sorted by planned delivery date. Active units only. |
| **BO Tracking** | 23 | Back-order tracking: only units that have a BO, grouped by BO, sorted by planned tanking date. |
| **All Items** | 74 | Everything, unfiltered and ungrouped. It's the default view, and the safety net, if a unit seems to be missing elsewhere, it's here. |

### You'll see others, and that's fine

The menu also has views colleagues have made for themselves, for example
**`Angelique reunion du lundi`**. Someone has already made **their own copy of `Planning`** for
their Monday meeting: start from an existing view, use "Save view as", and give it a name of
your own.

**That's section 1 in action.** Those views are **not** copies of the data, it's the same list
seen through different glasses. Opening a colleague's view disturbs nobody and changes nothing.

And that's the point at which you can start adjusting: drop columns, change the sort, group it
differently, **in your copy**, without touching the original. See section 6.

## 4. Grouping

In **Production Floor**, units are **grouped by `Location`**: the production step: `Bobinage`,
`Assemblage`, `Four`, `Finition`, `Livraison`, `Réparation`, `Entrepôt`, and the others you
already know.

- Every unit at the same step appears together, under one heading.
- The heading shows the **number of units** in the group. That's your workload at that step, at
  a glance.
- Click the arrow on a heading to **collapse** a group you don't care about. SharePoint remembers
  it.
- If you change a unit's `Location`, it **jumps to its new group by itself**. Nothing else to do.

## 5. Sorting and filtering without breaking anything

Click a **column header** and you can sort (A→Z, newest first, and so on) or filter to particular
values.

**Those changes are yours alone, and only for the moment.** They don't change the view for anyone
else and they don't touch the data. Nobody else sees your sort.

To get back to normal: reopen the view from the menu at the top, or clear the filter from the
same column menu.

An active filter shows a **small funnel icon** in the header. If a list looks unexpectedly short,
**look for the funnel**, that's nearly always the explanation.

## 6. What not to do

**Don't modify a shared view, and don't delete one.** The four views above are used by everyone.
If you change the columns or the sort on one of them, it changes **for the whole plant**, not
just for you.

Sorting and filtering from the column headers (section 5) is safe and is not what this is about.
What to avoid is **Edit current view** and **Save view**.

**If you want a layout of your own, that's completely fine**, it's how
`Angelique reunion du lundi` came about. The one catch is that a view made that way is **public
by default**: it shows up in everyone's menu. That's no disaster, but if you'd rather keep it to
yourself, or you're not sure, **come and find me** and we'll set it up together. It takes two
minutes.

## 7. If you group your view and some groups look empty

**Nothing has been deleted.** The rows are still there, the view just stopped early, before it
reached them.

This happens when one group is much bigger than all the others. If most units have no `Location`
set, that one group can fill the entire view on its own, and the smaller groups get pushed off
the end where you can't see them. It looks exactly like missing data. It isn't.

It is not a rare edge case: **`Production Floor` grouped by `Location` has 827 units with no
Location set.** Any grouping where one value dominates has the same shape.

Two settings prevent it:

- **Group By → "By default, show groupings: Collapsed."** A collapsed group still shows its
  header and its count, so you can see every group and click into the one you want.
- **Item Limit → "Display items in batches of the specified size."** *Not* "Limit the total
  number of items returned", that one makes the view stop at the limit with no way to see the
  rest.

Two things about grouping that surprise almost everyone:

- **If you group by a column, changing that column's sort in the Sort section does nothing.**
  The order of the groups is set in the **Group By** section instead. Setting it in Sort looks
  like it should work and silently has no effect.
- **A blank date counts as the *earliest* date.** So sorting by a date puts the unplanned items
  at the top, not the bottom. If that's not what you want, ask, we'll set up a sort that puts
  blanks last.

---

## Something look wrong?

**Come ask Soleil Anker-Baril**, on Teams, or at soleil.anker@ermco-eci.com.

Before you do, these three checks resolve the large majority of cases:

1. **Check which view you're on** (top of the list). It's the number-one cause of "units are
   missing".
2. **Look for a funnel icon** in the headers, a filter someone left on by accident.
3. **Is the view grouped?** If so, see section 7, whole groups can drop off the end of a view
   without any warning that they have.

If it's none of those: if a unit is missing, a column is empty when it shouldn't be, or something just doesn't seem right. **Don't work around it and don't guess.** Come and ask. It's a new system
and finding the rough edges early is genuinely helpful.
