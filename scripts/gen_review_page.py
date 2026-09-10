# -*- coding: utf-8 -*-
"""Build the cutover review page from the real documents.

    python scripts/gen_review_page.py

Reads the announcement and both handbooks and emits artifacts/cutover-review.html.
Generated rather than hand-written so the page cannot drift from the files that
actually get sent and published -- re-run it after editing any of them.
"""
import io, os, re, html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
OUT = os.path.join(ROOT, "artifacts", "cutover-review.html")


# ---------------------------------------------------------------- markdown -> html
def md(text):
    """Enough markdown for these documents: headings, tables, lists, quotes,
    bold, inline code, rules. Deliberately small -- a library would be a
    dependency for four files whose syntax we control."""
    out, i = [], 0
    lines = text.replace("\r\n", "\n").split("\n")

    def inline(s):
        s = html.escape(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\w)", r"<em>\1</em>", s)
        return s

    while i < len(lines):
        L = lines[i]
        if not L.strip():
            i += 1; continue
        if re.match(r"^---+\s*$", L):
            out.append("<hr>"); i += 1; continue
        m = re.match(r"^(#{1,4}) +(.*)$", L)
        if m:
            lvl = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lvl + 1, inline(m.group(2)), lvl + 1))
            i += 1; continue
        if L.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            head = [c.strip() for c in L.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append("<div class='tw'><table><thead><tr>"
                       + "".join("<th>%s</th>" % inline(h) for h in head)
                       + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>"
                                 for r in rows)
                       + "</tbody></table></div>")
            continue
        if L.lstrip().startswith(("- ", "* ")):
            items = []
            while i < len(lines) and (lines[i].lstrip().startswith(("- ", "* "))
                                      or (lines[i].startswith("  ") and lines[i].strip()
                                          and items)):
                if lines[i].lstrip().startswith(("- ", "* ")):
                    items.append(lines[i].lstrip()[2:])
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append("<ul>" + "".join("<li>%s</li>" % inline(x) for x in items) + "</ul>")
            continue
        if re.match(r"^\d+\. ", L.lstrip()):
            items = []
            while i < len(lines) and (re.match(r"^\d+\. ", lines[i].lstrip())
                                      or (lines[i].startswith("   ") and lines[i].strip() and items)):
                if re.match(r"^\d+\. ", lines[i].lstrip()):
                    items.append(re.sub(r"^\d+\. ", "", lines[i].lstrip()))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append("<ol>" + "".join("<li>%s</li>" % inline(x) for x in items) + "</ol>")
            continue
        if L.lstrip().startswith(">"):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                buf.append(lines[i].lstrip()[1:].strip()); i += 1
            out.append("<blockquote>%s</blockquote>" % md("\n".join(buf)))
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(("- ", "* ", "|", ">", "#")) \
                and not re.match(r"^---+\s*$", lines[i]) and not re.match(r"^\d+\. ", lines[i].lstrip()):
            buf.append(lines[i].strip()); i += 1
        if buf:
            out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out)


def read(name):
    return io.open(os.path.join(DOCS, name), encoding="utf-8").read().replace("\r\n", "\n")


