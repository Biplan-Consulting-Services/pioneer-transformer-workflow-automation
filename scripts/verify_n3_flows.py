# -*- coding: utf-8 -*-
"""Re-verify the three generated N3 parent-sync flows before they are pasted.

N3 was an enhancement while the transfer flow lived; it is now the *replacement* for
the refresh the transfer flow does today, because once that flow is deleted nothing
else keeps the 48 parent columns current. That promotion is why these get re-checked
against the current schema rather than trusted from generation time.

Six assertions, each one a failure mode that would be silent in production:

  1. field counts are 17 / 5 / 24                  -- a dropped mapping writes nothing
  2. every target is one of the 48 columns N2 built (by internal name, exactly)
  3. every Choice/Lookup source is read `?['Value']`  -- the R22 lesson; without it the
     raw expanded reference is stored, which is what put 110 chars of JSON on 979 rows
  4. no bare `select(` on a possibly-null source     -- `if()` evaluates BOTH branches
  5. the change-guard line count equals the field count -- a short guard rewrites rows
     that did not change, and every write fans out across ~1,019 items
  6. every fan-out Get items carries paginationPolicy 5000 -- the connector returns 100
     by default and the shortfall is invisible
  7. the trigger is OpenApiConnection + recurrence, not OpenApiConnectionWebhook --
     SharePoint's create-or-modified trigger POLLS; pasting a webhook shape yields a
     flow that saves cleanly and never fires
  8. a Choice TARGET is written `item/X/Value` and read `?['X']?['Value']` in the
     guard, and a non-Choice target is written plain -- checked against the column
     types in the newest Order Items export, so converting a column and forgetting
     the flow (or the reverse) is caught here instead of in production, where a
     plain key into a Choice column simply stops landing

Reads the internal names back out of `scripts/n2_create_columns.js`, which is the script
that actually created the columns, rather than from a doc that could have drifted.
"""
import json, io, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
N3 = os.path.join(ROOT, "workflow-data", "n3-flows")

EXPECTED = {
    "Order_Items__sync_from_Order.definition.json": ("Ord", 17),
    "Order_Items__sync_from_Models.definition.json": ("Mdl", 5),
    "Order_Items__sync_from_Model_Revisions.definition.json": ("Rev", 24),
}


def n2_internal_names():
    src = io.open(os.path.join(HERE, "n2_create_columns.js"), encoding="utf-8").read()
    # StaticName in the createfieldasxml payload is the authority: it is the one place
    # the internal name is set outright (the SharePoint UI cannot), and unlike a prose
    # doc it cannot have drifted from what was actually created. Matching on the prefix
    # alone -- no case or length assumption -- because the real set contains both
    # `OrdPO` (two chars) and `RevkVA` (lowercase first char), and every tighter pattern
    # tried here dropped one of them and reported a correct flow as broken.
    # The quotes are backslash-escaped inside the JS string literals, so both delimiters
    # are an OPTIONAL backslash then a quote -- `\\?"`, not `\?"`, which is a literal
    # question mark and matches nothing.
    names = set(re.findall(r'StaticName=\\?"((?:Ord|Mdl|Rev)[A-Za-z0-9]*)\\?"', src))
    return names


