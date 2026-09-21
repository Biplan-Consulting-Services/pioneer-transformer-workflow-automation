#!/usr/bin/env python3
"""Generate x22_repair_parent_sync.js from the LIVE N3 flow definitions.

Why generated and not hand-written
----------------------------------
The repair has to write the same 49 fields the flows write, from the same
source fields. Two documents already got those names wrong:

  - docs/n3-parent-sync-flow-spec.md names `OrdOrderNumber` and `OrdQty`.
    Neither exists on the list; a $select naming them returns 400.
  - docs/lookup-textfield-reference.md names a source field `Model_Revion_ID`
    that does not exist, per model-revision-modelid-repair-2026-09-14.md.

The flow definitions in workflow-data/n3-flows/ are not documentation - they
are what actually runs. Extracting the mapping from them means the repair
writes exactly what a healthy sync run would have written, including the
`/Value` suffix on Choice targets and SharePoint's encoded source names
(`Initial_x0020_Promised_x0020_Dat`).

Same relationship as gen_x7_verifier.py -> x7_verify_parent_sync.js. Re-run
this after any N3 mapping change or the repair silently writes the old shape.

    python scripts/gen_x22_repair.py
"""
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
FLOWS = ROOT / "workflow-data" / "n3-flows"
OUT = HERE / "x22_repair_parent_sync.js"

# flow file -> (group prefix, the Order Items lookup column holding the parent id)
SOURCES = {
    "Order_Items__sync_from_Order.definition.json":           ("Ord", "OrderNumberId",    "Order"),
    "Order_Items__sync_from_Models.definition.json":          ("Mdl", "ModelId",          "Models"),
    "Order_Items__sync_from_Model_Revisions.definition.json": ("Rev", "ModelRevisionId",  "Model Revisions"),
    "Order_Items__sync_from_Clients.definition.json":         ("Cli", "ClientId",         "Clients"),
}

# A BARE read: `@triggerOutputs()?['body/Foo']` or the same with ?['Value'].
BARE = re.compile(r"^@triggerOutputs\(\)\?\['body/([^']+)'\](\?\['Value'\])?$")
# Any read at all, used only to name the source inside a complex expression.
TRIGGER = re.compile(r"triggerOutputs\(\)\?\['body/([^']+)'\]")

# 🔴 The one mapping that is NOT a bare read, and the reason this distinction
# exists. RevModelDescription's source is a MultiChoice, so the flow does:
#   @if(empty(coalesce(body/Description, [])), null,
#       first(coalesce(body/Description, []))?['Value'])
# i.e. take the FIRST entry's Value. A regex that just grabs the first
# `triggerOutputs` match reduces that to a bare read, and over REST a
# MultiChoice comes back as `["PADMOUNT"]` - so the repair writes the ARRAY
# into the column. That is R22 exactly: the write-side trap that put 110
# characters of JSON into 979 rows, and it lands silently because the target is
# a Note field that accepts any string.
# Anything that is neither bare nor this shape aborts rather than being guessed.
FIRST_VALUE = re.compile(r"first\(.*?triggerOutputs\(\)\?\['body/([^']+)'\].*?\)\?\['Value'\]", re.S)


def find_update(node):
    """The Update item action, wherever the designer nested it."""
    if isinstance(node, dict):
        if node.get("type") == "OpenApiConnection":
            op = node.get("inputs", {}).get("host", {}).get("operationId", "")
            if "PatchItem" in op or "UpdateItem" in op:
                return node
        for v in node.values():
            hit = find_update(v)
            if hit:
                return hit
    return None


def parent_guid(d):
    """The parent list's GUID, off the flow's own trigger. Hand-typing these is
    how a placeholder ends up in a write script: the first draft of this
    generator carried `3bcf7d97-0000-...` for Clients."""
    trig = list(d["triggers"].values())[0]
    guid = trig["inputs"]["parameters"].get("table")
    if not guid or len(guid) != 36:
        raise SystemExit("ABORT: trigger carries no usable list GUID (%r)" % guid)
    return guid


