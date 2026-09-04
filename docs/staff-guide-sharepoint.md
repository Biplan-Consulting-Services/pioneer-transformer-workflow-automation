# Working in SharePoint — a short guide

> # 🛑 DO NOT HAND THIS OUT YET — as of 2026-09-04 it is not true
>
> **This guide describes the state *after* the cutover. The cutover has not happened.**
>
> It was written on 2026-09-01 for a cutover that was cut short: step **D5**, which would have
> put the read-only mirror in place, never ran. As of **2026-09-04** we are in a **parallel
> run**:
>
> - **FRM10-12 is still live, and staff must keep using it.** It is not a mirror, it is not
>   read-only, and nothing typed into it gets wiped.
> - `Order Items` in SharePoint is filling up alongside it — the order-creation app now creates
>   rows there too — but it is **not** the system of record yet.
>
> **The two instructions below that would cause real harm if followed today** are "**Don't type
> in it**" and "**Don't edit the Excel file any more … anything typed into it will be wiped**".
> Both are exactly backwards right now. Following them would stop staff updating the only
> workbook that is actually live.
>
> **Everything else in this guide is good and stays**, and the whole thing becomes correct on
> the day the cutover completes. Until then: **do not paste this onto the home page and do not
> circulate it.** For what to tell staff *today*, see `views-guide-sharepoint.md`.
>
> *(Flagged 2026-09-03. See `../../BUILD-NIGHT-2026-09-03.md` KEY FACTS.)*

## What changed

Production tracking has moved out of the FRM10-12 Excel file and into SharePoint. You now
update your units directly in a list on this site, instead of opening the workbook. This means
no more waiting for someone else to close the file, and no more lost changes.

The Excel file still exists, and it still looks the same — but it is now a **read-only copy**
that rebuilds itself from SharePoint. Look at it all you like. Don't type in it.

## Finding your work

Open the **Production Floor** view (*affichage*).

It shows only what matters when you are tracking an order: the unit number, the order number,
where the unit is
right now, who's winding it, and when it's due. Everything else is hidden.

Units are **grouped by Location** — the production step: `Bobinage`, `Stacking`, `Assemblage`,
`Four`, `Tanking`, `Test`, `Finition`, `Livraison`, and the others you already know. Every unit
sitting at the same step appears together under one heading, and you can collapse a group you
don't care about. It reads like a board, not a spreadsheet.

Each Location has its **own colour**, so you can see at a glance where the work is piling up.

Within each group, the most urgent unit is at the top — sorted by due date.

Only live work shows here. Units marked delivered or cancelled drop off the view automatically.

## Updating a unit

Click the cell. Type. Move on.

That's the whole thing. There is:

- **No save button** — it saves as you go
- **No refresh** — everyone sees your change straight away
- **No "someone else has it open"** — several people can work at once

If you change a unit's Location, it jumps to its new group by itself.

## If you want the old layout

Open the **Planning** view instead. It is the workbook's **collapsed** layout — the same
columns, in the same order, that you see in FRM10-12 when the column groups are closed. If you
need one of the detail columns you'd normally expand to reach, they are all still there in the
**All Items** view.

## Please don't

**Don't edit the Excel file any more.** It's a mirror now. Anything typed into it will be
wiped the next time it rebuilds, and it won't reach SharePoint. All real changes happen here.

## Something look wrong?

**Come ask Soleil Anker-Baril** — on Teams, or at soleil.anker@ermco-eci.com.

If a unit is missing, a column looks empty, or something just doesn't seem right — don't work
around it and don't guess. Come and ask. It's a new system and finding the rough edges early is
genuinely helpful.
