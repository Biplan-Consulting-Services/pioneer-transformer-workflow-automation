# -*- coding: utf-8 -*-
"""Take the em dashes out of the staff-facing guides.

    python scripts/dedash_guides.py            # dry run, shows every change
    python scripts/dedash_guides.py --apply

WHY
  Nobody writes a work email or a shop-floor guide with em dashes. It reads as
  machine-written, and staff who notice that trust the content less. The user asked
  for them gone, and they were mine: every one of these documents was drafted here.

  This is prose, so it is NOT a blind character swap. An em dash does three
  different jobs in these files and each wants a different fix:

      "**No refresh** — everyone sees your change"     a label and its gloss  -> colon
      "the same look — same columns, same order"       an appositive           -> comma
      "doesn't seem right — don't work around it"      two full sentences      -> full stop

  A comma is right most of the time, so it is the default, with the other two cases
  listed explicitly. Anything the explicit rules do not catch gets a comma and shows
  up in the dry run, so a bad one is visible before it ships.

  ⚠️ SCOPE: the four staff-facing guides only. Internal docs, code comments and
  commit messages are a different register with a different reader, and rewriting
  them would bury the real change in noise.
"""
import argparse, io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(os.path.dirname(HERE), "docs")
FILES = ["staff-guide-sharepoint.md", "staff-guide-sharepoint-fr.md",
         "views-guide-sharepoint.md", "views-guide-sharepoint-fr.md"]

# Two sentences pretending to be one. Comma would be a splice.
FULL_STOP = [
 ("something just doesn't seem right — don't work around it and don't guess.",
  "something just doesn't seem right. Don't work around it and don't guess."),
 ("something just doesn't seem right — **don't work around it and don't guess.**",
  "something just doesn't seem right. **Don't work around it and don't guess.**"),
 ("quelque chose a l'air croche — ne travaillez pas autour et ne devinez pas.",
  "quelque chose a l'air croche. Ne travaillez pas autour et ne devinez pas."),
 ("quelque chose a l'air croche — **ne travaillez pas autour et ne devinez pas.**",
  "quelque chose a l'air croche. **Ne travaillez pas autour et ne devinez pas.**"),
 ("no third option for \"not decided yet\" — if that distinction matters",
  "no third option for \"not decided yet\". If that distinction matters"),
 ("pour « pas encore décidé » — si la nuance compte",
  "pour « pas encore décidé ». Si la nuance compte"),
 ("from now on — so if a value you need is missing",
  "from now on. So if a value you need is missing"),
 ("à partir de maintenant — donc si une valeur dont vous avez besoin manque",
  "à partir de maintenant. Donc si une valeur dont vous avez besoin manque"),
]

# A title, or a label introducing what it means. Colon, spaced in French.
COLON = [
 ("# Working in SharePoint — a short guide", "# Working in SharePoint: a short guide"),
 ("# Travailler dans SharePoint — petit guide", "# Travailler dans SharePoint : petit guide"),
 ("# SharePoint views — how they work", "# SharePoint views: how they work"),
 ("# Les affichages SharePoint — comment ça marche",
  "# Les affichages SharePoint : comment ça marche"),
 ("- **No save button** — it saves", "- **No save button**: it saves"),
 ("- **No refresh** — everyone sees", "- **No refresh**: everyone sees"),
 ("- **No \"someone else has it open\"** — several people",
  "- **No \"someone else has it open\"**: several people"),
 ("- **Aucun bouton d'enregistrement** — ça se sauvegarde",
  "- **Aucun bouton d'enregistrement** : ça se sauvegarde"),
 ("- **Aucun rafraîchissement à faire** — tout le monde",
  "- **Aucun rafraîchissement à faire** : tout le monde"),
 ("- **Aucun « quelqu'un d'autre l'a ouvert »** — plusieurs personnes",
  "- **Aucun « quelqu'un d'autre l'a ouvert »** : plusieurs personnes"),
 ("**grouped by Location** — the production step",
  "**grouped by Location**: the production step"),
 ("**grouped by `Location`** — the production step",
  "**grouped by `Location`**: the production step"),
 ("**regroupées par Location** — l'étape de production",
  "**regroupées par Location** : l'étape de production"),
 ("**regroupées par `Location`** — l'étape de production",
  "**regroupées par `Location`** : l'étape de production"),
]

# Table cells: "| a **checkbox** — tick it |" reads fine as a comma.
CELL = re.compile(r"(\| [^|]*?\*\*) — ")


def flexible(pat):
    """Match across a line wrap. These files are hard-wrapped at ~95 columns, so a
    phrase-level rule written on one line does NOT match the file -- the first pass
    of this script missed four comma-splice fixes for exactly that reason and let
    them fall through to the comma default, which is the error it exists to avoid."""
    return re.compile(r"\s+".join(re.escape(w) for w in pat.split()))


def convert(text):
    """Returns (new_text, [(before, after), ...]) for the dry run."""
    changes = []
    for a, b in FULL_STOP + COLON:
        rx = flexible(a)
        if rx.search(text):
            # keep the replacement on one line; the file is re-wrapped by hand anyway
            text = rx.sub(lambda m: b, text)
            changes.append((a, b))
    # table cells
    def cell(m):
        return m.group(1) + ", "
    prev = None
    while prev != text:
        prev = text
        text = CELL.sub(cell, text)
    # everything else: a comma, and never a doubled one
    for m in re.finditer(r".{0,44}—.{0,44}", text):
        changes.append((" ".join(m.group(0).split()), "-> comma"))
    # The files are hard-wrapped, so a dash can sit at either end of a line and the
    # plain " - " form misses it. The second half of a PAIRED dash lands there often,
    # which is how one survived the first pass.
    # The files are hard-wrapped, so a dash can sit at either end of a line and the
    # plain " - " form misses it. The second half of a PAIRED dash lands there often,
    # which is how one survived the first pass.
    text = text.replace(", — ", ", ")
    text = re.sub(" +—\n", ",\n", text)          # dash closing a line
    text = re.sub("\n( *)— +", r"\n\1", text)     # dash opening one
    text = text.replace(" — ", ", ")
    text = text.replace(",,", ",").replace(" ,", ",").replace(",.", ".")

    return text, changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    total = 0
    for f in FILES:
        p = os.path.join(DOCS, f)
        s = io.open(p, encoding="utf-8").read().replace("\r\n", "\n")
        before = s.count("—")
        new, changes = convert(s)
        after = new.count("—")
        total += before
        print("\n%s   %d em dashes -> %d" % (f, before, after))
        for c in changes:
            if c[1] == "-> comma":
                print("   comma   ...%s..." % c[0])
        if a.apply:
            io.open(p, "w", encoding="utf-8", newline="\r\n").write(new)
    print("\n%d em dashes across %d files%s"
          % (total, len(FILES), "" if a.apply else "  -- DRY RUN, nothing written"))
    if a.apply:
        print("Now re-run gen_staff_handbook.py -- the handbooks are built from these.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
