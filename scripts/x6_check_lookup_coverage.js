/* X6 -- read-only. How well are the three parent LOOKUPS actually populated on
   Order Items, and which parent does a given unit really point at?

   Read-only: it writes nothing. Paste and press Enter.

   WHY
     The N3 fan-out filters on the lookup Id (`ModelId eq <trigger ID>`), so a unit
     is only reachable by its parent's sync flow if that lookup is SET. Every count
     I produced before this came from `*_TextField` mirrors in a CSV export, and
     those mirrors' sync flow has been off since 2026-08-21 -- so they say nothing
     reliable about the lookups the flow actually uses. An export cannot show a
     lookup at all, values or schema. This reads them directly.
*/
(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const J = async u => (await fetch(u, {credentials:"include",
              headers:{Accept:"application/json;odata=nometadata"}})).json();
  const page = async (u) => { let o=[],g=0;
    while (u && g++<30){ const j=await J(u); o=o.concat(j.value||[]); u=j["odata.nextLink"]||null; } return o; };

  const units = await page(base+"/_api/web/lists(guid'"+OI+"')/items"
    +"?$select=Id,Title,OrderNumberId,ModelId,ModelRevisionId&$top=500");
  if (!units.length) { console.error("ABORT: read 0 units."); return; }
  console.log("units read: " + units.length + "\n");

  for (const f of ["OrderNumberId","ModelId","ModelRevisionId"]) {
    const set = units.filter(u => u[f] != null && u[f] !== "").length;
    console.log("  " + f.padEnd(18) + "set on " + String(set).padStart(5) + " / "
      + units.length + "   empty on " + (units.length-set)
      + (set === 0 ? "   <-- this flow can never fan out to anything" : ""));
  }

  // fan-out size per parent: how many units would one parent edit touch?
  for (const f of ["OrderNumberId","ModelId","ModelRevisionId"]) {
    const c = {}; for (const u of units) if (u[f]) c[u[f]] = (c[u[f]]||0)+1;
    const v = Object.values(c).sort((a,b)=>b-a);
    if (!v.length) { console.log("\n" + f + ": no parent has any unit"); continue; }
    console.log("\n" + f + ": " + v.length + " distinct parents, fan-out avg "
      + (v.reduce((a,b)=>a+b,0)/v.length).toFixed(1) + ", worst " + v[0]
      + ", singles " + v.filter(x=>x===1).length);
  }

  // a good single-unit test parent for each flow, chosen from the REAL lookups
  console.log("\n=== single-unit test parents, read from the lookups themselves ===");
  for (const [f, list, name] of [["OrderNumberId","6fe35dfe-2b7d-455a-abe3-056abb386733","Order"],
                                 ["ModelId","b43a5140-0f9d-4ac1-9019-43b897074224","Models"],
                                 ["ModelRevisionId","e2ff8703-b590-4648-b181-9b47cf3883ba","Model Revisions"]]) {
    const c = {}; for (const u of units) if (u[f]) (c[u[f]] = c[u[f]] || []).push(u);
    const solo = Object.entries(c).filter(([,us]) => us.length === 1).slice(0, 3);
    if (!solo.length) { console.log("  " + name.padEnd(16) + "none with exactly one unit"); continue; }
    for (const [pid, us] of solo) {
      const p = await J(base+"/_api/web/lists(guid'"+list+"')/items("+pid+")");
      const label = p.Order_x0020_Number1 || p.Model_ID || p.ModelID || p.Title || "";
      console.log("  " + name.padEnd(16) + "parent id " + String(pid).padEnd(6)
        + (label+"").padEnd(20) + "-> unit " + us[0].Title + " (id " + us[0].Id + ")");
    }
  }
})();
