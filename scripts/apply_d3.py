# -*- coding: utf-8 -*-
"""Apply D3 -- the one-time BO Manager transfer -- to a flow definition.

Structurally bigger than D1/D2: it adds two actions and 19 mappings per write
action, so this asserts the shape it produced, not just the key count.

    python apply_d3.py <definition.json> -o <out.json>

WHAT IT ADDS
  1. `List_rows_present_in_a_table_BO`  -- a second Excel source, spliced into the
     existing top-level chain between the FRM10-12 list and Filter_array.
  2. `Filter_BO` inside the loop -- matches the BO row for the current unit, so
     there is no second nested loop and no extra connector call per row.
  3. 19 mappings on BOTH write actions, every one guarded.

🔴 REMOVE THIS AFTER ONE RUN. The transfer flow is re-runnable; left in place it
overwrites SharePoint-native BO edits with whatever the workbook held on every
future run. D3 and R7 are a pair.
"""
import json, io, sys, os, copy, argparse

# ---------------------------------------------------------------- the source
# Resolved live 2026-09-07, never typed:
#   drive  = the same document library as FRM10-12 (decoded from the existing action)
#   file   = /General/FAB/Achat/BOs/BO Manager.xlsx   <- the folder is BOs, not BO
#   table  = TableBO's xr:uid from the workbook XML. Confirmed method: TableOrders'
#            xr:uid is {72371618-48E3-4FA4-B667-3B76BFA2D42A}, which is exactly the
#            table id the live flow already uses.
BO_SOURCE = {
    "source": "sites/ermcopower.sharepoint.com,88b9ed6c-d686-4bbe-b445-4e753ad511f6,"
              "7f8472f6-8a89-4591-a116-98a1783e6bcc",
    "drive": "b!bO25iIbWvku0RU51OtUR9vZyhH-JipFFoRaYoXg-a8zPqBmaybwgS5qVv6sntK64",
    "file": "01DI2JQP7NBWFPJE6RMBFL5PPWQWB7HUO7",
    "table": "{3580DC32-2968-4A81-A234-0D14634618E2}",
}

LIST_BO = "List_rows_present_in_a_table_BO"
FILTER_BO = "Filter_BO"
M = "first(body('%s'))" % FILTER_BO


def src(col):
    """A source cell, coalesced to '' so a null never reaches trim()/int()."""
    return "%s?['%s']" % (M, col)


def blank(col):
    return "equals(trim(string(coalesce(%s, ''))), '')" % src(col)


def group_guard(n):
    """No match, or this BO group has no part number -> write nothing.

    Measured on the 2026-09-03 workbook: BO1 OK is a real boolean on all 1014 rows
    and is False on 988 of them. Mapping it ungated would put a value on every unit
    and make them all look like they carry BO data."""
    return "or(empty(body('%s')), %s)" % (FILTER_BO, blank("BO%d Part Numbre" % n))


def text_field(n, col):
    return "@if(%s, null, %s)" % (group_guard(n), src("BO%d %s" % (n, col)))


def date_field(n):
    """Guards blank AND `TBD`, case-insensitively.

    `TBD` is a real marker in these columns -- 21838-1/5 and 21840-1/10 in BO1 Date,
    21521-1/1 in BO2 Date -- and all three rows DO carry a part number, so the group
    guard alone does not catch them. int('TBD') throws, and that throw surfaces as
    `Action 'Switch' failed`, indistinguishable from the EC bug. Case-insensitive
    because that is exactly what made the EC guard fail for weeks.

    Serial-to-date conversion mirrors what the flow already does for every other
    Excel date column, same connector and same workbook family. Confirm it in the
    D4 smoke test rather than assuming."""
    col = "BO%d Date" % n
    return ("@if(or(%s, %s, equals(toLower(trim(string(coalesce(%s, '')))), 'tbd')), "
            "null, addDays('1899-12-30', int(%s)))"
            % (group_guard(n), blank(col), src(col), src(col)))


