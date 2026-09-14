/* X11 -- re-mirror Step Status Stamped, WITHOUT touching Status Date.

   DRY RUN by default: it writes nothing until APPLY = true.
   Paste into the browser console on the SharePoint site.

   🔴 RUN THIS WHILE THE TRIGGER FLOW IS OFF. That is the whole point -- once the flow is
   on, its first poll stamps these rows before anything can stop it.

   WHY
     `Step Status Stamped` is the mirror the auto-stamp compares against: when it differs
     from `Step Status`, the flow concludes the step just changed and writes
     `Status Date` = today.

     n8 set the mirror equal on every row at 05:55 on 2026-09-11. The flow was enabled,
     failed, and has been OFF since -- so for three days staff have been advancing units
     with nothing maintaining the mirror. As of 2026-09-14 that is 65 of 272 rows.

     ⚠️ THOSE 65 STATUS DATES ARE NOT STALE, AND THIS IS THE WHOLE REASON THIS SCRIPT
     EXISTS. Staff type `Status Date` by hand and always have -- that is exactly what the
     cutover handover says is acceptable while the flow is off. A row reading
     `step=Terminé, date=2026-08-28` is therefore most likely someone advancing the unit
     this week and DELIBERATELY dating it 08-28, because that is when the step actually
     finished. They are catching up on data entry, not leaving a field rotten.

     Enabling the flow against that state would overwrite 65 hand-entered dates with
     today. Re-mirroring first makes the flow treat them as already accounted for, so the
     auto-stamp only ever fires on changes made FROM NOW ON.

     (An earlier reading of this data argued the opposite -- that today was "closer" than
     an August date. That assumed nobody was maintaining the field. Somebody is. Do not
     re-derive that argument.)

   WHAT IT WRITES
     item/StepStatusStamped = the row's own current StepStatus. One field. Nothing else,
     and specifically NOT StatusDate -- which is verified by reading every StatusDate
     before and after and diffing them.
*/
(async () => {
  const APPLY = false;
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const CONC = 4;

  const J = async u => (await fetch(u, {credentials:"include",
              headers:{Accept:"application/json;odata=nometadata"}})).json();
  const page = async (u) => { let o=[],g=0;
    while (u && g++<30){ const j=await J(u); o=o.concat(j.value||[]); u=j["odata.nextLink"]||null; } return o; };

  const SEL = "Id,Title,StepStatus,StatusDate,StepStatusStamped";
  const read = () => page(base+"/_api/web/lists(guid'"+OI+"')/items?$select="+SEL+"&$top=500");

  const s = v => (v == null ? "" : String(v));
  const before = await read();
  if (!before.length) { console.error("ABORT: read 0 units. A zero-row read is a failed read."); return; }

  const drifted = before.filter(u => s(u.StepStatus) !== "" && s(u.StepStatus) !== s(u.StepStatusStamped));
  console.log("units read       : " + before.length);
  console.log("with a StepStatus: " + before.filter(u => s(u.StepStatus) !== "").length);
  console.log("DRIFTED          : " + drifted.length + "\n");

  if (!drifted.length) { console.log("Nothing to do -- the mirror is already clean."); return; }

  console.table(drifted.slice(0, 40).map(u => ({
    unit: u.Title, step: u.StepStatus, stamped: u.StepStatusStamped || "(empty)",
    statusDate: s(u.StatusDate).slice(0,10) + "  <- MUST NOT CHANGE" })));
  if (drifted.length > 40) console.log("  ... and " + (drifted.length - 40) + " more");

  if (!APPLY) {
    console.log("\nDRY RUN -- nothing written. Set APPLY = true.");
    console.log("Confirm the trigger flow is OFF before you do.");
    return;
  }

  const dg = await (await fetch(base + "/_api/contextinfo", { method:"POST",
    credentials:"include", headers:{Accept:"application/json;odata=nometadata"} })).json();

  let ok = 0, fail = 0; const errs = [];
  const patch = async (u) => {
    const r = await fetch(base+"/_api/web/lists(guid'"+OI+"')/items("+u.Id+")", {
      method:"POST", credentials:"include",
      headers:{ Accept:"application/json;odata=nometadata",
                "Content-Type":"application/json;odata=nometadata",
                "X-RequestDigest": dg.FormDigestValue,
                "IF-MATCH":"*", "X-HTTP-Method":"MERGE" },
      // ONE field. Adding StatusDate here is the mistake this script exists to avoid.
      body: JSON.stringify({ StepStatusStamped: u.StepStatus })
    });
    if (r.ok) ok++; else { fail++; errs.push(u.Title + ": " + (await r.text()).slice(0,160)); }
  };

  console.log("\nre-mirroring " + drifted.length + " rows ...");
  for (let i=0;i<drifted.length;i+=CONC) await Promise.all(drifted.slice(i,i+CONC).map(patch));
  console.log("written ok=" + ok + " failed=" + fail);
  for (const e of errs) console.error("  " + e);

  // ------------------------------------------------------------- verification
  // Trust this, not the write results. Two things have to hold, and the second one
  // matters more than the first.
  const after = await read();
  const byId = new Map(after.map(u => [u.Id, u]));

  const stillDrifted = after.filter(u => s(u.StepStatus) !== "" && s(u.StepStatus) !== s(u.StepStatusStamped));

  let moved = 0;
  for (const b of before) {
    const a = byId.get(b.Id);
    if (!a) { console.error("  row " + b.Title + " disappeared"); moved++; continue; }
    if (s(a.StatusDate) !== s(b.StatusDate)) {
      moved++;
      console.error("  STATUS DATE MOVED on " + b.Title + ": "
        + s(b.StatusDate).slice(0,10) + " -> " + s(a.StatusDate).slice(0,10));
    }
  }

  console.log("\n--- verification ---");
  console.log("mirror still drifted : " + stillDrifted.length + "   (expect 0)");
  console.log("StatusDate CHANGED   : " + moved + "   (expect 0 -- this is the one that matters)");
  console.log(stillDrifted.length === 0 && moved === 0
    ? "\nOK. Gate A will now pass, and every hand-entered date is untouched."
    : "\nNOT CLEAN. Do NOT enable the trigger flow until this reads 0 / 0.");
})();
