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

Open the **`FRM10-12 Layout`** view (*affichage*). It is the workbook's layout: the same
columns, in the same order you are used to, so you should find your way around it straight
away. Start there.

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

**`BO Tracking`** shows only units that have a back order.

You will also see views colleagues have built for themselves. Opening one changes nothing
for them, so look if it is useful. It is the same list either way.

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

The shared ones. The three FRM10-12 views are the same columns with a different filter:

| View | Columns | What it's for |
|---|---|---|
| **FRM10-12 Layout** | 24 | **Start here.** The workbook's layout: the same columns, in the same order you are used to. Sorted by planned delivery date. Active units only. |
| **FRM10-12 Completed** | 24 | Same columns, delivered units only. |
| **FRM10-12 All** | 24 | Same columns, no filter. **Check here first when a unit seems to be missing.** |
| **BO Tracking** | 23 | Back-order tracking: only units that have a BO, grouped by BO, sorted by planned tanking date. |

### You'll see others, and that's fine

The menu also has views colleagues have built for themselves. That is how it is meant to
work: start from an existing view, use "Save view as", and give it a name of your own.

**That's section 1 in action.** Those views are **not** copies of the data, it's the same list
seen through different glasses. Opening a colleague's view disturbs nobody and changes nothing.

And that's the point at which you can start adjusting: drop columns, change the sort, group it
differently, **in your copy**, without touching the original. See section 6.

## 4. Grouping

Where a view is **grouped by `Location`**, that is: the production step: `Bobinage`,
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

**A layout of your own is the goal, not the exception**, it's how the ones already in
the menu came about. The one catch is that a view made that way is **public
by default**: it shows up in everyone's menu. That's no disaster, but if you'd rather keep it to
yourself, or you're not sure, **come and find me and we'll do the first one together.** It
takes two minutes, and after that you won't need me.

## 7. If you group your view and some groups look empty

**Nothing has been deleted.** The rows are still there, the view just stopped early, before it
reached them.

This happens when one group is much bigger than all the others. If most units have no `Location`
set, that one group can fill the entire view on its own, and the smaller groups get pushed off
the end where you can't see them. It looks exactly like missing data. It isn't.

It is not a rare edge case: **grouping `Order Items` by `Location` puts 827 units under a single
"no Location" heading.** Any grouping where one value dominates has the same shape.

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
   missing", and the usual answer is that the unit was delivered, so it left
   `FRM10-12 Layout`. Look in **`FRM10-12 All`**.
2. **Look for a funnel icon** in the headers, a filter someone left on by accident.
3. **Is the view grouped?** If so, see section 7, whole groups can drop off the end of a view
   without any warning that they have.

If it's none of those: if a unit is missing, a column is empty when it shouldn't be, or something just doesn't seem right. **Don't work around it and don't guess.** Come and ask. It's a new system
and finding the rough edges early is genuinely helpful.
