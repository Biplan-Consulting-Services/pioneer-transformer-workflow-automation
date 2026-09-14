# -*- coding: utf-8 -*-
"""Emit the worksheet for the production session that settles the step vocabulary.

    python scripts/gen_step_mapping_workbook.py

WHY THIS EXISTS
  Four systems describe the same production line and none of them agree:

    blue folder            11 departments   (who receives which drawing)
    Order Items.Location   12 values        (where a unit physically is)
    Order Items stages      8 column pairs  (the tracked milestones)
    Monday groups          ~26              (what the floor actually clicks through)

  Routing documents to a step is impossible until these are reconciled, and the
  reconciliation cannot be derived - only production knows it. This is the single
  highest-risk unknown in docs/engineering-document-control.md.

  It is also cheap NOW and expensive later: the Monday board is still being built,
  so a step name can still change. Once operators are trained on it, it cannot.

DESIGN: A REVIEW, NOT A BLANK PAGE
  Every row arrives pre-filled with a best guess and a confidence marker. A meeting
  that starts from 26 blank rows spends its time on transcription; one that starts
  from 26 guesses spends it on the 8 that are wrong. Guesses are marked so nobody
  mistakes them for decisions:

    OK    - confident, confirm and move on
    ???   - a real question, needs an answer in the room
    N/A   - deliberately no documents (a buffer or a wait is still a tracked step)

  Decision already taken (2026-09-14): **every Monday step is tracked**, including
  the Stockage buffers. A step needing no documents is a valid, normal state -
  routing and tracking are independent axes. So "Documents?" = Non is an answer,
  not a gap, and nothing here is a case for deleting a step.

HONESTY ABOUT THE STEP LIST
  The 26 groups were read off the live board by eye on 2026-09-14 while collapsing
  groups one at a time. Two stretches scrolled past faster than they could be
  captured - between `Inspection Mise en Cuve` and `Vaccum`, and between
  `Montage Electrique` and `Finition`. **Re-read the board against this list before
  the meeting**; a missing step is a missing row, and this file cannot know it.
"""
import io, os, sys

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("openpyxl required:  pip install openpyxl")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "reports", "step-mapping-worksheet.xlsx")

# --- vocabularies -----------------------------------------------------------
BLUE = ["Essai", "Qualité", "Isolation", "Ass + Stacking", "Tanking", "Test",
        "Finition", "Filerie", "Cuve", "Vente", "Achats"]
BLUE_EXTRA = ["Aucun", "À confirmer"]

LOCATION = ["Isolation", "Bobinage", "Stacking", "Assemblage", "Four", "Tanking",
            "Test", "Finition", "Livraison", "Entrepôt", "Extérieur",
            "Réparation"]
LOCATION_EXTRA = ["(aucun équivalent)", "À confirmer"]

KIND = ["Poste de travail", "Tampon / stockage", "Inspection", "Attente",
        "Retouche", "Autre"]
YESNO = ["Oui", "Non", "À confirmer"]

