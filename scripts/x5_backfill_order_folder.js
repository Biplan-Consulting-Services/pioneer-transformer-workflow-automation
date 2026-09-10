/* X5 -- carry Order.Order Folder onto the Order Items units.

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
        (if Chrome refuses the paste, type  allow pasting  first)
     3. DRY RUN by default. Read the summary, then set APPLY = true and paste again.
     4. It prints an UNDO block and re-reads every row to verify.

   WHAT THIS IS FOR
     Order Folder points at the document library folder holding everything filed
     against an order -- drawings, correspondence, the project information folder.
     It is populated on 106 of 449 orders and on 0 of 1,124 units.

   WHY IT WAS NEVER DONE (roadmap 38)
     "A hyperlink is an object on both read and write, the shape was never sourced,
     and a wrong one either fails every row or writes nothing."

     That is true of the POWER AUTOMATE CONNECTOR, whose expected shape for a URL
     column could not be established from anything in this repo. It is not true of
     REST, where the shape is a documented type:

         { "__metadata": { "type": "SP.FieldUrlValue" },
           "Url": "...", "Description": "..." }

     So the blocker was the tool, not the problem. Doing it here sidesteps it
     entirely -- and it does NOT depend on the transfer flow, so it is not bound to
     the cutover window. The source is the Order list, which outlives cutover.

   THE VALUES, measured 2026-09-09
     All 106 are exactly:
         /sites/PioneerPlanificatio/Order%20Library/<Order Number>
     zero exceptions -- RELATIVE, note. This script writes them absolute, prefixed
     with the site origin, because that is the shape the Power Automate connector
     uses and therefore the shape N3 will keep them in. See the comment at the
     folder map below.

     The URL carries no information the order number does not already have.

     ⚠️ WHICH IS WHY THE COLUMN STILL HAS TO BE COPIED RATHER THAN GENERATED.
     Only 106 of 449 orders have a folder. Building the URL from the order number
     for every unit would hand staff a 404 on the other 343. The presence of the
     value IS the information. And the obvious flag does not help: "Create and
     Organize Project Information Document Folder" reads False on all 449 rows --
     it has never been used.

   SCOPE
     Only units whose order has a folder AND whose OrdOrderFolder is currently
     empty. Re-running is safe; it skips anything already set.

   ONGOING, after cutover
     This is a one-time backfill. Keeping it fresh for NEW orders is N3's job -- the
     Order sync flow currently excludes this column for the same connector-shape
     reason. Decide that separately; the units backfilled here do not go stale,
     because a folder's URL never changes once the order number exists.
*/

