/* X12 -- does TODAY() in a SharePoint calculated column read a day ahead in the evening?
   RUN THIS AFTER 20:00 EASTERN. Before that it cannot answer the question.

   DRY RUN by default. The real test needs ONE write per unit -- see below.

   THE QUESTION
     calculated-columns-plan.md:528 flags that TODAY() in a SharePoint calculated column
     is widely UTC-based rather than site-local. If so, a row recomputed between roughly
     20:00 Eastern and midnight sees UTC already on TOMORROW, and every TODAY()-derived
     branch of `Estimated Delivery Date` lands a day late until the next pass.

     The 01:00 Eastern nightly touch neutralises it for the day -- 05:00/06:00Z stamps the
     correct Eastern date -- so this is about what staff see in the evening, not about
     what the flow writes. Whether that is tolerable is a judgement; this establishes
     whether there is anything to judge.

   ⚠️ WHY THIS CANNOT BE READ-ONLY, WHICH THE ORIGINAL TEST PLAN MISSED
     A SharePoint calculated column is STORED, not evaluated on read. It recomputes when
     the ITEM is written and at no other time. Every row's Estimated Delivery Date was
     computed when the column was created (2026-09-14 ~14:20 Eastern, i.e. 18:20Z), which
     is before 20:00 -- so reading at 21:00 shows this afternoon's answer and proves
     nothing at all. "Check the test column after 8pm" would have looked like a clean pass
     no matter what the truth is.

     So: write, then read. The write is `Calc Refreshed`, which is our own column, which
     nothing reads, and which is exactly what the nightly touch does. One row per case.

   WHAT IT DOES
     STALLED   a unit on a TODAY() branch -- latest milestone already past, no delivery
               date, no manual override. Its estimate SHOULD be today + buffer + penalty.
     CONTROL   a unit on branch 1 (a Planned Delivery Date is set). That branch never
               calls TODAY(), so its estimate must not move at all. If the control moves
               too, the problem is not the UTC trap and is something else entirely --
               which is worth knowing before anyone redesigns around a trap that is not
               the cause.

   READING THE RESULT
     stalled matches TODAY_EASTERN + buffer      -> no trap. Calculated column is fine.
     stalled matches TOMORROW + buffer           -> TRAP IS REAL.
     control moved at all                        -> stop; something else is wrong.
*/
(async () => {
  const APPLY = false;
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";

  const J = async u => (await fetch(u, {credentials:"include",
              headers:{Accept:"application/json;odata=nometadata"}})).json();
  const page = async (u) => { let o=[],g=0;
    while (u && g++<30){ const j=await J(u); o=o.concat(j.value||[]); u=j["odata.nextLink"]||null; } return o; };

  const s = v => (v == null ? "" : String(v));
  const has = v => s(v).trim() !== "";
  const day = v => s(v).slice(0,10);

  // Eastern "today", computed in the browser rather than trusted from the clock's zone.
  const eastern = d => new Date(d.toLocaleString("en-US", {timeZone:"America/Toronto"}));
  const iso = d => d.getFullYear() + "-" + String(d.getMonth()+1).padStart(2,"0")
                   + "-" + String(d.getDate()).padStart(2,"0");
  const addDays = (isoStr, n) => { const d = new Date(isoStr + "T12:00:00Z");
    d.setUTCDate(d.getUTCDate() + n); return iso(new Date(d.toISOString().slice(0,10) + "T12:00:00")); };

  const now = new Date();
  const TODAY_ET  = iso(eastern(now));
  const TODAY_UTC = now.toISOString().slice(0,10);
  const hourET = Number(now.toLocaleString("en-US", {timeZone:"America/Toronto", hour:"2-digit", hour12:false}));

  console.log("clock now        : " + now.toISOString());
  console.log("today (Eastern)  : " + TODAY_ET + "   hour " + hourET);
  console.log("today (UTC)      : " + TODAY_UTC);
  if (TODAY_ET === TODAY_UTC) {
    console.warn("\n⚠️  Eastern and UTC are on the SAME date right now, so this test cannot");
    console.warn("   distinguish them. Run it between 20:00 and 23:59 Eastern.");
    if (hourET < 20) console.warn("   It is " + hourET + ":xx Eastern -- too early. Come back after 20:00.");
    return;
  }
  console.log("\nEastern and UTC are on DIFFERENT dates -- the test can discriminate.\n");

  const F = {dlv:"Planned_x0020_Delivery_x0020_Dat", man:"ManualEstimatedDeliveryDate",
             fin:"FinishingDate", tst:"TestingDate", tnk:"Planned_x0020_Tanking_x0020_Date",
             coil:["CoilingDate","StackingDate","AssemblyDate","DryingDate"],
             tankdlv:"TankDeliveryDate"};
  const SEL = ["Id","Title","ItemStatus","BO","EstimatedDeliveryDate","CalcRefreshed",
               F.dlv,F.man,F.fin,F.tst,F.tnk,F.tankdlv].concat(F.coil).join(",");

  const units = await page(base+"/_api/web/lists(guid'"+OI+"')/items?$select="+SEL+"&$top=500");
  if (!units.length) { console.error("ABORT: read 0 units."); return; }
  console.log("units read: " + units.length);

  const pen = u => (/^\s*(ok)?\s*$/i.test(s(u.BO)) ? 0 : 30);

  // The same exclusive cascade the calculated column walks. Returns the buffer, or null
  // when the unit is not on a TODAY() branch at all.
  const branch = u => {
    if (has(u[F.dlv]) || has(u[F.man])) return null;                 // branches 1-2
    if (has(u[F.fin])) return day(u[F.fin]) < TODAY_ET ? 7  : null;
    if (has(u[F.tst])) return day(u[F.tst]) < TODAY_ET ? 10 : null;
    if (has(u[F.tnk])) return day(u[F.tnk]) < TODAY_ET ? 14 : null;
    const set = F.coil.filter(f => has(u[f]));
    if (!set.length) return null;                                    // branch 7
    const ahead = F.coil.concat([F.tankdlv]).some(f => has(u[f]) && day(u[f]) >= TODAY_ET);
    return ahead ? null : 21;
  };

  const stalled = units.filter(u => s(u.ItemStatus) === "Active" && branch(u) !== null);
  const control = units.filter(u => has(u[F.dlv]) && has(u.EstimatedDeliveryDate));

  console.log("on a TODAY() branch right now : " + stalled.length
    + "   <-- also the honest count for the nightly touch");
  console.log("branch-1 controls available   : " + control.length + "\n");
  if (!stalled.length) { console.error("ABORT: no unit is on a TODAY() branch, nothing to test."); return; }
  if (!control.length) { console.error("ABORT: no branch-1 control available."); return; }

  const pick = [["STALLED", stalled[0]], ["CONTROL", control[0]]];
  for (const [label, u] of pick) {
    const b = branch(u);
    console.log(label + "  unit " + s(u.Title) + " (id " + u.Id + ")");
    console.log("   Estimated Delivery Date now : " + day(u.EstimatedDeliveryDate));
    console.log("   Calc Refreshed now          : " + (day(u.CalcRefreshed) || "(never)"));
    if (b !== null) {
      console.log("   branch buffer + BO penalty  : " + b + " + " + pen(u));
      console.log("   if NO trap, expect          : " + addDays(TODAY_ET, b + pen(u)));
      console.log("   if TRAP,   expect           : " + addDays(TODAY_ET, b + pen(u) + 1));
    } else {
      console.log("   branch 1 -- must not move at all");
    }
  }

  if (!APPLY) {
    console.log("\nDRY RUN -- nothing written, so nothing has recomputed and the question");
    console.log("is still open. Set APPLY = true to touch these two rows and re-read.");
    return;
  }

  const dg = await (await fetch(base + "/_api/contextinfo", { method:"POST",
    credentials:"include", headers:{Accept:"application/json;odata=nometadata"} })).json();

  console.log("\ntouching " + pick.length + " rows (Calc Refreshed only) ...");
  for (const [, u] of pick) {
    const r = await fetch(base+"/_api/web/lists(guid'"+OI+"')/items("+u.Id+")", {
      method:"POST", credentials:"include",
      headers:{ Accept:"application/json;odata=nometadata",
                "Content-Type":"application/json;odata=nometadata",
                "X-RequestDigest": dg.FormDigestValue,
                "IF-MATCH":"*", "X-HTTP-Method":"MERGE" },
      body: JSON.stringify({ CalcRefreshed: new Date().toISOString() })
    });
    if (!r.ok) { console.error("  write FAILED on " + u.Title + ": " + (await r.text()).slice(0,200)); return; }
  }

  console.log("\n--- re-read after the write (this is the answer) ---");
  let verdict = null;
  for (const [label, u] of pick) {
    const a = await J(base+"/_api/web/lists(guid'"+OI+"')/items("+u.Id+")?$select="+SEL);
    const before = day(u.EstimatedDeliveryDate), after = day(a.EstimatedDeliveryDate);
    const b = branch(u);
    console.log(label + "  " + s(u.Title) + " : " + before + " -> " + after);
    if (b === null) {
      if (before !== after) {
        console.error("   🔴 CONTROL MOVED. Branch 1 never calls TODAY(). The problem is");
        console.error("      NOT the UTC trap -- stop and find out what it is.");
        verdict = "control-moved";
      } else console.log("   unchanged, as it must be.");
    } else {
      const noTrap = addDays(TODAY_ET, b + pen(u)), trap = addDays(TODAY_ET, b + pen(u) + 1);
      if (after === noTrap)      { console.log("   ✅ matches TODAY-Eastern + " + (b+pen(u)) + ". No trap."); verdict = verdict || "clean"; }
      else if (after === trap)   { console.error("   🔴 matches TOMORROW + " + (b+pen(u)) + ". THE TRAP IS REAL."); verdict = "trap"; }
      else                       { console.error("   ⚠️ matches neither (" + noTrap + " / " + trap + ") -- recheck the branch logic."); verdict = "unexplained"; }
    }
  }
  console.log("\nVERDICT: " + verdict);
  console.log(verdict === "clean" ? "Estimated Delivery Date stays a calculated column."
            : verdict === "trap"  ? "Evening edits read a day late. Decide whether that is tolerable;\n"
                                  + "the fallback is the column formatting already built."
            : "Do not draw a conclusion from this run.");
})();
