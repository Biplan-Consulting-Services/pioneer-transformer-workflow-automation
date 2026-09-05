# -*- coding: utf-8 -*-
"""Two finite lists out of the Models/Model Revisions duplication:
  BACKFILL -- Models has a value, the revision is blank
  REVIEW   -- both have values and they genuinely differ

Most raw "disagreements" are formatting, not data, so they are classified rather
than dumped. Crucially the normalisation is PER COLUMN: turning ',' into '.' is
correct for Form ('7,875x13,25' is a dimension pair) and wrong for Oil Amount
('1,220' is far more likely a thousands separator). Applying one rule everywhere
would manufacture false matches, so numeric columns keep the comma and get
flagged AMBIGUOUS instead.

Join: Model Revisions.Pioneer_Model_Code_TextField -> Models.Model_ID.
"""
import csv, io, os, re, json, collections
from load_exports import load

WA = r"C:\Users\solei\OneDrive\Documents\Biplan\claude\Clients\Pioneer Transformer\Workflow-Automation"
OUT_CSV = WA + r"\sharepoint-lists\Models dedup worklist 2026-09-05.csv"
OUT_MD = WA + r"\docs\models-dedup-worklist.md"

n = lambda v: (v or "").strip()
mo = load("Models 2026-09-05 1427.csv")
mr = load("Model Revisions 2026-09-05 1428.csv")
mby = {n(m["Model_ID"]): m for m in mo}

TEXT, DIM, NUM = "text", "dim", "num"
PAIRS = [("Cable", "Cable", TEXT), ("Copper (LV)", "Copper (LV)", TEXT),
         ("Core Type", "Core Type", TEXT), ("Form", "Form", DIM),
         ("JS %23", "JS %23", NUM), ("Model Type", "Model Type", TEXT),
         ("Oil Amount", "Oil Amount", NUM), ("Oil Type", "Oil Type", TEXT),
         ("Overcoil", "Overcoil", NUM), ("Phases", "Phases", NUM),
         ("Spec_ID", "Spec_ID", TEXT), ("Wire (HV)", "Wire (HV)", TEXT),
         ("kVA and kV", "kVA", NUM), ("Description", "Model Description", TEXT)]

def unwrap(s):
    """Model Revisions multi-choice columns export as a JSON array."""
    if s.startswith("[") and s.endswith("]"):
        try:
            return ", ".join(str(x) for x in json.loads(s))
        except Exception:
            pass
    return s

def norm(s, kind):
    s = unwrap(n(s))
    s = re.sub(r"\s+", "", s).upper()
    if kind == DIM:
        s = s.replace(",", ".")          # safe: these are dimension pairs
    if kind == NUM:
        s = s.lstrip("0") or "0"         # 05 vs 5
    return s

def ambiguous(a, b):
    """Same digits, differing only by ',' / '.' -- cannot tell decimal from
    thousands without knowing the column's locale, so do not guess."""
    ca, cb = n(a).replace(" ", ""), n(b).replace(" ", "")
    return ca != cb and ca.replace(",", ".") == cb.replace(",", ".")

rows = []
stats = collections.defaultdict(lambda: collections.Counter())
orphans = 0
for rev in mr:
    key = n(rev.get("Pioneer_Model_Code_TextField")) or n(rev.get("Pioneer Model Code"))
    m = mby.get(key)
    if not m:
        orphans += 1
        continue
    for mc, rc, kind in PAIRS:
        a, b = n(m.get(mc)), n(rev.get(rc))
        label = "%s -> %s" % (mc, rc) if mc != rc else mc
        rid = n(rev.get("Model_Revion_ID"))
        if a and not b:
            stats[label]["backfill"] += 1
            rows.append(["BACKFILL", label, key, rid, a, "", unwrap(a)])
        elif a and b and a != b:
            if norm(a, kind) == norm(b, kind):
                stats[label]["formatting"] += 1
            elif kind == NUM and ambiguous(a, b):
                stats[label]["ambiguous"] += 1
                rows.append(["AMBIGUOUS", label, key, rid, a, b, ""])
            else:
                stats[label]["review"] += 1
                rows.append(["REVIEW", label, key, rid, a, b, ""])
        elif a and b:
            stats[label]["agree"] += 1
        else:
            stats[label]["neither"] += 1

order = {"BACKFILL": 0, "REVIEW": 1, "AMBIGUOUS": 2}
with io.open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Action", "Column", "Model_ID", "Model_Revion_ID",
                "Models value", "Model Revisions value", "Proposed write"])
    w.writerows(sorted(rows, key=lambda r: (order[r[0]], r[1], r[2])))

cnt = collections.Counter(r[0] for r in rows)
fmt = sum(s["formatting"] for s in stats.values())

