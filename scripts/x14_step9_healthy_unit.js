/* X14 -- step 9 of the evening runbook: does v004 still work on a HEALTHY unit?

   Two phases. Set PHASE below, paste, wait one poll, change PHASE, paste again.

       PHASE = "arm"     picks a healthy unit, stores its baseline, changes Step Status
       PHASE = "verify"  re-reads and compares against the stored baseline

   WHY A HEALTHY UNIT IS THE REAL TEST OF THE COALESCE
     Step 8 ran on a model-less unit whose four *_TextField mirrors were ALL NULL. Its
     8.5 check therefore passed trivially -- there was nothing there to wipe. The failure
     8.5 exists to catch is a POPULATED mirror cleared by a null flowing out of a skipped
     Get. That can only happen on a row that has populated mirrors, which means a healthy
     one. Step 8 did not test it. This does.

     Gate B (x10) reported 0 rows with a populated mirror over an empty lookup, i.e. the
     coalesce is belt-and-braces rather than load-bearing. This confirms the braces hold.

   THE WATERMARK TRAP, learned the hard way on 2026-09-14
     `GetOnUpdatedItems` sets its watermark on the first poll AFTER the flow is enabled,
     and a poll that finds nothing logs no run at all. An edit made in that window is
     silently ignored and looks exactly like a broken flow. The flow has been running
     since 22:40 so this no longer applies -- but if it is ever re-enabled, touch the row
     a SECOND time several minutes later before judging the logic.

   THIS EDITS A PRODUCTION ROW. It overwrites a hand-entered Status Date with today.
     "verify" prints the exact restore values. Restore Step Status first, then the date
     AFTER the stamp settles -- by then the mirror matches and the flow leaves it alone.
*/
(async () => {
  const PHASE = "arm";                      // "arm" | "verify"
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI    = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const KEY   = "x14_step9_baseline";
  const MIRRORS = ["Client_ID_TextField","Model_ID_TextField",
                   "Model_Revision_ID_TextField","Order_Number_TextField"];
  const SEL = ["Id","Title","StepStatus","StatusDate","StepStatusStamped","Modified",
               "ClientId","ModelId","ModelRevisionId"].concat(MIRRORS).join(",");

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

  /* ------------------------------------------------------------------- ARM */
  if (PHASE === "arm") {
    const units = await page(base+"/_api/web/lists(guid'"+OI+"')/items?$select="+SEL+"&$top=500");
    const ok = v => v != null && v !== "";
    // healthy = all three lookups present, mirror already settled, and at least three
    // populated *_TextField values so the coalesce has something real to lose.
    const cands = units.filter(u => ok(u.ClientId) && ok(u.ModelId) && ok(u.ModelRevisionId)
      && s(u.StepStatus) !== "" && s(u.StepStatus) === s(u.StepStatusStamped)
      && MIRRORS.filter(f => ok(u[f])).length >= 3);
    if (!cands.length) { console.error("ABORT: no healthy unit with populated mirrors."); return; }

    const u = cands[0];
    const NEXT = s(u.StepStatus) === "En cours" ? "Terminé" : "En cours";
    const b = {id:u.Id, title:s(u.Title), step:s(u.StepStatus), stamped:s(u.StepStatusStamped),
               statusDate:day(u.StatusDate), next:NEXT,
               mirrors:Object.fromEntries(MIRRORS.map(f=>[f,s(u[f])]))};
    localStorage.setItem(KEY, JSON.stringify(b));

    console.log("healthy candidates with populated mirrors: " + cands.length);
    console.log("chosen: " + b.title + " (id " + b.id + ")");
    console.log("  lookups      : " + [u.ClientId,u.ModelId,u.ModelRevisionId].join("/"));
    console.log("  step         : " + b.step + "   ->  will set to " + NEXT);
    console.log("  Status Date  : " + (b.statusDate||"(none)") + "   <- will become " + TODAY_ET);
    console.log("  mirrors      : " + MIRRORS.map(f=>f.replace("_TextField","")+"="+b.mirrors[f]).join("  "));
    console.log("");
    console.log("  ^ THESE FOUR MIRRORS MUST SURVIVE. That is the whole test.");

    const dg = await (await fetch(base+"/_api/contextinfo",{method:"POST",credentials:"include",
      headers:{Accept:"application/json;odata=nometadata"}})).json();
    const r = await fetch(base+"/_api/web/lists(guid'"+OI+"')/items("+u.Id+")",{
      method:"POST", credentials:"include",
      headers:{Accept:"application/json;odata=nometadata","Content-Type":"application/json;odata=nometadata",
               "X-RequestDigest":dg.FormDigestValue,"IF-MATCH":"*","X-HTTP-Method":"MERGE"},
      body: JSON.stringify({ StepStatus: NEXT })});
    console.log("");
    console.log("write status=" + r.status + "  at ET " + new Date().toLocaleString("en-US",{timeZone:"America/Toronto"}));
    console.log(r.ok ? "ARMED. Wait 5 minutes, set PHASE = verify, paste again."
                     : "WRITE FAILED -- nothing to verify.");
    return;
  }

  /* ---------------------------------------------------------------- VERIFY */
  const raw = localStorage.getItem(KEY);
  if (!raw) { console.error("ABORT: no stored baseline. Run PHASE = arm first."); return; }
  const b = JSON.parse(raw);
  const u = await J(base+"/_api/web/lists(guid'"+OI+"')/items("+b.id+")?$select="+SEL);
  const vers = (await J(base+"/_api/web/lists(guid'"+OI+"')/items("+b.id+")/versions?$top=4")).value || [];

  console.log("unit " + b.title + " (id " + b.id + ")   today " + TODAY_ET);
  console.log("");
  for (const v of vers.slice(0,4))
    console.log("  " + s(v.VersionLabel).padEnd(6) + s(v.Modified).slice(0,19) + "Z  "
      + "step=" + s(v.StepStatus).padEnd(10) + "stamped=" + s(v.StepStatusStamped).padEnd(10)
      + "date=" + (day(v.StatusDate)||"-"));

  const wiped   = MIRRORS.filter(f => b.mirrors[f] !== "" && s(u[f]) === "");
  const changed = MIRRORS.filter(f => b.mirrors[f] !== "" && s(u[f]) !== "" && s(u[f]) !== b.mirrors[f]);

  console.log("");
  console.log("=== step 9 ===");
  console.log("  stamped follows step : step=" + s(u.StepStatus) + " stamped=" + s(u.StepStatusStamped)
    + "   " + (s(u.StepStatus)===s(u.StepStatusStamped) ? "PASS" : "FAIL"));
  console.log("  Status Date = today  : " + (day(u.StatusDate)||"(none)")
    + "   " + (day(u.StatusDate)===TODAY_ET ? "PASS" : "FAIL"));
  console.log("  lookups intact       : " + [u.ClientId,u.ModelId,u.ModelRevisionId].map(v=>v==null?"NULL":v).join("/")
    + "   " + ([u.ClientId,u.ModelId,u.ModelRevisionId].every(v=>v!=null) ? "PASS" : "FAIL -- the flow CLEARED a lookup"));
  console.log("  mirrors NOT wiped    : " + (wiped.length===0 ? "PASS -- the coalesce holds"
    : "FAIL -- wiped: " + wiped.join(",")));
  if (changed.length) console.log("  mirrors CHANGED value: " + changed.map(f=>f+": "+b.mirrors[f]+" -> "+s(u[f])).join(", ")
    + "   <- inspect; a refresh to a correct value is fine, a wrong value is not");

  console.log("");
  console.log("=== restore this row ===");
  console.log("  Step Status -> " + b.step + "   then, after the next stamp settles,");
  console.log("  Status Date -> " + (b.statusDate || "(it had none -- clear it)"));
})();
