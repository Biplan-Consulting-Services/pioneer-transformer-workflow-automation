/* X2 -- reconciliation. Mark the 66 archived-and-delivered units as Delivered.

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
        (if Chrome refuses the paste, type  allow pasting  first)
     3. DRY RUN by default. Read the summary, then set APPLY = true and paste again.
     4. It prints an UNDO block (every previous value) and re-reads to verify.

   WHY THESE 66
     The rule is the user's own, given 2026-09-08: a unit is delivered when
     Location is LI and a delivery date is entered.

     104 units sit in Order Items but no longer exist in FRM10-12's live
     TableOrders. In Archive active's TableArchiveFRM10_12 all 104 have
     Location = LI AND a Delivery Date -- so all 104 are genuinely delivered.
     36 already read Item Status = Delivered. These 66 are the rest.
     (68 were candidates; 2 are held back -- see EXCLUDED below.)

     ⚠️ Archive presence alone proves NOTHING -- the archive is a backup and
     holds every order ever, including all 1,019 currently-live units. What
     identifies these 104 is being ABSENT from the live workbook while the
     archive records them at LI with a delivery date.

   WHY Location IS ALSO REWRITTEN
     These 66 carry a STALE Location in the list -- Extérieur 24, Finition 14,
     blank 11, Test 9, Tanking 8, Four 2 -- frozen at whatever it was when the
     unit was archived out of the workbook. The archive says LI for all of them.
     Leaving the stale value would also make X1 wrongly clear their delivery,
     since X1 keys on Location. So this sets Location = Livraison too, and X2
     MUST run before X1.

   EXCLUDED, deliberately -- 2 units for a human
     21792-3/5 and 21792-4/5. Location LI, but the archive delivery date is
     2026-09-24, in the FUTURE. Delivered on a future date is the same
     contradiction X1 uses as its hard test, so applying the rule literally here
     would be inconsistent. Decide these two by hand.

   FLAGGED, but included -- 9 units
     21803-4/8, 22021-1/20, 22021-5/20, 22021-6/20, 22021-7/20, 22021-8/20,
     22021-9/20, 22021-10/20, 22021-12/20 still read archive Status = EC
     (En Cours) even though they are at LI with a delivery date. They meet the
     stated rule so they are included -- but the status disagrees, so check them.
     🔑 Those eight 22021 units are EXACTLY the eight R15 lists as "genuinely
     unexplained". They are delivered and archived. R15's mystery is closed.
*/