L = []; w = L.append
w("# `Models` / `Model Revisions` dedup — the worklists")
w("")
w("Generated 2026-09-05 from the exports (`scripts/gen_dedup.py`, re-runnable). Roadmap item 23")
w("says remove the 14 spec columns duplicated on `Models` because the revision is authoritative.")
w("This turns that into finite lists rather than a research task.")
w("")
w("Full rows: **`sharepoint-lists/Models dedup worklist 2026-09-05.csv`** — sort by `Action`.")
w("")
w("| Action | Rows | Meaning |")
w("|---|---|---|")
w("| **BACKFILL** | **%d** | `Models` has a value, the revision is blank. Safe to write. |" % cnt["BACKFILL"])
w("| **REVIEW** | **%d** | Both populated and genuinely different. Needs a human. |" % cnt["REVIEW"])
w("| **AMBIGUOUS** | **%d** | Same digits, `,` vs `.` — cannot tell decimal from thousands. |" % cnt["AMBIGUOUS"])
w("| *(formatting)* | *%d* | Same value, different serialisation. **Not listed** — nothing to do. |" % fmt)
w("")
w("## Most \"disagreements\" were formatting, not data")
w("")
w("A naive comparison reports **%d** conflicts. **%d of those are cosmetic**, from two causes:" % (fmt + cnt["REVIEW"] + cnt["AMBIGUOUS"], fmt))
w("")
w("- **Multi-choice columns export as a JSON array.** `Models.Description` holds `SUBWAY`;")
w("  `Model Revisions.Model Description` holds `[\"SUBWAY\"]`. Same value.")
w("- **French vs English decimal separators, plus stray spaces.** `Models.Form` holds")
w("  `7,875x13,25` where the revision holds `7.875x13.25`; also `9x12.5` vs `9x 12.5`.")
w("")
w("⚠️ **Two corrections to earlier notes in this repo, both from over-reading raw counts:**")
w("")
w("- `Description` vs `Model Description` was called *\"probably not the same field at all\"* on the")
w("  strength of **zero agreements in 295 comparisons**. They *are* the same field — the zero was")
w("  the JSON wrapper. Only **%d** genuinely differ." % stats["Description -> Model Description"]["review"])
w("- `Form` was called the one *\"where a wrong call silently attaches the wrong physical spec, so")
w("  it deserves the closest look\"* on 102 disagreements. **%d** survive normalisation." % stats["Form"]["review"])
w("")
w("## Per column")
w("")
w("| Column | Backfill | Review | Ambiguous | Formatting only | Agree |")
w("|---|---|---|---|---|---|")
for mc, rc, _k in PAIRS:
    label = "%s -> %s" % (mc, rc) if mc != rc else mc
    s = stats[label]
    d = lambda v: ("**%d**" % v) if v else "—"
    w("| `%s` | %s | %s | %s | %s | %d |" % (label.replace("%23", "#"),
      d(s["backfill"]), d(s["review"]), d(s["ambiguous"]), d(s["formatting"]), s["agree"]))
w("")
w("## What the real conflicts look like")
w("")
w("Two distinct shapes, and only one needs judgement:")
w("")
w("- **`Models` holding a placeholder where the revision has real data** — `Core Type` `None` vs")
w("  `Amorphe`, `Oil Type` `None` vs `Midel`, `Phases` `0` vs `3`, `Oil Amount` `0` vs a real")
w("  figure. These support \"the revision wins\" rather than contradicting it, and can be cleared in")
w("  bulk once someone confirms `None`/`0` are placeholders rather than meaningful.")
w("- **Genuine differences** — `Model Type` `ZIG-ZAG` vs `MALT`, `kVA` `1,500` vs `7,500`,")
w("  `Copper (LV)` `114*228` vs `152*430`. These need a person. They are the minority.")
w("")
w("## How to run the backfill")
w("")
w("**Write only where the revision's value is blank.** `Model Revisions` has been the source of")
w("truth for weeks, so a populated cell is a deliberate edit and must survive — that is why this is")
w("split into lists rather than run as one sync. `Proposed write` carries the value (JSON wrapper")
w("already stripped) and is deliberately empty on REVIEW and AMBIGUOUS rows.")
w("")
w("Join is `Model Revisions.Pioneer_Model_Code_TextField` → `Models.Model_ID`, effectively 1:1 —")
w("385 of 391 revisions map cleanly, one model carries 6, and **%d revisions have no model key**" % orphans)
w("at all. Those %d are excluded from every list above and deserve their own look." % orphans)
w("")
w("Nothing gets **deleted** from `Models` until the lists are clear *and* FRM10-12's `.pq` queries")
w("have been grepped for each column name — Power Query binds by name and breaks silently.")

io.open(OUT_MD, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("BACKFILL %d | REVIEW %d | AMBIGUOUS %d | formatting-only %d | orphan revisions %d"
      % (cnt["BACKFILL"], cnt["REVIEW"], cnt["AMBIGUOUS"], fmt, orphans))
for mc, rc, _k in PAIRS:
    label = "%s -> %s" % (mc, rc) if mc != rc else mc
    s = stats[label]
    if s["backfill"] or s["review"] or s["ambiguous"]:
        print("   %-32s bf %-4d rev %-4d amb %-4d fmt %d"
              % (label, s["backfill"], s["review"], s["ambiguous"], s["formatting"]))
