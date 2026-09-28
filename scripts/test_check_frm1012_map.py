#!/usr/bin/env python3
"""check_frm1012_map.py must FAIL on each unsafe mutation of the FRM10-12 archive map.

    python scripts/test_check_frm1012_map.py
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_frm1012_map as C  # noqa: E402

fails = []


def row(d, target):
    return next(r for r in d["map"] if r["TargetColumn"] == target)


def expect_abort(name, mutate, base=False):
    d = copy.deepcopy(BASE)
    mutate(d)
    try:
        C.checks(d)
        if base:
            C.check_base(d["map"], BASEVALS)
    except SystemExit as e:
        print("  ok   %-52s -> %s" % (name, str(e).replace("\n", " ")[18:108]))
        return
    fails.append(name)
    print("  FAIL %-52s -> passed the checks" % name)


BASE = C.load_all()
C.checks(BASE)
BASEVALS = C.base_values(C.DEFAULT_BASE) if os.path.exists(C.DEFAULT_BASE) else None
if BASEVALS:
    C.check_base(BASE["map"], BASEVALS)
print("unmutated map passes (%d rows, %d joins); base values %s" % (
    len(BASE["map"]), len(BASE["joins"]), "checked" if BASEVALS else "SKIPPED (no base workbook)"))


def swap(d, a, b):
    m = d["map"]
    i, j = m.index(row(d, a)), m.index(row(d, b))
    m[i], m[j] = m[j], m[i]
    m[i]["Position"], m[j]["Position"] = m[j]["Position"], m[i]["Position"]


def drop(d, target):
    d["map"].remove(row(d, target))
    for p, r in enumerate(d["map"], 1):
        r["Position"] = p


print("each unsafe mutation must abort:")
# source rule
expect_abort("Order Items sync copy as source (OrdPO)", lambda d: row(d, "PO").update(SourceList="Order Items", SourceField="OrdPO"))
expect_abort("Order Items sync copy as source (RevkVA)", lambda d: row(d, "KVA and KV").update(SourceList="Order Items", SourceField="RevkVA"))
expect_abort("Order Items copy CliLeadTimeWeeks for Lead Time", lambda d: row(d, "Lead Time").update(SourceList="Order Items"))
expect_abort("_TextField mirror as source", lambda d: row(d, "Order").update(SourceField="Order_Number_TextField"))
expect_abort("copy column hidden in a computed ref", lambda d: row(d, "Ing. Due Date").update(
    Arg="Order Items.TankingDate;Order Items.OrdInitialPromisedDate;Lead Time"))
expect_abort("field that does not exist on the list", lambda d: row(d, "Coiling Date").update(SourceField="CoilingEndDate"))
expect_abort("display name instead of internal name", lambda d: row(d, "Tanking date change justification").update(SourceField="Planning Notes"))
expect_abort("join key that is not a lookup into its parent", lambda d: d["joins"][0].update(ChildKey="ModelRevisionId"))
expect_abort("join onto a copy column", lambda d: d["joins"][2].update(Child="Order Items", ChildKey="CliLeadTimeWeeks"))
# pinned shape
expect_abort("missing pinned column (Delivery Date)", lambda d: drop(d, "Delivery Date"))
expect_abort("missing BO detail column", lambda d: drop(d, "BO3 OK"))
expect_abort("reordered columns (Tanking/Testing Date)", lambda d: swap(d, "Tanking Date", "Testing Date"))
expect_abort("renamed column", lambda d: row(d, "BO1 Part Numbre").update(TargetColumn="BO1 Part Number"))
expect_abort("extra column", lambda d: d["map"].append(dict(row(d, "BO3 OK"), TargetColumn="Extra", Position=112)))
# viewer agreement
expect_abort("marker letter drifted from ValueConversions", lambda d: row(d, "Tank").update(Arg="x"))
expect_abort("conversion dropped (Location copied raw)", lambda d: row(d, "Location").update(Rule="copy"))
expect_abort("viewer-basis row re-sourced (Delivery End Date)", lambda d: row(d, "Delivery Date").update(SourceField="DeliveryDate"))
# vocabulary copies
expect_abort("drifted LocationCodes copy", lambda d: d["vocabs"].update(LocationCodes=(
    d["vocabs"]["LocationCodes"][0].replace('Code = "XT"', 'Code = "EX"'), d["vocabs"]["LocationCodes"][1])))
expect_abort("drifted StatusStampCodes copy", lambda d: d["vocabs"].update(StatusStampCodes=(
    d["vocabs"]["StatusStampCodes"][0].replace('Code = "TE"', 'Code = "TR"'), d["vocabs"]["StatusStampCodes"][1])))
# rules
expect_abort("BO column without the backfill rule", lambda d: row(d, "BO2 Date").update(Rule="copy"))
expect_abort("unknown rule", lambda d: row(d, "Qty").update(Rule="int"))
# types vs the archived history
if BASEVALS:
    expect_abort("Tanking Date typed date ('ANed' history)", lambda d: row(d, "Tanking Date").update(Type="date"), base=True)
    expect_abort("KVA typed number ('24.9 kV' history)", lambda d: row(d, "KVA and KV").update(Type="number"), base=True)
    expect_abort("CSA typed logical ('x' history)", lambda d: row(d, "CSA").update(Type="logical"), base=True)

# the parser must refuse a record it cannot read, not skip it
try:
    C.parse_map('        [Position = 1, TargetColumn = "Order", SourceList = "Order Items", Rule = "copy"],\n')
    fails.append("parser skipped an unparseable record")
    print("  FAIL parser skipped an unparseable record")
except SystemExit:
    print("  ok   %-52s" % "parser refuses an unparseable record")

print("\n%s" % ("ALL PASS" if not fails else "%d FAILED: %s" % (len(fails), fails)))
sys.exit(1 if fails else 0)