def main():
    email = read("cutover-announcement-2026-09-08.md")
    fr = email[email.index("## FRANÇAIS") + len("## FRANÇAIS"):email.index("## ENGLISH")]
    fr = fr.rsplit("---", 1)[0]
    en = email[email.index("## ENGLISH") + len("## ENGLISH"):email.index("## Before you send")]
    en = en.rsplit("---", 1)[0]
    checklist = email[email.index("## Before you send"):]
    hb_en = read("staff-handbook-sharepoint.md")
    hb_fr = read("staff-handbook-sharepoint-fr.md")

    page = TEMPLATE
    for token, value in [("__EMAIL_FR__", md(fr)), ("__EMAIL_EN__", md(en)),
                         ("__CHECKLIST__", md(checklist)),
                         ("__HB_EN__", md(hb_en)), ("__HB_FR__", md(hb_fr))]:
        page = page.replace(token, value)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(page)
    print("wrote %s  (%d KB)" % (OUT, len(page) // 1024))


TEMPLATE = r"""<title>Cutover Review</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,600;1,6..72,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --paper:#f7f5f2; --card:#fffefc; --ink:#1b1e22; --muted:#5d6670;
  --rule:#ded8d0; --copper:#a85c2b; --copper-soft:#f0e2d6;
  --steel:#3d4a56; --flag:#8f2f2f; --flag-soft:#f6e6e4; --ok:#2f6b4f;
  --shadow:0 1px 2px rgba(27,30,34,.05), 0 8px 24px -16px rgba(27,30,34,.25);
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --paper:#16181b; --card:#1d2024; --ink:#e9e6e1; --muted:#9aa3ad;
  --rule:#32373d; --copper:#d98d55; --copper-soft:#3a2b20;
  --steel:#9fb0bf; --flag:#e08b83; --flag-soft:#3a2523; --ok:#7dc0a0;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.7);
}}
:root[data-theme="dark"]{
  --paper:#16181b; --card:#1d2024; --ink:#e9e6e1; --muted:#9aa3ad;
  --rule:#32373d; --copper:#d98d55; --copper-soft:#3a2b20;
  --steel:#9fb0bf; --flag:#e08b83; --flag-soft:#3a2523; --ok:#7dc0a0;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.7);
}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,-apple-system,Segoe UI,sans-serif;
  font-size:15px;line-height:1.62;margin:0;padding:0 20px 96px}
.wrap{max-width:820px;margin:0 auto}
code{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:.875em;background:var(--copper-soft);color:var(--ink);
  padding:.08em .34em;border-radius:3px;white-space:nowrap}
hr{border:0;border-top:1px solid var(--rule);margin:26px 0}

header{padding:52px 0 26px;border-bottom:2px solid var(--ink)}
.eyebrow{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--copper);margin:0 0 12px}
h1{font-family:Newsreader,Georgia,serif;font-weight:600;font-size:clamp(34px,6vw,52px);
  line-height:1.04;margin:0;letter-spacing:-.015em;text-wrap:balance}
.sub{color:var(--muted);margin:14px 0 0;max-width:60ch}

.decisions{background:var(--card);border:1px solid var(--rule);border-left:3px solid var(--flag);
  border-radius:6px;padding:22px 24px;margin:30px 0 8px;box-shadow:var(--shadow)}
.decisions h2{font-family:"IBM Plex Sans",sans-serif;font-size:12px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--flag);margin:0 0 16px;font-weight:600}
.dec{display:flex;gap:14px;padding:13px 0;border-top:1px solid var(--rule)}
.dec:first-of-type{border-top:0;padding-top:0}
.dec input{margin-top:5px;accent-color:var(--copper);width:15px;height:15px;flex:none}
.dec div{min-width:0}
.dec b{display:block;font-weight:600}
.dec span{color:var(--muted);font-size:13.5px}

nav{position:sticky;top:0;z-index:5;background:var(--paper);
  border-bottom:1px solid var(--rule);padding:10px 0;margin:34px 0 0;
  display:flex;gap:6px;flex-wrap:wrap}
nav a{font-family:"IBM Plex Mono",monospace;font-size:11.5px;letter-spacing:.05em;
  text-transform:uppercase;color:var(--muted);text-decoration:none;
  padding:6px 11px;border-radius:4px;border:1px solid transparent}
nav a:hover,nav a:focus-visible{color:var(--ink);border-color:var(--rule);background:var(--card)}

section{padding-top:38px}
h2.sec{font-family:Newsreader,Georgia,serif;font-weight:600;font-size:29px;
  margin:0 0 4px;letter-spacing:-.01em}
.note{color:var(--muted);font-size:13.5px;margin:0 0 20px}
.file{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--copper)}

.tabs{display:flex;gap:4px;margin:0 0 -1px}
.tabs button{font-family:"IBM Plex Mono",monospace;font-size:11.5px;letter-spacing:.06em;
  text-transform:uppercase;padding:9px 16px;border:1px solid var(--rule);
  border-bottom-color:transparent;background:var(--paper);color:var(--muted);
  cursor:pointer;border-radius:5px 5px 0 0}
.tabs button[aria-selected="true"]{background:var(--card);color:var(--ink);font-weight:500;
  box-shadow:inset 0 2px 0 var(--copper)}

.doc{background:var(--card);border:1px solid var(--rule);border-radius:0 6px 6px 6px;
  padding:34px 38px;box-shadow:var(--shadow);overflow-wrap:break-word}
.doc h2{font-family:Newsreader,Georgia,serif;font-size:24px;font-weight:600;
  margin:34px 0 10px;letter-spacing:-.01em}
.doc h3{font-size:15px;font-weight:600;margin:26px 0 8px;
  padding-bottom:5px;border-bottom:1px solid var(--rule)}
.doc h4{font-size:13.5px;font-weight:600;margin:20px 0 6px;color:var(--steel)}
.doc > :first-child{margin-top:0}
.doc p{margin:0 0 13px;max-width:66ch}
.doc ul,.doc ol{margin:0 0 15px;padding-left:22px;max-width:66ch}
.doc li{margin:0 0 6px}
.doc blockquote{margin:16px 0;padding:12px 18px;border-left:3px solid var(--copper);
  background:var(--copper-soft);border-radius:0 5px 5px 0}
.doc blockquote p:last-child{margin-bottom:0}
.tw{overflow-x:auto;margin:0 0 18px}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--rule);vertical-align:top}
th{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);
  font-weight:600;border-bottom:1px solid var(--ink)}
tbody tr:last-child td{border-bottom:0}

details{background:var(--card);border:1px solid var(--rule);border-radius:6px;
  margin:0 0 12px;box-shadow:var(--shadow)}
summary{cursor:pointer;padding:16px 22px;font-weight:600;list-style:none;
  display:flex;justify-content:space-between;align-items:center;gap:14px}
summary::-webkit-details-marker{display:none}
summary::after{content:"open";font-family:"IBM Plex Mono",monospace;font-size:11px;
  letter-spacing:.08em;text-transform:uppercase;color:var(--copper);flex:none}
details[open] summary::after{content:"close"}
details[open] summary{border-bottom:1px solid var(--rule)}
details .doc{border:0;box-shadow:none;border-radius:0;background:transparent}
summary span{color:var(--muted);font-weight:400;font-size:13px}

footer{margin-top:56px;padding-top:22px;border-top:1px solid var(--rule);
  color:var(--muted);font-size:13px}
@media (max-width:600px){ .doc{padding:22px 18px} body{padding:0 14px 70px} }
@media (prefers-reduced-motion:reduce){ *{transition:none!important;animation:none!important} }
</style>

<div class="wrap">
<header>
  <p class="eyebrow">Pioneer Transformer · 10 September 2026</p>
  <h1>Cutover review</h1>
  <p class="sub">The staff email and the handbook, exactly as they stand. Read them before
  anything is sent — three things still need a decision from you, and they are at the top.</p>
</header>

<div class="decisions">
  <h2>Needs you before sending</h2>
  <label class="dec"><input type="checkbox">
    <div><b>Two links</b><span>The read-only workbook, and wherever the handbook gets
    published. Both appear in the email as <code>[LIEN]</code> / <code>[LIEN GUIDE]</code>.
    Neither was invented here.</span></div></label>
  <label class="dec"><input type="checkbox">
    <div><b>Three French UI labels</b><span>Section 7 of the French handbook names
    « Regrouper par », « Réduits » and « Limite d'éléments ». They were reasoned, never read
    off the screen. Open the classic view-settings page in French and confirm — 30 seconds.</span></div></label>
  <label class="dec"><input type="checkbox">
    <div><b>Every line of “what changes tonight” has to have actually happened</b>
    <span>It is written ahead of the work. The dropdowns depend on <code>n4</code>, the order
    folder on <code>x5</code> plus the Order flow, the two removed columns on a manual delete.
    If a step slips, cut the line rather than send a promise.</span></div></label>
</div>

<nav>
  <a href="#email">The email</a>
  <a href="#checklist">Before sending</a>
  <a href="#handbook">The handbook</a>
</nav>

<section id="email">
  <h2 class="sec">The staff email</h2>
  <p class="note">French first — the office is in Montreal, the factory in Granby, and the
  shop-floor vocabulary is already French. <span class="file">docs/cutover-announcement-2026-09-08.md</span></p>
  <div class="tabs" role="tablist">
    <button role="tab" aria-selected="true" aria-controls="em-fr" id="t-fr">Français</button>
    <button role="tab" aria-selected="false" aria-controls="em-en" id="t-en">English</button>
  </div>
  <div class="doc" id="em-fr" role="tabpanel" aria-labelledby="t-fr">__EMAIL_FR__</div>
  <div class="doc" id="em-en" role="tabpanel" aria-labelledby="t-en" hidden>__EMAIL_EN__</div>
</section>

<section id="checklist">
  <h2 class="sec">Before you send</h2>
  <p class="note">The working checklist that travels with the email — not part of what staff receive.</p>
  <div class="doc" style="border-radius:6px">__CHECKLIST__</div>
</section>

<section id="handbook">
  <h2 class="sec">The handbook</h2>
  <p class="note">Four guides consolidated into one document per language: doing the work,
  then the views. Stitched from the reviewed text rather than rewritten.
  <span class="file">docs/staff-handbook-sharepoint.md · -fr.md</span></p>
  <details>
    <summary>English <span>Part 1 doing the work · Part 2 the views</span></summary>
    <div class="doc">__HB_EN__</div>
  </details>
  <details>
    <summary>Français <span>Partie 1 faire le travail · Partie 2 les affichages</span></summary>
    <div class="doc">__HB_FR__</div>
  </details>
</section>

<footer>
  Generated from the repository by <code>scripts/gen_review_page.py</code>. Edit the
  documents, not this page — re-run the script and republish.
</footer>
</div>

<script>
(function(){
  var tabs=[].slice.call(document.querySelectorAll('.tabs button'));
  tabs.forEach(function(b){
    b.addEventListener('click',function(){
      tabs.forEach(function(o){
        var sel=o===b;
        o.setAttribute('aria-selected',sel?'true':'false');
        document.getElementById(o.getAttribute('aria-controls')).hidden=!sel;
      });
    });
  });
})();
</script>
"""

if __name__ == "__main__":
    main()