def bool_field(n):
    return "@if(%s, null, %s)" % (group_guard(n), src("BO%d OK" % n))


def build_mappings():
    m = {
        # The roll-up. Choice column, so the connector wants the /Value suffix --
        # matching how Location, Frame and the stage statuses are already written.
        # Blank-guarded: 938 of 1014 source rows have no BO value, and the Choice
        # domain is exactly BO/OK.
        "item/BO/Value": "@if(or(empty(body('%s')), %s), null, %s)"
                         % (FILTER_BO, blank("BO"), src("BO")),
    }
    for n in (1, 2, 3):
        m["item/BO%dPartNumber" % n] = text_field(n, "Part Numbre")
        m["item/BO%dDescription" % n] = text_field(n, "Description")
        m["item/BO%dPOIntern" % n] = text_field(n, "PO Intern")
        m["item/BO%dDate" % n] = date_field(n)
        m["item/BO%dFournisseur" % n] = text_field(n, "Fournisseur Interne")
        m["item/BO%dOK" % n] = bool_field(n)
    return m


MAPPINGS = build_mappings()
WRITES = (("No_Items_Found", "CreateOrderItem"), ("One_Item_Found", "UpdateOrderItem"))


def def_of(doc):
    return doc.get("properties", {}).get("definition", doc.get("definition", doc))


