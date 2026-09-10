/* X8 -- read, and then repoint, the `Index` row that four workbooks resolve through.

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
     3. READ-ONLY by default. It prints every Index row and highlights FRM10-12.
     4. To repoint: set NEW_PATH to the target, set APPLY = true, paste again.
        It prints the old value as UNDO before writing and re-reads afterwards.

   WHY THIS EXISTS RATHER THAN EDITING THE ROW BY HAND
     There is not one hardcoded workbook URL anywhere in the estate. Every
     cross-workbook read goes through this list (Title -> Path), so FRM09, FRM11,
     FRM13 and BO Manager all resolve FRM10-12 through this single row. That is what
     makes the cutover a one-row edit.

     It is also what makes it the quietest failure in the whole system. There are TWO
     real FRM10-12 files -- the old `Revue/FRM10-12.xlsx` and a separate
     `Revue/Formulaires/FRM10-12.xlsx` created 2026-08-28 -- and the row currently
     resolves to `Formulaires/`. So a wrong path does not error. `Web.Contents` keeps
     succeeding against a workbook that has simply stopped changing, and four
     consumers keep serving last-known-good data to eight outside companies with
     nothing reporting anything.

     🔴 **This row had never actually been read** as of 2026-09-10. Read it before you
     touch it, and read it after. That is the entire job of this script: turn a
     one-line manual edit on an unread row into a recorded before/after.

   BEFORE YOU REPOINT
     - Snapshot the file you are about to overwrite into live-workbook-data/. That
       snapshot is the rollback; the Index row itself rolls back from the UNDO below.
     - Break permission inheritance on the deployed file: staff Read, refresh
       operators Edit. A Power Query refresh has to SAVE, so read-only-for-everyone
       breaks the thing keeping FRM09 alive.
*/

(async () => {
  const APPLY    = false;
  const NEW_PATH = "";          // e.g. "/sites/PioneerPlanificatio/Shared Documents/General/FAB/Revue/FRM10-12.xlsx"
  const ROW      = "FRM10-12";  // the Index row's Title

  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const J = async (u, o) => {
    const r = await fetch(u, Object.assign({credentials:"include",
      headers:{Accept:"application/json;odata=nometadata"}}, o||{}));
    if (!r.ok) return {__err: r.status + " " + (await r.text()).slice(0,300)};
    return r.status === 204 ? {} : r.json();
  };

  const lst = await J(base+"/_api/web/lists/getbytitle('Index')?$select=Id,ListItemEntityTypeFullName");
  if (lst.__err) { console.error("cannot read the Index list: " + lst.__err); return; }

  const items = await J(base+"/_api/web/lists(guid'"+lst.Id+"')/items?$top=200");
  if (items.__err || !(items.value||[]).length) { console.error("ABORT: read 0 Index rows."); return; }

  // The Path column's internal name is not assumed -- find whichever field on the row
  // actually holds a path, so a renamed column does not silently read as empty.
  const sample = items.value[0];
  const pathKey = Object.keys(sample).find(k =>
      /path|url|lien/i.test(k) && typeof sample[k] === "string") ||
    Object.keys(sample).find(k => typeof sample[k] === "string" && sample[k].includes("/sites/"));
  console.log("Index list id: " + lst.Id + "   rows: " + items.value.length
              + "   path column: " + (pathKey || "NOT FOUND"));
  if (!pathKey) { console.error("could not identify the path column -- inspect a row:", sample); return; }

  console.log("\n=== every Index row ===");
  for (const r of items.value.slice().sort((a,b)=>String(a.Title).localeCompare(String(b.Title)))) {
    const mark = String(r.Title).trim() === ROW ? " <<<<" : "";
    console.log("  " + String(r.Title).padEnd(22) + String(r[pathKey] || "").slice(0,88) + mark);
  }

  const row = items.value.find(r => String(r.Title).trim() === ROW);
  if (!row) { console.error("\nno Index row titled " + JSON.stringify(ROW)); return; }
  const current = row[pathKey] || "";
  console.log("\n=== the row four workbooks resolve through ===");
  console.log("  Title   : " + row.Title);
  console.log("  Id      : " + row.Id);
  console.log("  " + pathKey.padEnd(8) + ": " + current);
  console.log("  reads   : FRM09 (TableOrders) · FRM11 (TableOrders + 3 code tables)");
  console.log("            FRM13 (TableOrders) · BO Manager (Location, Status, Tanking Date)");

  if (!APPLY) {
    console.log("\nREAD-ONLY. To repoint: set NEW_PATH, set APPLY = true, paste again.");
    if (NEW_PATH && NEW_PATH !== current) console.log("  would become: " + NEW_PATH);
    return;
  }
  if (!NEW_PATH) { console.error("APPLY is true but NEW_PATH is empty -- refusing."); return; }
  if (NEW_PATH === current) { console.log("\nalready points there. Nothing to do."); return; }

  console.log("\n=== UNDO -- paste this back into NEW_PATH to revert ===");
  console.log("  " + JSON.stringify(current));

  const dg = await (await fetch(base+"/_api/contextinfo",{method:"POST",credentials:"include",
    headers:{Accept:"application/json;odata=nometadata"}})).json();
  const body = {__metadata:{type: lst.ListItemEntityTypeFullName}};
  body[pathKey] = NEW_PATH;
  const w = await fetch(base+"/_api/web/lists(guid'"+lst.Id+"')/items("+row.Id+")",
    {method:"POST", credentials:"include",
     headers:{Accept:"application/json;odata=nometadata",
              "Content-Type":"application/json;odata=verbose",
              "X-RequestDigest":dg.FormDigestValue,
              "X-HTTP-Method":"MERGE","IF-MATCH":"*"},
     body: JSON.stringify(body)});
  console.log(w.ok ? "\nwritten." : "\nFAILED " + w.status + " " + (await w.text()).slice(0,300));
  if (!w.ok) return;

  const after = await J(base+"/_api/web/lists(guid'"+lst.Id+"')/items("+row.Id+")");
  console.log("\n--- verification (trust this, not the write result) ---");
  console.log("  now reads : " + (after[pathKey] || "(empty)"));
  console.log("  expected  : " + NEW_PATH);
  console.log("  " + ((after[pathKey] === NEW_PATH) ? "MATCH" : "*** MISMATCH -- fix before anyone refreshes ***"));
  console.log("\nNEXT: refresh ONE consumer (FRM09 is the cheapest) and confirm it still");
  console.log("      returns rows. A wrong path does not error -- it serves stale data.");
})();