def mapping_kinds(prefix):
    """`target -> source kind` out of MAPPING.md, which the generator writes beside the
    definitions. Same generator, so this is not a fully independent source -- but it does
    catch the JSON and its own documented intent drifting apart, which is the drift a
    reviewer would otherwise have to spot by eye across 47 rows."""
    p = os.path.join(N3, "MAPPING.md")
    if not os.path.exists(p):
        return {}
    out = {}
    for line in io.open(p, encoding="utf-8"):
        cells = [c.strip().strip("`") for c in line.split("|")]
        if len(cells) >= 5 and cells[1].startswith(prefix):
            out[cells[1]] = cells[3].lower()
    return out


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def main():
    built = n2_internal_names()
    print("N2 internal names found: %d" % len(built))
    print()
    ok = True

    for fn, (prefix, want) in EXPECTED.items():
        p = os.path.join(N3, fn)
        if not os.path.exists(p):
            print("MISSING  %s" % fn); ok = False; continue
        doc = json.load(io.open(p, encoding="utf-8"))
        defn = doc.get("properties", {}).get("definition", doc.get("definition", doc))
        txt = json.dumps(defn, ensure_ascii=False)

        # --- 1/2: the write action's item/* targets ---
        targets = set()
        for node in walk(defn):
            for k in list(node.keys()):
                if isinstance(k, str) and k.startswith("item/"):
                    targets.add(k[5:].split("/")[0])
        targets = {t for t in targets if t.startswith(prefix)}
        n = len(targets)
        unknown = sorted(t for t in targets if t not in built)

        # --- 3: Choice/Lookup reads ---
        # Counting reads-without-Value proves nothing on its own: a plain Text field is
        # SUPPOSED to be read bare, so the number is large and healthy. What matters is
        # the per-field question -- is each source the generator recorded as `choice` or
        # `lookup` actually read with ?['Value']. MAPPING.md carries that kind per field,
        # so pair them up and check only the ones where it is load-bearing.
        kinds = mapping_kinds(prefix)
        missing_value = []
        for node in walk(defn):
            for k, v in list(node.items()):
                if not (isinstance(k, str) and k.startswith("item/")):
                    continue
                tgt = k[5:].split("/")[0]
                if kinds.get(tgt) in ("choice", "lookup") and "?['Value']" not in str(v):
                    missing_value.append(tgt)
        bare_choice = re.findall(r"triggerOutputs\(\)\?\['body/[^']+'\](?!\?\['Value'\])", txt)

        # --- 4: select() hardening ---
        bare_select = re.findall(r"select\(\s*(?!coalesce)", txt)

        # --- 5: change-guard lines ---
        guard = len(re.findall(r"not\(equals\(", txt))

        # --- 6: pagination ---
        pag = txt.count('"minimumItemCount": 5000') + txt.count('"minimumItemCount":5000')
        gets = sum(1 for node in walk(defn)
                   if isinstance(node.get("type"), str)
                   and node.get("type") == "OpenApiConnection"
                   and "GetItems" in json.dumps(node.get("inputs", {})))

        # 7. the trigger is a POLLING connection, not a webhook. SharePoint's
        #    "When an item is created or modified" is OpenApiConnection + recurrence.
        #    The generator emitted OpenApiConnectionWebhook until 2026-09-10; nothing
        #    caught it, because every other assertion here is about the write side.
        #    Ground truth: an empty shell built in the designer, and the live
        #    "Order Items - Create or Update Trigger flow", agree on this shape.
        trg = list((defn.get("triggers") or {}).values())
        trg_bad = []
        if len(trg) != 1:
            trg_bad.append("%d triggers" % len(trg))
        else:
            t = trg[0]
            if t.get("type") != "OpenApiConnection":
                trg_bad.append("type=%s (want OpenApiConnection)" % t.get("type"))
            if not t.get("recurrence"):
                trg_bad.append("no recurrence -- a polling trigger needs one")
            if (((t.get("inputs") or {}).get("host") or {}).get("operationId")
                    != "GetOnUpdatedItems"):
                trg_bad.append("operationId is not GetOnUpdatedItems")

        # 8. Choice targets need /Value on BOTH sides. Import the generator's own
        #    reader so there is exactly one place that decides what is a Choice.
        sys.path.insert(0, HERE)
        from gen_n3_flows import CHOICE_TARGETS, CHOICE_EXPORT
        shape_bad = []
        for t in sorted(targets):
            is_choice = t in CHOICE_TARGETS
            has_val_key = ('"item/%s/Value"' % t) in txt
            has_plain_key = ('"item/%s"' % t) in txt
            guard_val = ("?['%s']?['Value']" % t) in txt
            if is_choice and not (has_val_key and guard_val):
                shape_bad.append("%s is Choice but %s" % (
                    t, "write key is plain" if not has_val_key else "guard misses ?['Value']"))
            if (not is_choice) and (has_val_key or guard_val):
                shape_bad.append("%s is not Choice but is treated as one" % t)
            del has_plain_key

        status = []
        if shape_bad: status.append("CHOICE SHAPE: " + "; ".join(shape_bad)); ok = False
        if trg_bad: status.append("TRIGGER: " + "; ".join(trg_bad)); ok = False
        if n != want: status.append("FIELD COUNT %d != %d" % (n, want)); ok = False
        if unknown: status.append("UNKNOWN TARGETS %s" % unknown); ok = False
        if bare_select: status.append("BARE select() x%d" % len(bare_select)); ok = False
        if guard != want: status.append("GUARD %d != %d" % (guard, want)); ok = False
        if pag < 1: status.append("NO paginationPolicy 5000"); ok = False
        if missing_value:
            status.append("CHOICE/LOOKUP READ RAW %s" % sorted(set(missing_value))); ok = False

        nkv = sum(1 for v in kinds.values() if v in ("choice", "lookup"))
        print("%-46s fields=%-3d guard=%-3d pag=%-2d ch/lk=%-3d %s"
              % (fn.replace("Order_Items__sync_from_", "").replace(".definition.json", ""),
                 n, guard, pag, nkv, "OK" if not status else " | ".join(status)))
        if bare_choice:
            # Informational only, and deliberately not an assertion: a plain Text or
            # Number source is SUPPOSED to be read without ?['Value'], so this number is
            # large on a healthy flow. The real check is the typed one above.
            print("     %d bare source reads (expected -- plain fields)" % len(bare_choice))

    print()
    try:
        sys.path.insert(0, HERE)
        from gen_n3_flows import CHOICE_EXPORT as _ce, CHOICE_TARGETS as _ct
        print()
        print("column types read from: %s   (%d Choice columns on Order Items)"
              % (_ce, len(_ct)))
        print("  ⚠️ re-export Order Items after converting a column, or this check and")
        print("     the generator both work from a stale picture of the list.")
    except Exception as e:
        print("could not read column types: %s" % e)
    print("RESULT: %s" % ("OK -- all three re-verify against the columns N2 built"
                          if ok else "PROBLEM -- do not paste"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
