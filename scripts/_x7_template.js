/* X7 -- read-back verification of a parent sync. READ-ONLY, writes nothing.

   Paste into the SharePoint tab. Set UNIT to the Order Items item id you want to
   check (994 is the N3 test unit).

   WHY, when the run already said 200
     A PatchItem 200 means the request was accepted, not that the values are right.
     This project has been bitten by exactly that gap: the runbook's own rule is
     "verify by read-back on a handful of rows -- never from run status, which
     reports Failed even on a healthy run." A wrong-but-well-formed value returns
     200 all day.

   WHAT IT CHECKS
     Every field the three N3 flows map, read from the unit and from each of its
     three parents through the unit's own LOOKUP ids -- the same join the flows
     filter on, not the stale *_TextField mirrors.

   THE FIELD MAP BELOW IS GENERATED from scripts/gen_n3_flows.py. Re-run
   scripts/gen_x7_verifier.py after changing a mapping, or this silently verifies
   the wrong thing.
*/
(async () => {
  const UNIT = 994;                       // <-- Order Items item id to verify
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const PARENT = {
    "Order":           {id:"6fe35dfe-2b7d-455a-abe3-056abb386733", fk:"OrderNumberId"},
    "Models":          {id:"b43a5140-0f9d-4ac1-9019-43b897074224", fk:"ModelId"},
    "Model Revisions": {id:"e2ff8703-b590-4648-b181-9b47cf3883ba", fk:"ModelRevisionId"},
  };
  const MAP = __MAP__;

  const J = async u => (await fetch(u,{credentials:"include",
              headers:{Accept:"application/json;odata=nometadata"}})).json();

  const unit = await J(base+"/_api/web/lists(guid'"+OI+"')/items("+UNIT+")");
  if (!unit || unit.error) { console.error("could not read unit "+UNIT); return; }
  console.log("unit "+UNIT+"  "+(unit.Title||"")+"\n");

  // Compare the way the flow does: coalesce both sides to '' and string-compare.
  // null and '' are different in Power Automate; the guard coalesces, so we do too.
  const norm = v => {
    if (v === null || v === undefined) return "";
    if (typeof v === "object") return JSON.stringify(v);
    return String(v).trim();
  };
  let ok=0, bad=0, blank=0;
  for (const pname of Object.keys(MAP)) {
    const p = PARENT[pname];
    const pid = unit[p.fk];
    console.log("=== "+pname+"  (unit."+p.fk+" = "+(pid==null?"NOT SET":pid)+") ===");
    if (pid == null) { console.log("   unit is not linked to a "+pname+" -- this flow can never reach it\n"); continue; }
    const par = await J(base+"/_api/web/lists(guid'"+p.id+"')/items("+pid+")");
    if (!par || par.error) { console.error("   could not read parent "+pid); continue; }

    // LOOKUPS ARE NOT IN THE PLAIN ITEM READ. Probed on the live tenant 2026-09-11,
    // Models item 507:
    //    plain REST            ModelRevision   -> undefined   (only ModelRevisionId = 390)
    //    $expand + /Title      ModelRevision   -> {"Title":null}
    //    FieldValuesAsText     ModelRevision   -> "MR-ATCO-0002-V1"   <-- correct
    //
    // So a lookup field is ABSENT from the item, not empty, and the obvious
    // $expand=X&$select=X/Title returns NULL because these lookups do not show Title.
    // Reaching for that would read as "the parent has no value" and send someone
    // hunting a data problem that does not exist - which is exactly what the first
    // version of this script did: it reported MISMATCH 2 on a healthy unit, because
    // every populated lookup compared a real unit value against undefined.
    // FieldValuesAsText renders every field as its display text, lookups included,
    // without needing to know which column each lookup shows.
    const parTxt = await J(base+"/_api/web/lists(guid'"+p.id+"')/items("+pid+")/FieldValuesAsText");
    if (!parTxt || parTxt.error) {
      // Do NOT fall through to the plain read for lookups - that silently reproduces
      // the original false mismatch. Say so and skip this parent.
      console.error("   FieldValuesAsText failed for "+pname+" "+pid
                    +" - lookup fields cannot be verified, skipping this parent");
      continue;
    }
    for (const [tgt, src, kind] of MAP[pname]) {
      // Lookup -> the display text; everything else -> the raw item value.
      let pv = (kind === "lookup") ? parTxt[src] : par[src];
      // a Choice reads as a plain string over REST; a URL field as an object.
      if (pv && typeof pv === "object") pv = pv.Value !== undefined ? pv.Value
                                         : (pv.Url !== undefined ? pv.Url : pv);
      if (Array.isArray(pv)) pv = pv.map(x => (x && x.Value !== undefined) ? x.Value : x).join("; ");
      let cv = unit[tgt];
      if (cv && typeof cv === "object") cv = cv.Value !== undefined ? cv.Value
                                         : (cv.Url !== undefined ? cv.Url : cv);
      const a = norm(cv), b = norm(pv);
      const both_blank = !a && !b;
      if (both_blank) { blank++; console.log("   .  "+tgt.padEnd(26)+"(both empty)"); }
      else if (a === b) { ok++; console.log("   OK "+tgt.padEnd(26)+JSON.stringify(a).slice(0,60)); }
      else { bad++; console.log("   XX "+tgt.padEnd(26)+"unit="+JSON.stringify(a).slice(0,40)
                                +"   parent="+JSON.stringify(b).slice(0,40)); }
    }
    console.log("");
  }
  console.log("match "+ok+"   both-empty "+blank+"   MISMATCH "+bad+"   (expect MISMATCH 0)");
  console.log("\nnote: a mismatch here is what the change-guard sees, so any nonzero count");
  console.log("means the next parent edit rewrites this unit again -- the guard cannot settle.");
})();
