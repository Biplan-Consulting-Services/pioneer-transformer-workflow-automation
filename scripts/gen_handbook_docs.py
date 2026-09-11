# -*- coding: utf-8 -*-
"""Render the two handbooks as print-shaped HTML, ready for Word to convert.

    python scripts/gen_handbook_docs.py
    powershell -File scripts/Convert-HandbookDocs.ps1

    docs/staff-handbook-sharepoint.md     -> dist/FRM10-12 SharePoint Handbook (EN).html
    docs/staff-handbook-sharepoint-fr.md  -> dist/FRM10-12 SharePoint - Guide du personnel (FR).html

WHY HTML IN THE MIDDLE
  There is no pandoc on this machine and no pywin32, but Word 16 is installed and opens
  HTML natively. So the chain is markdown -> HTML here, HTML -> .docx/.pdf in the
  PowerShell script. Word's HTML import is the weak link, which drives every CSS choice
  below: no flex, no grid, no CSS variables, no web fonts. Word silently drops all four
  and you get an unstyled wall of text that still looks plausible at a glance.

  The filenames are what staff will see in the SharePoint guides folder, so they are
  written for that reader, not for the repo.

⚠️ EDIT THE GUIDES, NOT THESE. Everything here is build output, two generations
   downstream: staff-guide-* + views-guide-* -> gen_staff_handbook.py -> the handbooks
   -> this.
"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
DIST = os.path.join(ROOT, "dist")
sys.path.insert(0, HERE)
from gen_review_page import md  # noqa: E402  the same small renderer the review page uses

# Word maps these to real Word styles on import; anything cleverer gets dropped.
CSS = """
body { font-family: Calibri, "Segoe UI", sans-serif; font-size: 11pt; color: #1a1a1a;
       line-height: 1.45; margin: 0; }
h1 { font-family: "Segoe UI Semibold", Calibri, sans-serif; font-size: 24pt; color: #0f3a5f;
     margin: 0 0 4pt 0; page-break-after: avoid; }
h2 { font-family: "Segoe UI Semibold", Calibri, sans-serif; font-size: 17pt; color: #0f3a5f;
     margin: 22pt 0 6pt 0; border-bottom: 1.5pt solid #c8d6e0; padding-bottom: 3pt;
     page-break-after: avoid; }
h3 { font-family: "Segoe UI Semibold", Calibri, sans-serif; font-size: 13pt; color: #14507f;
     margin: 16pt 0 4pt 0; page-break-after: avoid; }
h4 { font-size: 11.5pt; font-weight: bold; margin: 12pt 0 3pt 0; page-break-after: avoid; }
p  { margin: 0 0 8pt 0; }
ul, ol { margin: 0 0 8pt 0; padding-left: 20pt; }
li { margin: 0 0 4pt 0; }
code { font-family: Consolas, "Courier New", monospace; font-size: 10pt;
       background: #eef2f6; color: #0b3d62; padding: 1pt 3pt; }
strong { color: #0b2b45; }
table { border-collapse: collapse; width: 100%; margin: 0 0 10pt 0; font-size: 10pt; }
th { background: #0f3a5f; color: #ffffff; text-align: left; padding: 5pt 7pt;
     border: 0.75pt solid #0f3a5f; font-weight: bold; }
td { padding: 5pt 7pt; border: 0.75pt solid #c8d6e0; vertical-align: top; }
blockquote { margin: 0 0 10pt 0; padding: 7pt 10pt; background: #f4f7fa;
             border-left: 3pt solid #14507f; }
hr { border: 0; border-top: 0.75pt solid #c8d6e0; margin: 16pt 0; }
.sub { color: #4a6076; font-size: 10.5pt; margin: 0 0 16pt 0; }
h2.part { page-break-before: always; }
"""

CFG = [
    dict(src="staff-handbook-sharepoint.md",
         out="FRM10-12 SharePoint Handbook (EN).html",
         sub="Pioneer Transformer · Order Items · September 2026"),
    dict(src="staff-handbook-sharepoint-fr.md",
         out="FRM10-12 SharePoint - Guide du personnel (FR).html",
         sub="Pioneer Transformer · Order Items · septembre 2026"),
]


def part_breaks(body):
    """Start each Part on its own page.

    md() shifts every heading down one level, so the three `#` headings of a handbook
    (the title, Part 1, Part 2) all arrive as `<h2>`. The first is the title and stays
    where it is; the rest open a page. The `---` rule that precedes each Part goes with
    it, otherwise it is left dangling alone at the foot of the previous page.
    """
    bits = body.split("<h2>")
    if len(bits) < 3:
        return body
    out = [bits[0], "<h2>" + bits[1]]
    for b in bits[2:]:
        out.append('<h2 class="part">' + b)
    body = "".join(out)
    return body.replace('<hr>\n<h2 class="part">', '<h2 class="part">')


def main():
    if not os.path.isdir(DIST):
        os.makedirs(DIST)
    for c in CFG:
        text = io.open(os.path.join(DOCS, c["src"]), encoding="utf-8").read()
        body = md(text)
        body = part_breaks(body)
        # the subtitle goes under the H1, which md() emits first
        head, sep, rest = body.partition("</h2>")
        # md() shifts headings down one level, so the document title arrives as <h2>
        doc = ("<html><head><meta charset='utf-8'><title>%s</title><style>%s</style></head>"
               "<body>%s%s<p class='sub'>%s</p>%s</body></html>"
               % (os.path.splitext(c["out"])[0], CSS, head, sep, c["sub"], rest))
        p = os.path.join(DIST, c["out"])
        io.open(p, "w", encoding="utf-8", newline="\r\n").write(doc)
        print("wrote  %s  (%d KB)" % (c["out"], len(doc) // 1024))
    print("\nNow: powershell -File scripts/Convert-HandbookDocs.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