(async () => {
  const APPLY = false;                     // <-- set true to actually write
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI    = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";   // Order Items

  // unit -> archive Delivery Date (the ACTUAL ship date, from the archive)
  const PAY = [
    ["21387-3/6","2026-08-31"],["21407-2/3","2026-08-24"],["21408-1/1","2026-08-31"],
    ["21408-1/1 SA","2026-08-31"],["21776-1/1","2026-08-31"],["21786-13/14","2026-08-19"],
    ["21787-5/5","2026-08-19"],["21792-1/5","2026-09-02"],["21792-2/5","2026-09-02"],
    ["21803-2/8","2026-08-31"],["21803-3/8","2026-08-31"],["21803-4/8","2026-08-31"],
    ["21813-1/1","2026-08-28"],["21838-1/5","2026-08-31"],["21838-2/5","2026-08-31"],
    ["21838-3/5","2026-08-28"],["21838-4/5","2026-08-31"],["21838-5/5","2026-08-28"],
    ["21839-6/10","2026-08-31"],["21839-7/10","2026-08-28"],["21839-8/10","2026-08-31"],
    ["21839-9/10","2026-08-28"],["21839-10/10","2026-08-31"],["21840-1/10","2026-08-28"],
    ["21840-2/10","2026-08-28"],["21840-3/10","2026-08-28"],["21840-4/10","2026-08-31"],
    ["21840-5/10","2026-08-31"],["21840-6/10","2026-08-31"],["21840-7/10","2026-08-28"],
    ["21840-8/10","2026-08-31"],["21840-9/10","2026-08-31"],["21844-1/1","2026-08-31"],
    ["21845-1/1","2026-08-31"],["21846-1/1","2026-08-31"],["21850-1/2","2026-08-28"],
    ["21850-2/2","2026-08-28"],["21941-1/3","2026-08-19"],["21941-2/3","2026-08-19"],
    ["21945-1/2","2026-08-31"],["21945-2/2","2026-08-31"],["21952-1/1","2026-08-31"],
    ["21965-1/4","2026-08-25"],["21965-2/4","2026-08-25"],["21965-3/4","2026-08-31"],
    ["21966-1/3","2026-08-19"],["21968-1/4","2026-08-19"],["21968-2/4","2026-08-19"],
    ["22021-1/20","2026-07-16"],["22021-5/20","2026-07-16"],["22021-6/20","2026-07-16"],
    ["22021-7/20","2026-07-16"],["22021-8/20","2026-07-16"],["22021-9/20","2026-07-16"],
    ["22021-10/20","2026-07-16"],["22021-12/20","2026-07-16"],["22021-14/20","2026-08-18"],
    ["22032-1/20","2026-08-18"],["22032-2/20","2026-08-18"],["22032-3/20","2026-08-18"],
    ["22032-5/20","2026-08-18"],["22032-6/20","2026-08-18"],["22032-20/20","2026-08-31"],
    ["E21010-1/2","2026-08-27"],["E21010-2/2","2026-08-27"],["E21014-1/1","2026-08-31"]
  ];

  const J = async (u) => (await fetch(u,{headers:{Accept:"application/json;odata=nometadata"}})).json();
  let url = base + "/_api/web/lists(guid'" + OI +
    "')/items?$select=Id,Title,ItemStatus,Location,DeliveryStatus,DeliveryEndDate&$top=500";
  let rows = [], g = 0;
  while (url && g++ < 10) { const j = await J(url); rows = rows.concat(j.value||[]); url = j["odata.nextLink"]||null; }
  const byT = {}; for (const r of rows) byT[r.Title] = r;

  const plan = [], missing = [];
  for (const [t,d] of PAY) {
    const r = byT[t];
    if (!r) { missing.push(t); continue; }
    plan.push({Id:r.Id, Title:t, to:d, from:{ItemStatus:r.ItemStatus, Location:r.Location,
      DeliveryStatus:r.DeliveryStatus, DeliveryEndDate:r.DeliveryEndDate}});
  }
  console.log("rows in list: " + rows.length + " | to change: " + plan.length +
              (missing.length ? " | TITLE NOT FOUND: " + JSON.stringify(missing) : ""));
  const byStatus = {};
  for (const p of plan) byStatus[p.from.ItemStatus||"(blank)"] = (byStatus[p.from.ItemStatus||"(blank)"]||0)+1;
  console.log("current Item Status of those rows: " + JSON.stringify(byStatus) +
              "   (all should be Active)");
  console.log("sample: " + plan.slice(0,3).map(p =>
    p.Title+" ["+p.from.ItemStatus+"/"+p.from.Location+"] -> Delivered/Livraison, end "+p.to).join(" | "));

  if (!APPLY) {
    console.log("\nDRY RUN -- nothing written. Set APPLY = true and paste again.");
    console.log("UNDO block would be printed after the write.");
    return;
  }

  // print UNDO FIRST, so it survives even if the run is interrupted
  console.log("\n=== UNDO (previous values -- keep this) ===");
  console.log(JSON.stringify(plan.map(p => Object.assign({Id:p.Id,Title:p.Title}, p.from))));

  const dg = await (await fetch(base+"/_api/contextinfo",{method:"POST",
                    headers:{Accept:"application/json;odata=nometadata"}})).json();
  const et = (await J(base+"/_api/web/lists(guid'"+OI+"')?$select=ListItemEntityTypeFullName"))
               .ListItemEntityTypeFullName;
  let ok=0, fail=0; const errs=[];
  for (const p of plan) {
    const body = {__metadata:{type:et}, ItemStatus:"Delivered", Location:"Livraison",
                  DeliveryStatus:"Completed", DeliveryEndDate:p.to};
    const w = await fetch(base+"/_api/web/lists(guid'"+OI+"')/items("+p.Id+")",{method:"POST",
      headers:{Accept:"application/json;odata=nometadata","Content-Type":"application/json;odata=verbose",
               "X-RequestDigest":dg.FormDigestValue,"X-HTTP-Method":"MERGE","IF-MATCH":"*"},
      body:JSON.stringify(body)});
    if (w.ok) ok++; else { fail++; if (errs.length<5) errs.push(p.Title+": "+w.status+" "+(await w.text()).slice(0,140)); }
  }
  console.log("\nwritten ok=" + ok + " failed=" + fail);
  for (const e of errs) console.error("  " + e);

  // ---------------------------------------------------------- verification
  const ids = new Set(plan.map(p=>p.Id));
  let u2 = base+"/_api/web/lists(guid'"+OI+"')/items?$select=Id,Title,ItemStatus,Location,DeliveryStatus,DeliveryEndDate&$top=500";
  let after=[], g2=0;
  while (u2 && g2++<10) { const j=await J(u2); after=after.concat(j.value||[]); u2=j["odata.nextLink"]||null; }
  const mine = after.filter(r=>ids.has(r.Id));
  const bad = mine.filter(r => r.ItemStatus!=="Delivered" || r.Location!=="Livraison" ||
                               r.DeliveryStatus!=="Completed" || !r.DeliveryEndDate);
  console.log("\n--- verification (trust this, not the write results) ---");
  console.log("rows checked: " + mine.length + " | not fully updated: " + bad.length + "  (expect 0)");
  for (const r of bad.slice(0,5)) console.error("  " + JSON.stringify(r));
  const totals = {};
  for (const r of after) totals[r.ItemStatus||"(blank)"] = (totals[r.ItemStatus||"(blank)"]||0)+1;
  console.log("list-wide Item Status now: " + JSON.stringify(totals) +
              "   (Delivered should be 36 + " + ok + ")");
})();

/* ---------------------------------------------------------------- UNDO ----
   Paste the UNDO array printed above in place of [] below and run.

(async () => {
  const base="https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI="d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const PREV = [];   // <- paste the UNDO array here
  const J=async u=>(await fetch(u,{headers:{Accept:"application/json;odata=nometadata"}})).json();
  const dg=await (await fetch(base+"/_api/contextinfo",{method:"POST",
                  headers:{Accept:"application/json;odata=nometadata"}})).json();
  const et=(await J(base+"/_api/web/lists(guid'"+OI+"')?$select=ListItemEntityTypeFullName"))
             .ListItemEntityTypeFullName;
  for (const p of PREV) {
    const body={__metadata:{type:et}, ItemStatus:p.ItemStatus, Location:p.Location,
                DeliveryStatus:p.DeliveryStatus, DeliveryEndDate:p.DeliveryEndDate};
    const w=await fetch(base+"/_api/web/lists(guid'"+OI+"')/items("+p.Id+")",{method:"POST",
      headers:{Accept:"application/json;odata=nometadata","Content-Type":"application/json;odata=verbose",
               "X-RequestDigest":dg.FormDigestValue,"X-HTTP-Method":"MERGE","IF-MATCH":"*"},
      body:JSON.stringify(body)});
    console.log(p.Title+" -> "+w.status);
  }
})();
---------------------------------------------------------------------------- */
