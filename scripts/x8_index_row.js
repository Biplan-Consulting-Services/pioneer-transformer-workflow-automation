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

   WHAT THE LIST ACTUALLY LOOKS LIKE  (read 2026-09-10)
     24 rows, two columns: `Title` (Text) and `Path` (URL / Hyperlink).
     FRM10-12 is row Id 8 and currently reads, percent-encoded and relative:
       /sites/PioneerPlanificatio/Shared%20Documents/General/FAB/Revue/Formulaires/FRM10-12.xlsx
     Keep that encoding when you repoint -- every other row uses it.

   ⚠️ SEVEN ROWS ARE EXACT DUPLICATES. `FRM11 (new)` and the six `Rapport … (new)`
   rows resolve to the SAME path as their non-`(new)` twin, byte for byte. Harmless
   today, because both point at the same file. The hazard is that they can be edited
   independently, and the day one is repointed and the other is not, half the estate
   silently reads a different file. Not tonight's work; worth not forgetting.

   BEFORE YOU REPOINT
     - Snapshot the file you are about to overwrite into live-workbook-data/. That
       snapshot is the rollback; the Index row itself rolls back from the UNDO below.
     - Break permission inheritance on the deployed file: staff Read, refresh
       operators Edit. A Power Query refresh has to SAVE, so read-only-for-everyone
       breaks the thing keeping FRM09 alive.
*/

(async () => {
  const APPLY    = false;
  const NEW_PATH = "";  // the target, percent-encoded like every other row:
                        // /sites/PioneerPlanificatio/Shared%20Documents/General/FAB/Revue/FRM10-12.xlsx
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

  // Find the column that actually holds a path. Two rules, in this order, because
  // the obvious one is wrong:
  //
  //   1. A field whose VALUE looks like a path, on a row that has one. Value first,
  //      not name -- matching on /url/i picked `ServerRedirectedEmbedUrl`, a built-in
  //      SharePoint field that is empty on every row, so every path printed blank and
  //      the script looked like it had worked. 2026-09-10.
  //   2. Only then fall back to the name, and only for names SharePoint did not
  //      invent itself.
  const BUILTIN = /^(ServerRedirected|FileRef|FileDirRef|FileLeafRef|LinkFilename|LinkTitle|_|OData__|ContentType|GUID|Attachments|ComplianceAsset)/;
  // `Path` is Type="URL" Format="Hyperlink" (read off the list's own schema
  // 2026-09-10), so REST hands it over as {Url, Description} -- an OBJECT. The first
  // version of this script only considered string fields and therefore could not see
  // the one column it exists to read. Unwrap before testing.
  const asStr = v => (v && typeof v === "object" && typeof v.Url === "string") ? v.Url
                   : (typeof v === "string" ? v : "");
  const looksLikePath = v => {
    const t = asStr(v);
    return t.indexOf("/sites/") >= 0 || t.indexOf("://") >= 0 || t.indexOf(".xls") >= 0;
  };
  const candidates = new Map();
  for (const row of items.value) {
    for (const k of Object.keys(row)) {
      if (BUILTIN.test(k)) continue;
      if (looksLikePath(row[k])) candidates.set(k, (candidates.get(k) || 0) + 1);
    }
  }
  let pathKey = null;
  if (candidates.size) {
    pathKey = [...candidates.entries()].sort((a, b) => b[1] - a[1])[0][0];
    console.log("path column chosen by VALUE: " + pathKey + " (looks like a path on "
                + candidates.get(pathKey) + " of " + items.value.length + " rows)");
  } else {
    pathKey = Object.keys(items.value[0]).find(k =>
        !BUILTIN.test(k) && /path|chemin|lien/i.test(k) && typeof items.value[0][k] === "string");
    if (pathKey) console.log("path column chosen by NAME: " + pathKey
                             + "  -- no row held anything path-shaped, which is itself odd");
  }
  if (!pathKey) {
    console.error("could not identify the path column. Every non-empty text field on the "
                  + "FRM10-12 row, so you can pick it by eye:");
    const r0 = items.value.find(r => String(r.Title).trim() === ROW) || items.value[0];
    for (const k of Object.keys(r0).sort())
      if (typeof r0[k] === "string" && r0[k].trim())
        console.error("   " + k.padEnd(34) + String(r0[k]).slice(0, 110));
    return;
  }
  console.log("Index list id: " + lst.Id + "   rows: " + items.value.length);

  console.log("\n=== every Index row ===");
  for (const r of items.value.slice().sort((a,b)=>String(a.Title).localeCompare(String(b.Title)))) {
    const mark = String(r.Title).trim() === ROW ? " <<<<" : "";
    console.log("  " + String(r.Title).padEnd(24) + asStr(r[pathKey]).slice(0,80) + mark);
  }

  const row = items.value.find(r => String(r.Title).trim() === ROW);
  if (!row) { console.error("\nno Index row titled " + JSON.stringify(ROW)); return; }
  const currentObj = row[pathKey] || null;
  const current = asStr(currentObj);
  const currentDesc = (currentObj && currentObj.Description) || "";
  console.log("\n=== the row four workbooks resolve through ===");
  console.log("  Title   : " + row.Title);
  console.log("  Id      : " + row.Id);
  console.log("  " + pathKey.padEnd(12) + ": " + (current || "(empty)"));
  console.log("  link text   : " + (currentDesc || "(none)"));
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
  // A URL column over REST takes SP.FieldUrlValue -- {Url, Description} -- NOT a
  // bare string. This is the same shape x5_backfill_order_folder.js uses, and the
  // opposite of what the Power Automate connector wants (that one takes a plain
  // string; see gen_n3_flows.py's `url` kind). REST and the connector genuinely
  // disagree here, so neither is a safe guide to the other.
  //
  // Description is carried over rather than regenerated: it is the link text staff
  // see, and blanking it turns a labelled link into a raw URL for no reason.
  const body = {__metadata:{type: lst.ListItemEntityTypeFullName}};
  body[pathKey] = {__metadata:{type:"SP.FieldUrlValue"},
                   Url: NEW_PATH,
                   Description: currentDesc || NEW_PATH};
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
  console.log("  now reads : " + (asStr(after[pathKey]) || "(empty)"));
  console.log("  expected  : " + NEW_PATH);
  console.log("  " + ((asStr(after[pathKey]) === NEW_PATH) ? "MATCH"
              : "*** MISMATCH -- fix before anyone refreshes ***"));
  console.log("\nNEXT: refresh ONE consumer (FRM09 is the cheapest) and confirm it still");
  console.log("      returns rows. A wrong path does not error -- it serves stale data.");
})();
