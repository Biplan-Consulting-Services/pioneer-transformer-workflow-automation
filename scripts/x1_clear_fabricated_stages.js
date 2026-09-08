/* X1 -- clear the fabricated Tanking / Delivery completions.

   🔴 RUN scripts/x2_set_delivered.js FIRST. X1 keys on Location, and X2 is what
      corrects the stale Location on the 104 archived units. Run X1 first and it
      will wrongly clear the delivery of 68 genuinely-shipped units. The script
      refuses to apply if it detects X2 has not run.

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
        (if Chrome refuses the paste, type  allow pasting  first)
     3. DRY RUN by default. Read the tier counts, then set APPLY = true.

   THE RULE -- the user's own, 2026-09-08
     Delivery is real  <=>  Location = Livraison AND a delivery date is entered.
     Tanking  is real  <=>  the unit is PAST the tanking stage.

     Production sequence, from the flow's own MappedLocation table:
       Isolation -> Bobinage -> Stacking -> Assemblage -> Four -> Tanking
                 -> Test -> Finition -> Livraison
     so "past tanking" = Test, Finition, Livraison.

   NO UNIT LIST IS EMBEDDED, on purpose. The rule is a pure function of
   Location, so the script derives the whole population from the live list. That
   means it cannot drift out of date against a stale hard-coded array, and it
   stays correct if someone edits a Location between now and when you run it.

   WHY THESE VALUES ARE FABRICATED -- three independent proofs, not one
     1. Tanking End Date is a byte-for-byte copy of Planned Tanking Date on
        921 of 975 rows; Delivery End Date copies Planned Delivery Date on
        337 of 400.
     2. 811 of 975 "completed" Tanking dates and 287 of 400 Delivery dates are
        in the FUTURE. A completed stage cannot complete in the future.
     3. Delivery = Completed appears with Location = Bobinage (29), Tanking (23),
        Four (14), Assemblage (11) -- delivered while still in the winding shop.
     Neither stage is mapped by the transfer flow at all, so nothing maintains
     these columns; they are residue from an old mapping (R14).

   WHAT IT WRITES
     {Stage} Status  -> null
     {Stage} End Date -> null
     Nothing else. Item Status is X2's business, not X1's.

   ⚠️ CLEARED TO BLANK, NOT TO "Pending"
     Blank is load-bearing. R10 records that the trigger flow's stage-stamping
     wrote Pending into stages the backfill deliberately left blank and thereby
     "destroyed the very marker the Tanking/Delivery cleanup depends on". Writing
     Pending here would repeat that. Blank is the correct empty state.
     (Raw REST null DOES clear a field -- verified 2026-09-08. It is the Power
     Automate connector that leaves the old value, which is why 844 stale
     Pending statuses survived the run.)

   HELD BACK FOR A HUMAN -- 52 rows, one question
     Every REVIEW row is Location = Extérieur (31 tanking + 21 delivery).
     Extérieur is not in the production sequence -- a unit could be outside
     waiting for its tank to be fabricated by a supplier (BEFORE tanking, per
     FRM11) or finished and stored outside (AFTER). One answer settles all 52.
     Until then they are left exactly as they are.
*/

