# -*- coding: utf-8 -*-
"""D1/D2 paste sheet. Both sides of every mapping are READ, never typed:
 - target internal names come from the Order Items export's ListSchema record
 - source keys come from a real Excel-connector payload in workflow-data/
"""
import csv, io, re, json

WA = r"C:\Users\solei\OneDrive\Documents\Biplan\claude\Clients\Pioneer Transformer\Workflow-Automation"
LIST = WA + r"\sharepoint-lists\Order Items 2026-09-05 1432.csv"
PAYLOAD = WA + r"\workflow-data\Excel Table list items raw output.json"
OUT = WA + r"\docs\a5-d1-d2-paste-sheet.md"

csv.field_size_limit(10 ** 7)

# ---- target side -------------------------------------------------------------
blob = ",".join(next(csv.reader(io.StringIO(
    io.open(LIST, encoding="utf-8-sig", newline="").read())))).split("=", 1)[1]
xmls = re.findall(r"<Field\b.*?(?:/>|</Field>)", blob, re.S)

def at(x, a):
    # Rejoining the CSV record leaves the FIRST attribute of each <Field>
    # mangled -- the reader unescapes doubled quotes, so it reads
    #   Type=\Text\"        instead of   Type=\"Text\"
    # Tolerate a missing opening quote rather than assuming a clean form.
    m = re.search(a + r'=\\*"?([^\\"]*)\\*"', x)
    return m.group(1) if m else ""

TARGET = {}
for x in xmls:
    d = at(x, "DisplayName").replace("&amp;", "&")
    if d:
        TARGET[d] = (at(x, "StaticName") or at(x, "Name"), at(x, "Type"))

# ---- source side -------------------------------------------------------------
pj = json.load(io.open(PAYLOAD, encoding="utf-8"))
rows = pj.get("value") or pj.get("body", {}).get("value") or pj
SRC = set(rows[0].keys())

# ---- the mappings ------------------------------------------------------------
# (display name on Order Items, Excel key, expression template)
MAPS = [
    ("Info+", "Info+", "@item()?[{k}]"),
    ("Technical Notes", "Technical Notes", "@item()?[{k}]"),
    ("Protector & Switchgear Item #", "Protector & Switchgear Item _x0023_", "@item()?[{k}]"),
    ("Configuration", "Configuration",
     "@if(or(equals(trim(string(item()?[{k}])), ''), equals(trim(string(item()?[{k}])), '00:00:00')), null, item()?[{k}])"),
    ("Section Qty", "Section Qty",
     "@if(equals(trim(string(item()?[{k}])), ''), null, int(item()?[{k}]))"),
]

L = []
w = L.append
w("# A5 D1 / D2 — the six mappings, paste-ready")
w("")
w("Generated 2026-09-05. **Every name on both sides was read, not typed:**")
w("")
w("- **Target** internal names come from the `ListSchema` record at the top of")
w("  `sharepoint-lists/Order Items 2026-09-05 1432.csv`.")
w("- **Source** keys come from a real Excel-connector payload,")
w("  `workflow-data/Excel Table list items raw output.json` (256 rows, 85 columns).")
w("")
w("This matters more than it sounds. See the warning under `Protector & Switchgear Item #`.")
w("")
w("Add each to **both** `CreateOrderItem` and `UpdateOrderItem`.")
w("")
w("## The mappings")
w("")
w("| Order Items column | Internal name (target) | Type | Excel key (source) |")
w("|---|---|---|---|")
missing = []
for disp, key, _tpl in MAPS:
    tn, tt = TARGET.get(disp, ("**NOT FOUND**", "?"))
    ok = "`%s`" % key if key in SRC else "**NOT IN PAYLOAD** (`%s`)" % key
    if key not in SRC or tn.startswith("**"):
        missing.append(disp)
    w("| `%s` | `%s` | %s | %s |" % (disp, tn, tt or "—", ok))
w("| `Order_Number_TextField` | `%s` | %s | *(from the existing `OrderNumberText` Compose, not Excel)* |"
  % (TARGET.get("Order_Number_TextField", ("?", ""))[0], TARGET.get("Order_Number_TextField", ("", "Text"))[1] or "Text"))
w("")

tn_prot = TARGET.get("Protector & Switchgear Item #", ("?", ""))[0]
w("> 🔴 **`Protector & Switchgear Item #` is the one that will bite.** Its internal name is")
w("> `` %s `` — SharePoint escaped it and then **truncated at 32 characters**, so it" % tn_prot)
w("> stops mid-word and looks nothing like the display name. Type it out or guess the escape and")
w("> the mapping writes **nothing, silently** — exactly how `Planned_x0020_Delivery_x0020_Dat`")
w("> failed once already. And because this column is expected to land **0 populated** (it is blank")
w("> at source), a silent failure here would never show up in verification. **Verify the mapping")
w("> exists by reading the write action's raw inputs in run history, never by counting values.**")
w("")

w("## Expressions")
w("")
for disp, key, tpl in MAPS:
    tn, _ = TARGET.get(disp, ("?", ""))
    w("### `%s`  →  `%s`" % (disp, tn))
    w("")
    w("```")
    w(tpl.replace("{k}", "'%s'" % key))
    w("```")
    w("")

w("### `Order_Number_TextField`")
w("")
w("```")
w("@outputs('OrderNumberText')")
w("```")
w("")
w("One mapping, no extra connector calls — and with the TextField sync flows off, this is what")
w("keeps Order Number populated on every backfilled row.")
w("")
w("## Two guards that are load-bearing")
w("")
w("- **`Configuration`'s `00:00:00` test.** Nine rows hold an Excel *time* value rather than text.")
w("  Without the guard those write `00:00:00` into a Text column. The column is `Text`, not Choice,")
w("  so there is no rejection to warn you.")
w("- **`Section Qty`'s blank test.** An empty string fed to `int()` throws, and that throw surfaces")
w("  as `Action 'Switch' failed` — indistinguishable at a glance from the A5c bug.")
w("")
w("## Do NOT map")
w("")
w("- **`BO`** (internal `%s`, %s). It is SharePoint-native now. It comes from `TableBO` in"
  % (TARGET.get("BO", ("BO", ""))[0], TARGET.get("BO", ("", "Choice"))[1] or "Choice"))
w("  BO Manager as a **one-time** transfer (D3), and the mapping is **removed after that run**.")
w("  Sourcing it from `TableOrders` would null the 73 imported rows.")
w("- **`Bo Sort Date`** — unrelated to `BO`, and mapping it was a documented mistake.")
w("- Anything that touches a **List Name dropdown**. Re-selecting one has wiped every mapping on")
w("  both write actions before.")
w("")
w("## Verify")
w("")
w("Expected populated counts after the run — from the source workbook, not guesses:")
w("")
w("| Column | Expect |")
w("|---|---|")
w("| `Info+` | ~96 |")
w("| `Technical Notes` | ~6 |")
w("| `Configuration` | ~491 |")
w("| `Section Qty` | ~112 |")
w("| `Protector & Switchgear Item #` | **0 — verify the mapping exists, never by count** |")
w("| `BO` | **still 73, unchanged** |")

io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("wrote a5-d1-d2-paste-sheet.md")
if missing:
    print("!! unresolved:", missing)
else:
    print("all 5 mappings resolved on both sides")
