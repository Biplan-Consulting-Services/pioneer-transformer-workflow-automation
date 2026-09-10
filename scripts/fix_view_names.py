# -*- coding: utf-8 -*-
"""Bring the guides in line with the views that actually exist.

    python scripts/fix_view_names.py

The views on `Order Items`, confirmed by the user 2026-09-10:

    FRM10-12 Layout            the one everybody starts in
    BO Tracking                back orders
    Angelique bobinage         one person's own
    Angelique reunion du lundi one person's own

`Production Floor` is gone, and it was the view the guides told people to open. `All
Items` still exists as SharePoint's default but is not somewhere anyone works.

Two changes follow from that:

  1. Every `Production Floor` reference is wrong, not just stale. The grouping section
     and the empty-groups warning both used it as their worked example.

  2. The guides used `Angelique reunion du lundi` by name as the example of a personal
     view. The user asked not to. It is somebody's own workspace, and holding it up as
     the model invites people to open it, copy it, or wonder why theirs should look like
     hers. The behaviour is worth teaching; the name is not.
"""
import io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(os.path.dirname(HERE), "docs")

EN_OTHER = """**The other views**

- **`BO Tracking`** shows only units that have a back order.
- You will also see views colleagues have built for themselves. Opening one changes
  nothing for them, so look if it is useful. It is the same list either way.

"""

FR_OTHER = """**Les autres affichages**

- **`BO Tracking`** montre seulement les unités qui ont un back order.
- Vous verrez aussi des affichages que des collègues se sont bâtis. En ouvrir un ne change
  rien pour eux, alors regardez si ça vous sert. C'est la même liste de toute façon.

"""

REPL = {
 "staff-guide-sharepoint.md": [
  # the "other views" block, Production Floor and All Items out
  (re.compile(r"\*\*The other views that already exist\*\*\n\n(?:- .*\n(?:  .*\n)*)+\n", re.M), EN_OTHER),
  ("You will mostly meet them in **All Items**; the day-to-day views\nshow only a handful.",
   "Most of them are hidden in the views you work in day to day; you meet the whole set\nonly if you go looking."),
 ],
 "staff-guide-sharepoint-fr.md": [
  (re.compile(r"\*\*Les autres affichages qui existent déjà\*\*\n\n(?:- .*\n(?:  .*\n)*)+\n", re.M), FR_OTHER),
  ("Vous les croiserez surtout dans **All Items**; les affichages du quotidien\nn'en montrent qu'une poignée.",
   "La plupart sont masquées dans les affichages où vous travaillez au quotidien; vous ne\nvoyez l'ensemble que si vous allez le chercher."),
 ],
 "views-guide-sharepoint.md": [
  (re.compile(r"\| \*\*Production Floor\*\* \| 6 \|[^\n]*\n"), ""),
  (re.compile(r"\| \*\*All Items\*\* \| 74 \|[^\n]*\n"),
   "| **BO Tracking** | 23 | Back-order tracking: only units that have a BO, grouped by BO, sorted by planned tanking date. |\n"),
  (re.compile(r"\| \*\*BO Tracking\*\* \| 23 \| Back-order tracking: only units that have a BO, grouped by BO, sorted by planned tanking date\. \|\n(?=\| \*\*BO Tracking\*\*)"), ""),
  ("The four you'll use day to day:", "The two shared ones:"),
  ("In **Production Floor**, units are **grouped by `Location`**:",
   "Where a view is **grouped by `Location`**, that is:"),
  ("**`Production Floor` grouped by `Location` has 827 units with no\nLocation set.**",
   "**grouping `Order Items` by `Location` puts 827 units under a single\n\"no Location\" heading.**"),
 ],
 "views-guide-sharepoint-fr.md": [
  (re.compile(r"\| \*\*Production Floor\*\* \| 6 \|[^\n]*\n"), ""),
  (re.compile(r"\| \*\*All Items\*\* \| 74 \|[^\n]*\n"),
   "| **BO Tracking** | 23 | Suivi des back orders : seulement les unités qui ont un BO, regroupé par BO, trié par date d'encuvage prévue. |\n"),
  (re.compile(r"\| \*\*BO Tracking\*\* \| 23 \| Suivi des back orders[^\n]*\|\n(?=\| \*\*BO Tracking\*\*)"), ""),
  ("Dans **Production Floor**, les unités sont **regroupées par `Location`** :",
   "Quand un affichage est **regroupé par `Location`**, c'est-à-dire :"),
  ("**`Production Floor` regroupé par `Location` a 827 unités sans\nLocation.**",
   "**regrouper `Order Items` par `Location` met 827 unités sous une seule\nrubrique « sans Location ».**"),
 ],
}

# Named personal views, replaced with the behaviour rather than the person.
ANON = [
 ("The menu also has views colleagues have made for themselves, for example\n**`Angelique reunion du lundi`**. Someone has already made **their own copy of `FRM10-12 Layout`** for\ntheir Monday meeting: start from an existing view, use \"Save view as\", and give it a name of\nyour own.",
  "The menu also has views colleagues have built for themselves. That is how it is meant to\nwork: start from an existing view, use \"Save view as\", and give it a name of your own."),
 ("it's how\n`Angelique reunion du lundi` came about.",
  "it's how the ones already in\nthe menu came about."),
 ("Il y a aussi des affichages que des collègues se sont créés, par exemple\n**`Angelique reunion du lundi`**. Quelqu'un s'est déjà fait **sa propre copie de `FRM10-12 Layout`**\npour sa réunion du lundi : partez d'un affichage existant, faites « Enregistrer l'affichage\nsous », et donnez-lui un nom à vous.",
  "Il y a aussi des affichages que des collègues se sont bâtis. C'est exactement l'idée :\npartez d'un affichage existant, faites « Enregistrer l'affichage sous », et donnez-lui un\nnom à vous."),
 ("c'est comme ça que `Angelique reunion du lundi` a été fait.",
  "c'est comme ça que ceux déjà dans le menu ont été faits."),
]


def main():
    for f, reps in REPL.items():
        p = os.path.join(DOCS, f)
        s = io.open(p, encoding="utf-8").read().replace("\r\n", "\n")
        n = 0
        for a, b in reps:
            if hasattr(a, "sub"):
                s2 = a.sub(b, s, count=1)
            else:
                s2 = s.replace(a, b, 1)
            if s2 != s:
                n += 1
            s = s2
        for a, b in ANON:
            if a in s:
                s = s.replace(a, b, 1); n += 1
        io.open(p, "w", encoding="utf-8", newline="\r\n").write(s)
        left = s.count("Production Floor") + s.count("Angelique")
        print("  %-32s %2d edits, %d Production Floor/Angelique left" % (f, n, left))
    return 0


if __name__ == "__main__":
    sys.exit(main())
