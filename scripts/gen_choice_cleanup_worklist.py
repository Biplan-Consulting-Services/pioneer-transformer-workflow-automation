# -*- coding: utf-8 -*-
"""Worklist for making Model Revisions' Choice columns STRICT.

Plan (user, 2026-09-08): make the PARENT strict rather than mirroring its fill-in
permissiveness -- free text is where the inconsistency entered, so closing it stops new
dirt at the source. Clean the data onto the real vocabulary, then the Order Items copies
can be strict Choice columns too.

THE FOUR RULES THE USER GAVE, and what each one changed here
------------------------------------------------------------
1. The canonical vocabularies below are authoritative -- not the current SharePoint
   option lists, which are only what happens to be there today.

2. "None" STAYS a Model Type option. It is not junk: it is the deliberate "not yet
   decided" value used when a model is first created. Never cleared, never retired.

3. LTC (Onload Tap Changer) belongs in the NOTES, never as a type or a description.

4. "If there is no clear replacement for a type or description we have to keep it in the
   list until it is phased out." So an unmappable value is neither cleared nor guessed
   at: it becomes a legitimate option flagged PHASE-OUT. That keeps the column strict
   (nothing is rejected on write, which is what the Order Items copy needs) while still
   closing the door on NEW free text.

5. "For the 3PH or 1PH we can reference the phase number column." The Phases column
   resolves the phase-ambiguous names -- and, used as a CHECK rather than only as a
   resolver, it also disagreed with three name-based mappings that looked obvious:

     PADMOUNT   33 rows -> 28 at Phases=3, but 5 BLANK
     VAULT-1PH  13 rows -> 10 at Phases=1, 1 at Phases=3 (a real contradiction), 2 blank

   So a name is never trusted over the data. Where Phases confirms the name the row is
   MECHANICAL; where Phases is blank/0 it is UNRESOLVED; where Phases contradicts the
   name it is a CONTRADICTION and goes to the top of the review list.

Model Description stays MultiChoice on purpose: a transformer can legitimately be several
of these at once (the user's reason -- e.g. an LTC substation).

NOTHING HERE IS APPLIED. Every row is a PROPOSAL for the user to confirm -- their
explicit instruction: "we really dont want to loos data". Two rules enforce it:

  * Every proposal carries `preserve_to_notes`: the original text to append to Notes
    whenever a value is cleared, replaced or dropped. Defaulted ON; only a pure case fix
    or a move that rewrites the same text elsewhere is exempt, being recoverable by
    inspection.
  * The tiers are a CONFIDENCE signal, not permission:
      MECHANICAL     deterministic and data-confirmed -- still needs sign-off
      DECIDE         a person must answer before anything is written
      PHASE-OUT      keep the value AND the option; retire it when usage hits zero

This script reads the newest sharepoint-lists export and writes one CSV report. It makes
no network calls and touches no SharePoint list.
"""
import io, os, re, csv, glob, json, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lib  # noqa: E402

DEC = json.JSONDecoder()

# ---------------------------------------------------------------- the vocabulary
MODEL_TYPES = [
    "None",                              # deliberate "not yet decided" at model creation
    "1PH PAD (MINIPAD)", "3PH PAD (PADMOUNT)", "POLEMOUNT", "SUBSTATION",
    "NETWORK", "1PH SUBMERSIBLE", "3PH SUBMERSIBLE", "GROUNDING TX",
]
# GROUNDING TX: only Primary Voltage is required; kVA and Secondary may be empty.

DESCRIPTIONS = [
    "POWER-S", "POWER-W", "C2",                        # substations
    "UNITIZED", "FLAT FRONT",
    "MALT", "MALT + SA", "ZIG-ZAG", "ZIG-ZAG + SA",    # grounding
    "PARTS", "SPAREPARTS",
    "SUBSTATION", "SUBST-STACK",
    "SUBWAY", "1PH-VAULT", "3PH-VAULT",                # network
]

