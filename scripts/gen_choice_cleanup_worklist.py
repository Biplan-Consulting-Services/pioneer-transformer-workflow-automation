# -*- coding: utf-8 -*-
"""Build the worklist for making Model Revisions' Choice columns STRICT.

The user's plan (2026-09-08): stop mirroring the parent's fill-in permissiveness and
make the PARENT strict instead -- fill-in was only ever enabled because FRM10-12 had
inconsistent data -- seeding the option lists with every value currently present, then
retiring the non-standard options as they empty out.

That plan is right. This script exists because of what it turned up on the way: a large
share of the "non-standard values" are NOT values needing an option. They are values
sitting in the WRONG COLUMN, or duplicated across two columns. Seeding those as options
would make the mix-up permanent, which is the opposite of the intent.

So the worklist splits every out-of-list value three ways:

  AUTO    -- mechanical and deterministic. No judgement, no engineering input.
  REVIEW  -- a person must decide (a near-match, or a value nobody here can map).
  OPTION  -- genuinely a distinct value: add it as an option, mark it for phase-out.

Writes reports/Model Revisions choice cleanup <date>.csv. Reads the newest
sharepoint-lists export; writes NOTHING to the tenant.
"""
import io, os, re, csv, glob, json, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lib  # noqa: E402  (same loader every gen_* script uses)

DEC = json.JSONDecoder()


