# -*- coding: utf-8 -*-
"""Emit scripts/x7_verify_parent_sync.js with the field map taken from the flows.

    python scripts/gen_x7_verifier.py

A browser-console script cannot import gen_n3_flows.py, so the field map has to be
inlined into the JS. Hand-copying it would be a second copy of the mapping -- the
exact drift this repo keeps getting caught by -- so it is generated instead. Re-run
this after any change to ORDER_MAP / MODELS_MAP / REV_MAP, or x7 will quietly verify
a mapping the flows no longer have.
"""
import io, json, os, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("g", os.path.join(HERE, "gen_n3_flows.py"))
G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
M = {"Order":           [list(t) for t in G.ORDER_MAP],
     "Models":          [list(t) for t in G.MODELS_MAP],
     "Model Revisions": [list(t) for t in G.REV_MAP]}

TPL = os.path.join(HERE, "_x7_template.js")
OUT = os.path.join(HERE, "x7_verify_parent_sync.js")
if not os.path.exists(TPL):
    raise SystemExit("missing template: %s\n"
                     "It is x7_verify_parent_sync.js with the MAP literal replaced by "
                     "the token __MAP__." % TPL)
js = io.open(TPL, encoding="utf-8").read()
js = js.replace("__MAP__", json.dumps(M, ensure_ascii=False, indent=2).replace("\n", "\n  "))
io.open(OUT, "w", encoding="utf-8", newline="\r\n").write(js)
print("wrote %s  (%d + %d + %d fields)"
      % (os.path.basename(OUT), len(M["Order"]), len(M["Models"]), len(M["Model Revisions"])))