# --- the rows: Monday step, kind, needs docs, blue dept, Location, confidence, note
# Guesses, deliberately. The ??? rows are the agenda.
STEPS = [
    ("En attente de production", "Attente", "Non", "Aucun", "(aucun équivalent)", "OK",
     "Avant le début. Suivi du temps d'attente seulement."),
    ("Isolation", "Poste de travail", "Oui", "Isolation", "Isolation", "OK",
     "Correspondance directe, 11 dessins."),
    ("Stockage Isolation", "Tampon / stockage", "Non", "Aucun", "(aucun équivalent)", "N/A",
     "Tampon. Suivi oui, documents non."),
    ("Bobinage", "Poste de travail", "À confirmer", "À confirmer", "Bobinage", "???",
     "QUESTION 1 - le dossier bleu ne donne AUCUN document au bobinage, alors que "
     "c'est un vrai poste avec son propre classeur (FRM09). Lacune ou réalité ?"),
    ("Stockage Bobinage", "Tampon / stockage", "Non", "Aucun", "(aucun équivalent)", "N/A", ""),
    ("Enroulage", "Poste de travail", "À confirmer", "À confirmer", "À confirmer", "???",
     "QUESTION 2 - Enroulage vs Bobinage : deux postes distincts sur Monday. "
     "Lequel reçoit quoi ?"),
    ("Stockage Enroulage", "Tampon / stockage", "Non", "Aucun", "(aucun équivalent)", "N/A", ""),
    ("Assemblage", "Poste de travail", "Oui", "Ass + Stacking", "Assemblage", "???",
     "QUESTION 3 - 'Ass + Stacking' est UNE chemise couvrant DEUX valeurs de Location "
     "(Assemblage + Stacking), et Monday n'a pas de groupe Stacking. 26 dessins en jeu."),
    ("Test Ratio", "Inspection", "À confirmer", "À confirmer", "À confirmer", "???",
     "QUESTION 4 - Essai (rouge, 8 doc) et Test (vert, 9 doc) sont DEUX chemises "
     "distinctes. Laquelle correspond à Test Ratio, et laquelle à Tests ?"),
    ("Stockage Assemblage", "Tampon / stockage", "Non", "Aucun", "(aucun équivalent)", "N/A", ""),
    ("Four", "Poste de travail", "À confirmer", "Aucun", "Four", "???",
     "Étuvage. Aucun dessin évident - à confirmer."),
    ("Sortie Four et Test DF", "Inspection", "À confirmer", "À confirmer", "Four", "???",
     "Voir question 4."),
    ("Encuvage", "Poste de travail", "Oui", "Tanking", "Tanking", "OK",
     "Mise en cuve = Tanking, 17 dessins."),
    ("Inspection Mise en Cuve", "Inspection", "À confirmer", "Qualité", "Tanking", "???",
     "Qualité a 24 dessins mais n'est pas un poste - c'est une fonction. "
     "Où arrivent-ils réellement ?"),
    ("Vaccum", "Poste de travail", "À confirmer", "À confirmer", "Tanking", "???",
     "Orthographe sur Monday : 'Vaccum'. À corriger en 'Vacuum' ?"),
    ("Tests", "Poste de travail", "Oui", "Test", "Test", "???", "Voir question 4."),
    ("Soudure", "Poste de travail", "À confirmer", "À confirmer", "À confirmer", "???",
     "Aucune colonne dossier bleu ne correspond."),
    ("Montage Électrique", "Poste de travail", "Oui", "Filerie", "Assemblage", "???",
     "Filerie (violet, 9 dessins) = filage. À confirmer."),
    ("Finition", "Poste de travail", "Oui", "Finition", "Finition", "OK",
     "Correspondance directe, 19 dessins."),
    ("Inspection Finale", "Inspection", "À confirmer", "Qualité", "Finition", "???",
     "Voir Inspection Mise en Cuve."),
    ("En attente de tests d'huiles", "Attente", "Non", "Aucun", "(aucun équivalent)", "N/A",
     "Attente d'un résultat externe."),
    ("Vérification NC", "Inspection", "À confirmer", "Qualité", "Réparation", "???",
     "Non-conformités - géré sur les tableaux NC, pas ici."),
    ("Expédition", "Poste de travail", "À confirmer", "À confirmer", "Livraison", "???",
     "Palette (PL-Master) va à Finition/Cuve/Vente - et à l'expédition ?"),
    ("Reparation", "Retouche", "À confirmer", "À confirmer", "Réparation", "???",
     "Orthographe sur Monday : 'Reparation'. À corriger en 'Réparation' ?"),
]

# The 11 blue-folder columns, from reports/dossier-bleu.json
BLUE_ROWS = [
    ("Essai", "Rouge", 8, "Poste", "???  Essai vs Test - deux chemises, un seul 'Test' dans Location"),
    ("Qualité", "Rose", 24, "Fonction",
     "???  2e plus gros volume, mais Qualité n'est pas un poste de la ligne"),
    ("Isolation", "Jaune", 11, "Poste", "OK  correspondance directe"),
    ("Ass + Stacking", "Gris", 26, "Poste", "???  une chemise, deux postes"),
    ("Tanking", "Bleu", 17, "Poste", "OK  = Encuvage sur Monday"),
    ("Test", "Vert", 9, "Poste", "???  voir Essai"),
    ("Finition", "Orange", 19, "Poste", "OK  correspondance directe"),
    ("Filerie", "Violet", 9, "Poste", "???  = Montage Électrique ?"),
    ("Cuve", "Beige", 26, "EXTERNE",
     "???  PLUS GROS VOLUME. Fournisseur de cuves (CADORETTE/METELEC/FRAMECO) - "
     "ces documents sortent de l'usine. Pas une tablette d'atelier."),
    ("Vente", "Beige", 4, "Bureau", "Hors atelier"),
    ("Achats", "Beige", 10, "Bureau", "Hors atelier"),
]

