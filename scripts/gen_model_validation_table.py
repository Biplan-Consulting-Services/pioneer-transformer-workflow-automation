# -*- coding: utf-8 -*-
"""Build the sheet the SHOP validates: every Model Revision whose Type or Description
cannot be resolved from data, with enough context to recognise the transformer.

User's instruction, 2026-09-08: "some thing that can be done about those questions is to
build a table that i can pass to the users to validate the real values."

So this replaces me guessing. Each row states what is there now, what the candidates are,
and leaves blank columns for the shop to fill. Nothing is proposed as an answer.

WHY THE ARCHIVE PASS CANNOT FILL THE BLANK PHASES
-------------------------------------------------
The user also asked for a pass over the archive, matching `PO Item #` (the client model
code) to fill the empty `Phases` values -- empty only, never overwriting. Done, and the
answer is that it fills **nothing**. The reason matters more than the result:

  * Where Phases IS already populated, the archive agrees on **277 of 277** rows -- zero
    disagreements, zero conflicts.
  * Where Phases is blank (94 rows), it fills **0**.

That combination is not a join bug. It says the archive is a **mirror of the same datum,
not an independent source**: an archive order row inherits Phases from its model revision,
so when the revision is blank every one of its order rows is blank too. Measured
directly -- the 23 blank-phase revisions that DO have a matching `PO Item #` have Phases
blank on **all 81** of their archive rows, and 0 of the 23 have any archive row carrying
1 or 3. The remaining 71 were never ordered at all, appearing in neither the archive nor
the live workbook, which is also why they have no phase: nothing was ever built.

So 100% agreement was never corroboration -- it was copying. The archive cannot answer
this question, which is exactly why the shop has to.

Reads the newest export plus the archive (for identifying context only). Writes one CSV.
No network calls; touches no SharePoint list.
"""
import io, os, re, csv, glob, json, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lib  # noqa: E402
from gen_choice_cleanup_worklist import (MODEL_TYPES, DESCRIPTIONS, canon, multi,
                                         schema, GOOD_PHASES)  # noqa: E402

TYPE_OK, DESC_OK = set(MODEL_TYPES), set(DESCRIPTIONS)


def main():
    path, sch = schema("Model Revisions")
    rows = lib.load(path)
    TD = sch["Model_x0020_Type"]["disp"]
    DD = sch["Description"]["disp"]
    CMC = sch["ModelName"]["disp"]          # Client_Model_Code
    MRID = sch["ModelID"]["disp"]           # Model_Revion_ID
    # Pioneer Model Code's internal name is `Model` -- and it is a LOOKUP, so it is absent
    # from a CSV export entirely (values AND schema; see CLAUDE.md). Fall back to whatever
    # identifying column the export does carry rather than failing.
    PMC = next((sch[k]["disp"] for k in ("Model", "Title") if k in sch), None)
    if PMC is None or PMC not in (rows[0] if rows else {}):
        PMC = next((c for c in ("Pioneer Model Code", "Title") if rows and c in rows[0]), None)

    # --- archive context, for RECOGNISING the unit (never as an answer)
    wb = sorted(glob.glob(os.path.join(ROOT, "workbooks", "Archive active *.xlsx")))[-1]
    _, arch = lib.xl_table(wb, "TableArchiveFRM10_12")
    nrm = lambda s: re.sub(r'\s+', '', str(s or '').strip().upper())
    by_item = defaultdict(list)
    for a in arch:
        k = nrm(a.get("PO Item #"))
        if k:
            by_item[k].append(a)

    # --- The sheet is EXACTLY the worklist's KEEP tier, nothing more.
    # Not every non-canonical value: 339 of the 374 proposals are resolvable from data
    # (Phases confirms them, or the value belongs in the other column), and putting those
    # in front of the shop would bury the 35 that actually need a person in 300 that do
    # not. The dependency is deliberate -- run gen_choice_cleanup_worklist.py first.
    wl = os.path.join(ROOT, "reports", "Model Revisions choice cleanup 2026-09-08.csv")
    if not os.path.exists(wl):
        raise SystemExit("run scripts/gen_choice_cleanup_worklist.py first -- %s is missing" % wl)
    keep = defaultdict(list)
    with io.open(wl, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["tier"] == "KEEP":
                keep[str(row["row_id"])].append(row)
    print("worklist KEEP rows: %d, across %d model revisions\n"
          % (sum(len(v) for v in keep.values()), len(keep)))

    out = []
    for r in rows:
        rid = str(r.get("Id") or r.get("ID") or "")
        items = keep.get(rid)
        if not items:
            continue
        tv = str(r.get(TD) or "").strip()
        dv = multi(r.get(DD))
        phases = str(r.get("Phases") or "").strip()
        bad_type = [i for i in items if i["column"] == "Model Type"]
        bad_desc = [i["current_value"] for i in items if i["column"] == "Model Description"]
        unconfirmed = phases not in GOOD_PHASES

        ctx = by_item.get(nrm(r.get(CMC)), [])
        orders = sorted({str(a.get("Order") or "").strip() for a in ctx if a.get("Order")})
        kva = sorted({str(a.get("KVA and KV") or "").strip() for a in ctx if a.get("KVA and KV")})
        clients = sorted({str(a.get("Client") or "").strip() for a in ctx if a.get("Client")})

        needs = [i["why"] for i in items]
        if unconfirmed:
            needs.append("Phases is %s, so 1PH/3PH cannot be confirmed from data either"
                         % (phases or "blank"))

        out.append({
            "model_revision_id": r.get(MRID) or "",
            "pioneer_model_code": (r.get(PMC) or "") if PMC else "",
            "client_model_code": r.get(CMC) or "",
            "client_from_archive": "; ".join(clients[:3]),
            "orders_from_archive": "; ".join(orders[:6]) or "(never ordered)",
            "kVA_from_archive": "; ".join(kva[:3]),
            "phases_now": phases or "(blank)",
            "model_type_now": tv or "(blank)",
            "description_now": "; ".join(dv),
            "what_needs_confirming": "; ".join(needs),
            "CONFIRM_model_type": "",          # <- the shop fills these three
            "CONFIRM_descriptions": "",
            "CONFIRM_phases": "",
            "shop_notes": "",
            "valid_model_types": " | ".join(MODEL_TYPES),
            "valid_descriptions": " | ".join(DESCRIPTIONS),
        })

    outp = os.path.join(ROOT, "reports", "Model validation for shop 2026-09-08.csv")
    with io.open(outp, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(sorted(out, key=lambda x: (x["model_type_now"], x["client_model_code"])))

    print("wrote %s\n   %d model revisions for the shop to validate\n" % (outp, len(out)))
    from collections import Counter
    print("why each row is in the sheet:")
    for k, n in Counter(x["what_needs_confirming"] for x in out).most_common(14):
        print("   %-74s %d" % (k[:74], n))
    print("\ncontext coverage (does the shop have something to recognise it by?):")
    print("   with archive orders listed : %d" % sum(1 for x in out if x["orders_from_archive"] != "(never ordered)"))
    print("   never ordered              : %d" % sum(1 for x in out if x["orders_from_archive"] == "(never ordered)"))
    print("   with a kVA figure          : %d" % sum(1 for x in out if x["kVA_from_archive"]))


if __name__ == "__main__":
    main()
