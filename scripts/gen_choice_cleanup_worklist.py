# -*- coding: utf-8 -*-
"""Worklist for making Model Revisions' Choice columns STRICT.

Plan (user, 2026-09-08): make the PARENT strict rather than mirroring its fill-in
permissiveness -- free text is where the inconsistency entered, so closing it stops new
dirt at the source. Seed the option lists with the real vocabulary, clean the data onto
it, then the Order Items copies can be strict Choice columns too.

⚠️ THE TARGET IS THE USER'S CANONICAL VOCABULARY, NOT THE CURRENT SHAREPOINT OPTIONS.
The live option lists are what is there today; the lists below are what they should be.
They differ in two deliberate ways, both given by the user:

  * Model Description drops "LTC"    -- "If a model has LTC (Onload Tap Changer) it should
                                        be in the NOTES, not a model type or description."

Model Description stays MultiChoice on purpose: a transformer can legitimately be several
of these at once. That is the user's stated reason, not an accident of the data.

🔴 NOTHING HERE IS APPLIED. Every row is a PROPOSAL for the user to confirm -- their
explicit instruction: "we really dont want to loos data". Two rules enforce it:

  1. Every proposal carries `preserve_to_notes`: the original text to append to Notes
     whenever a value is cleared, replaced or dropped. Nothing is silently discarded.
     It is defaulted ON; only a pure case fix or a move that rewrites the same text
     elsewhere is exempt, because those are recoverable by inspection.
  2. The tiers are a CONFIDENCE signal, not permission:
       MECHANICAL  deterministic, safe to approve in bulk -- still needs sign-off
       DECIDE      a person must answer before anything is written

Reads the newest sharepoint-lists export. Writes NOTHING to the tenant.
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
    "None",                              # deliberate: "not yet decided" at model creation
    "1PH PAD (MINIPAD)", "3PH PAD (PADMOUNT)", "POLEMOUNT", "SUBSTATION",
    "NETWORK", "1PH SUBMERSIBLE", "3PH SUBMERSIBLE", "GROUNDING TX",
]
# GROUNDING TX: only Primary Voltage is required; kVA and Secondary may be empty.

DESCRIPTIONS = [
    "POWER-S", "POWER-W", "C2",          # substations
    "UNITIZED", "FLAT FRONT",
    "MALT", "MALT + SA", "ZIG-ZAG", "ZIG-ZAG + SA",   # grounding
    "PARTS", "SPAREPARTS",
    "SUBSTATION", "SUBST-STACK",
    "SUBWAY", "1PH-VAULT", "3PH-VAULT",  # network
]

TYPE_SET, DESC_SET = set(MODEL_TYPES), set(DESCRIPTIONS)
# 'None' is deliberately NOT junk: it is the real "not yet decided" value.
JUNK = re.compile(r'^(0+|N/?A|-+)$', re.I)


def schema(list_name):
    """Field metadata from the export's ListSchema record.

    Two traps, both hit while writing this: the raw CSV text has doubled quotes so the XML
    is only well-formed after the JSON decode, and `\\b` on the attribute name matters --
    a bare `Type="` also matches inside `FromBaseType="FALSE"`.
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


def canon(s):
    return re.sub(r'[^A-Z0-9]', '', str(s).upper().replace("&", "AND"))


TYPE_CANON = {canon(v): v for v in MODEL_TYPES}
DESC_CANON = {canon(v): v for v in DESCRIPTIONS}
# Word-order variants: canon() strips punctuation but not order, so these need naming.
DESC_CANON.update({canon("VAULT-1PH"): "1PH-VAULT", canon("VAULT-3PH"): "3PH-VAULT"})


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