(async () => {
  const APPLY = false;                     // <-- set true to actually write
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const ORIGIN = "https://ermcopower.sharepoint.com";
  const CONC  = 4;

  const J = async u => (await fetch(u, {headers:{Accept:"application/json;odata=nometadata"}})).json();
  const page = async (url) => {
    let out = [], g = 0;
    while (url && g++ < 20) { const j = await J(url); out = out.concat(j.value||[]); url = j["odata.nextLink"]||null; }
    return out;
  };

  // ---------------------------------------------------------- resolve the lists
  const ord = await J(base+"/_api/web/lists/getbytitle('Order')?$select=Id");
  const oi  = await J(base+"/_api/web/lists/getbytitle('Order Items')?$select=Id,ListItemEntityTypeFullName");
  if (!ord.Id || !oi.Id) { console.error("could not resolve both lists -- aborting"); return; }
  const ET = oi.ListItemEntityTypeFullName;

  // ------------------------------------------- order number -> folder URL + text
  const orders = await page(base+"/_api/web/lists(guid'"+ord.Id+"')/items"
                            +"?$select=Id,Order_x0020_Number1,Order_x0020_Folder&$top=500");
  if (!orders.length) { console.error("ABORT: read 0 orders -- broken query, not an empty list."); return; }
  // Keyed on the Order's list ID, not its order number. Order Items reaches its parent
  // through the `OrderNumber` LOOKUP, so `OrderNumberId` is the join the platform already
  // resolved -- no string matching, and it keeps working after the redundant
  // `OrdOrderNumber` text copy is deleted (2026-09-10).
  const folder = new Map();
  for (const o of orders) {
    const num = (o["Order_x0020_Number1"]||"").trim();
    const f = o["Order_x0020_Folder"];
    // a URL field comes back as {Url, Description} -- or null
    let url = f && (f.Url || f.url);
    // Store the ABSOLUTE form, matching what the N3 Order flow writes.
    //
    // The Order list holds all 106 as relative paths (/sites/PioneerPlanificatio/...),
    // but the Power Automate connector normalises to absolute on the way through: Test C
    // run 1 wrote https://ermcopower.sharepoint.com/sites/... to the unit, and run 2
    // then found the guard settled, which proves the connector READS that absolute form
    // back as well. Both measured 2026-09-10.
    //
    // If this backfill wrote the relative path, every unit it filled would differ from
    // what N3 reads, so the next edit to that order would rewrite it once. Harmless but
    // pointless churn across 106 orders' units, and it would look like a bug in the
    // guard. Writing the same shape means the two agree from the start.
    if (url && url.startsWith("/")) url = ORIGIN + url;
    if (url) folder.set(o.Id, {Url: url, Description: (f.Description || f.description || num), num: num});
  }
  console.log("orders read: " + orders.length + " | with a folder: " + folder.size);
  if (!folder.size) { console.error("ABORT: no order carries a folder URL. Check the field name."); return; }

  // ------------------------------------------------------------ the units to fill
  const units = await page(base+"/_api/web/lists(guid'"+oi.Id+"')/items"
                           +"?$select=Id,Title,OrderNumberId,OrdOrderFolder&$top=500");
  if (!units.length) { console.error("ABORT: read 0 units -- broken query, not an empty list."); return; }
  console.log("units read : " + units.length);

  const plan = [], already = [], noFolder = [], noOrder = [];
  for (const u of units) {
    const num = u.OrderNumberId;
    if (!num) { noOrder.push(u.Title); continue; }
    const f = folder.get(num);
    if (!f) { noFolder.push(u.Title); continue; }
    const cur = u.OrdOrderFolder && (u.OrdOrderFolder.Url || u.OrdOrderFolder.url);
    if (cur) { already.push(u.Title); continue; }
    plan.push({Id:u.Id, Title:u.Title, num:f.num, val:f});
  }
  console.log("\n=== plan ===");
  console.log("  to fill                    : " + plan.length);
  console.log("  already have a folder      : " + already.length);
  console.log("  order has no folder        : " + noFolder.length);
  console.log("  unit not linked to an Order : " + noOrder.length
              + (noOrder.length ? "   <- these have no OrderNumber lookup set" : ""));
  const byOrder = {};
  for (const p of plan) byOrder[p.num] = (byOrder[p.num]||0)+1;
  console.log("  distinct orders covered    : " + Object.keys(byOrder).length + " of " + folder.size);
  console.log("\n  sample:");
  for (const p of plan.slice(0,4)) console.log("     " + p.Title + "  ->  " + p.val.Url);

  if (!plan.length) { console.log("\nnothing to do."); return; }
  if (!APPLY) { console.log("\nDRY RUN -- nothing written. Set APPLY = true and paste again."); return; }

  console.log("\n=== UNDO (these were empty before -- clearing restores them) ===");
  console.log(JSON.stringify(plan.map(p => ({Id:p.Id, Title:p.Title}))));

  // ------------------------------------------------------------------- write
  const dg = await (await fetch(base+"/_api/contextinfo",{method:"POST",
                    headers:{Accept:"application/json;odata=nometadata"}})).json();
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  let ok=0, fail=0; const errs=[];
  const patch = async (p) => {
    // SP.FieldUrlValue -- the documented shape for a URL column over REST. This is
    // the whole reason the column is doable here and not in the connector.
    const body = {__metadata:{type:ET},
                  OrdOrderFolder:{__metadata:{type:"SP.FieldUrlValue"},
                                  Url:p.val.Url, Description:p.val.Description}};
    for (let a=1; a<=4; a++) {
      const r = await fetch(base+"/_api/web/lists(guid'"+oi.Id+"')/items("+p.Id+")",{method:"POST",
        headers:{Accept:"application/json;odata=nometadata",
                 "Content-Type":"application/json;odata=verbose",
                 "X-RequestDigest":dg.FormDigestValue,"X-HTTP-Method":"MERGE","IF-MATCH":"*"},
        body:JSON.stringify(body)});
      if (r.ok) { ok++; return; }
      const retryable = (r.status===409 || r.status===429 || r.status>=500);
      if (!retryable || a===4) {
        fail++;
        if (errs.length<8) errs.push(p.Title+": "+r.status+" "+(await r.text()).slice(0,200));
        return;
      }
      await sleep(250*Math.pow(2,a-1) + Math.random()*200);
    }
  };
  console.log("\nwriting " + plan.length + " ...");
  for (let i=0;i<plan.length;i+=CONC) {
    await Promise.all(plan.slice(i,i+CONC).map(patch));
    if (i % 200 === 0) console.log("  " + Math.min(i+CONC, plan.length) + "/" + plan.length);
  }
  console.log("written ok=" + ok + " failed=" + fail);
  for (const e of errs) console.error("  " + e);

  // ------------------------------------------------------------ verification
  const after = await page(base+"/_api/web/lists(guid'"+oi.Id+"')/items"
                           +"?$select=Id,Title,OrderNumberId,OrdOrderFolder&$top=500");
  const ids = new Set(plan.map(p=>p.Id));
  const mine = after.filter(r=>ids.has(r.Id));
  const bad  = mine.filter(r => !(r.OrdOrderFolder && (r.OrdOrderFolder.Url||r.OrdOrderFolder.url)));
  const wrong = mine.filter(r => {
    const u = r.OrdOrderFolder && (r.OrdOrderFolder.Url||r.OrdOrderFolder.url);
    const want = folder.get(r.OrderNumberId);
    return u && want && u !== want.Url;
  });
  console.log("\n--- verification (trust this, not the write results) ---");
  console.log("rows checked           : " + mine.length);
  console.log("still empty            : " + bad.length + "   (expect 0)");
  console.log("URL does not match Order: " + wrong.length + "   (expect 0)");
  for (const r of bad.slice(0,5))   console.error("  empty: " + r.Title);
  for (const r of wrong.slice(0,5)) console.error("  wrong: " + r.Title);
  const total = after.filter(r=>r.OrdOrderFolder && (r.OrdOrderFolder.Url||r.OrdOrderFolder.url)).length;
  console.log("list-wide units with a folder link: " + total);
})();

