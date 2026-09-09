/* X1 -- clear the fabricated Tanking / Delivery completions.

   🔴 RUN scripts/x2_set_delivered.js FIRST. X1 keys on Location, and X2 is what
      corrects the stale Location on the 104 archived units. Run X1 first and it
      will wrongly clear the delivery of 68 genuinely-shipped units. The script
      refuses to apply if it detects X2 has not run.

      ⚠️ THE EXTÉRIEUR RULING MADE THIS ORDER MORE LOAD-BEARING, NOT LESS.
      24 of X2's 66 units still read Location = Extérieur (X2's own breakdown:
      Extérieur 24, Finition 14, blank 11, Test 9, Tanking 8, Four 2). Under the
      OLD code Extérieur was REVIEW, so running X1 first would merely have left
      those 24 alone -- wrong, but harmless. Now Extérieur delivery CLEARS, so
      running X1 first would actively wipe the delivery of 24 units the archive
      proves were shipped. Do not skip the guard, and do not run these two out
      of order.

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
     so "past tanking" = Test, Finition, Livraison, and -- per the ruling below --
     Extérieur.

   EXTÉRIEUR -- ruled 2026-09-08, in the user's words:
     "it's completed and waiting outside to be shipped"

     That single answer resolves the two stages in OPPOSITE directions, which is
     why it was worth asking rather than guessing:
       Tanking  -> production is COMPLETE, so the unit is PAST tanking  => KEEP
       Delivery -> it is still WAITING to be shipped, so delivery is not
                   complete and its "Completed" is fabricated like the rest
                                                                        => CLEAR
     Guessing either way would have been wrong on one of the two stages.

     🔑 FRM11's own M code INDEPENDENTLY AGREES on the tanking half. Its
     "Rows to purge" query -- power-query/FRM11/Rows to purge.pq, live
     production code, written by nobody in this project -- computes:

       "Already Tanked" = List.Contains({"XT","TE","FI","LI"}, [Location.1])
                          or ([Location.1] = "TA" and Text.Contains([Status.1],"TE"))

     XT is Extérieur, and it sits in that set beside TE/FI/LI -- the exact
     past-tanking set this script keeps. FRM11 stops tracking a tank once the
     unit reaches XT because the tank is already on it. So the ruling is not
     just the user's word: the tank-tracking workbook has encoded it all along.
     (And it rules out the opposite reading I had considered -- a unit parked
     outside WAITING for a supplier's tank -- which would have put XT before
     tanking, not after.)

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

   NOTHING IS HELD BACK ANY MORE
     The 52 rows this script used to leave for a human were all Location =
     Extérieur, and the ruling above resolves every one of them -- 31 tanking to
     KEEP, 21 delivery to CLEAR. REVIEW is expected to print 0.
     Entrepôt and Réparation stay wired as REVIEW on purpose: no row carries
     either location today, but if one appears later it is genuinely off-sequence
     and this script must not guess at it.
*/