QUESTIONS = [
    ("1", "Bobinage ne reçoit aucun dessin dans le dossier bleu",
     "C'est un vrai poste avec son propre classeur (FRM09). Une lacune de "
     "l'analyse, ou le bobinage travaille-t-il vraiment sans dessin ?",
     "Bloque le routage vers un poste complet"),
    ("2", "Enroulage vs Bobinage", "Deux groupes distincts sur Monday. Lequel reçoit quoi ?",
     "Bloque le routage sur deux postes"),
    ("3", "'Ass + Stacking' = une chemise, deux postes",
     "Assemblage + Stacking dans Location, et Monday n'a pas de groupe Stacking du tout.",
     "26 dessins - le 2e plus gros volume d'atelier"),
    ("4", "Essai (rouge) vs Test (vert)",
     "Deux chemises distinctes, mais Location n'a qu'un 'Test'. Monday a "
     "'Test Ratio', 'Sortie Four et Test DF' et 'Tests'.",
     "17 dessins répartis entre trois étapes"),
    ("5", "Cuve = fournisseur externe, pas un poste",
     "26 exemplaires, le plus gros volume. Va chez CADORETTE/METELEC/FRAMECO. "
     "Comment ces documents sortent-ils ? Lien partagé, PDF par courriel, autre ?",
     "Exigence différente des tablettes d'atelier"),
    ("6", "Qualité / Vente / Achats ne sont pas des postes",
     "38 exemplaires au total vers des fonctions de bureau. Quelle interface ?",
     "Ces gens n'ont pas de tablette de poste"),
    ("7", "Deux des 56 lignes sont des formulaires à REMPLIR",
     "'Formulaire: Points a surveiller' et 'Order Check List' - l'atelier écrit "
     "dessus. En numérique, ce n'est plus un PDF à consulter.",
     "Portée séparée - formulaire Monday ou liste SharePoint"),
    ("8", "Sept lignes n'ont aucun numéro de dessin",
     "Com. atelier, Estampes, Flange Network, HV busbar, X0 Bar support, "
     "X0 Connection, LY Layout. X0 Bar support a 0 exemplaire - à retirer ?",
     "Impossible de les étiqueter sans source"),
    ("9", "Une consigne physique sans équivalent numérique",
     "Nameplate (avec +), colonne Essai : 'placer dans chemise sur la table à dessins'.",
     "Que devient-elle sans papier ?"),
    ("10", "Les 56 types de documents sont-ils tous encore d'actualité ?",
     "L'analyse date du 2026-08-21. La migration est le bon moment pour élaguer.",
     "Évite de migrer des dessins morts"),
]

# --- styling ---------------------------------------------------------------
HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(color="FFFFFF", bold=True, size=11)
Q_FILL = PatternFill("solid", fgColor="FCE4D6")     # ??? rows
NA_FILL = PatternFill("solid", fgColor="F2F2F2")    # N/A rows
OK_FILL = PatternFill("solid", fgColor="E2EFDA")    # OK rows
TITLE = Font(bold=True, size=14)
THIN = Border(*[Side(style="thin", color="BFBFBF")] * 4)