def locate(defn):
    sw = defn["actions"]["Apply_to_each"]["actions"]["CheckOrderMatch"]["actions"]["Switch"]
    return {act: sw["cases"][case]["actions"][act]["inputs"]["parameters"]
            for case, act in WRITES}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("-o", "--out")
    a = ap.parse_args()
    out = a.out or a.src.replace(".json", " +d3.json")

    doc = json.load(io.open(a.src, encoding="utf-8"))
    before = copy.deepcopy(doc)
    defn = def_of(doc)
    top = defn["actions"]
    loop = top["Apply_to_each"]["actions"]

    for name in (LIST_BO, FILTER_BO):
        if name in top or name in loop:
            raise SystemExit("%s already exists -- D3 looks already applied" % name)
    for act, P in locate(defn).items():
        clash = [k for k in MAPPINGS if k in P]
        if clash:
            raise SystemExit("%s already has %s -- aborting" % (act, clash))

    # --- 1. the second Excel source, spliced into the existing chain ---------
    # Chain today: List_rows -> Filter_array -> Init -> Init -> Apply_to_each.
    # Insert after the FRM10-12 list so both sources are loaded before the loop.
    top[LIST_BO] = {
        "type": "OpenApiConnection",
        "runAfter": {"List_rows_present_in_a_table": ["Succeeded"]},
        "metadata": {"01DI2JQP7NBWFPJE6RMBFL5PPWQWB7HUO7":
                     "/General/FAB/Achat/BOs/BO Manager.xlsx"},
        "runtimeConfiguration": {"paginationPolicy": {"minimumItemCount": 5000}},
        "inputs": {
            "host": copy.deepcopy(top["List_rows_present_in_a_table"]["inputs"]["host"]),
            "parameters": dict(BO_SOURCE),
            "authentication": copy.deepcopy(
                top["List_rows_present_in_a_table"]["inputs"].get("authentication")),
        },
    }
    if top[LIST_BO]["inputs"]["authentication"] is None:
        del top[LIST_BO]["inputs"]["authentication"]
    top["Filter_array"]["runAfter"] = {LIST_BO: ["Succeeded"]}

    # --- 2. the in-loop match ------------------------------------------------
    # RawOrder is trim(item()?['Order']) and Order Items.Title matches it exactly,
    # SA suffix included, so the join needs no normalising.
    loop[FILTER_BO] = {
        "type": "Query",
        "runAfter": {"RawOrder": ["Succeeded"]},
        "inputs": {"from": "@outputs('%s')?['body/value']" % LIST_BO,
                   "where": "@equals(trim(string(coalesce(item()?['Order'], ''))), "
                            "outputs('RawOrder'))"},
    }
    loop["IsSA"]["runAfter"] = {FILTER_BO: ["Succeeded"]}

    # --- 3. the mappings, on both write actions -----------------------------
    for act, P in locate(defn).items():
        for k, v in MAPPINGS.items():
            P[k] = v

    io.open(out, "w", encoding="utf-8").write(json.dumps(doc, indent=2, ensure_ascii=False))

    # ------------------------------------------------------------- verify ---
    after = json.load(io.open(out, encoding="utf-8"))
    da, db = def_of(after), def_of(before)
    pa, pb = locate(da), locate(db)
    ok = True
    print("wrote %s\n" % os.path.basename(out))
    print("added actions   : %s, %s" % (LIST_BO, FILTER_BO))
    print("BO source       : /General/FAB/Achat/BOs/BO Manager.xlsx")
    print("                  table %s\n" % BO_SOURCE["table"])
    for act in pa:
        add = sorted(set(pa[act]) - set(pb[act]))
        rm = sorted(set(pb[act]) - set(pa[act]))
        ch = [k for k in set(pa[act]) & set(pb[act]) if pa[act][k] != pb[act][k]]
        nb = len([k for k in pb[act] if k.startswith("item/")])
        na = len([k for k in pa[act] if k.startswith("item/")])
        print("%-16s %d -> %d item/*   +%d  -%d  ~%d" % (act, nb, na, len(add), len(rm), len(ch)))
        if sorted(add) != sorted(MAPPINGS) or rm or ch:
            ok = False; print("   UNEXPECTED +%s -%s ~%s" % (add, rm, ch))

    # the chain must still be one connected path into the loop
    chain_ok = (da["actions"]["Filter_array"]["runAfter"] == {LIST_BO: ["Succeeded"]}
                and da["actions"][LIST_BO]["runAfter"] ==
                {"List_rows_present_in_a_table": ["Succeeded"]}
                and da["actions"]["Apply_to_each"]["actions"]["IsSA"]["runAfter"] ==
                {FILTER_BO: ["Succeeded"]})
    print("\ntop-level actions : %d -> %d" % (len(db["actions"]), len(da["actions"])))
    print("in-loop actions   : %d -> %d" % (len(db["actions"]["Apply_to_each"]["actions"]),
                                            len(da["actions"]["Apply_to_each"]["actions"])))
    print("chain rewired ok  : %s" % chain_ok)

    # nothing outside the two parameter objects and the two new actions moved
    def strip(d):
        c = copy.deepcopy(def_of(d))
        c["actions"].pop(LIST_BO, None)
        c["actions"]["Apply_to_each"]["actions"].pop(FILTER_BO, None)
        c["actions"]["Filter_array"].pop("runAfter", None)
        c["actions"]["Apply_to_each"]["actions"]["IsSA"].pop("runAfter", None)
        sw = c["actions"]["Apply_to_each"]["actions"]["CheckOrderMatch"]["actions"]["Switch"]
        for case, act in WRITES:
            sw["cases"][case]["actions"][act]["inputs"]["parameters"].clear()
        return json.dumps(c, sort_keys=True)
    rest = strip(after) == strip(before)
    print("rest untouched    : %s" % rest)
    # 3 date fields carry a TBD guard, and every mapping lands on BOTH write
    # actions -- so D3 adds 6 toLower calls, not 3.
    tl_before = json.dumps(db).count("toLower(")
    tl = json.dumps(da).count("toLower(")
    expect = tl_before + 6
    print("toLower( count    : %d -> %d  (expect %d: %d from P3 + 3 TBD guards x 2 actions)"
          % (tl_before, tl, expect, tl_before))
    good = ok and chain_ok and rest and tl == expect
    print("\nRESULT: %s" % ("OK -- 19 mappings on both actions, 2 actions added, chain intact"
                            if good else "PROBLEM -- do not paste this"))
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
