# -*- coding: utf-8 -*-
"""Stitch the four staff guides into one handbook per language.

    python scripts/gen_staff_handbook.py

    docs/staff-guide-sharepoint.md   + views-guide-sharepoint.md
        -> docs/staff-handbook-sharepoint.md
    docs/staff-guide-sharepoint-fr.md + views-guide-sharepoint-fr.md
        -> docs/staff-handbook-sharepoint-fr.md

WHY STITCHED AND NOT REWRITTEN
  The four guides were written and reviewed line by line. Merging them by hand would
  put that wording at risk for no gain, and would leave two copies of every sentence
  to keep in step. So this takes the reviewed bodies verbatim, drops the
  pre-publication banners (everything above the first `##`), reorders into two parts,
  and keeps a single "something look wrong" at the end.

  EDIT THE SOURCE GUIDES, NOT THE HANDBOOKS. The handbooks are build output.

  ⚠️ NO EM DASHES in anything staff read. They are a tell of machine-written text and
  nobody writes a work guide with them; the user asked for them gone on 2026-09-10 and
  `dedash_guides.py` took 84 out of the four source guides. The title and intro strings
  BELOW are part of what staff read, so they follow the same rule. A colon or a comma
  does the job in almost every case, and two sentences want a full stop.
"""
import io, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(os.path.dirname(HERE), "docs")

CFG = [
    dict(lang="en",
         staff="staff-guide-sharepoint.md", views="views-guide-sharepoint.md",
         out="staff-handbook-sharepoint.md",
         title="# Order Items in SharePoint: staff handbook",
         intro=("FRM10-12 has moved out of Excel and into SharePoint. Your units are now in a\n"
                "SharePoint list called **Order Items**.\n\n"
                "**Part 1** is how to update a unit. **Part 2** is how the views work, so you can set\n"
                "the list up the way you want it.\n\n"
                "If you have questions or see anything wrong, you can contact\n"
                "**Soleil Anker-Baril** on Teams or at soleil.anker@ermco-eci.com. Asking is always\n"
                "better than guessing.\n"),
         p1="# Part 1 · Doing the work", p2="# Part 2 · The views",
         ask_staff="Something look wrong"),
    dict(lang="fr",
         staff="staff-guide-sharepoint-fr.md", views="views-guide-sharepoint-fr.md",
         out="staff-handbook-sharepoint-fr.md",
         title="# Order Items dans SharePoint : guide du personnel",
         intro=("FRM10-12 sort d'Excel et s'en va dans SharePoint. Vos unités sont maintenant dans\n"
                "une liste SharePoint qui s'appelle **Order Items**.\n\n"
                "La **partie 1**, c'est comment mettre une unité à jour. La **partie 2**, c'est comment\n"
                "fonctionnent les affichages, pour que vous puissiez organiser la liste à votre goût.\n\n"
                "Si vous avez des questions ou si vous voyez quelque chose d'anormal, vous pouvez\n"
                "contacter **Soleil Anker-Baril** sur Teams ou à soleil.anker@ermco-eci.com.\n"
                "Demander vaut toujours mieux que deviner.\n"),
         p1="# Partie 1 · Faire le travail", p2="# Partie 2 · Les affichages",
         ask_staff="Quelque chose"),
]


def body(path):
    """Everything from the first level-2 heading on: drops title, banners, notes."""
    s = io.open(path, encoding="utf-8").read().replace("\r\n", "\n")
    return s[s.index("\n## ") + 1:].rstrip() + "\n"


def cut(text, heading_prefix):
    """Remove one '## <prefix>...' section and return (rest, removed)."""
    m = re.search(r"^## +%s.*?$" % re.escape(heading_prefix), text, re.M)
    if not m:
        return text, ""
    nxt = re.search(r"^## ", text[m.end():], re.M)
    end = m.end() + (nxt.start() if nxt else len(text) - m.end())
    return text[:m.start()] + text[end:], text[m.start():end]


def main():
    for c in CFG:
        b1 = body(os.path.join(DOCS, c["staff"]))
        b2 = body(os.path.join(DOCS, c["views"]))
        # both guides close with their own "come and ask" section; keep one, at the end
        b1, ask1 = cut(b1, c["ask_staff"])
        b2, ask2 = cut(b2, "8.")
        tail = ask2 if ask2.strip() else ask1
        tail = re.sub(r"^## +\d*\.? *", "## ", tail, flags=re.M)
        parts = [c["title"], "", c["intro"], "---", "", c["p1"], "", b1.rstrip(), "",
                 "---", "", c["p2"], "", b2.rstrip(), "", "---", "", tail.rstrip(), ""]
        out = os.path.join(DOCS, c["out"])
        io.open(out, "w", encoding="utf-8", newline="\r\n").write("\n".join(parts))
        print("wrote %-34s from %s + %s" % (c["out"], c["staff"], c["views"]))


if __name__ == "__main__":
    main()
