# -*- coding: utf-8 -*-
"""Turn `Utilisateurs dossier bleu V2` into the document-routing table.

    python scripts/parse_dossier_bleu.py            # validate + report
    python scripts/parse_dossier_bleu.py --write    # also emit reports/

WHAT THIS IS
  The sheet is the completed 2026-08-21 analysis of which department needs which
  drawing -- the digital form of the colour-coded paper folders that get walked
  down the production line today. It is the seed for the `Document Types` /
  `Recipients` SharePoint lists, and it is the reason routing can be derived from
  a document's TYPE rather than tagged per file.

  It is a MATRIX, not a table: 3 header rows, then 56 drawing rows, then 11
  department columns whose cells are copy counts.

FIVE TRAPS IN THIS FILE, every one of them measured, not guessed

  1. cp1252, NOT UTF-8. `Qualite`, `Shema electrique`, `Boite de controle` all
     mojibake if read as UTF-8. The .xlsx in docs/ is the original; this CSV is a
     Sheet1 export and carries the codepage with it.

  2. Cells are COUNTS, not booleans. `Cover - Couvercle` sends 2 copies to Cuve
     and `Tank - Cuve` (G1158D) sends 3. Treating a cell as a flag undercounts
     Cuve by 5 and silently loses the reason that folder is thick.

  3. One cell holds free text where a number belongs. Row `Nameplate - Plaque
     signalet. ` (G2102/G2112 *avec +*), Essai column, reads "placer dans chemise
     sur la table a dessins" -- a physical-workflow instruction with no digital
     equivalent. A naive int() dies here. Carried as a note, never as a copy.

  4. The title is not a key. Three pairs share one: `Connection Diagram`
     (G1130,G1339 vs G1309C), `Tank - Cuve` (G1158D vs G1150,G1350,G1158C), and
     `Nameplate - Plaque signalet.` twice -- those two differ ONLY by a trailing
     space plus a `(sans +)`/`(avec +)` qualifier living in the drawing-number
     column. Keys are built from title + that qualifier.

  5. `NO. DESSIN` is not an identifier either, so it cannot be the key. Real
     values include comma-lists (`G1168-, G1371, G1368`), open ranges
     (`G1318A----`), `et autres`, a conditional rule (`Si inscrit "Metelec" dans
     M.P.L.`), a print instruction (`Copie sur des feuilles oranges *`), and 7
     blanks. Captured verbatim as a reference, never parsed as an ID.

THE CROSS-FOOT IS THE TEST
  Column C (`exemplaires`) and row 1 (per-department totals) are independent sums
  of the same 163 sheets. If a change to this parser breaks either, the parse is
  wrong -- not the sheet.
"""
import csv, json, os, re, sys, io, collections

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "workflow-data", "Utilisateurs dossier bleu V2.csv")
OUT = os.path.join(ROOT, "reports")

# Row 1 of the sheet, kept here as an independent check on our own column sums.
EXPECTED_DEPT_TOTALS = {
    "Essai": 8, "Qualité": 24, "Isolation": 11, "Ass + Stacking": 26,
    "Tanking": 17, "Test": 9, "Finition": 19, "Filerie": 9,
    "Cuve": 26, "Vente": 4, "Achats": 10,
}
EXPECTED_GRAND_TOTAL = 163

# Which of the 11 columns is actually a shop-floor station. `Cuve` is the tank
# fabricator (CADORETTE/METELEC/FRAMECO) -- documents leaving the building, not a
# station. Qualite/Vente/Achats are office functions. This split decides what can
# hang off a Monday step at all, so it is data, not a comment.
RECIPIENT_KIND = {
    "Essai": "station", "Isolation": "station", "Ass + Stacking": "station",
    "Tanking": "station", "Test": "station", "Finition": "station",
    "Filerie": "station",
    "Qualité": "office", "Vente": "office", "Achats": "office",
    "Cuve": "external",
}

ACCENTS = [("à", "a"), ("â", "a"), ("ä", "a"), ("é", "e"),
           ("è", "e"), ("ê", "e"), ("ë", "e"), ("î", "i"),
           ("ï", "i"), ("ô", "o"), ("ö", "o"), ("ù", "u"),
           ("û", "u"), ("ü", "u"), ("ç", "c")]