def extract(path):
    """[(child field, whether the target takes /Value, source field, whether the
    source is read as ?['Value'])] for one flow."""
    d = json.loads(path.read_text(encoding="utf-8"))
    act = find_update(d)
    if act is None:
        raise SystemExit("ABORT: no Update item action found in %s" % path.name)
    out = []
    for key, expr in act["inputs"]["parameters"].items():
        if not key.startswith("item/"):
            continue
        target = key[len("item/"):]
        target_is_choice = target.endswith("/Value")
        if target_is_choice:
            target = target[: -len("/Value")]
        if not isinstance(expr, str):
            continue

        bare = BARE.match(expr.strip())
        if bare:
            out.append((target, target_is_choice, bare.group(1), bool(bare.group(2)), False))
            continue

        multi = FIRST_VALUE.search(expr)
        if multi:
            out.append((target, target_is_choice, multi.group(1), True, True))
            continue

        if not TRIGGER.search(expr):
            # A constant. The repair cannot reproduce it from the parent row.
            out.append((target, target_is_choice, None, False, False))
            continue

        # Reads the parent, but in a shape this generator does not understand.
        # Guessing here is how R22 happened, so: stop.
        raise SystemExit(
            "ABORT: %s in %s reads the parent through an expression this "
            "generator cannot reproduce:\n    %s\n"
            "Teach gen_x22_repair.py the shape rather than letting it guess."
            % (target, path.name, expr))
    return parent_guid(d), out


def main():
    mapping, skipped = {}, []
    for fname, (prefix, fk, parent) in SOURCES.items():
        path = FLOWS / fname
        if not path.exists():
            raise SystemExit("ABORT: missing %s" % path)
        guid, raw = extract(path)
        fields = []
        for target, tgt_choice, source, src_choice, src_multi in raw:
            if source is None:
                skipped.append("%s (%s): not read from the parent row" % (target, prefix))
                continue
            if src_multi:
                print("  %s: MultiChoice source %r - takes first().Value, as the flow does"
                      % (target, source))
            fields.append({"target": target, "targetChoice": tgt_choice,
                           "source": source, "sourceChoice": src_choice,
                           "sourceMulti": src_multi})
        mapping[prefix] = {"parent": parent, "list": guid, "fk": fk, "fields": fields}
        print("%-4s %-16s %2d fields   %s" % (prefix, parent, len(fields), guid))

    for s in skipped:
        print("  skipped: %s" % s)

    js = TEMPLATE.replace("__MAPPING__", json.dumps(mapping, indent=2, ensure_ascii=False))
    OUT.write_text(js, encoding="utf-8")
    print("\nwrote %s" % OUT.relative_to(ROOT))