def style_header(ws, row=1):
    for c in ws[row]:
        if c.value:
            c.fill, c.font = HDR_FILL, HDR_FONT
            c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def widths(ws, spec):
    for i, w in enumerate(spec, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def build():
    wb = openpyxl.Workbook()

    # ---- Sheet: Vocabulaire (feeds every dropdown; a range beats an inline list,
    # which Excel caps at 255 characters) ----
    voc = wb.active
    voc.title = "Vocabulaire"
    voc["A1"], voc["B1"], voc["C1"], voc["D1"] = ("Dossier bleu", "Location", "Type d'étape", "Oui/Non")
    for i, v in enumerate(BLUE + BLUE_EXTRA, start=2):
        voc.cell(row=i, column=1, value=v)
    for i, v in enumerate(LOCATION + LOCATION_EXTRA, start=2):
        voc.cell(row=i, column=2, value=v)
    for i, v in enumerate(KIND, start=2):
        voc.cell(row=i, column=3, value=v)
    for i, v in enumerate(YESNO, start=2):
        voc.cell(row=i, column=4, value=v)
    style_header(voc)
    widths(voc, [20, 20, 20, 14])

    nblue, nloc, nkind, nyn = len(BLUE + BLUE_EXTRA), len(LOCATION + LOCATION_EXTRA), len(KIND), len(YESNO)

    # ---- Sheet: Correspondance (the main worksheet) ----
    ws = wb.create_sheet("Correspondance", 0)
    ws["A1"] = "Correspondance des étapes de production"
    ws["A1"].font = TITLE
    ws["A2"] = ("Chaque ligne est une PROPOSITION à confirmer, pas une décision. "
                "Orange = question réelle. Gris = aucun document (normal). Vert = confirmer et passer.")
    ws["A3"] = ("Décision déjà prise : TOUTES les étapes Monday sont suivies, "
                "y compris les tampons. Une étape sans document reste une étape suivie.")
    ws["A4"] = ("⚠ La liste des 26 étapes a été relevée à l'œil le 2026-09-14. "
                "VÉRIFIER contre le tableau Monday avant la réunion - il peut en manquer.")
    for r in (2, 3, 4):
        ws.cell(row=r, column=1).font = Font(italic=True, size=10)

    hdr = ["Étape Monday", "Type d'étape", "Documents ?", "Chemise dossier bleu",
           "Équivalent Location", "État", "Note / question", "DÉCISION (à remplir)"]
    for i, h in enumerate(hdr, start=1):
        ws.cell(row=6, column=i, value=h)
    style_header(ws, row=6)
    ws.freeze_panes = "A7"

    for i, (step, kind, docs, blue, loc, conf, note) in enumerate(STEPS, start=7):
        vals = [step, kind, docs, blue, loc, conf, note, ""]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=i, column=j, value=v)
            c.border = THIN
            c.alignment = Alignment(vertical="top", wrap_text=(j in (7, 8)))
        fill = Q_FILL if conf == "???" else (NA_FILL if conf == "N/A" else OK_FILL)
        for j in range(1, 9):
            ws.cell(row=i, column=j).fill = fill
        ws.cell(row=i, column=1).font = Font(bold=True)

    last = 6 + len(STEPS)
    for col, src, n in (("B", "C", nkind), ("C", "D", nyn), ("D", "A", nblue), ("E", "B", nloc)):
        dv = DataValidation(type="list",
                            formula1="=Vocabulaire!$%s$2:$%s$%d" % (src, src, n + 1),
                            allow_blank=True)
        ws.add_data_validation(dv)
        dv.add("%s7:%s%d" % (col, col, last))

    widths(ws, [30, 20, 14, 22, 22, 8, 52, 30])
    ws.row_dimensions[6].height = 30

    # ---- Sheet: Dossier bleu ----
    b = wb.create_sheet("Dossier bleu")
    b["A1"] = "Les 11 chemises, et pourquoi elles ne correspondent pas 1-pour-1"
    b["A1"].font = TITLE
    b["A2"] = ("Trois natures différentes : poste d'atelier, fonction de bureau, "
               "fournisseur externe. Seuls les postes peuvent être accrochés à une étape Monday.")
    b["A2"].font = Font(italic=True, size=10)
    for i, h in enumerate(["Chemise", "Couleur", "Exemplaires", "Nature", "État / question",
                           "Étape(s) Monday (à remplir)"], start=1):
        b.cell(row=4, column=i, value=h)
    style_header(b, row=4)
    b.freeze_panes = "A5"
    for i, (name, colour, n, nature, note) in enumerate(BLUE_ROWS, start=5):
        for j, v in enumerate([name, colour, n, nature, note, ""], start=1):
            c = b.cell(row=i, column=j, value=v)
            c.border = THIN
            c.alignment = Alignment(vertical="top", wrap_text=(j in (5, 6)))
        if note.startswith("???"):
            for j in range(1, 7):
                b.cell(row=i, column=j).fill = Q_FILL
        b.cell(row=i, column=1).font = Font(bold=True)
    b.cell(row=5 + len(BLUE_ROWS), column=1, value="TOTAL")
    b.cell(row=5 + len(BLUE_ROWS), column=3, value=sum(r[2] for r in BLUE_ROWS))
    b.cell(row=5 + len(BLUE_ROWS), column=1).font = Font(bold=True)
    b.cell(row=5 + len(BLUE_ROWS), column=3).font = Font(bold=True)
    widths(b, [20, 12, 14, 14, 62, 30])

    # ---- Sheet: Questions ----
    q = wb.create_sheet("Questions")
    q["A1"] = "Les 10 questions à régler"
    q["A1"].font = TITLE
    for i, h in enumerate(["#", "Question", "Détail", "Pourquoi ça bloque",
                           "RÉPONSE (à remplir)"], start=1):
        q.cell(row=3, column=i, value=h)
    style_header(q, row=3)
    q.freeze_panes = "A4"
    for i, row in enumerate(QUESTIONS, start=4):
        for j, v in enumerate(list(row) + [""], start=1):
            c = q.cell(row=i, column=j, value=v)
            c.border = THIN
            c.alignment = Alignment(vertical="top", wrap_text=(j in (2, 3, 4, 5)))
        q.row_dimensions[i].height = 46
    widths(q, [5, 38, 58, 34, 38])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    p = build()
    n_q = sum(1 for s in STEPS if s[5] == "???")
    print("wrote %s" % os.path.relpath(p, ROOT).replace("\\", "/"))
    print("  %d Monday steps, %d marked as real questions" % (len(STEPS), n_q))
    print("  %d blue-folder columns, %d copies total" % (len(BLUE_ROWS), sum(r[2] for r in BLUE_ROWS)))
    print("  %d questions for the room" % len(QUESTIONS))