def slug(s):
    s = (s or "").strip().lower()
    for a, b in ACCENTS:
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def qualifier(dessin):
    """A short disambiguator for two rows sharing a title (trap 4).

    Prefer a parenthetical -- `(sans +)` / `(avec +)` is what actually separates
    the two Nameplate rows. Otherwise the first drawing-number-looking token."""
    m = re.search(r"\(([^)]*)\)", dessin or "")
    if m and m.group(1).strip():
        return m.group(1).strip()
    m = re.search(r"\b([A-Z]{1,3}\d{3,}[A-Z0-9]*)", dessin or "")
    return m.group(1) if m else None


def parse_cell(raw):
    """-> (copies, note). Traps 2 and 3 both land here."""
    s = (raw or "").strip()
    if not s:
        return 0, None
    if re.fullmatch(r"\d+", s):
        return int(s), None
    return 0, s          # free text: an instruction, never a copy


def load():
    with io.open(SRC, "r", encoding="cp1252", newline="") as fh:   # trap 1
        rows = list(csv.reader(fh))

    totals_row, colour_row, header_row = rows[0], rows[1], rows[2]
    depts = [h.strip() for h in header_row[3:] if h.strip()]
    colours = {depts[i]: colour_row[3 + i].strip() for i in range(len(depts))}
    sheet_totals = {}
    for i, d in enumerate(depts):
        v = totals_row[3 + i].strip()
        sheet_totals[d] = int(v) if re.fullmatch(r"\d+", v) else None

    docs, seen = [], collections.Counter()
    for idx, r in enumerate(rows[3:], start=4):
        if not r or not (r[0] or "").strip():
            continue                                   # trailing blank rows
        title_raw = r[0]
        dessin = (r[1] or "").strip()
        ex = (r[2] or "").strip()
        exemplaires = int(ex) if re.fullmatch(r"\d+", ex) else 0

        routing, notes = {}, {}
        for i, d in enumerate(depts):
            cell = r[3 + i] if 3 + i < len(r) else ""
            n, note = parse_cell(cell)
            if n:
                routing[d] = n
            if note:
                notes[d] = note

        key = slug(title_raw)
        docs.append({
            "row": idx,
            "title": title_raw.strip(),
            "title_raw": title_raw,          # trailing space is load-bearing (trap 4)
            "drawing_numbers_raw": dessin,   # never parsed as an ID (trap 5)
            "qualifier": qualifier(dessin),
            "key": key,
            "exemplaires": exemplaires,
            "routing": routing,
            "notes": notes,
        })
        seen[key] += 1

    # Trap 4: disambiguate only the keys that actually collide, so the common case
    # keeps a clean readable slug.
    dupes = set(k for k, c in seen.items() if c > 1)
    for d in docs:
        if d["key"] in dupes:
            tail = slug(d["qualifier"] or ("row%d" % d["row"]))
            d["key"] = "%s__%s" % (d["key"], tail)

    return {
        "source": os.path.relpath(SRC, ROOT).replace("\\", "/"),
        "departments": [
            {"name": d, "colour": colours.get(d), "kind": RECIPIENT_KIND.get(d, "?"),
             "sheet_total": sheet_totals.get(d)}
            for d in depts
        ],
        "documents": docs,
    }


