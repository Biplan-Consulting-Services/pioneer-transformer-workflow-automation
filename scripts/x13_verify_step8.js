/* X13 -- read-only. Verify step 8 of the evening runbook: did v004 stamp the model-less
   test unit correctly, and did it leave everything else alone?

   Read-only: it writes nothing. Paste into the browser console on the SharePoint site.

   WHY THIS EXISTS
     The 2026-09-14 enable produced NO runs for the first ~16 minutes. That was not a
     v004 defect: `GetOnUpdatedItems` sets its watermark on the first poll AFTER the flow
     is enabled, and a poll that finds nothing logs no run at all. The test edit at
     22:24:16 landed inside that blind spot and was never eligible. Re-touching the row
     once the trigger had initialised produced a successful run at 22:40.

     ⚠️ CARRY THIS FORWARD: after enabling any GetOnUpdatedItems flow, the first edit you
     make may be silently ignored. Always touch the test row a second time, several
     minutes after enabling, before concluding anything about the flow's logic.

   WHAT IT CHECKS -- the runbook's 8.3 to 8.6, plus the two safety numbers.
     A green run is NOT the result. The 09-11 failure and the 09-14 no-op both looked
     fine from outside; only the stored values settle it.

   WHAT IT CANNOT CHECK
     8.1 (run succeeded) and 8.2 (Get_Client / Get_Model SKIPPED rather than Failed) live
     in the Power Automate run history and are not readable from SharePoint. 8.2 is the
     entire point of v004 -- a green run does not prove it, because a guard that skipped
     Update_item as well would also be green. Read it in the designer.
*/
(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const ID   = 21;                          // 22021-14/20, model-less test unit
  const ENABLED = "2026-09-15T02:23:00Z";   // flow turned on ~22:23 ET

  // Baseline captured 2026-09-14 22:23 ET, BEFORE the test edit. v15.0 was the last
  // pre-test version. All four mirrors and all three lookups were null.
  const BASE = { step:"Terminé", stamped:"Terminé", statusDate:"2026-08-11", lastVer:"15.0",
                 // all four were null at 22:23, before the test edit
                 mirrors:{ Client_ID_TextField:"", Model_ID_TextField:"",
                           Model_Revision_ID_TextField:"", Order_Number_TextField:"" } };
  const MIRRORS = ["Client_ID_TextField","Model_ID_TextField",
                   "Model_Revision_ID_TextField","Order_Number_TextField"];

  const J = async u => {
    const c = new AbortController(); const t = setTimeout(()=>c.abort(), 20000);
    try { return await (await fetch(u,{credentials:"include",signal:c.signal,
            headers:{Accept:"application/json;odata=nometadata"}})).json(); }
    finally { clearTimeout(t); }
  };
  const page = async (u) => { let o=[],g=0;
    while (u && g++<30){ const j=await J(u); o=o.concat(j.value||[]); u=j["odata.nextLink"]||null; } return o; };

  const s = v => (v == null ? "" : String(v));
  const day = v => s(v).slice(0,10);
  const iso = d => d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");
  const TODAY_ET = iso(new Date(new Date().toLocaleString("en-US",{timeZone:"America/Toronto"})));

  const SEL = ["Id","Title","StepStatus","StatusDate","StepStatusStamped","Modified",
               "ClientId","ModelId","ModelRevisionId"].concat(MIRRORS).join(",");
  const u = await J(base+"/_api/web/lists(guid'"+OI+"')/items("+ID+")?$select="+SEL);
  const vers = (await J(base+"/_api/web/lists(guid'"+OI+"')/items("+ID+")/versions?$top=10")).value || [];

  console.log("today (Eastern): " + TODAY_ET + "     unit " + s(u.Title) + " (id " + ID + ")\n");

  console.log("=== version trail since the test began ===");
  for (const v of vers.slice(0,6))
    console.log("  " + s(v.VersionLabel).padEnd(6) + s(v.Modified).slice(0,19) + "Z  "
      + "step=" + s(v.StepStatus==null?"-":v.StepStatus).padEnd(10)
      + "stamped=" + s(v.StepStatusStamped==null?"-":v.StepStatusStamped).padEnd(10)
      + "date=" + (day(v.StatusDate)||"-"));

  // --- 8.3 / 8.4 -------------------------------------------------------------
  const ok83 = day(u.StatusDate) === TODAY_ET;
  const ok84 = s(u.StepStatusStamped) === s(u.StepStatus);
  // --- 8.5: the mirrors must not have been CLEARED by the coalesce -----------
  // Direction matters, and an earlier version of this check got it wrong. The failure
  // 8.5 guards against is a populated mirror being wiped by a null from a SKIPPED Get.
  // An EMPTY mirror becoming populated is the opposite: the flow refreshing a value the
  // dead *_TextField sync stopped maintaining on 2026-08-21. That is not a failure, and
  // flagging it as one hides the failure that is.
  const wiped  = MIRRORS.filter(f => BASE.mirrors[f] !== "" && s(u[f]) === "");
  const filled = MIRRORS.filter(f => BASE.mirrors[f] === "" && s(u[f]) !== "");
  const ok85 = wiped.length === 0;

  console.log("\n=== the checks the runbook asks for ===");
  console.log("  8.3 Status Date = today        : " + (day(u.StatusDate)||"(none)")
    + "   " + (ok83 ? "PASS" : "FAIL -- wanted " + TODAY_ET));
  console.log("  8.4 Stamped follows Step Status: step=" + s(u.StepStatus)
    + " stamped=" + s(u.StepStatusStamped) + "   " + (ok84 ? "PASS" : "FAIL"));
  console.log("  8.5 no mirror was CLEARED      : " + (ok85 ? "PASS"
    : "FAIL -- wiped: " + wiped.join(",") + "  <- the coalesce did not take"));
  if (filled.length) {
    console.log("      (refreshed, not a failure)  : " + filled.map(f=>f+"="+s(u[f])).join(", "));
    console.log("      ^ the flow repopulates mirrors as it stamps. See the note in");
    console.log("        evening-runbook-2026-09-14.md: this slowly un-stales the");
    console.log("        *_TextField columns that lookup-coverage counts were wrong about.");
  }
  console.log("      lookups still empty        : "
    + [u.ClientId,u.ModelId,u.ModelRevisionId].map(v=>v==null?"-":v).join("/"));

  // --- 8.6 + the safety numbers ----------------------------------------------
  const all = await page(base+"/_api/web/lists(guid'"+OI+"')/items?$select=Id,Title,Modified,StepStatus,StepStatusStamped&$top=500");
  const touched = all.filter(x => s(x.Modified) > ENABLED);
  const drift   = all.filter(x => s(x.StepStatus)!=="" && s(x.StepStatus)!==s(x.StepStatusStamped));

  console.log("\n=== safety -- did it touch anything it should not have? ===");
  console.log("  units in the list                 : " + all.length);
  console.log("  modified since the flow was on    : " + touched.length);
  for (const x of touched.slice(0,12))
    console.log("      id " + String(x.Id).padEnd(5) + s(x.Title).padEnd(14) + s(x.Modified).slice(0,19) + "Z");
  console.log("  DRIFTED rows now                  : " + drift.length + "   (0 = every row settled)");
  if (drift.length) for (const x of drift.slice(0,10))
    console.log("      id " + String(x.Id).padEnd(5) + s(x.Title).padEnd(14)
      + "step=" + s(x.StepStatus) + " stamped=" + s(x.StepStatusStamped));

  console.log("\n  8.6 (next poll writes nothing): re-run this in 5 minutes. The version");
  console.log("      number above must NOT have advanced. A row rewritten every poll is");
  console.log("      the runaway case -- turn the flow off if the number keeps climbing.");

  console.log("\n=== still owed ===");
  console.log("  Restore the test unit once 8.6 holds: Step Status -> " + BASE.step
    + ", then Status Date -> " + BASE.statusDate + " AFTER the stamp settles.");
  console.log("  8.1/8.2 are in the run history, not here. Confirm Get_Client and");
  console.log("  Get_Model show SKIPPED, not Failed -- that is what v004 exists to do.");
})();