# Rule 4: no clear replacement -> keep the value and keep the option, flagged for retirement.
PHASE_OUT_TYPES = {
    "ANNEX":     "5 rows. Not in the canonical list; unclear against Core Type's 'Annexe'.",
    "POWER-LTC": "9 rows. LTC belongs in Notes, but POWER-? is ambiguous between POWER-S "
                 "and POWER-W, so there is no clear replacement. All 9 are Phases=3.",
}
PHASE_OUT_DESCRIPTIONS = {
    "ANNEX":          "5 rows, the same rows as the Model Type ANNEX.",
    "PROTOTYPE":      "1 row.",
    "Goujon":         "1 row. A stud/bolt -- plausibly PARTS, but not confidently.",
    "PLAQUE ANCRAGE": "1 row. An anchor plate -- same.",
    "LTC":            "7 rows where LTC is the ONLY description. LTC moves to Notes for new "
                      "models, but removing it here would leave these rows with no subtype, "
                      "so the option stays until they are re-typed.",
}

TYPE_SET = set(MODEL_TYPES) | set(PHASE_OUT_TYPES)
DESC_SET = set(DESCRIPTIONS) | set(PHASE_OUT_DESCRIPTIONS)
JUNK = re.compile(r'^(0+|N/?A|-+)$', re.I)          # 'None' is NOT junk -- rule 2
GOOD_PHASES = ("1", "3")


def canon(s):
    return re.sub(r'[^A-Z0-9]', '', str(s).upper().replace("&", "AND"))


# alias -> list of (target, required Phases or None). More than one entry means the
# Phases column is the discriminator.
TYPE_ALIAS = {
    "PADMOUNT":       [("3PH PAD (PADMOUNT)", "3")],
    "MINPAD":         [("1PH PAD (MINIPAD)", "1")],
    "PROTOMINIPAD":   [("1PH PAD (MINIPAD)", "1")],
    "SUBMERSIBLE":    [("1PH SUBMERSIBLE", "1"), ("3PH SUBMERSIBLE", "3")],
    "PAD":            [("1PH PAD (MINIPAD)", "1"), ("3PH PAD (PADMOUNT)", "3")],
}
DESC_ALIAS = {
    "VAULT1PH":   [("1PH-VAULT", "1")],
    "VAULT3PH":   [("3PH-VAULT", "3")],
    "VAULT":      [("1PH-VAULT", "1"), ("3PH-VAULT", "3")],
    "SUBWAY1PH":  [("SUBWAY", "1")],
    "SUBWAY3PH":  [("SUBWAY", "3")],
    "SPAREPARTS": [("SPAREPARTS", None)],
}
for _v in MODEL_TYPES:
    TYPE_ALIAS.setdefault(canon(_v), [(_v, None)])
for _v in DESCRIPTIONS:
    DESC_ALIAS.setdefault(canon(_v), [(_v, None)])


def multi(value):
    s = str(value or "").strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            return [str(p.get("Value", p) if isinstance(p, dict) else p).strip() for p in json.loads(s)]
        except Exception:
            return [s]
    return [p.strip() for p in re.split(r";\s*", s) if p.strip()]


def schema(list_name):
    """Field metadata from the export's own ListSchema record.

    Two traps, both hit while writing this: the raw CSV text carries doubled quotes so the
    XML is only well-formed after the JSON decode, and `\\b` on the attribute name matters
    -- a bare `Type="` also matches inside `FromBaseType="FALSE"`.
    """
    path = sorted(glob.glob(os.path.join(ROOT, "sharepoint-lists", "%s 2026-*.csv" % list_name)))[-1]
    raw = io.open(path, encoding="utf-8-sig").read()
    xml = DEC.raw_decode(raw, raw.find("{"))[0]["schemaXmlList"]
    xml = xml if isinstance(xml, str) else " ".join(xml)
    out = {}
    for m in re.finditer(r'<Field\b([^>]*?)(/>|>(.*?)</Field>)', xml, re.S):
        attrs, body = m.group(1), m.group(3) or ""
        g = lambda k: (re.search(r'\b' + k + r'="([^"]*)"', attrs) or [None, None])[1]
        out[g("Name")] = {
            "disp": g("DisplayName"), "type": g("Type"),
            "fill": (g("FillInChoice") or "FALSE").upper(),
            "choices": [c.replace("&amp;", "&") for c in re.findall(r'<CHOICE>(.*?)</CHOICE>', body, re.S)],
        }
    return path, out


