# -*- coding: utf-8 -*-
"""Assemble the bilingual announcement into ONE email, French first.

    python scripts/gen_email_html.py
    -> dist/email/Cutover email (FR + EN).html

Open it in a browser, Ctrl+A, Ctrl+C, paste into Outlook. Pasting from a browser keeps
the bold and the tables; pasting from the markdown file gives you asterisks.

WHY dist/email/ AND NOT dist/
  Convert-HandbookDocs.ps1 globs `dist/*.html` and overwrites the matching .docx/.pdf.
  The handbooks in dist/ were laid out by hand after that script produced them, so
  anything new dropped beside them is a trap for the next person who runs it. The
  subfolder is not tidiness, it is the only thing stopping that.

THE PLACEHOLDERS ARE LEFT IN, AND MADE LOUD
  Four of them: the workbook link and the guide link, in each language. They are the one
  thing in this email that cannot be written here, and an email that ships with `[LIEN]`
  in it is worse than no email. So they render in red on yellow rather than as quiet
  grey text you skim past at 22:00.
"""
import io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "docs", "cutover-announcement-2026-09-08.md")
OUT = os.path.join(ROOT, "dist", "email", "Cutover email (FR + EN).html")
sys.path.insert(0, HERE)
from gen_review_page import md  # noqa: E402

CSS = """
body { font-family: Calibri, "Segoe UI", sans-serif; font-size: 11pt; color: #1a1a1a;
       line-height: 1.45; max-width: 820px; margin: 24px auto; padding: 0 16px; }
p { margin: 0 0 10pt 0; }
ul { margin: 0 0 10pt 0; padding-left: 22pt; }
li { margin: 0 0 5pt 0; }
code { font-family: Consolas, monospace; font-size: 10.5pt; }
strong { color: #0b2b45; }
hr { border: 0; border-top: 1pt solid #c8d6e0; margin: 22pt 0; }
.subject { background: #0f3a5f; color: #fff; padding: 10pt 14pt; font-size: 12pt;
           margin: 0 0 6pt 0; }
.note { background: #fff8e1; border-left: 3pt solid #e0a800; padding: 8pt 12pt;
        margin: 0 0 18pt 0; font-size: 10.5pt; color: #5a4600; }
.ph { background: #ffe08a; color: #a3200a; font-weight: bold; padding: 1pt 4pt; }
.lang { color: #4a6076; font-size: 10pt; letter-spacing: 0.08em; margin: 0 0 10pt 0; }
"""

SUBJECT = ("FRM10-12 : la migration se fait ce soir / "
           "the migration happens tonight")

BRIDGE_FR = "<p class='lang'>ENGLISH VERSION BELOW</p>"
BRIDGE_EN = "<p class='lang'>VERSION FRAN&Ccedil;AISE PLUS HAUT</p>"


def half(text, heading):
    """The body of one language section, without its `## FRANÇAIS` heading, its
    `**Objet :**` line (that becomes the subject) or the checklist that follows."""
    m = re.search(r"^## %s\s*$" % heading, text, re.M)
    body = text[m.end():]
    nxt = re.search(r"^## ", body, re.M)
    if nxt:
        body = body[:nxt.start()]
    body = re.sub(r"^\*\*(Objet|Subject).*$", "", body, flags=re.M)
    return body.strip("-\n \t")


def main():
    text = io.open(SRC, encoding="utf-8").read().replace("\r\n", "\n")
    fr, en = md(half(text, "FRANÇAIS")), md(half(text, "ENGLISH"))
    todo = 0
    for tag in ("[LIEN GUIDE]", "[GUIDE LINK]", "[LIEN]", "[LINK]"):
        todo += fr.count(tag) + en.count(tag)
        esc = tag.replace("[", "&#91;").replace("]", "&#93;")
        fr = fr.replace(tag, "<span class='ph'>%s</span>" % esc)
        en = en.replace(tag, "<span class='ph'>%s</span>" % esc)

    doc = ("<html><head><meta charset='utf-8'><title>Cutover email</title>"
           "<style>%s</style></head><body>"
           "<p class='subject'>%s</p>"
           "<p class='note'>Copy from below the subject line. Replace the four "
           "<span class='ph'>highlighted</span> placeholders with real links first: the "
           "read-only workbook, and the guide, in each language. This banner and the "
           "subject bar are not part of the email.</p>"
           "%s%s<hr>%s%s</body></html>"
           % (CSS, SUBJECT, BRIDGE_FR, fr, BRIDGE_EN, en))

    d = os.path.dirname(OUT)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(OUT, "w", encoding="utf-8", newline="\r\n").write(doc)
    print("wrote  %s" % os.path.relpath(OUT, ROOT))
    print("       %d placeholders still to fill" % todo)
    print("\nOpen it, Ctrl+A, Ctrl+C, paste into Outlook.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