def schema(list_name):
    """Field metadata incl. CHOICES, from the export's own ListSchema record.

    The raw CSV text has CSV-doubled quotes, so the XML is only well-formed after the
    JSON decode -- regexing the raw file finds <Field> tags whose attributes cannot be
    read. And `\\b` on the attribute name matters: a bare `Type="` also matches inside
    `FromBaseType="FALSE"`, which silently reports every field as Type FALSE.
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
            "disp": g("DisplayName"),
            "type": g("Type"),
            "fill": (g("FillInChoice") or "FALSE").upper(),
            "choices": [c.replace("&amp;", "&") for c in re.findall(r'<CHOICE>(.*?)</CHOICE>', body, re.S)],
        }
    return path, out


def canon(s):
    """Case / space / hyphen-insensitive key, for spotting variants of a real option."""
    return re.sub(r'[^A-Z0-9]', '', str(s).upper().replace("&", "AND"))


def multi(value):
    """A MultiChoice cell: exports as a JSON array (the R19 trap) or a '; ' string."""
    s = str(value or "").strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            return [str(p.get("Value", p) if isinstance(p, dict) else p).strip() for p in json.loads(s)]
        except Exception:
            return [s]
    return [p.strip() for p in re.split(r";\s*", s) if p.strip()]


# Near-matches a person should confirm once, then they apply to every row.
# Deliberately NOT applied automatically: each is a judgement about what the shop
# means, and a wrong one writes a plausible-looking wrong value on every row.
SUGGEST = {
    "Model_x0020_Type": {
        "PADMOUNT":       "3PH PAD (PADMOUNT)",
        "MINPAD":         "1PH PAD (MINIPAD)",
        "PROTO MINIPAD":  "1PH PAD (MINIPAD)",
        "Substation":     "SUBSTATION",
        "ZIG ZAG":        "(move to Model Description as ZIG-ZAG)",
        "SPARE PARTS":    "(move to Model Description as SPAREPARTS)",
        "POWER-LTC":      "(move to Model Description: POWER-? + LTC)",
        "POWER LTC":      "(move to Model Description: POWER-? + LTC)",
        "ANNEX":          "?  no obvious target - Core Type has 'Annexe'",
    },
    "Description": {
        "VAULT-1PH":        "1PH-VAULT",
        "SUBWAY-1PH":       "SUBWAY  (+ a 1PH marker?)",
        "SUBSTATION LTC":   "SUBSTATION + LTC   (MultiChoice: two selections)",
        "SUBSTATION + LTC": "SUBSTATION + LTC   (MultiChoice: two selections)",
        "MINPAD-1PH":       "(MINPAD is a Model Type value, not a Description)",
        "MINPAD-1HP":       "(typo of MINPAD-1PH; and MINPAD is a Model Type value)",
        "ZIG ZAG":          "ZIG-ZAG",
        "SPARE PARTS":      "SPAREPARTS",
        "PADMOUNT":         "(PADMOUNT is a Model Type value, not a Description)",
        "ANNEX":            "?  no obvious target",
        "PROTOTYPE":        "?  one-off",
        "Goujon":           "?  one-off",
        "PLAQUE ANCRAGE":   "?  one-off",
    },
}
JUNK = re.compile(r'^(0+|N/?A|-+)$', re.I)


def main():
    path, sch = schema("Model Revisions")
    rows = lib.load(path)
    TY, DE, OI = "Model_x0020_Type", "Description", "Oil_x0020_Type"
    ty_d, de_d, oi_d = sch[TY]["disp"], sch[DE]["disp"], sch[OI]["disp"]
    ty_o, de_o, oi_o = (set(sch[TY]["choices"]), set(sch[DE]["choices"]), set(sch[OI]["choices"]))
    ty_c = {canon(o): o for o in ty_o}
    de_c = {canon(o): o for o in de_o}
    oi_c = {canon(o): o for o in oi_o}

    work = []

    def add(r, col, cur, tier, action, proposed, why):
        work.append({
            "row_id": r.get("Id") or r.get("ID") or "",
            "model_revision": r.get("Model_Revion_ID") or r.get("Pioneer Model Code") or r.get("Title") or "",
            "column": col, "current_value": cur, "tier": tier,
            "action": action, "proposed_value": proposed, "why": why,
        })

    for r in rows:
        tv = str(r.get(ty_d) or "").strip()
        dv = multi(r.get(de_d))
        ov = str(r.get(oi_d) or "").strip()

        # ---- Model Type -------------------------------------------------------
        if tv and tv not in ty_o:
            if JUNK.match(tv):
                add(r, "Model Type", tv, "AUTO", "clear", "",
                    "not a real value")
            elif tv == "SUBMERSIBLE":
                ph = str(r.get("Phases") or "").strip()
                tgt = {"1": "1PH SUBMERSIBLE", "3": "3PH SUBMERSIBLE"}.get(ph)
                if tgt:
                    add(r, "Model Type", tv, "AUTO", "set", tgt,
                        "Phases=%s resolves 1PH vs 3PH deterministically" % ph)
                else:
                    add(r, "Model Type", tv, "REVIEW", "set", "1PH/3PH SUBMERSIBLE",
                        "Phases is %r so it cannot be resolved" % ph)
            elif tv in de_o:
                # a Model DESCRIPTION value sitting in Model Type
                if tv in dv:
                    add(r, "Model Type", tv, "AUTO", "clear", "",
                        "already present in Model Description; Model Type then needs a real type")
                else:
                    add(r, "Model Type", tv, "AUTO", "move to Model Description", tv,
                        "a Model Description option, not a Model Type; MultiChoice so nothing is lost")
            elif canon(tv) in ty_c:
                add(r, "Model Type", tv, "AUTO", "set", ty_c[canon(tv)],
                    "case/spacing variant of an existing option")
            else:
                add(r, "Model Type", tv, "REVIEW", "set",
                    SUGGEST[TY].get(tv, "?"), "no exact option; confirm the target once")

        # ---- Model Description (MultiChoice) ---------------------------------
        for v in dv:
            if v in de_o:
                continue
            if JUNK.match(v):
                add(r, "Model Description", v, "AUTO", "remove selection", "",
                    "not a real value")
            elif v == "NETWORK" and tv == "NETWORK":
                add(r, "Model Description", v, "AUTO", "remove selection", "",
                    "duplicates Model Type, which already reads NETWORK - nothing is lost")
            elif canon(v) in de_c:
                add(r, "Model Description", v, "AUTO", "set", de_c[canon(v)],
                    "case/spacing variant of an existing option")
            else:
                add(r, "Model Description", v, "REVIEW", "set",
                    SUGGEST[DE].get(v, "?"), "no exact option; confirm the target once")

        # ---- Oil Type ---------------------------------------------------------
        if ov and ov not in oi_o:
            if JUNK.match(ov):
                add(r, "Oil Type", ov, "AUTO", "clear", "", "not a real value")
            elif canon(ov) in oi_c:
                add(r, "Oil Type", ov, "AUTO", "set", oi_c[canon(ov)],
                    "case variant of an existing option")
            else:
                add(r, "Oil Type", ov, "REVIEW", "set", "?", "no exact option")

    stamp = "2026-09-08"
    outp = os.path.join(ROOT, "reports", "Model Revisions choice cleanup %s.csv" % stamp)
    with io.open(outp, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["row_id", "model_revision", "column", "current_value",
                                           "tier", "action", "proposed_value", "why"])
        w.writeheader()
        w.writerows(sorted(work, key=lambda x: (x["tier"], x["column"], x["current_value"])))

    print("wrote %s   (%d rows)" % (outp, len(work)))
    print("\n%-8s %s" % ("tier", "rows"))
    for t, n in Counter(x["tier"] for x in work).most_common():
        print("%-8s %d" % (t, n))
    print("\nby column and action:")
    for k, n in Counter("%s | %s | %s" % (x["column"], x["tier"], x["action"]) for x in work).most_common():
        print("   %-56s %d" % (k, n))
    print("\nREVIEW values needing one decision each (applies to every row carrying it):")
    seen = {}
    for x in work:
        if x["tier"] == "REVIEW":
            seen.setdefault((x["column"], x["current_value"], x["proposed_value"]), 0)
            seen[(x["column"], x["current_value"], x["proposed_value"])] += 1
    for (col, cur, prop), n in sorted(seen.items(), key=lambda kv: -kv[1]):
        print("   %-18s %-18s %3d rows  suggested: %s" % (col, cur, n, prop))
    print("\n%d distinct decisions cover all %d REVIEW rows." %
          (len(seen), sum(seen.values())))


if __name__ == "__main__":
    main()