TEMPLATE = r"""/* X22 -- repair the parent data the N3 sync flows lost.

   🔴 GENERATED by scripts/gen_x22_repair.py from the LIVE flow definitions in
   workflow-data/n3-flows/. Do not hand-edit the MAP below - re-run the
   generator after any N3 mapping change, or this writes the old shape.

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
     3. It runs DRY by default and writes nothing. Read the plan, then set
        DRY = false and paste again.

   WHAT IT DOES
     For each unit id in UNITS: follow that unit's own lookup to each parent,
     read the parent row, and write only the mapped fields that are BLANK on
     the unit. It never overwrites a value that is already there, so a unit
     that was only partly damaged is completed rather than rewritten.

   WHY IT RESOLVES THROUGH THE LOOKUP AND NOT A SIBLING OR A MIRROR
     Copying from a healthy sibling would be quicker and is how this goes
     wrong: x18's first version derived its fix from a `_TextField` mirror, in
     a script written to repair damage caused by trusting mirrors. The lookup
     against the live parent list is the only source that cannot be stale.

   WHY A RE-RUN OF THE FLOW WOULD NOT DO THIS
     Per the N3 spec's finding 2, the Power Automate connector LEAVES the
     existing value when handed null - measured, not assumed. These fields are
     blank rather than wrong, so no re-run removes or fills them. They need an
     explicit write, which is what raw REST does.

   ⚠️ CHECK BEFORE TRUSTING A RESULT
     - A 200 from a PATCH means accepted, not correct. This reads every unit
       back afterwards and reports per field.
     - Dates go in as a BARE yyyy-mm-dd. A full instant stores UTC midnight,
       which renders as the previous day on an Eastern site - the exact bug the
       2026-09-08 backfill existed to fix.
     - A lookup or choice read off a parent comes back as
       {"Id":5,"Value":"MALT"}, not "MALT". Passing the whole object is R22,
       which put 110 characters of JSON into 979 rows. The MAP records which
       fields need ?.Value on the way out.
*/
(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";

  const DRY = true;   // <-- set false to actually write

  /* The units to repair. From x19 on the three orders the client flagged:
       22169  1223-1226  lost Ord* and Mdl*   (the fan-out race: a clean tail)
       22172  1235       lost Ord*            (Save Conflict: its sibling is fine)
       22175  1245       lost Ord* and Mdl*   (Save Conflict)
              1246       lost Rev*            (Save Conflict, the other direction)
     Cli* is blank on all of them, and on every other unit checked - that is a
     separate question, not this repair. Leave CliLeadTimeWeeks out until the
     whole-list number is known. */
  const UNITS = [1223, 1224, 1225, 1226, 1235, 1245, 1246];
  const SKIP_GROUPS = ["Cli"];

  const MAP = __MAPPING__;

  /* Each group's `list` GUID comes from that flow's own trigger, via the
     generator - not hand-typed here. The first draft of the generator did type
     them, and carried a placeholder `3bcf7d97-0000-...` for Clients. */

  const J = async (u, opt) => {
    const r = await fetch(u, Object.assign({ credentials: "include",
      headers: { Accept: "application/json;odata=nometadata" } }, opt || {}));
    if (!r.ok) throw new Error(r.status + " " + r.statusText + " " + (await r.text()).slice(0, 300));
    return r.status === 204 ? {} : r.json();
  };
  const items = base + "/_api/web/lists(guid'" + OI + "')/items";
  const isBlank = (v) => v === null || v === undefined || String(v).trim() === "";

  /* A parent value on its way into a child column.

     🔴 The array case is R22. A MultiChoice source comes back from REST as
     `["PADMOUNT"]`, and the target (`RevModelDescription`) is a Note field that
     will accept the stringified array without complaint - which is how 979 rows
     ended up holding 110 characters of JSON. The flow itself does
     `first(...)?['Value']`, so this does the same.

     ⚠️ Taking first() loses the rest when a revision carries several values.
     The N3 spec argues against it ("a MultiChoice returns several entries --
     join them, do not take first() blindly"), but v007 shipped first(). The
     repair MATCHES the flow rather than improving on it, so repaired rows and
     synced rows cannot disagree. Change both together or neither. */
  const unwrap = (v, isChoice) => {
    if (v === null || v === undefined) return null;
    if (Array.isArray(v)) {
      if (!v.length) return null;
      return unwrap(v[0], isChoice);
    }
    if (isChoice || (typeof v === "object" && "Value" in v))
      return (typeof v === "object") ? (v.Value === undefined ? null : v.Value) : v;
    return v;
  };
  /* A Date-Only column takes a bare date. Anything with a time renders a day
     early on an Eastern site. */
  const asDate = (v) => (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T/.test(v)) ? v.slice(0, 10) : v;

  /* 🔴 A LOOKUP source does not come back from a plain item read.
     `items(498)` returns `ModelRevisionId`, an integer - there is no
     `ModelRevision` property at all. The flow gets the display value because
     the Power Automate connector expands lookups for it; raw REST does not.
     So four fields (MdlLatestModelRevision, MdlParentModel, RevDuplicateOrder,
     RevPioneerModelCode) read as `undefined`, which `isBlank` calls blank, and
     the repair skipped them SILENTLY - visible only as Mdl 3/5 on a repaired
     unit against 4/5 on its siblings.

     Resolved here the way the N3 spec documents as the one route that works on
     this tenant: _api/v2.0/.../columns gives each lookup its target listId and
     the column it displays. `_api/web/lists/.../fields` HANGS here - four
     45-second timeouts on record - so do not "simplify" this to that. */
  const lookupMeta = {};   // parent list GUID -> {fieldName: {listId, columnName}}
  const lookupsOf = async (listGuid) => {
    if (lookupMeta[listGuid]) return lookupMeta[listGuid];
    const m = {};
    try {
      const cols = await J(base + "/_api/v2.0/sites/root/lists/" + listGuid + "/columns");
      for (const c of (cols.value || [])) if (c.lookup && c.lookup.listId)
        m[c.name] = { listId: c.lookup.listId, columnName: c.lookup.columnName };
    } catch (e) { console.log("  (columns unreadable for " + listGuid + ": " + e.message + ")"); }
    lookupMeta[listGuid] = m;
    return m;
  };
  const rowCache = {};
  const resolveLookup = async (listGuid, field, parentRow) => {
    const meta = (await lookupsOf(listGuid))[field];
    const id = parentRow[field + "Id"];
    if (!meta || id === null || id === undefined || id === "") return null;
    const key = meta.listId + "/" + id;
    if (!(key in rowCache)) {
      try { rowCache[key] = await J(base + "/_api/web/lists(guid'" + meta.listId + "')/items(" + id + ")"); }
      catch (e) { rowCache[key] = null; }
    }
    const row = rowCache[key];
    return row ? (row[meta.columnName] === undefined ? null : row[meta.columnName]) : null;
  };

  const digest = await J(base + "/_api/contextinfo", { method: "POST" })
    .then(j => j.FormDigestValue).catch(() => null);
  if (!DRY && !digest) { console.error("ABORT: no form digest, cannot write."); return; }

  const plan = [];
  let bail = false;
  for (const id of UNITS) {
    const unit = await J(items + "(" + id + ")");
    console.log("--- Id " + id + "  " + unit.Title + " ---");

    for (const g of Object.keys(MAP)) {
      if (SKIP_GROUPS.indexOf(g) >= 0) continue;
      const m = MAP[g];
      const pid = unit[m.fk];
      if (isBlank(pid)) { console.log("  " + g + "*: no " + m.parent + " lookup - skipped"); continue; }
      let parent;
      try { parent = await J(base + "/_api/web/lists(guid'" + m.list + "')/items(" + pid + ")"); }
      catch (e) { console.log("  " + g + "*: parent " + pid + " unreadable - " + e.message); continue; }

      const write = {};
      let already = 0, empty = 0;
      for (const f of m.fields) {
        if (!isBlank(unit[f.target])) { already++; continue; }
        let raw = parent[f.source];
        /* Present as `<name>Id` but absent as `<name>` = a lookup. Resolve it
           rather than treating it as blank. */
        if (raw === undefined && parent[f.source + "Id"] !== undefined)
          raw = await resolveLookup(m.list, f.source, parent);
        let v = unwrap(raw, f.sourceChoice);
        v = asDate(v);
        if (isBlank(v)) { empty++; continue; }
        /* Nothing structured may reach a write. If unwrap left an object or an
           array here, the mapping is one this generator does not understand -
           refuse rather than write JSON into a column. */
        if (typeof v === "object" && !(v && v.Url !== undefined)) {
          console.log("      🔴 " + f.target + " would receive " + JSON.stringify(v)
            + " -- structured value, refusing. Teach gen_x22_repair.py this mapping.");
          bail = true; continue;
        }
        /* 🔴 Do not propagate the Model Revisions.ModelID corruption.
           A revision id is `MR-…-V1` (or `MRSA-…-V1` for an SA model). Rows
           holding their MODEL's code instead were repaired on 2026-09-14 by
           x18_repair_revision_modelid.js -- 29 of them -- but the CAUSE was
           never found, and revisions 106 and 387 hold model codes again today.
           Writing one here would spread damage under cover of a repair. */
        if (f.target === "RevModelRevionID" && !/^MRS?A?-.+-V\d+$/.test(String(v))) {
          console.log("      🔴 " + f.target + " = " + JSON.stringify(v)
            + " is a MODEL code, not a revision id. Revision " + pid + " is corrupt."
            + "\n         Run x17_audit_revision_modelid.js / x18_repair_revision_modelid.js"
            + " FIRST, then re-run this.");
          bail = true; continue;
        }
        /* 🔴 NO `/Value` SUFFIX HERE. `item/OrdOrderType/Value` is the Power
           Automate CONNECTOR's parameter name; raw REST takes a Choice as a
           plain string on the field itself. Copying the flow's key shape into
           a REST body writes to a field that does not exist. `targetChoice`
           is still used - but to unwrap the SOURCE, not to name the target. */
        write[f.target] = v;
      }
      const n = Object.keys(write).length;
      console.log("  " + g + "* <- " + m.parent + " " + pid + ": " + n + " to write, "
        + already + " already set, " + empty + " blank on the parent");
      for (const k of Object.keys(write)) console.log("      " + k.padEnd(34) + " = " + JSON.stringify(write[k]));
      if (n) plan.push({ id: id, group: g, write: write });
    }
  }

  console.log("\n=== " + plan.length + " writes planned across " + UNITS.length + " units ===");
  if (bail) { console.error("🔴 ABORT: a structured value reached a write. Nothing written."); return; }
  if (DRY) { console.log("DRY RUN - nothing written. Set DRY = false and paste again."); return; }

  /* One PATCH per group per unit, mirroring what the flow would have done. */
  for (const p of plan) {
    try {
      /* nometadata on the way in too, so no __metadata / entity-type name is
         needed - one less thing to hand-type wrong. IF-MATCH * because this is
         a deliberate repair, not a concurrent edit: the losing side of a Save
         Conflict is exactly what we are here to fix. */
      await J(items + "(" + p.id + ")", {
        method: "POST",
        headers: { Accept: "application/json;odata=nometadata", "Content-Type": "application/json;odata=nometadata",
                   "X-RequestDigest": digest, "X-HTTP-Method": "MERGE", "IF-MATCH": "*" },
        body: JSON.stringify(p.write),
      });
      console.log("  wrote " + p.id + " " + p.group + "*");
    } catch (e) { console.log("  🔴 FAILED " + p.id + " " + p.group + "*: " + e.message); }
  }

  /* Read back. A 200 is not evidence. */
  console.log("\n=== read-back ===");
  let bad = 0;
  for (const p of plan) {
    const after = await J(items + "(" + p.id + ")");
    for (const field of Object.keys(p.write)) {
      const got = after[field], want = p.write[field];
      /* A URL column reads back as {Url, Description}; compare the Url. */
      const flat = (v) => (v && typeof v === "object")
        ? (v.Url !== undefined ? v.Url : (v.Value !== undefined ? v.Value : JSON.stringify(v)))
        : v;

      /* ⚠️ A Date-Only column NEVER reads back in the shape it was written.
         We send a bare `2026-09-16`; SharePoint stores site-local midnight and
         returns `2026-09-16T04:00:00Z` (05:00Z outside DST). That is the
         CORRECT result - a full instant would store UTC midnight and render as
         the previous day, which is the bug the 2026-09-08 backfill existed to
         fix. The first version of this read-back compared the strings raw and
         called all 12 date writes failures when every one of them was right.
         So: when we sent a bare date, compare only the date part. */
      const same = (w, g) => {
        const a = flat(w), b = flat(g);
        if (typeof a === "string" && /^\d{4}-\d{2}-\d{2}$/.test(a) && typeof b === "string")
          return b.slice(0, 10) === a;
        return String(a) === String(b);
      };
      if (!same(want, got)) {
        bad++;
        console.log("  🔴 " + p.id + " " + field + ": wanted " + JSON.stringify(want) + " got " + JSON.stringify(got));
      }
    }
  }
  console.log(bad ? "\n🔴 " + bad + " fields did not land." : "\n✅ every written field verified.");
})();
"""

if __name__ == "__main__":
    main()