def main():
    path, sch = schema("Model Revisions")
    rows = lib.load(path)
    TD, DD, ND = sch["Model_x0020_Type"]["disp"], sch["Description"]["disp"], sch["Notes"]["disp"]
    work = []

    def add(r, col, cur, tier, action, proposed, why, preserve=None):
        if preserve is None:
            pure_case = action == "set" and canon(cur) == canon(proposed)
            rewritten = "move to" in action
            preserve = "" if (pure_case or rewritten) else "%s was %r" % (col, cur)
        work.append({"row_id": r.get("Id") or r.get("ID") or "",
                     "model_revision": r.get("Model_Revion_ID") or r.get("Title") or "",
                     "column": col, "current_value": cur, "tier": tier,
                     "action": action, "proposed_value": proposed,
                     "preserve_to_notes": preserve, "why": why})

    for r in rows:
        tv = str(r.get(TD) or "").strip()
        dv = multi(r.get(DD))
        phases = str(r.get("Phases") or "").strip()

        # ---------------------------------------------------------- Model Type
        if tv and tv not in TYPE_SET:
            if JUNK.match(tv):
                add(r, "Model Type", tv, "MECHANICAL", "clear", "",
                    "not a real value -- 'None' is a REAL option and is left untouched")
            elif tv == "SUBMERSIBLE":
                tgt = {"1": "1PH SUBMERSIBLE", "3": "3PH SUBMERSIBLE"}.get(phases)
                if tgt:
                    add(r, "Model Type", tv, "MECHANICAL", "set", tgt,
                        "Phases=%s resolves 1PH vs 3PH deterministically" % phases)
                else:
                    add(r, "Model Type", tv, "DECIDE", "set", "1PH/3PH SUBMERSIBLE",
                        "Phases is %r" % phases)
            elif "LTC" in tv.upper():
                # user's rule: LTC belongs in Notes, never as a type or a description
                base = tv.upper().replace("LTC", "").replace("-", " ").strip()
                sugg = ("Notes += 'LTC'; Model Type = ?" if not base else
                        "Notes += 'LTC'; Description = POWER-S or POWER-W?; Model Type = ?")
                add(r, "Model Type", tv, "DECIDE", "split", sugg,
                    "LTC goes in Notes. %s" % ("POWER-? is ambiguous between POWER-S and POWER-W"
                                               if base else "leaves Model Type needing a real value"))
            elif canon(tv) in TYPE_CANON:
                add(r, "Model Type", tv, "MECHANICAL", "set", TYPE_CANON[canon(tv)],
                    "case/spacing variant of a real type")
            elif tv in DESC_SET or canon(tv) in DESC_CANON:
                tgt = DESC_CANON[canon(tv)]
                add(r, "Model Type", tv, "MECHANICAL", "move to Model Description", tgt,
                    "a Description value, not a Type; Description is MultiChoice so nothing is lost")
            elif canon(tv) in ("PADMOUNT",):
                add(r, "Model Type", tv, "MECHANICAL", "set", "3PH PAD (PADMOUNT)", "shorthand")
            elif canon(tv) in ("MINPAD", "PROTOMINIPAD"):
                add(r, "Model Type", tv, "MECHANICAL", "set", "1PH PAD (MINIPAD)",
                    "shorthand" + ("; 'PROTO' -> Notes" if "PROTO" in tv.upper() else ""))
            else:
                add(r, "Model Type", tv, "DECIDE", "set", "?",
                    "not in the canonical Model Type list")

        # ------------------------------------------------- Model Description
        for v in dv:
            if v in DESC_SET:
                continue
            if JUNK.match(v):
                add(r, "Model Description", v, "MECHANICAL", "remove selection", "", "not a real value")
            elif v == "NETWORK" and tv == "NETWORK":
                add(r, "Model Description", v, "MECHANICAL", "remove selection", "",
                    "duplicates Model Type, which already reads NETWORK")
            elif v in TYPE_SET or canon(v) in TYPE_CANON or canon(v) in ("PADMOUNT", "MINPAD", "MINPAD1PH", "MINPAD1HP"):
                tgt = TYPE_CANON.get(canon(v)) or {"PADMOUNT": "3PH PAD (PADMOUNT)"}.get(
                    canon(v), "1PH PAD (MINIPAD)")
                add(r, "Model Description", v, "MECHANICAL", "remove selection; ensure Model Type", tgt,
                    "a Model Type value sitting in Description")
            elif canon(v) in DESC_CANON:
                add(r, "Model Description", v, "MECHANICAL", "set", DESC_CANON[canon(v)],
                    "case/word-order variant of a real description")
            elif "SUBSTATION" in canon(v) and canon(v).replace("SUBSTATION", "") == "LTC":
                add(r, "Model Description", v, "MECHANICAL", "set + note", "SUBSTATION   (Notes += 'LTC')",
                    "LTC goes in Notes; the SUBSTATION part is a real description")
            elif v.upper() == "LTC":
                add(r, "Model Description", v, "DECIDE", "remove selection; Notes += 'LTC'", "",
                    "LTC goes in Notes - but it is the ONLY description on these rows, "
                    "so they end up with no subtype")
            elif canon(v) == "SUBWAY1PH":
                add(r, "Model Description", v, "MECHANICAL", "set", "SUBWAY",
                    "SUBWAY has no phase variants in the canonical list")
            else:
                add(r, "Model Description", v, "DECIDE", "set", "?",
                    "not in the canonical Model Description list")

    stamp = "2026-09-08"
    outp = os.path.join(ROOT, "reports", "Model Revisions choice cleanup %s.csv" % stamp)
    with io.open(outp, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["row_id", "model_revision", "column", "current_value",
                                           "tier", "action", "proposed_value",
                                           "preserve_to_notes", "why"])
        w.writeheader()
        w.writerows(sorted(work, key=lambda x: (x["tier"], x["column"], x["current_value"])))

    print("wrote %s   (%d rows)\n" % (outp, len(work)))
    for t, n in Counter(x["tier"] for x in work).most_common():
        print("%-8s %d" % (t, n))
    print("\nMECHANICAL -- deterministic, but still needs your sign-off:")
    for k, n in Counter("%-18s %-16s %-30s -> %s" % (x["column"], x["current_value"], x["action"],
                                                     x["proposed_value"] or "(nothing)")
                        for x in work if x["tier"] == "MECHANICAL").most_common():
        print("   %s  %d" % (k, n))
    kept = sum(1 for x in work if x["preserve_to_notes"])
    print("\n   %d of %d proposals write the original value into Notes first, so nothing is lost."
          % (kept, len(work)))
    print("\nDECIDE -- open questions, nothing is written until these are answered:")
    seen = Counter((x["column"], x["current_value"], x["proposed_value"], x["why"])
                   for x in work if x["tier"] == "DECIDE")
    for (col, cur, prop, why), n in sorted(seen.items(), key=lambda kv: -kv[1]):
        print("   %-18s %-18s %3d rows" % (col, cur, n))
        print("        suggested: %s" % prop)
        print("        %s" % why)
    print("\n%d distinct decisions cover all %d DECIDE rows."
          % (len(seen), sum(seen.values())))

    # option-list deltas the tenant needs
    print("\nOption-list changes needed on Model Revisions:")
    for fld, canon_list in (("Model_x0020_Type", MODEL_TYPES), ("Description", DESCRIPTIONS)):
        cur = sch[fld]["choices"]
        print("   %-22s remove: %-28s add: %s"
              % (sch[fld]["disp"],
                 ", ".join(c for c in cur if c not in canon_list) or "(none)",
                 ", ".join(c for c in canon_list if c not in cur) or "(none)"))


if __name__ == "__main__":
    main()
