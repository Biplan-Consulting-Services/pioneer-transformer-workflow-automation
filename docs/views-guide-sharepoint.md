# SharePoint views — how they work

*French version: `views-guide-sharepoint-fr.md`. Both have the same structure, section by
section.*

> **Where things stand today (2026-09-04).** We are in a **parallel run**: **FRM10-12 is still
> live and you keep using it exactly as before.** Nothing about your daily work changes yet.
> SharePoint is filling up alongside it so it is ready on the day we switch over properly. This
> guide explains how to read what's there — not how to change the way you work.

---

## 1. What is a view?

In SharePoint there is **one single list** of units. Everybody is looking at the same data.

A **view** (*affichage*) is a **way of looking** at that list: which columns are shown, in what
order, grouped how, sorted how, and which ones are hidden.

The picture to keep in mind: the list is the whole workbook. A view is a **pair of glasses**.
Changing glasses doesn't change what's written — only what you see.

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
| **Planning** | 24 | The workbook's **collapsed** layout — the same columns, in the same order you see in FRM10-12 when the column groups are closed. Sorted by planned delivery date. Active units only. |
| **BO Tracking** | 23 | Back-order tracking: only units that have a BO, grouped by BO, sorted by planned tanking date. |
| **All Items** | 74 | Everything, unfiltered and ungrouped. It's the default view, and the safety net — if a unit seems to be missing elsewhere, it's here. |

### You'll see others, and that's fine

The menu also has views colleagues have made for themselves — for example
**`Angelique reunion du lundi`**. Someone has already made **their own copy of `Planning`** for
their Monday meeting: start from an existing view, use "Save view as", and give it a name of
your own.

**That's section 1 in action.** Those views are **not** copies of the data — it's the same list
seen through different glasses. Opening a colleague's view disturbs nobody and changes nothing.

And that's the point at which you can start adjusting: drop columns, change the sort, group it
differently — **in your copy**, without touching the original. See section 6.

## 4. Grouping

In **Production Floor**, units are **grouped by `Location`** — the production step: `Bobinage`,
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
**look for the funnel** — that's nearly always the explanation.

## 6. What not to do

**Don't modify a shared view, and don't delete one.** The four views above are used by everyone.
If you change the columns or the sort on one of them, it changes **for the whole plant**, not
just for you.

Sorting and filtering from the column headers (section 5) is safe and is not what this is about.
What to avoid is **Edit current view** and **Save view**.

**If you want a layout of your own, that's completely fine** — it's how
`Angelique reunion du lundi` came about. The one catch is that a view made that way is **public
by default**: it shows up in everyone's menu. That's no disaster, but if you'd rather keep it to
yourself, or you're not sure, **come and find me** and we'll set it up together. It takes two
minutes.

## 7. Something look wrong?

**Come ask Soleil Anker-Baril** — on Teams, or at soleil.anker@ermco-eci.com.

Before you do, these two checks resolve the large majority of cases:

1. **Check which view you're on** (top of the list). It's the number-one cause of "units are
   missing".
2. **Look for a funnel icon** in the headers — a filter someone left on by accident.

If it's neither: if a unit is missing, a column is empty when it shouldn't be, or something just
doesn't seem right — **don't work around it and don't guess.** Come and ask. It's a new system
and finding the rough edges early is genuinely helpful.