def resolve(alias_table, value, phases):
    """(target, tier, why) for a value, using Phases as resolver AND as a check.

    Returns tier None when the value is already canonical and needs no change.
    """
    key = canon(value)
    opts = alias_table.get(key)
    if not opts:
        return None, None, None
    if len(opts) == 1 and opts[0][1] is None:
        tgt = opts[0][0]
        if tgt == value:
            return None, None, None                      # already correct
        return tgt, "MECHANICAL", "case/spacing variant of %r" % tgt
    by_phase = {p: t for t, p in opts if p}
    if phases in by_phase:
        return (by_phase[phases], "MECHANICAL",
                "Phases=%s confirms %r" % (phases, by_phase[phases]))
    if phases not in GOOD_PHASES:
        return (None, "DECIDE",
                "Phases is %r, so the phase cannot be resolved from the data" %
                (phases or "(blank)"))
    # Phases is valid but names a different variant than the text does.
    named = [t for t, p in opts if p]
    return (by_phase.get(phases), "DECIDE",
            "CONTRADICTION: the value says %s but Phases=%s. Candidates: %s"
            % (value, phases, ", ".join(named)))


def main():
    path, sch = schema("Model Revisions")
    rows = lib.load(path)
    TD, DD = sch["Model_x0020_Type"]["disp"], sch["Description"]["disp"]
    work = []

    def add(r, col, cur, tier, action, proposed, why, preserve=None):
        if preserve is None:
            pure_case = action == "set" and canon(cur) == canon(proposed or "")
            rewritten = "move to" in action
            preserve = "" if (pure_case or rewritten) else "%s was %r" % (col, cur)
        work.append({"row_id": r.get("Id") or r.get("ID") or "",
                     "model_revision": r.get("Model_Revion_ID") or r.get("Title") or "",
                     "phases": str(r.get("Phases") or "").strip(),
                     "column": col, "current_value": cur, "tier": tier,
                     "action": action, "proposed_value": proposed or "",
                     "preserve_to_notes": preserve, "why": why})

    for r in rows:
        tv = str(r.get(TD) or "").strip()
        dv = multi(r.get(DD))
        phases = str(r.get("Phases") or "").strip()

        # ------------------------------------------------------------ Model Type
        if tv and tv not in set(MODEL_TYPES):
            if tv in PHASE_OUT_TYPES:
                add(r, "Model Type", tv, "PHASE-OUT", "keep value; keep option", tv,
                    "no clear replacement -- %s" % PHASE_OUT_TYPES[tv], preserve="")
            elif JUNK.match(tv):
                add(r, "Model Type", tv, "MECHANICAL", "clear", "",
                    "not a real value ('None' is a REAL option and is left untouched)")
            elif "LTC" in tv.upper():
                add(r, "Model Type", tv, "DECIDE", "move LTC to Notes; retype", "None",
                    "LTC belongs in Notes (rule 3). Model Type is then undecided, and "
                    "'None' is the value for that -- confirm rather than assume.")
            else:
                tgt, tier, why = resolve(TYPE_ALIAS, tv, phases)
                if tier:
                    add(r, "Model Type", tv, tier, "set", tgt, why)
                elif canon(tv) in {canon(d) for d in DESCRIPTIONS}:
                    real = next(d for d in DESCRIPTIONS if canon(d) == canon(tv))
                    add(r, "Model Type", tv, "MECHANICAL", "move to Model Description", real,
                        "a Description value, not a Type; Description is MultiChoice so "
                        "nothing is lost")
                else:
                    add(r, "Model Type", tv, "DECIDE", "set", "?",
                        "not in the canonical list and no alias matches")

        # ----------------------------------------------------- Model Description
        for v in dv:
            if v in set(DESCRIPTIONS):
                continue
            if v in PHASE_OUT_DESCRIPTIONS:
                add(r, "Model Description", v, "PHASE-OUT", "keep value; keep option", v,
                    "no clear replacement -- %s" % PHASE_OUT_DESCRIPTIONS[v], preserve="")
            elif JUNK.match(v):
                add(r, "Model Description", v, "MECHANICAL", "remove selection", "",
                    "not a real value")
            elif v == "NETWORK" and tv == "NETWORK":
                add(r, "Model Description", v, "MECHANICAL", "remove selection", "",
                    "duplicates Model Type, which already reads NETWORK")
            elif canon(v) in {canon(t) for t in MODEL_TYPES} or canon(v) in ("PADMOUNT", "MINPAD", "MINPAD1PH", "MINPAD1HP"):
                tgt, tier, why = resolve(TYPE_ALIAS, v.replace("-1HP", "").replace("-1PH", "")
                                         if v.upper().startswith("MINPAD") else v, phases)
                add(r, "Model Description", v, tier or "MECHANICAL",
                    "remove selection; set Model Type", tgt or "?",
                    "a Model Type value sitting in Description. %s" % (why or ""))
            elif "LTC" in canon(v) and canon(v) != "LTC":
                base = canon(v).replace("LTC", "").replace("AND", "")
                real = next((d for d in DESCRIPTIONS if canon(d) == base), None)
                if real:
                    add(r, "Model Description", v, "MECHANICAL", "set + note",
                        "%s   (Notes += 'LTC')" % real,
                        "LTC goes in Notes (rule 3); the %s part is a real description" % real)
                else:
                    add(r, "Model Description", v, "DECIDE", "split", "?",
                        "contains LTC but the remainder %r is not a known description" % base)
            else:
                tgt, tier, why = resolve(DESC_ALIAS, v, phases)
                if tier:
                    add(r, "Model Description", v, tier, "set", tgt, why)
                else:
                    add(r, "Model Description", v, "DECIDE", "set", "?",
                        "not in the canonical list and no alias matches")

    stamp = "2026-09-08"
    outp = os.path.join(ROOT, "reports", "Model Revisions choice cleanup %s.csv" % stamp)
    with io.open(outp, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["row_id", "model_revision", "phases", "column",
                                           "current_value", "tier", "action",
                                           "proposed_value", "preserve_to_notes", "why"])
        w.writeheader()
        w.writerows(sorted(work, key=lambda x: (x["tier"], x["column"], x["current_value"])))

    print("wrote %s   (%d proposals)\n" % (outp, len(work)))
    for t, n in Counter(x["tier"] for x in work).most_common():
        print("  %-12s %d" % (t, n))

    print("\nMECHANICAL -- deterministic, Phases-confirmed where phase matters:")
    for k, n in Counter("%-18s %-16s %-34s -> %s"
                        % (x["column"], x["current_value"], x["action"], x["proposed_value"] or "(nothing)")
                        for x in work if x["tier"] == "MECHANICAL").most_common():
        print("   %s  %d" % (k, n))
    kept = sum(1 for x in work if x["preserve_to_notes"])
    print("\n   %d of %d proposals copy the original value into Notes first." % (kept, len(work)))

    print("\nDECIDE -- nothing is written until these are answered:")
    seen = Counter((x["column"], x["current_value"], x["proposed_value"], x["why"])
                   for x in work if x["tier"] == "DECIDE")
    for (col, cur, prop, why), n in sorted(seen.items(),
                                           key=lambda kv: (0 if "CONTRADICTION" in kv[0][3] else 1, -kv[1])):
        print("   %-18s %-16s %3d rows -> %s" % (col, cur, n, prop or "?"))
        print("        %s" % why)
    print("\n   %d questions covering %d rows." % (len(seen), sum(seen.values())))

    print("\nPHASE-OUT -- value and option both retained until usage reaches zero:")
    for (col, cur), n in Counter((x["column"], x["current_value"])
                                 for x in work if x["tier"] == "PHASE-OUT").most_common():
        print("   %-18s %-16s %3d rows" % (col, cur, n))

    print("\nOption-list changes on Model Revisions:")
    for fld, final in (("Model_x0020_Type", list(MODEL_TYPES) + list(PHASE_OUT_TYPES)),
                       ("Description", list(DESCRIPTIONS) + list(PHASE_OUT_DESCRIPTIONS))):
        cur = sch[fld]["choices"]
        print("   %-22s remove: %-22s add: %s"
              % (sch[fld]["disp"],
                 ", ".join(c for c in cur if c not in final) or "(none)",
                 ", ".join(c for c in final if c not in cur) or "(none)"))


if __name__ == "__main__":
    main()
