/* X17 -- read-only. Which `Model Revisions` rows have a wrong `ModelID`, and what do they
   have in common?

   Read-only: it writes nothing. Paste into the browser console on the SharePoint site.

   NOT CONSOLE-ONLY ANY MORE (2026-09-25): Model Revisions is on disk in
   sharepoint-lists/mirror/live/ (scripts/Refresh-SharePointMirror.ps1). ⚠️ There the Model
   lookup's id column is `ModelId2`, not `ModelId` (Excel names are case-insensitive and the
   text column `ModelID` exists) - live/Columns.csv's idColumn says so. mirror_health.py does
   not port this check yet.
   PROBABLE WRITER FOUND 2026-09-24: revision 26's version history (mirror VersionProbe) shows a
   Power App save by a staff account writing the MODEL code back into ModelID on 09-17, undoing
   the x18 repair. Look at the app's save formula before repairing again. Board 2026-09-24 22:38.

   HOW WE GOT HERE, INCLUDING TWO WRONG TURNS WORTH NOT REPEATING
     Step 9 saw the trigger flow rewrite a unit's `Model_Revision_ID_TextField`:

         21408-1/1    MR-HYQU-0092-V1  ->  M-HYQU-0092

     First reading: the flow writes the MODEL's id into the REVISION's mirror, so the
     mapping is wrong -- fix the flow. WRONG.
     Second reading: no field on `Model Revisions` holds an MR- value, so there is nothing
     to source from -- stop the flow writing the column. ALSO WRONG.

     `ModelID` on `Model Revisions` IS the revision identifier: 348 of 393 rows hold MR-
     values in it, and the lookup's ShowField resolves to it. The flow's mapping is
     correct and has always been correct. What is wrong is the DATA: revision 344's own
     `ModelID` reads "M-HYQU-0092", its model's code, instead of "MR-HYQU-0092-V1".

     The flow mirrored a corrupt source faithfully. And the Order Items mirror still held
     the RIGHT value only because the *_TextField sync has been off since 2026-08-21,
     while revision 344 was modified 2026-09-01 -- the stale copy was more accurate than
     the live list.

     🔑 Both wrong turns came from reasoning about field NAMES instead of reading field
     VALUES. `lookup-textfield-reference.md` names a source field (`Model_Revion_ID`) that
     does not exist, and calls the `Client_ID_TextFiel` column `Client_ID_TextField`. It
     says it was built from the CSV exports -- and CLAUDE.md records that those exports
     omit every Lookup, values and schema alike. Do not design against that table.

   WHAT THIS ANSWERS
     - exactly which revisions have a ModelID that is not an MR- value
     - whether they are the SA models (the 2026-09-01 SA fan-out is the prime suspect)
     - when they were last modified, and by whom
     - how many Order Items rows point at a bad revision, i.e. the blast radius

   WHAT IT DOES NOT DO
     It proposes no repair. The correct ModelID for a broken row is a judgement about what
     the revision IS, and 29+ of them predate any decision made tonight.
*/
(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";

  const J = async (u) => {
    const c = new AbortController(); const t = setTimeout(()=>c.abort(), 25000);
    try { return await (await fetch(u,{credentials:"include",signal:c.signal,
            headers:{Accept:"application/json;odata=nometadata"}})).json(); }
    finally { clearTimeout(t); }
  };
  const page = async (u) => { let o=[],g=0;
    while (u && g++<40){ const j=await J(u); o=o.concat(j.value||[]); u=j["odata.nextLink"]||null; } return o; };
  const s = v => (v == null ? "" : String(v));
  const L = t => base + "/_api/web/lists/getbytitle('" + t + "')";

  const revs = await page(L("Model Revisions") + "/items?$top=2000");
  if (!revs.length) { console.error("ABORT: read 0 revisions -- a zero-row read is a failed read."); return; }
  const units = await page(L("Order Items") + "/items?$top=500&$select=Id,Title,ModelId,ModelRevisionId,Model_Revision_ID_TextField");
  if (!units.length) { console.error("ABORT: read 0 units."); return; }

  // ⚠️ `/^MR-/` IS WRONG and the first run of this script used it. SA models are `MSA-`,
  // so their revisions are `MRSA-HYQU-0064-V1` -- correct ids that the pattern rejected,
  // inflating the suspect set from 29 to 45 and inverting the SA conclusion.
  //
  // The real rule is derivable: a revision's id is its MODEL's code with an `R` inserted
  // after the leading `M`, plus a version suffix.
  //     M-HYQU-0092    ->  MR-HYQU-0092-V1
  //     MSA-HYQU-0064  ->  MRSA-HYQU-0064-V1
  // Checking against the model it actually points at beats any prefix guess.
  const expected = r => { const m = s(r.Pioneer_Model_Code_TextField);
    return m ? "M" + "R" + m.slice(1) : null; };            // prefix, without the -V<n>
  const isMR  = (v, r) => { const e = expected(r);
    return e ? s(v).toUpperCase().startsWith(e.toUpperCase() + "-V") : /^MRS?A?-/i.test(s(v)); };
  const isSA  = r => /SA/.test(s(r.Model_x0020_Type)) || /SA/.test(s(r.Description))
                  || /MSA-|MRSA-/i.test(s(r.ModelID)) || /MSA-/i.test(s(r.Pioneer_Model_Code_TextField));

  const bad = revs.filter(r => !isMR(r.ModelID, r));
  console.log("revisions read        : " + revs.length);
  console.log("ModelID matches model : " + revs.filter(r => isMR(r.ModelID, r)).length);
  console.log("NOT an MR- id         : " + bad.length + "   <- the suspect set");
  console.log("  of those, empty     : " + bad.filter(r => s(r.ModelID) === "").length);
  console.log("  equal to their model: " + bad.filter(r => s(r.ModelID) !== "" && s(r.ModelID) === s(r.Pioneer_Model_Code_TextField)).length);
  console.log("  something else again: " + bad.filter(r => s(r.ModelID) !== "" && s(r.ModelID) !== s(r.Pioneer_Model_Code_TextField)).length);

  /* ---- is it the SA models? ------------------------------------------------- */
  const saAll = revs.filter(isSA);
  console.log("\n=== the SA hypothesis (2026-09-01 SA fan-out) ===");
  console.log("  SA revisions overall     : " + saAll.length + " of " + revs.length);
  console.log("  SA among the suspect set : " + bad.filter(isSA).length + " of " + bad.length);
  console.log("  non-SA among suspects    : " + bad.filter(r => !isSA(r)).length
    + (bad.filter(r => !isSA(r)).length ? "   <- if non-zero the SA story is incomplete" : ""));

  /* ---- when were they touched? ---------------------------------------------- */
  const byDay = {};
  for (const r of bad) { const d = s(r.Modified).slice(0,10); byDay[d] = (byDay[d]||0)+1; }
  console.log("\n=== suspect rows by Modified date ===");
  for (const d of Object.keys(byDay).sort()) console.log("  " + d + "   " + byDay[d]);

  const byEditor = {};
  for (const r of bad) { const e = s(r.EditorId); byEditor[e] = (byEditor[e]||0)+1; }
  console.log("  EditorId histogram: " + JSON.stringify(byEditor));

  /* ---- blast radius on Order Items ------------------------------------------ */
  const badIds = new Set(bad.map(r => r.Id));
  const hit = units.filter(u => u.ModelRevisionId != null && badIds.has(u.ModelRevisionId));
  const revById = new Map(revs.map(r => [r.Id, r]));
  const mirrorStillRight = hit.filter(u => {
    const r = revById.get(u.ModelRevisionId);
    return r ? isMR(u.Model_Revision_ID_TextField, r) : false; });
  console.log("\n=== blast radius on Order Items ===");
  console.log("  units pointing at a suspect revision : " + hit.length + " of " + units.length);
  console.log("  ...whose mirror still holds an MR- id: " + mirrorStillRight.length
    + "   <- these are the ones the flow will overwrite as staff touch them");
  console.log("  ...already overwritten               : " + (hit.length - mirrorStillRight.length));

  /* ---- the rows themselves --------------------------------------------------- */
  console.log("\n=== suspect revisions (first 40) ===");
  for (const r of bad.slice(0, 40))
    console.log("  id " + String(r.Id).padEnd(5)
      + "ModelID=" + (s(r.ModelID) || "(empty)").padEnd(18)
      + "model=" + s(r.Pioneer_Model_Code_TextField).padEnd(18)
      + "want=" + (expected(r) ? expected(r)+"-V?" : "?").padEnd(22)
      + "type=" + s(r.Model_x0020_Type).padEnd(16)
      + "mod=" + s(r.Modified).slice(0,10));
  if (bad.length > 40) console.log("  ... and " + (bad.length - 40) + " more");

  console.log("\n=== what this means for tonight ===");
  console.log("  The trigger flow is NOT the defect and needs no change. It propagates a");
  console.log("  bad ModelID into the Order Items mirror one row at a time, as staff edit.");
  console.log("  Turning the flow off does not repair anything; fixing the revisions does,");
  console.log("  and then the flow spreads the CORRECT value by the same mechanism.");
})();
