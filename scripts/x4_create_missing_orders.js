/* X4 -- create the two Order rows that keep their units out of Order Items.

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
        (if Chrome refuses the paste, type  allow pasting  first)
     3. DRY RUN by default. Read the resolved payloads, then set APPLY = true
        and paste again.
     4. It prints an UNDO block (the new item Ids) and re-reads to verify.

   WHY THESE TWO
     The transfer flow's CheckOrderMatch is  length(Get_Orders) == 1  -- exactly
     one, not "at least one". When it is false the flow skips the WHOLE row: no
     write, no log, no count. Six units failed it, at both ends of the condition:

       0 matches : 20877R1-1/1, P1_001-1/1, P20001-1/1, P20002-1/1
       2 matches : P20004-1/2, P20004-2/2   (the duplicate Order, since deleted)

     Four have since resolved on their own -- P1_001 and P20001 got Order rows,
     and deleting Order 487 took P20004 from 2 matches to 1. In each case the
     Power App fan-out then created the unit. These two are the remainder, both
     still at 0 matches:

       20877R1  -- no Order row, and none under plain "20877" either
       P20002   -- no Order row

     Both units exist ONLY in FRM10-12. Once the workbook is frozen and Order
     Items becomes the reference they stop existing, silently. Creating the
     Orders lets Thursday's run create the units, and the re-diff comes out at 0
     instead of 2.

   WHERE THE VALUES COME FROM
     Straight off the units' own rows in the workbook's TableOrders
     (FRM10-12 2026-09-09, sheet rows 980 and 998). Three are inferred and are
     marked INFERRED below -- none of them affects whether the run picks the
     units up, only what lands in the 18 parent-sync columns.

   INTERNAL NAMES ARE RESOLVED AT RUNTIME, NEVER TYPED
     This repo has been bitten twice by a retyped internal name -- a wrong one
     does not error, it silently writes nothing (R22, Planned Delivery Date). So
     the payloads below are keyed by DISPLAY name and translated against the
     live column list. Anything that fails to resolve is reported and the script
     refuses to write.
     ⚠️ Read via  _api/v2.0/sites/root/lists/<id>/columns . The "sites/root"
     segment is required, and _api/web/lists/.../fields HANGS on this tenant.

   DATES ARE PRE-CONVERTED TO UTC
     The site runs Eastern and stores midnight local. DST 2026 runs Mar 8 to
     Nov 1, so Jan 1 is EST (05:00Z) and everything else here is EDT (04:00Z).
     Sent as explicit UTC so the browser's own timezone cannot shift them.
*/

