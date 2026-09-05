# -*- coding: utf-8 -*-
"""Generate the 24 toLower() replacements by transforming the CURRENT expression
text from the exported definition. Nothing is retyped, so a transcription slip
cannot silently write nothing -- the failure mode that cost us Planned Delivery
Date once already."""
import json, io, os, re

SRC = (r"C:\Users\solei\AppData\Local\Temp\claude\C--Users-solei-OneDrive-Documents-Biplan-claude"
       r"\e9121471-9854-4057-96e4-65e90b55cbe5\scratchpad\flowzip"
       r"\Microsoft.Flow\flows\0afd5532-7a23-4da8-ba1c-4441116a9b72\definition.json")
OUT = (r"C:\Users\solei\OneDrive\Documents\Biplan\claude\Clients\Pioneer Transformer"
       r"\Workflow-Automation\docs\a5c-tolower-paste-sheet.md")

d = json.load(io.open(SRC, encoding="utf-8"))

def find(o, name, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == name: yield path, v
            yield from find(v, name, path + "/" + k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from find(v, name, path + "/%d" % i)

sets = {}
for p, v in find(d, "parameters"):
    if isinstance(v, dict) and any(k.startswith("item/") for k in v):
        owner = p.split("/actions/")[-1].split("/")[0] if "/actions/" in p else p[-30:]
        sets[owner] = v

# equals(trim(X), 'EC')  ->  equals(toLower(trim(X)), 'ec')
PAT = re.compile(r"equals\((trim\((?:[^()]|\([^()]*\))*\)),\s*'EC'\)")
def fix(expr):
    return PAT.sub(lambda m: "equals(toLower(%s), 'ec')" % m.group(1), expr)

lines = []
w = lines.append
w("# A5c — the 24 `toLower()` replacements, paste-ready")
w("")
w("Generated 2026-09-05 from `workflow-data/Order Items Excel Transfer Flow 2026-09-05 1900")
w("definition.json` by transforming the live expression text. **Nothing here was retyped** — the")
w("\"after\" is the \"before\" with `equals(trim(X), 'EC')` rewritten to")
w("`equals(toLower(trim(X)), 'ec')`, so a transcription slip cannot silently write nothing.")
w("")
w("**Why this matters:** the guard is case-sensitive and three rows hold lowercase `ec`, which")
w("falls through to `int('ec')` and throws. That surfaces as `Action 'Switch' failed` — the")
w("iteration-497 failure. See `transfer-flow-forensics-2026-09-04.md` §9.1.")
w("")
w("Do **both** actions. Skipping one leaves half the rows failing.")
w("")

total = 0
for act in ("CreateOrderItem", "UpdateOrderItem"):
    v = sets[act]
    keys = sorted(k for k in v if isinstance(v[k], str) and "'EC'" in v[k])
    w("## `%s` — %d fields" % (act, len(keys)))
    w("")
    for k in keys:
        before = v[k]
        after = fix(before)
        assert after != before, k
        assert "'EC'" not in after, k
        total += 1
        w("### `%s`" % k)
        w("")
        w("```")
        w(after)
        w("```")
        w("")
    w("")

w("---")
w("")
w("**%d expressions total.** After pasting, re-export the flow and confirm:" % total)
w("")
w("```")
w("grep -c \"toLower(\"  definition.json   # expect 28  (24 new + 4 already on Tanking/Delivery)")
w("grep -c \"'EC'\"      definition.json   # expect 0")
w("```")
w("")
w("The 4 pre-existing `toLower()` calls are on `Tanking` and `Delivery`, which are deliberately")
w("not mapped (A5b) — leave them alone.")

io.open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("wrote %d expressions -> %s" % (total, os.path.basename(OUT)))
print()
print("sample:")
print(fix(sets["UpdateOrderItem"]["item/CoilingDate"]))
print(fix(sets["UpdateOrderItem"]["item/CoilingStatus/Value"]))
