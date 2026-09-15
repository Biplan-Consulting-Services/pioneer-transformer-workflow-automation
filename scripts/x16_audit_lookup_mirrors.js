/* X16 -- read-only. Audit every *_TextField mirror on Order Items against the value its
   lookup actually points at, and say exactly how many rows are wrong and in which way.

   Read-only: it writes nothing. Paste into the browser console on the SharePoint site.

   WHY THIS EXISTS
     On 2026-09-14 the trigger flow stamped a healthy unit and overwrote
     `Model_Revision_ID_TextField` with the MODEL's id:

         21408-1/1   MR-HYQU-0092-V1  ->  M-HYQU-0092

     ⚠️ THE FIRST TWO DIAGNOSES WERE BOTH WRONG. The flow is fine.

     `ModelID` on `Model Revisions` IS the revision identifier -- 348 of 393 rows hold MR-
     values in it -- and the lookup's ShowField resolves to it, so
     `@triggerBody()?['ModelRevision/Value']` is the correct expression and always was.

     The defect is in the DATA: revision 344's own `ModelID` reads "M-HYQU-0092", its
     model's code, where it should read "MR-HYQU-0092-V1". The flow mirrored a corrupt
     source faithfully. The Order Items mirror still held the right value only because the
     *_TextField sync has been off since 2026-08-21 while the revision was modified
     2026-09-01 -- the stale copy was more accurate than the live list.

     See x17 for the revision-side audit. This script measures the Order Items side.

   WHAT IT CANNOT ASSUME, AND WHY IT PROBES INSTEAD
     A bad $select returns 400, and the usual `rows.concat(j.value||[])` turns that into
     ZERO ROWS -- which reads as "nothing wrong here" rather than "broken query". That has
     already produced a confidently wrong answer on this project (see CLAUDE.md). So every
     field name is probed one at a time against the live list and the script ABORTS rather
     than reporting a clean result it did not actually measure.

     ⚠️ Do not take field names from `lookup-textfield-reference.md`. It names
     `Model_Revion_ID` (does not exist; the field is `ModelID`) and `Client_ID_TextField`
     (the real internal name is `Client_ID_TextFiel`, genuinely truncated). It says it was
     built from the CSV exports, and CLAUDE.md records that those omit every Lookup's
     values AND schema -- which is how it drifted. Probe, do not trust.

   WHAT IT REPORTS
     For each of Client / Model / Model Revision, every Order Items row is classified:

       OK          mirror matches the value the lookup resolves to
       CORRUPTED   mirror holds the MODEL's id where the revision's belongs -- the
                   signature of the bug above
       WRONG       mirror disagrees some other way; listed individually, because an
                   unexplained shape is how the last four defects were found
       EMPTY       mirror never populated (the sync has been off since 2026-08-21)
       NO LOOKUP   the lookup itself is null, so there is nothing to mirror
*/
(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";

  const raw = async (u) => {
    const c = new AbortController(); const t = setTimeout(()=>c.abort(), 25000);
    try { return await fetch(u, {credentials:"include", signal:c.signal,
            headers:{Accept:"application/json;odata=nometadata"}}); }
    finally { clearTimeout(t); }
  };
  const J = async (u) => (await raw(u)).json();
  const page = async (u) => { let o=[],g=0;
    while (u && g++<40){ const j=await J(u); o=o.concat(j.value||[]); u=j["odata.nextLink"]||null; } return o; };
  const s = v => (v == null ? "" : String(v));
  const L = t => base + "/_api/web/lists/getbytitle('" + t + "')";

  /* -- probe: which of these field names does this list actually have? ---------- */
  const probe = async (title, candidates) => {
    for (const f of candidates) {
      const r = await raw(L(title) + "/items?$top=1&$select=Id," + f);
      if (r.ok) { console.log("  " + title.padEnd(17) + "id field -> " + f); return f; }
    }
    console.error("  " + title + ": none of [" + candidates.join(", ") + "] exist. ABORT.");
    return null;
  };

  console.log("=== probing field names on the live lists ===");
  // `ModelID` -- NOT `Model_Revion_ID`. lookup-textfield-reference.md names a field that
  // does not exist on this list; `ModelID` on `Model Revisions` is the revision id (MR-...)
  // and is what the lookup's ShowField resolves to. Confirmed against live values, not names.
  const fRev = await probe("Model Revisions",
        ["ModelID","Model_Revion_ID","Model_Revision_ID","ModelRevisionID"]);
  const fMod = await probe("Models", ["ModelID","Model_ID","ModelId"]);
  const fCli = await probe("Clients", ["Client_ID","ClientID"]);
  if (!fRev || !fMod || !fCli) return;

  /* -- load the three reference lists ------------------------------------------ */
  const load = async (title, idField) => {
    const rows = await page(L(title) + "/items?$top=2000&$select=Id," + idField);
    if (!rows.length) { console.error("ABORT: read 0 rows from " + title + " -- a zero-row read is a failed read."); return null; }
    console.log("  " + title.padEnd(17) + rows.length + " rows");
    return new Map(rows.map(r => [r.Id, s(r[idField])]));
  };
  console.log("\n=== loading reference lists ===");
  const REV = await load("Model Revisions", fRev);
  const MOD = await load("Models", fMod);
  const CLI = await load("Clients", fCli);
  if (!REV || !MOD || !CLI) return;

  /* -- load Order Items --------------------------------------------------------- */
  const SEL = ["Id","Title","ClientId","ModelId","ModelRevisionId",
               "Client_ID_TextField","Model_ID_TextField","Model_Revision_ID_TextField"].join(",");
  const units = await page(L("Order Items") + "/items?$top=500&$select=" + SEL);
  if (!units.length) { console.error("ABORT: read 0 units."); return; }
  console.log("  Order Items      " + units.length + " rows");

  /* -- classify ----------------------------------------------------------------- */
  const CASES = [
    {name:"Client",         lk:"ClientId",         mir:"Client_ID_TextField",         map:CLI},
    {name:"Model",          lk:"ModelId",          mir:"Model_ID_TextField",          map:MOD},
    {name:"Model Revision", lk:"ModelRevisionId",  mir:"Model_Revision_ID_TextField", map:REV},
  ];

  const report = {};
  for (const c of CASES) {
    const r = {ok:[], corrupted:[], wrong:[], empty:[], nolookup:[]};
    for (const u of units) {
      const id = u[c.lk];
      if (id == null || id === "") { r.nolookup.push(u); continue; }
      const truth  = c.map.get(id);
      const mirror = s(u[c.mir]);
      if (truth === undefined) { r.wrong.push({u, truth:"(lookup id " + id + " not in list)", mirror}); continue; }
      if (mirror === "")       { r.empty.push(u); continue; }
      if (mirror === truth)    { r.ok.push(u); continue; }
      // is it holding the MODEL's id? that is the known corruption signature
      const modelId = u.ModelId != null ? MOD.get(u.ModelId) : undefined;
      if (c.name === "Model Revision" && modelId !== undefined && mirror === modelId)
        r.corrupted.push({u, truth, mirror});
      else r.wrong.push({u, truth, mirror});
    }
    report[c.name] = r;
  }

  console.log("\n=== mirror audit ===");
  console.log("  " + "case".padEnd(16) + "OK".padStart(6) + "CORRUPT".padStart(9)
    + "WRONG".padStart(7) + "EMPTY".padStart(7) + "NO-LK".padStart(7));
  for (const c of CASES) {
    const r = report[c.name];
    console.log("  " + c.name.padEnd(16) + String(r.ok.length).padStart(6)
      + String(r.corrupted.length).padStart(9) + String(r.wrong.length).padStart(7)
      + String(r.empty.length).padStart(7) + String(r.nolookup.length).padStart(7));
  }

  const rev = report["Model Revision"];
  if (rev.corrupted.length) {
    console.error("\n=== Model Revision: mirror holds the MODEL id (the 2026-09-14 bug) ===");
    for (const x of rev.corrupted.slice(0, 25))
      console.error("  " + s(x.u.Title).padEnd(14) + "should be " + s(x.truth).padEnd(20) + "is " + s(x.mirror));
    if (rev.corrupted.length > 25) console.error("  ... and " + (rev.corrupted.length - 25) + " more");
  }

  for (const c of CASES) {
    const w = report[c.name].wrong;
    if (!w.length) continue;
    console.error("\n=== " + c.name + ": mirror disagrees, unexplained shape -- INSPECT ===");
    for (const x of w.slice(0, 20))
      console.error("  " + s(x.u.Title).padEnd(14) + "should be " + s(x.truth).padEnd(24) + "is " + s(x.mirror));
    if (w.length > 20) console.error("  ... and " + (w.length - 20) + " more");
  }

  /* -- what the fix has to restore ---------------------------------------------- */
  console.log("\n=== scope of the repair ===");
  console.log("  rows whose Model Revision mirror needs rewriting : "
    + (rev.corrupted.length + rev.wrong.length));
  console.log("  rows where it is simply unset (was never synced) : " + rev.empty.length);
  console.log("\n  Every row the flow stamps rewrites this column, so the corrupted count");
  console.log("  grows by one per staff edit until the mapping is fixed. Nothing else");
  console.log("  reads it for staff -- FRM10-12 reads the lists directly -- but the CSV");
  console.log("  exports carry ONLY the mirrors, so export-based analysis silently");
  console.log("  inherits every wrong value.");
})();
