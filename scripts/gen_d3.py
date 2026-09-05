# -*- coding: utf-8 -*-
"""D3 -- the one-time BO Manager -> Order Items transfer, paste-ready.

Both sides read, not typed: TableBO's headers come from the workbook, the target
internal names from the Order Items export's ListSchema record.
"""
import openpyxl, io, re, collections
from openpyxl.utils import column_index_from_string as ci
from schema import schema_fields

WA = r"C:\Users\solei\OneDrive\Documents\Biplan\claude\Clients\Pioneer Transformer\Workflow-Automation"
LIST = WA + r"\sharepoint-lists\Order Items 2026-09-05 1432.csv"
BOWB = (r"C:\Users\solei\OneDrive\Documents\Biplan\claude\Clients\Pioneer Transformer"
        r"\FRM10-12\live-workbook-data\BO Manager_2026-09-03_23h48m.xlsx")
OUT = WA + r"\docs\a5-d3-bo-transfer-paste-sheet.md"

tgt = {}
for f in schema_fields(LIST):
    d = f["display"].replace("&amp;", "&")
    if d == "BO" or re.match(r"^BO[123] ", d):
        tgt[d] = (f["static"] or f["name"], f["type"], f["choices"], f["fillin"])

ws = openpyxl.load_workbook(BOWB, data_only=True)["Sheet1"]
rows = list(ws.iter_rows(min_row=5, max_row=1019, min_col=ci("B"), max_col=ci("X"), values_only=True))
hdr = [str(h).strip() if h is not None else "" for h in rows[0]]
data = rows[1:]
H = {h: i for i, h in enumerate(hdr)}

n = lambda v: "" if v is None else str(v).strip()
pop = {h: sum(1 for r in data if n(r[H[h]])) for h in hdr if h}
# the OK booleans are FALSE on nearly every row -- the trap from the 626 mistake
okcols = [h for h in hdr if h.endswith(" OK")]
okvals = {h: collections.Counter(n(r[H[h]]) for r in data) for h in okcols}
bo = collections.Counter(n(r[H["BO"]]) for r in data)

L = []; a = L.append
a("# A5 D3 — the one-time BO transfer, paste-ready")
a("")
a("Generated 2026-09-05 (`scripts/gen_d3.py`). **Both sides read, not typed:** `TableBO` headers")
a("from `BO Manager.xlsx`, target internal names from the Order Items export's `ListSchema` record.")
a("")
a("## The source")
a("")
a("`BO Manager.xlsx` → sheet **`Sheet1`**, table **`TableBO`**, ref **`B5:X1019`** — header on row 5,")
a("**%d data rows**, 23 columns. Live path: `General/FAB/Achat/BO`." % len(data))
a("")
a("**Join key is `Order`**, which matches `Order Items.Title` exactly, including the ` SA` suffix.")
a("")
a("## 🔴 This mapping is removed after the run")
a("")
a("The transfer flow is re-runnable. Left in place, every future run overwrites SharePoint-native BO")
a("edits with whatever the workbook held — so **D3 and R7 are a pair**: add it, run once, take it out.")
a("R7 already covers removing it alongside the five `Order` companion writes.")
a("")
a("And never source `BO` from `TableOrders`. FRM10-12's `BO` column is itself pulled from BO Manager,")
a("so it is a stale second-hand mirror — that is the 69-vs-76 gap.")
a("")
a("## Shape of the data")
a("")
a("| | |")
a("|---|---|")
a("| `BO` populated | **%d** of %d |" % (sum(v for k, v in bo.items() if k), len(data)))
a("| …values | %s |" % ", ".join("`%s` %d" % (k, v) for k, v in bo.most_common() if k))
for g in ("BO1", "BO2", "BO3"):
    a("| `%s Part Numbre` populated | %d |" % (g, pop.get(g + " Part Numbre", 0)))