(async () => {
  const APPLY = false;                    // <-- set true to actually write
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI    = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";   // Order Items
  const CONC  = 8;

  const PAST_TANK   = new Set(["Test","Finition","Livraison"]);
  const AT_OR_BEFORE= new Set(["","Isolation","Bobinage","Stacking","Assemblage","Four","Tanking"]);
  const OFF_SEQ     = new Set(["Extérieur","Entrepôt","Réparation"]);

  const J = async (u) => (await fetch(u,{headers:{Accept:"application/json;odata=nometadata"}})).json();
  let url = base + "/_api/web/lists(guid'" + OI + "')/items?$select=Id,Title,ItemStatus,Location," +
            "TankingStatus,TankingEndDate,DeliveryStatus,DeliveryEndDate&$top=500";
  let rows = [], g = 0;
  while (url && g++ < 10) { const j = await J(url); rows = rows.concat(j.value||[]); url = j["odata.nextLink"]||null; }
  console.log("rows read: " + rows.length);

  // ---- guard: has X2 run? it should leave 104 units at Livraison / Delivered
  const livr = rows.filter(r => r.Location === "Livraison").length;
  const deliv = rows.filter(r => r.ItemStatus === "Delivered").length;
  console.log("Location=Livraison: " + livr + " | Item Status=Delivered: " + deliv);
  if (livr < 100 || deliv < 100) {
    console.error("\n*** X2 HAS NOT RUN ***");
    console.error("Expected ~104 units at Livraison / Delivered; found " + livr + " / " + deliv + ".");
    console.error("Run scripts/x2_set_delivered.js first, or X1 will clear the delivery of");
    console.error("68 genuinely-shipped units whose Location is still stale. Stopping.");
    return;
  }

  const work = [], review = [], keep = [];
  for (const r of rows) {
    const loc = (r.Location || "").trim();
    // Tanking
    if ((r.TankingStatus || "") !== "" || r.TankingEndDate) {
      if (PAST_TANK.has(loc))           keep.push([r.Title,"Tanking","past tanking"]);
      else if (OFF_SEQ.has(loc))        review.push([r.Title,"Tanking",loc]);
      else if (AT_OR_BEFORE.has(loc))   work.push({Id:r.Id,Title:r.Title,stage:"Tanking",
                                            from:{s:r.TankingStatus,e:r.TankingEndDate}});
      else                              review.push([r.Title,"Tanking","unknown location "+loc]);
    }
    // Delivery
    if ((r.DeliveryStatus || "") !== "" || r.DeliveryEndDate) {
      if (loc === "Livraison" && r.DeliveryEndDate) keep.push([r.Title,"Delivery","LI + date"]);
      else if (OFF_SEQ.has(loc))                    review.push([r.Title,"Delivery",loc]);
      else                                          work.push({Id:r.Id,Title:r.Title,stage:"Delivery",
                                                        from:{s:r.DeliveryStatus,e:r.DeliveryEndDate}});
    }
  }
  const cnt = (st) => work.filter(w=>w.stage===st).length;
  console.log("\n=== tiers ===");
  console.log("  CLEAR  Tanking : " + cnt("Tanking"));
  console.log("  CLEAR  Delivery: " + cnt("Delivery"));
  console.log("  KEEP           : " + keep.length);
  console.log("  REVIEW (left as-is): " + review.length +
              "  by location: " + JSON.stringify(review.reduce((m,r)=>{m[r[2]]=(m[r[2]]||0)+1;return m;},{})));
  console.log("  sample to clear: " + work.slice(0,3).map(w=>w.Title+"/"+w.stage+" was ["+w.from.s+","+String(w.from.e).slice(0,10)+"]").join(" | "));

  if (!APPLY) { console.log("\nDRY RUN -- nothing written. Set APPLY = true and paste again."); return; }

  console.log("\n=== UNDO (previous values -- keep this) ===");
  console.log(JSON.stringify(work.map(w=>({Id:w.Id,Title:w.Title,stage:w.stage,s:w.from.s,e:w.from.e}))));

  const dg = await (await fetch(base+"/_api/contextinfo",{method:"POST",
                    headers:{Accept:"application/json;odata=nometadata"}})).json();
  const et = (await J(base+"/_api/web/lists(guid'"+OI+"')?$select=ListItemEntityTypeFullName"))
               .ListItemEntityTypeFullName;
  let ok=0, fail=0; const errs=[];
  const patch = async (w) => {
    const body = {__metadata:{type:et}};
    body[w.stage+"Status"]  = null;
    body[w.stage+"EndDate"] = null;
    const r = await fetch(base+"/_api/web/lists(guid'"+OI+"')/items("+w.Id+")",{method:"POST",
      headers:{Accept:"application/json;odata=nometadata","Content-Type":"application/json;odata=verbose",
               "X-RequestDigest":dg.FormDigestValue,"X-HTTP-Method":"MERGE","IF-MATCH":"*"},
      body:JSON.stringify(body)});
    if (r.ok) ok++; else { fail++; if (errs.length<5) errs.push(w.Title+"/"+w.stage+": "+r.status+" "+(await r.text()).slice(0,140)); }
  };
  console.log("\nwriting " + work.length + " stage-clears ...");
  for (let i=0;i<work.length;i+=CONC) {
    await Promise.all(work.slice(i,i+CONC).map(patch));
    if (i % 200 === 0) console.log("  " + Math.min(i+CONC, work.length) + "/" + work.length);
  }
  console.log("written ok=" + ok + " failed=" + fail);
  for (const e of errs) console.error("  " + e);

  // ---------------------------------------------------------- verification
  let u2 = base+"/_api/web/lists(guid'"+OI+"')/items?$select=Id,Location,TankingStatus,TankingEndDate,DeliveryStatus,DeliveryEndDate&$top=500";
  let after=[], g2=0;
  while (u2 && g2++<10) { const j=await J(u2); after=after.concat(j.value||[]); u2=j["odata.nextLink"]||null; }
  const stillBad = after.filter(r => {
    const loc=(r.Location||"").trim();
    const tBad = ((r.TankingStatus||"")!=="" || r.TankingEndDate) && AT_OR_BEFORE.has(loc);
    const dBad = ((r.DeliveryStatus||"")!=="" || r.DeliveryEndDate) && !(loc==="Livraison" && r.DeliveryEndDate) && !OFF_SEQ.has(loc);
    return tBad || dBad;
  });
  const tank = after.filter(r=>(r.TankingStatus||"")!=="").length;
  const dely = after.filter(r=>(r.DeliveryStatus||"")!=="").length;
  console.log("\n--- verification (trust this, not the write results) ---");
  console.log("rows still violating the rule: " + stillBad.length + "   (expect 0)");
  console.log("Tanking Status populated : " + tank + "   (was 975; expect ~141 = 110 keep + 31 review)");
  console.log("Delivery Status populated: " + dely + "   (was 400; expect ~114 = 93 keep + 21 review)");
})();
