/* X24 -- level `Step Status Stamped` and `Location Stamped` with the row. OPTIONAL.

   DRY RUN by default: it writes nothing until APPLY = true.
   Paste into the browser console on the SharePoint site. Run it with the trigger flow OFF.

   WHY IT IS OPTIONAL NOW
     From v008 the trigger flow no longer writes Status Date (user decision 2026-09-24), so a
     stale stamp can no longer overwrite a date. What a stale stamp still does, on that
     unit's next edit, is make the flow think the step or location just changed:
       - it rewrites both stamps (harmless), and
       - if the unit is at Livraison, it forces Step Status = Terminé and Item Status =
         Delivered (the CompletOrder rule).
     The 09-16 export had 8 units at Livraison still `Active`. Running this first means
     that rule only fires on units that MOVE from now on; skipping it means those units get
     completed on their next edit. Either is defensible -- run the dry run and decide.

     (An earlier draft of this script also created a `Status Date Stamped` column for
     v007's date logic. v007 was superseded before it was pasted; the column is not needed.)

   WHAT IT WRITES
     per row, only the stamps that differ:
       StepStatusStamped = StepStatus
       LocationStamped   = Location
     Never StepStatus, Location or StatusDate themselves -- verified by reading all three
     before and after and diffing them.
*/
(async () => {
  const APPLY = false;
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const CONC = 4;
  const H    = {Accept:"application/json;odata=nometadata"};

  const J = async u => { const r = await fetch(u, {credentials:"include", headers:H});
    if (!r.ok) throw new Error(r.status + " " + (await r.text()).slice(0,200)); return r.json(); };
  const page = async (u) => { let o=[],g=0;
    while (u && g++<30){ const j=await J(u); o=o.concat(j.value||[]); u=j["odata.nextLink"]||null; } return o; };

  const s = v => (v == null ? "" : String(v));
  const items = "/_api/web/lists(guid'" + OI + "')/items";
  const SEL = "Id,Title,StepStatus,StepStatusStamped,Location,LocationStamped,StatusDate,ItemStatus";
  const read = () => page(base + items + "?$select=" + SEL + "&$top=500");

  const before = await read();
  if (!before.length) { console.error("ABORT: read 0 units. A zero-row read is a failed read."); return; }

  const want = u => {
    const w = {};
    if (s(u.StepStatus) !== s(u.StepStatusStamped)) w.StepStatusStamped = s(u.StepStatus);
    if (s(u.Location)   !== s(u.LocationStamped))   w.LocationStamped   = s(u.Location);
    return w;
  };
  const todo = before.map(u => ({u, w: want(u)})).filter(x => Object.keys(x.w).length);
  const count = k => todo.filter(x => k in x.w).length;
  const livr = todo.filter(({u}) => s(u.Location) === "Livraison"
                                && (s(u.StepStatus) !== "Terminé" || s(u.ItemStatus) !== "Delivered"));

  console.log("units read          : " + before.length);
  console.log("StepStatusStamped   : " + count("StepStatusStamped") + " to level");
  console.log("LocationStamped     : " + count("LocationStamped") + " to level");
  console.log("rows to write       : " + todo.length);
  console.log("of which at Livraison and not yet Terminé/Delivered: " + livr.length
              + "   <- these get completed on their next edit if you DON'T run this\n");
  console.table(todo.slice(0, 30).map(({u, w}) => ({unit: u.Title, location: u.Location,
    step: u.StepStatus, item: u.ItemStatus, ...w})));
  if (todo.length > 30) console.log("  ... and " + (todo.length - 30) + " more");

  if (!todo.length) { console.log("Nothing to do -- every stamp is level."); return; }
  if (!APPLY) { console.log("\nDRY RUN -- nothing written. Confirm the trigger flow is OFF, then set APPLY = true."); return; }

  const dg = (await (await fetch(base + "/_api/contextinfo", {method:"POST",
    credentials:"include", headers:H})).json()).FormDigestValue;
  let ok = 0, fail = 0; const errs = [];
  const patch = async ({u, w}) => {
    const r = await fetch(base + items + "(" + u.Id + ")", {
      method:"POST", credentials:"include",
      headers:{ Accept:"application/json;odata=nometadata",
                "Content-Type":"application/json;odata=nometadata",
                "X-RequestDigest": dg, "IF-MATCH":"*", "X-HTTP-Method":"MERGE" },
      body: JSON.stringify(w)     // stamps only
    });
    if (r.ok) ok++; else { fail++; errs.push(u.Title + ": " + (await r.text()).slice(0,160)); }
  };
  console.log("\nwriting " + todo.length + " rows ...");
  for (let i=0;i<todo.length;i+=CONC) await Promise.all(todo.slice(i,i+CONC).map(patch));
  console.log("written ok=" + ok + " failed=" + fail);
  for (const e of errs) console.error("  " + e);

  // ---------------------------------------------------------------- verification
  // Trust this, not the write results.
  const after = await read();
  const byId = new Map(after.map(u => [u.Id, u]));
  const still = after.filter(u => Object.keys(want(u)).length);
  let moved = 0;
  for (const b of before) {
    const a = byId.get(b.Id);
    if (!a) { console.error("  row " + b.Title + " disappeared"); moved++; continue; }
    for (const f of ["StatusDate", "StepStatus", "Location", "ItemStatus"])
      if (s(a[f]) !== s(b[f])) { moved++; console.error("  " + f + " MOVED on " + b.Title + ": " + s(b[f]) + " -> " + s(a[f])); }
  }
  console.log("\n--- verification ---");
  console.log("stamps still off level : " + still.length + "   (expect 0)");
  console.log("real values CHANGED    : " + moved + "   (expect 0 -- this is the one that matters)");
  console.log(still.length === 0 && moved === 0 ? "\nOK." : "\nNOT CLEAN -- look before enabling the flow.");
})();
