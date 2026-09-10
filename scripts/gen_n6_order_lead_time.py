# -*- coding: utf-8 -*-
"""Emit scripts/n6_order_lead_time.js from _n6_template.js.

    python scripts/gen_n6_order_lead_time.py

Only one value is substituted -- the generic fallback -- and it is read from
reports/frm13-leedtime.json rather than typed, for the same reason n5 is generated:
a lead time that is merely wrong produces a plausible date, not an error.
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
lt = json.load(io.open(os.path.join(ROOT, "reports", "frm13-leedtime.json"), encoding="utf-8"))
generic = next((int(float(r["lead_weeks"])) for r in lt
                if (r["client"] or "").strip() == "GENERIC VALUE"), None)
if generic is None:
    raise SystemExit("no GENERIC VALUE row -- refusing to guess a default")
js = io.open(os.path.join(HERE, "_n6_template.js"), encoding="utf-8").read()
js = js.replace("__GENERIC__", str(generic))
out = os.path.join(HERE, "n6_order_lead_time.js")
io.open(out, "w", encoding="utf-8", newline="\r\n").write(js)
print("wrote n6_order_lead_time.js  (generic %d weeks)" % generic)
