/* X15 -- put the two 2026-09-14 test units back the way staff left them.

   DRY RUN by default. Two phases, and the order is not optional.

       PHASE = "step"   restore Step Status. This DELIBERATELY causes one more stamp.
       PHASE = "date"   restore Status Date, after that stamp has landed.

   WHY TWO PHASES, AND WHY THE DATE CANNOT GO FIRST
     Restoring Step Status re-creates the drift the flow watches for: the row now reads
     step=Terminé against stamped=En cours, so the next poll stamps Status Date = today
     and re-syncs the mirror. Anything written to Status Date BEFORE that poll is
     overwritten by it.

     Once the mirror matches again the flow has no reason to touch the row, so the date
     written in phase 2 sticks. This is exactly the behaviour the runbook tells staff to
     rely on: "change the step and leave the date alone -- it fills in within 5 minutes.
     If the real date differs, correct it AFTER the stamp lands and it sticks."

     So this script is also a live rehearsal of the instruction we are about to give the
     shop floor. If phase 2 does not stick, that instruction is wrong and staff need to
     be told something else.

   WHAT WAS CHANGED, AND BY WHAT
     id 21  22021-14/20  model-less unit, step 8. Terminé -> En cours at 02:24:17Z.
                         Status Date 2026-08-11 overwritten with 2026-09-14 by the flow.
     id 4   21408-1/1    healthy unit, step 9 (x14). Terminé -> En cours at 03:00:32Z.
                         Status Date 2026-07-16 overwritten with 2026-09-14 by the flow.

     Both dates below are the values read from the rows BEFORE any edit tonight. Neither
     is a guess; both are in the version history if they need checking.
*/
(async () => {
  const APPLY = false;
  const PHASE = "step";                     // "step" | "date"
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI    = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";

  const ROWS = [
    { id:21, title:"22021-14/20", step:"Terminé", date:"2026-08-11" },
    { id:4,  title:"21408-1/1",   step:"Terminé", date:"2026-07-16" },
  ];

  const J = async u => {
    const c = new AbortController(); const t = setTimeout(()=>c.abort(), 20000);
    try { return await (await fetch(u,{credentials:"include",signal:c.signal,
            headers:{Accept:"application/json;odata=nometadata"}})).json(); }
    finally { clearTimeout(t); }
  };
  const s = v => (v == null ? "" : String(v));
  const day = v => s(v).slice(0,10);
  const SEL = "Id,Title,StepStatus,StatusDate,StepStatusStamped";

  console.log("PHASE = " + PHASE + (APPLY ? "   APPLY" : "   DRY RUN"));
  console.log("");

  const live = [];
  for (const r of ROWS) {
    const u = await J(base+"/_api/web/lists(guid'"+OI+"')/items("+r.id+")?$select="+SEL);
    live.push({r, u});
    console.log("id " + String(r.id).padEnd(4) + s(u.Title).padEnd(14)
      + "step=" + s(u.StepStatus).padEnd(10) + "stamped=" + s(u.StepStatusStamped).padEnd(10)
      + "date=" + (day(u.StatusDate)||"-"));
    if (s(u.Title) !== r.title) console.error("  TITLE MISMATCH -- expected " + r.title + ". Wrong row; stop.");
    if (PHASE === "step") console.log("     -> Step Status will become " + r.step
      + (s(u.StepStatus)===r.step ? "   (already correct, will skip)" : ""));
    if (PHASE === "date") {
      const settled = s(u.StepStatus) === s(u.StepStatusStamped);
      console.log("     -> Status Date will become " + r.date
        + (settled ? "   (mirror settled, safe to write)"
                   : "   🔴 MIRROR NOT SETTLED -- the next poll will overwrite this. WAIT."));
    }
  }

  if (PHASE === "date" && live.some(({u}) => s(u.StepStatus) !== s(u.StepStatusStamped))) {
    console.error("");
    console.error("ABORT: at least one row is still drifted. Run PHASE = step, wait a full");
    console.error("poll for the stamp to land, and only then run PHASE = date.");
    return;
  }

  if (!APPLY) { console.log(""); console.log("DRY RUN -- nothing written. Set APPLY = true."); return; }

  const dg = await (await fetch(base+"/_api/contextinfo",{method:"POST",credentials:"include",
    headers:{Accept:"application/json;odata=nometadata"}})).json();

  for (const {r, u} of live) {
    if (PHASE === "step" && s(u.StepStatus) === r.step) { console.log("skip id " + r.id + " -- already " + r.step); continue; }
    const body = PHASE === "step" ? { StepStatus: r.step } : { StatusDate: r.date + "T12:00:00Z" };
    const resp = await fetch(base+"/_api/web/lists(guid'"+OI+"')/items("+r.id+")",{
      method:"POST", credentials:"include",
      headers:{Accept:"application/json;odata=nometadata","Content-Type":"application/json;odata=nometadata",
               "X-RequestDigest":dg.FormDigestValue,"IF-MATCH":"*","X-HTTP-Method":"MERGE"},
      body: JSON.stringify(body)});
    console.log("id " + r.id + "  " + JSON.stringify(body) + "  -> " + resp.status
      + (resp.ok ? "" : "  FAILED: " + (await resp.text()).slice(0,160)));
  }

  console.log("");
  if (PHASE === "step") {
    console.log("Step Status restored. Both rows are now DRIFTED on purpose, so the next");
    console.log("poll will stamp Status Date = today and re-sync the mirror. Wait a full");
    console.log("5 minutes, confirm the stamp landed, THEN run PHASE = date.");
  } else {
    console.log("Status Date restored. Re-read in 5 minutes: if the dates still read");
    console.log("2026-08-11 and 2026-07-16, the 'correct it after the stamp' instruction");
    console.log("we are giving staff is sound. If the flow overwrote them again, it is");
    console.log("NOT sound and the staff guidance has to change before anyone is told it.");
  }
})();