(async () => {
  const APPLY = false;                     // <-- set true to actually write
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";

  // Keyed by DISPLAY name. Translated to internal names below.
  const ORDERS = [
    { "Order Number": "20877R1",
      "_client":      "BEAVER ELECTRICAL",          // lookup, resolved by name
      "Qty":                    1,
      "Order Date":             "2026-04-27T04:00:00Z",
      "Initial Promised Date":  "2026-07-30T04:00:00Z",
      "Ing. Due Date":          "2026-01-01T05:00:00Z",   // EST, not EDT
      "Lead Time":              26,
      "SA":                     false,
      "Order Type":             "Standard",          // INFERRED: workbook Type is
                                                     // SUBSTATION, a product type.
                                                     // Standard is 418 of 447.
      "Order Status":           "Active"             // INFERRED: unit is live
    },
    { "Order Number": "P20002",
      "_client":      "CONED",
      "PO":                     "ERMCO",
      "Qty":                    1,
      "Province/State":         "QC",
      "Indexing":               "N",
      "Order Date":             "2025-08-11T04:00:00Z",
      "Initial Promised Date":  "2026-09-30T04:00:00Z",
      "Ing. Due Date":          "2026-03-18T04:00:00Z",
      "Lead Time":              24,
      "Engineering Required":   true,
      "SA":                     false,
      "Order Type":             "R&D",               // INFERRED: workbook says
                                                     // "Prototype"; siblings
                                                     // P20001/P20004 are R&D
      "Order Status":           "Active"             // INFERRED
    }
  ];

  const J = async u => (await fetch(u, {headers:{Accept:"application/json;odata=nometadata"}})).json();

  // ------------------------------------------------------------- resolve lists
  const ord = await J(base+"/_api/web/lists/getbytitle('Order')?$select=Id,ListItemEntityTypeFullName");
  if (!ord.Id) { console.error("could not resolve the Order list"); return; }
  const OID = ord.Id, ET = ord.ListItemEntityTypeFullName;
  console.log("Order list " + OID + "  (" + ET + ")");

  const cl = await J(base+"/_api/web/lists/getbytitle('Clients')?$select=Id");
  if (!cl.Id) { console.error("could not resolve the Clients list"); return; }

  // ------------------------------------------------- display name -> internal
  const cols = await (await fetch(base+"/_api/v2.0/sites/root/lists/"+OID+"/columns",
                      {headers:{Accept:"application/json"}})).json();
  const map = {};
  for (const c of (cols.value||[])) map[(c.displayName||"").trim()] = c.name;
  console.log("resolved " + Object.keys(map).length + " columns on Order");

  // ------------------------------------------------------- resolve the clients
  let cu = base+"/_api/web/lists(guid'"+cl.Id+"')/items?$top=500", clients=[], g=0;
  while (cu && g++ < 10) { const j = await J(cu); clients = clients.concat(j.value||[]); cu = j["odata.nextLink"]||null; }
  console.log("Clients list rows: " + clients.length);
  const findClient = name => {
    const want = name.trim().toUpperCase();
    // match on ANY field -- the name lives in a column whose internal name is
    // not assumed here (the export shows Client_ID and Client)
    const hits = clients.filter(r => Object.values(r).some(v =>
      typeof v === "string" && v.trim().toUpperCase() === want));
    return hits;
  };

  // the lookup's internal name, plus the "Id" suffix REST wants for writes
  const clientField = map["Client"];
  if (!clientField) { console.error("no 'Client' column on Order -- aborting"); return; }

  // ------------------------------------------------- refuse to duplicate
  const numField = map["Order Number"];
  if (!numField) { console.error("no 'Order Number' column on Order -- aborting"); return; }
  let ou = base+"/_api/web/lists(guid'"+OID+"')/items?$select=Id,"+numField+"&$top=500";
  let existing=[], g2=0;
  while (ou && g2++ < 10) { const j = await J(ou); existing = existing.concat(j.value||[]); ou = j["odata.nextLink"]||null; }
  console.log("existing Order rows: " + existing.length);

  // ------------------------------------------------------------- build payloads
  const plan = [], problems = [];
  for (const src of ORDERS) {
    const num = src["Order Number"];
    const clash = existing.filter(r => (r[numField]||"").trim() === num);
    if (clash.length) {
      problems.push(num + ": already exists (Id " + clash.map(r=>r.Id).join(",") + ") -- will not duplicate");
      continue;
    }
    const hits = findClient(src._client);
    if (hits.length !== 1) {
      problems.push(num + ": client " + JSON.stringify(src._client) + " matched " +
                    hits.length + " rows in Clients -- need exactly 1");
      continue;
    }
    const body = { __metadata: { type: ET } };
    body[clientField + "Id"] = hits[0].Id;
    for (const [disp, val] of Object.entries(src)) {
      if (disp === "_client") continue;
      const internal = map[disp];
      if (!internal) { problems.push(num + ": no column named " + JSON.stringify(disp)); continue; }
      body[internal] = val;
    }
    plan.push({ num, body, clientRow: hits[0] });
  }

  console.log("\n=== resolved payloads ===");
  for (const p of plan) {
    console.log("\n" + p.num + "   client -> Clients Id " + p.clientRow.Id +
                " " + JSON.stringify(Object.values(p.clientRow).filter(v =>
                  typeof v === "string" && v.trim()).slice(0,2)));
    console.log(JSON.stringify(p.body, null, 2));
  }
  if (problems.length) {
    console.log("\n=== PROBLEMS ===");
    for (const p of problems) console.error("  " + p);
  }
  console.log("\nwould create: " + plan.length + "   problems: " + problems.length);

  if (problems.length) { console.error("\nrefusing to write while anything is unresolved."); return; }
  if (!plan.length)    { console.log("\nnothing to do."); return; }
  if (!APPLY) { console.log("\nDRY RUN -- nothing written. Set APPLY = true and paste again."); return; }

  // ------------------------------------------------------------------- write
  const dg = await (await fetch(base+"/_api/contextinfo",{method:"POST",
                    headers:{Accept:"application/json;odata=nometadata"}})).json();
  const made = [];
  for (const p of plan) {
    const w = await fetch(base+"/_api/web/lists(guid'"+OID+"')/items",{method:"POST",
      headers:{Accept:"application/json;odata=nometadata",
               "Content-Type":"application/json;odata=verbose",
               "X-RequestDigest":dg.FormDigestValue},
      body: JSON.stringify(p.body)});
    if (w.ok) { const j = await w.json(); made.push({num:p.num, Id:j.Id}); console.log("created " + p.num + " -> Id " + j.Id); }
    else      { console.error("FAILED " + p.num + ": " + w.status + " " + (await w.text()).slice(0,300)); }
  }

  console.log("\n=== UNDO (delete these Ids -- keep this) ===");
  console.log(JSON.stringify(made));

  // ------------------------------------------------------------ verification
  let vu = base+"/_api/web/lists(guid'"+OID+"')/items?$select=Id,"+numField+","+clientField+"Id&$top=500";
  let after=[], g3=0;
  while (vu && g3++ < 10) { const j = await J(vu); after = after.concat(j.value||[]); vu = j["odata.nextLink"]||null; }
  console.log("\n--- verification (trust this, not the write results) ---");
  console.log("Order rows now: " + after.length + "   (expect " + (existing.length + made.length) + ")");
  for (const src of ORDERS) {
    const n = after.filter(r => (r[numField]||"").trim() === src["Order Number"]).length;
    console.log("  " + src["Order Number"] + " -> " + n + " row(s)   " +
                (n === 1 ? "OK, CheckOrderMatch will pass" : "PROBLEM -- must be exactly 1"));
  }
})();

/* ---------------------------------------------------------------- UNDO ----
   Paste the UNDO array printed above in place of [] below and run.

(async () => {
  const base="https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const MADE = [];   // <- paste the UNDO array here
  const J=async u=>(await fetch(u,{headers:{Accept:"application/json;odata=nometadata"}})).json();
  const ord=await J(base+"/_api/web/lists/getbytitle('Order')?$select=Id");
  const dg=await (await fetch(base+"/_api/contextinfo",{method:"POST",
                  headers:{Accept:"application/json;odata=nometadata"}})).json();
  for (const m of MADE) {
    const w=await fetch(base+"/_api/web/lists(guid'"+ord.Id+"')/items("+m.Id+")",{method:"POST",
      headers:{Accept:"application/json;odata=nometadata",
               "X-RequestDigest":dg.FormDigestValue,"X-HTTP-Method":"DELETE","IF-MATCH":"*"}});
    console.log(m.num+" (Id "+m.Id+") -> "+w.status);
  }
})();
---------------------------------------------------------------------------- */
