# -*- coding: utf-8 -*-
"""Generate scripts/n5_clients_lead_time.js with the FRM13 lead times inlined.

    python scripts/gen_n5_lead_times.py

Reads reports/frm13-leedtime.json (extracted from FRM13's `LeedTime` table, sheet
`DelaisApproParClients`, A6:H24) and writes the console script that creates the
Clients columns and seeds them.

Generated rather than hand-typed for the usual reason: 17 clients x 6 fields is
102 values, and a mistyped lead time is invisible -- it produces a date that is
merely wrong, not one that fails.

The two aliases are the only judgement in here, and both were resolved against the
Order list rather than guessed:
    CITY OF RED DEER -> RED DEER      (REDE)   1 order
    HYDRO OTTAWA     -> OTTAWA HYDRO  (OTHY)   15 orders
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "reports", "frm13-leedtime.json")
TPL = os.path.join(HERE, "_n5_template.js")
OUT = os.path.join(HERE, "n5_clients_lead_time.js")

ALIAS = {"CITY OF RED DEER": "RED DEER", "HYDRO OTTAWA": "OTTAWA HYDRO"}


def main():
    lt = json.load(io.open(SRC, encoding="utf-8"))
    rows, generic = [], None
    for r in lt:
        if (r["client"] or "").strip() == "GENERIC VALUE":
            generic = int(float(r["lead_weeks"]))
            continue
        name = (r["client"] or "").replace("&amp;", "&")
        rows.append({"frm13": name,
                     "client": ALIAS.get(name, name),
                     "weeks": int(float(r["lead_weeks"])),
                     "delai": r.get("delai"),
                     "p1": r.get("critical1"), "s1": r.get("supplier1"),
                     "p2": r.get("critical2"), "s2": r.get("supplier2")})
    if generic is None:
        raise SystemExit("no GENERIC VALUE row in %s -- refusing to guess a default" % SRC)

    if not os.path.exists(TPL):
        raise SystemExit("missing template %s" % TPL)
    js = io.open(TPL, encoding="utf-8").read()
    js = js.replace("__DATA__", json.dumps(rows, ensure_ascii=False, indent=2).replace("\n", "\n  "))
    js = js.replace("__GENERIC__", str(generic))
    io.open(OUT, "w", encoding="utf-8", newline="\r\n").write(js)
    print("wrote %s  (%d clients, generic %d weeks)"
          % (os.path.basename(OUT), len(rows), generic))
    aliased = [r for r in rows if r["frm13"] != r["client"]]
    for a in aliased:
        print("   alias: %-20s -> %s" % (a["frm13"], a["client"]))


if __name__ == "__main__":
    main()