/* ---------------------------------------------------------------- UNDO ----
   Clears OrdOrderFolder on the ids listed. They were empty before this ran.

(async () => {
  const base="https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const MADE = [];   // <- paste the UNDO array here
  const J=async u=>(await fetch(u,{headers:{Accept:"application/json;odata=nometadata"}})).json();
  const oi=await J(base+"/_api/web/lists/getbytitle('Order Items')?$select=Id,ListItemEntityTypeFullName");
  const dg=await (await fetch(base+"/_api/contextinfo",{method:"POST",
                  headers:{Accept:"application/json;odata=nometadata"}})).json();
  let ok=0;
  for (const m of MADE) {
    const w=await fetch(base+"/_api/web/lists(guid'"+oi.Id+"')/items("+m.Id+")",{method:"POST",
      headers:{Accept:"application/json;odata=nometadata","Content-Type":"application/json;odata=verbose",
               "X-RequestDigest":dg.FormDigestValue,"X-HTTP-Method":"MERGE","IF-MATCH":"*"},
      body:JSON.stringify({__metadata:{type:oi.ListItemEntityTypeFullName}, OrdOrderFolder:null})});
    if (w.ok) ok++; else console.error(m.Title+" -> "+w.status);
  }
  console.log("cleared "+ok+" of "+MADE.length);
})();
---------------------------------------------------------------------------- */