a("")
a("⚠️ **Do not blind-map the `BO{n} OK` booleans.** Their distribution:")
a("")
a("| Column | Values |")
a("|---|---|")
for c in okcols:
    a("| `%s` | %s |" % (c, ", ".join("`%s` %d" % (k or "(blank)", v) for k, v in okvals[c].most_common(4))))
a("")
a("Mapping them unconditionally writes a value to **every** row and makes units look like they carry")
a("BO data. This is the same trap that produced a bogus \"626 expected\" figure earlier — counting")
a("Boolean `FALSE` cells as populated. **Only write a `BO{n} …` group where that group's")
a("`Part Numbre` is non-blank.**")
a("")
a("## Flow shape")
a("")
a("Add a second `List rows present in a table` **before** the `Apply to each`, pointed at `TableBO`.")
a("Inside the loop use a `Filter array` — the flow already uses that pattern, so no second nested")
a("loop and no extra connector calls per row:")
a("")
a("```")
a("Filter array   From:  body('List_rows_present_in_a_table_BO')?['value']")
a("               Where: item()?['Order']  is equal to  <the current RawOrder>")
a("```")
a("")
a("Then read the matched row with `first()`. Guard every field on the match existing —")
a("`first()` of an empty array is null, and a null fed to a Choice write fails the row.")
a("")
a("## Mappings")
a("")
a("| Order Items column | Internal name | Type | `TableBO` column |")
a("|---|---|---|---|")
missing = []
for d in ["BO"] + [g + " " + s for g in ("BO1", "BO2", "BO3")
                   for s in ("Part Numbre", "Description", "PO Intern", "Date",
                             "Fournisseur Interne", "OK")]:
    if d not in tgt:
        missing.append(d); continue
    s, t, ch, fi = tgt[d]
    src = "`%s`" % d if d in H else "**NOT IN TableBO**"
    a("| `%s` | `%s` | %s | %s |" % (d, s, t or "—", src))
a("")
if "BO" in tgt and tgt["BO"][2]:
    s, t, ch, fi = tgt["BO"]
    a("> **`BO` is a Choice** with options %s and **fill-in `%s`**. Anything outside that domain is"
      % (", ".join("`%s`" % c for c in ch), fi or "?"))
    a("> rejected — per row, silently, inside the loop. `TableBO`'s `List` sheet confirms the domain is")
    a("> exactly `BO`/`OK`, so it lines up today; it is worth re-checking if anyone edits the workbook.")
    a("")
a("## Expressions")
a("")
a("Take `Filter_BO` as the name of the Filter array. For the roll-up:")
a("")
a("```")
a("@if(empty(body('Filter_BO')), null, first(body('Filter_BO'))?['BO'])")
a("```")
a("")
a("For each detail field, guarded on that group's part number being present:")
a("")
a("```")
a("@if(or(empty(body('Filter_BO')),")
a("      equals(trim(string(coalesce(first(body('Filter_BO'))?['BO1 Part Numbre'], ''))), '')),")
a("   null, first(body('Filter_BO'))?['BO1 Description'])")
a("```")
a("")
a("Same shape for `BO2`/`BO3`, swapping the group prefix in both places. The source really is spelled")
a("**`Numbre`** — that is the workbook's spelling and the SharePoint column matches it, so it is not a")
a("typo to fix here.")
a("")
a("## Verify")
a("")
a("Afterwards, count `BO` populated on `Order Items`. Track B's earlier import covered **73**; the")
a("real source holds **%d**, so expect the gap to close rather than the number to stay put. Anything" % sum(v for k, v in bo.items() if k))
a("far above that means the roll-up was sourced from the wrong table.")
if missing:
    a("")
    a("⚠️ Not found on `Order Items`: %s" % ", ".join("`%s`" % m for m in missing))

io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("wrote a5-d3-bo-transfer-paste-sheet.md")
print("target columns resolved: %d/19  missing: %s" % (len(tgt), missing or "none"))
print("BO roll-up:", dict(bo))
for c in okcols:
    print("  %-26s %s" % (c, dict(okvals[c])))