(async () => {
  // ⚠️ INTERNAL NAMES, resolved from the live list 2026-09-09 -- do not "correct" these.
  // Every stage's END date is internally  <Stage>Date , NOT <Stage>EndDate: the columns
  // were created as "Coiling Date"/"Tanking Date"/... and renamed to "... End Date" when
  // the Start Dates were added, and a SharePoint rename does not change the internal
  // name. The Start Dates, created later, really are <Stage>StartDate.
  //   Tanking End Date  -> TankingDate        Delivery End Date -> DeliveryDate
  // This script previously used TankingEndDate/DeliveryEndDate; the read 400'd with
  // "The field or property 'DeliveryEndDate' does not exist." and, because the paging
  // loop did  j.value||[] , that surfaced as "rows in list: 0" and 66 phantom missing
  // titles rather than an error.

  const APPLY = false;                   // <-- set true to actually write
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI    = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";   // Order Items
  // 4, not 8. Even with one write per item, ~1,100 MERGEs in a burst draws
  // throttling (the 500s seen on ids 171/195/200/204/208). Retries cover the rest.
  const CONC  = 4;

  // Extérieur = finished goods waiting outside to ship (user, 2026-09-08):
  //   past tanking  -> in PAST_TANK, so its Tanking is KEPT
  //   not shipped   -> NOT in OFF_SEQ, so its Delivery falls through and is CLEARED
  const PAST_TANK   = new Set(["Test","Finition","Livraison","Extérieur"]);
  const AT_OR_BEFORE= new Set(["","Isolation","Bobinage","Stacking","Assemblage","Four","Tanking"]);
  const OFF_SEQ     = new Set(["Entrepôt","Réparation"]);

  const J = async (u) => (await fetch(u,{headers:{Accept:"application/json;odata=nometadata"}})).json();
  let url = base + "/_api/web/lists(guid'" + OI + "')/items?$select=Id,Title,ItemStatus,Location," +
            "TankingStatus,TankingDate,DeliveryStatus,DeliveryDate&$top=500";
  let rows = [], g = 0;
  while (url && g++ < 10) { const j = await J(url); rows = rows.concat(j.value||[]); url = j["odata.nextLink"]||null; }

  if (rows.length === 0) {
    console.error("ABORT: the list read returned 0 rows. That is a broken query, not an "
                + "empty list -- check the $select field names against the live column "
                + "list. Refusing to continue.");
    return;
  }
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
    if ((r.TankingStatus || "") !== "" || r.TankingDate) {
      if (PAST_TANK.has(loc))           keep.push([r.Title,"Tanking","past tanking"]);
      else if (OFF_SEQ.has(loc))        review.push([r.Title,"Tanking",loc]);
      else if (AT_OR_BEFORE.has(loc))   work.push({Id:r.Id,Title:r.Title,stage:"Tanking",
                                            from:{s:r.TankingStatus,e:r.TankingDate}});
      else                              review.push([r.Title,"Tanking","unknown location "+loc]);
    }
    // Delivery
    if ((r.DeliveryStatus || "") !== "" || r.DeliveryDate) {
      if (loc === "Livraison" && r.DeliveryDate) keep.push([r.Title,"Delivery","LI + date"]);
      else if (OFF_SEQ.has(loc))                    review.push([r.Title,"Delivery",loc]);
      else                                          work.push({Id:r.Id,Title:r.Title,stage:"Delivery",
                                                        from:{s:r.DeliveryStatus,e:r.DeliveryDate}});
    }
  }
  // ---- assertion: no genuinely-shipped unit may lose its delivery ----------
  // This is the whole reason X2 runs first, and until now it was only ever argued,
  // never checked. A Delivered unit appearing in the CLEAR set means either X2 left a
  // stale Location behind or the keep rule has drifted -- both silent, both destructive
  // across ~100 real shipments. Cheap to assert, so assert it.
  const deliveredIds = new Set(rows.filter(r => r.ItemStatus === "Delivered").map(r => r.Id));
  const clash = work.filter(w => w.stage === "Delivery" && deliveredIds.has(w.Id));
  console.log("\nDelivered units in the CLEAR set: " + clash.length + "   (expect 0)");
  if (clash.length) {
    console.error("*** STOPPING -- these are Delivered and would lose their delivery: ***");
    for (const c of clash.slice(0, 20)) console.error("    " + c.Title);
    return;
  }

  const cnt = (st) => work.filter(w=>w.stage===st).length;
  console.log("\n=== tiers ===");
  console.log("  CLEAR  Tanking : " + cnt("Tanking"));
  console.log("  CLEAR  Delivery: " + cnt("Delivery"));
  console.log("  KEEP           : " + keep.length);
  console.log("  REVIEW (left as-is): " + review.length + "   <- expect 0" +
              "  by location: " + JSON.stringify(review.reduce((m,r)=>{m[r[2]]=(m[r[2]]||0)+1;return m;},{})));
  console.log("  sample to clear: " + work.slice(0,3).map(w=>w.Title+"/"+w.stage+" was ["+w.from.s+","+String(w.from.e).slice(0,10)+"]").join(" | "));

  if (!APPLY) { console.log("\nDRY RUN -- nothing written. Set APPLY = true and paste again."); return; }

  console.log("\n=== UNDO (previous values -- keep this) ===");
  console.log(JSON.stringify(work.map(w=>({Id:w.Id,Title:w.Title,stage:w.stage,s:w.from.s,e:w.from.e}))));

  const dg = await (await fetch(base+"/_api/contextinfo",{method:"POST",
                    headers:{Accept:"application/json;odata=nometadata"}})).json();
  const et = (await J(base+"/_api/web/lists(guid'"+OI+"')?$select=ListItemEntityTypeFullName"))
               .ListItemEntityTypeFullName;
  // ---- ONE WRITE PER ITEM, not per (item, stage) --------------------------
  // `work` holds one entry per stage, so a unit needing BOTH Tanking and Delivery
  // cleared produced TWO PATCHes to the same item. Run concurrently, SharePoint
  // rejects the second with 409 Conflict -- item-level save conflict, which
  // IF-MATCH:"*" does not help with, because it is a lock and not an etag mismatch.
  // Observed 2026-09-09: ids 27, 28, 30, 50, 118, 126, 127, 144, 146 ... every one
  // of them a unit appearing twice in the UNDO block.
  // Both stages go in one body, so an item is written exactly once.
  const byItem = new Map();
  for (const w of work) {
    if (!byItem.has(w.Id)) byItem.set(w.Id, {Id:w.Id, Title:w.Title, stages:[]});
    byItem.get(w.Id).stages.push(w.stage);
  }
  const items = [...byItem.values()];

  let ok=0, fail=0; const errs=[];
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const patch = async (it) => {
    const body = {__metadata:{type:et}};
    for (const st of it.stages) {
      body[st+"Status"] = null;
      // NOT st+"EndDate" -- the end-date column is internally <Stage>Date. A blanket
      // find/replace of the read fields would have missed this one, because the write
      // field name is BUILT here rather than written out.
      body[st+"Date"]   = null;
    }
    // 409/500/429 here are transient -- save conflict or throttling, not a bad
    // request. Retry with backoff rather than reporting a failure the operator then
    // has to chase by hand across 1,100 rows.
    for (let attempt = 1; attempt <= 4; attempt++) {
      const r = await fetch(base+"/_api/web/lists(guid'"+OI+"')/items("+it.Id+")",{method:"POST",
        headers:{Accept:"application/json;odata=nometadata","Content-Type":"application/json;odata=verbose",
                 "X-RequestDigest":dg.FormDigestValue,"X-HTTP-Method":"MERGE","IF-MATCH":"*"},
        body:JSON.stringify(body)});
      if (r.ok) { ok++; return; }
      const retryable = (r.status === 409 || r.status === 429 || r.status >= 500);
      if (!retryable || attempt === 4) {
        fail++;
        if (errs.length < 8) errs.push(it.Title+" ["+it.stages.join("+")+"]: "+r.status+" "
                                       +(await r.text()).slice(0,140));
        return;
      }
      await sleep(250 * Math.pow(2, attempt - 1) + Math.random()*200);
    }
  };
  console.log("\nwriting " + work.length + " stage-clears across "
              + items.length + " items (" + (work.length - items.length)
              + " items need both stages) ...");
  for (let i=0;i<items.length;i+=CONC) {
    await Promise.all(items.slice(i,i+CONC).map(patch));
    if (i % 200 === 0) console.log("  " + Math.min(i+CONC, items.length) + "/" + items.length);
  }
  console.log("written ok=" + ok + " failed=" + fail + "   (of " + items.length + " items)");
  for (const e of errs) console.error("  " + e);

  // ---------------------------------------------------------- verification
  let u2 = base+"/_api/web/lists(guid'"+OI+"')/items?$select=Id,Location,TankingStatus,TankingDate,DeliveryStatus,DeliveryDate&$top=500";
  let after=[], g2=0;
  while (u2 && g2++<10) { const j=await J(u2); after=after.concat(j.value||[]); u2=j["odata.nextLink"]||null; }
  const stillBad = after.filter(r => {
    const loc=(r.Location||"").trim();
    const tBad = ((r.TankingStatus||"")!=="" || r.TankingDate) && AT_OR_BEFORE.has(loc);
    const dBad = ((r.DeliveryStatus||"")!=="" || r.DeliveryDate) && !(loc==="Livraison" && r.DeliveryDate) && !OFF_SEQ.has(loc);
    return tBad || dBad;
  });
  const tank = after.filter(r=>(r.TankingStatus||"")!=="").length;
  const dely = after.filter(r=>(r.DeliveryStatus||"")!=="").length;
  console.log("\n--- verification (trust this, not the write results) ---");
  console.log("rows still violating the rule: " + stillBad.length + "   (expect 0)");
  console.log("Tanking Status populated : " + tank + "   (was 975; expect 141 = 110 in-sequence + 31 Extérieur, all KEEP)");
  console.log("Delivery Status populated: " + dely + "   (was 400; expect 93 = Livraison + a delivery date)");
})();