def validate(data):
    """Returns (ok, lines). The cross-foot IS the test -- see module docstring."""
    out, ok = [], True
    depts = [d["name"] for d in data["departments"]]
    docs = data["documents"]

    by_dept = collections.Counter()
    for d in docs:
        for k, v in d["routing"].items():
            by_dept[k] += v

    out.append("%-16s %6s %6s %6s   %s" % ("DEPARTMENT", "PARSED", "SHEET", "EXPECT", "KIND"))
    for name in depts:
        sheet = next(x["sheet_total"] for x in data["departments"] if x["name"] == name)
        exp = EXPECTED_DEPT_TOTALS.get(name)
        kind = RECIPIENT_KIND.get(name, "?")
        bad = not (by_dept[name] == sheet == exp)
        if bad:
            ok = False
        out.append("%-16s %6d %6s %6s   %-9s%s"
                   % (name, by_dept[name], sheet, exp, kind, "   <-- MISMATCH" if bad else ""))

    grand_cols = sum(by_dept.values())
    grand_ex = sum(d["exemplaires"] for d in docs)
    out.append("")
    out.append("documents parsed          : %d" % len(docs))
    out.append("sum of column counts      : %d" % grand_cols)
    out.append("sum of `exemplaires`      : %d" % grand_ex)
    out.append("expected (both)           : %d" % EXPECTED_GRAND_TOTAL)
    if not (grand_cols == grand_ex == EXPECTED_GRAND_TOTAL):
        ok = False
        out.append("   <-- CROSS-FOOT FAILED")

    # Per-row disagreement between `exemplaires` and the row's own marks. These are
    # data-quality findings to take to production, not parser bugs.
    out.append("")
    out.append("ROWS WHERE `exemplaires` != sum of that row's own marks:")
    bad_rows = [d for d in docs if d["exemplaires"] != sum(d["routing"].values())]
    if not bad_rows:
        out.append("  (none)")
    for d in bad_rows:
        out.append("  row %-3d %-34s exemplaires=%-3d marks=%-3d %s"
                   % (d["row"], d["title"][:34], d["exemplaires"],
                      sum(d["routing"].values()), d["drawing_numbers_raw"][:28]))

    out.append("")
    out.append("FREE-TEXT CELLS (trap 3) -- instructions, not copies:")
    any_note = False
    for d in docs:
        for dept, note in sorted(d["notes"].items()):
            any_note = True
            out.append("  row %-3d %-30s [%s] %s" % (d["row"], d["title"][:30], dept, note))
    if not any_note:
        out.append("  (none)")

    out.append("")
    out.append("DEAD ROWS (0 copies, no marks) -- candidates to prune:")
    dead = [d for d in docs if d["exemplaires"] == 0 and not d["routing"]]
    for d in dead:
        out.append("  row %-3d %s" % (d["row"], d["title"]))
    if not dead:
        out.append("  (none)")

    out.append("")
    out.append("DISAMBIGUATED KEYS (trap 4):")
    for d in docs:
        if "__" in d["key"]:
            out.append("  row %-3d %-36s -> %s" % (d["row"], d["title"][:36], d["key"]))

    out.append("")
    out.append("ROWS WITH NO DRAWING NUMBER (trap 5) -- need a source before tagging:")
    for d in docs:
        if not d["drawing_numbers_raw"]:
            out.append("  row %-3d %s" % (d["row"], d["title"]))

    return ok, out


def write(data):
    os.makedirs(OUT, exist_ok=True)
    jp = os.path.join(OUT, "dossier-bleu.json")
    with io.open(jp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    # Long form: one row per (document type, recipient). This is the shape the
    # `Document Types` routing list wants -- a matrix does not import.
    cp = os.path.join(OUT, "dossier-bleu-routing.csv")
    colours = dict((d["name"], d["colour"]) for d in data["departments"])
    order = [d["name"] for d in data["departments"]]
    with io.open(cp, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["DocTypeKey", "Title", "DrawingNumbersRaw", "Recipient",
                    "RecipientKind", "FolderColour", "Copies", "Note"])
        for d in data["documents"]:
            for dept in order:
                n = d["routing"].get(dept, 0)
                note = d["notes"].get(dept, "")
                if not n and not note:
                    continue
                w.writerow([d["key"], d["title"], d["drawing_numbers_raw"], dept,
                            RECIPIENT_KIND.get(dept, "?"), colours.get(dept, ""),
                            n, note])
    return jp, cp


if __name__ == "__main__":
    data = load()
    ok, lines = validate(data)
    print("\n".join(lines))
    if "--write" in sys.argv:
        jp, cp = write(data)
        print("")
        print("wrote %s" % os.path.relpath(jp, ROOT).replace("\\", "/"))
        print("wrote %s" % os.path.relpath(cp, ROOT).replace("\\", "/"))
    print("")
    print("CROSS-FOOT OK" if ok else "CROSS-FOOT FAILED -- do not build from this")
    sys.exit(0 if ok else 1)
