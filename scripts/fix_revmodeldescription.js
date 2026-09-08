/* R22 -- replace the raw lookup reference in Order Items.RevModelDescription
   with the value it was supposed to carry.

   HOW TO RUN
     1. Open the site in the browser, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio
     2. F12 -> Console. Paste this whole file. Press Enter.
     3. It runs a DRY RUN first and changes nothing. Read the sample.
     4. Set APPLY = true (line below) and paste again to write.
     5. It re-reads afterwards and prints how many blobs remain. Expect 0.

   WHAT IS WRONG
     979 of 1,117 rows hold about 110 characters of JSON where a short string
     belongs:

       [{"@odata.type":"#Microsoft.Azure.Connectors.SharePoint.SPListExpandedReference",
         "Id":5,"Value":"MALT"}]

     The intended value is MALT. The v006 mapping passes the WHOLE expanded
     lookup array instead of its .Value. This script keeps only the Value(s).

   SCOPE -- deliberately narrow
     Only rows whose current value actually contains "@odata.type" are touched.
     A row already holding a clean string is left alone, so this is safe to
     re-run and safe to stop halfway.

   ⚠️ THIS FIXES THE DATA, NOT THE CAUSE
     The mapping in the transfer flow still produces the blob. If that flow is
     ever run again as-is, all 979 rows get re-broken. Two things stop that:
       - the flow is manual-trigger only (kind: Button), so nothing fires it
         on a schedule, and
       - it is being reduced to create-only, after which it never rewrites an
         existing row.
     The mapping itself should still be corrected to
     ...?['ModelDescription']?['Value'] -- see docs/n3-parent-sync-flow-spec.md,
     which now carries the same warning for the N3 sync flows.

   SIDE EFFECTS
     Each write bumps Modified and adds a version. That is ~979 versions on one
     column; cap version history (N5) if that matters. No flow fires: all three
     sync flows are OFF (C1), which is why this is a good moment to do it.
*/

(async () => {
  const APPLY = false;                       // <-- set true to actually write
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const LIST  = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";   // Order Items
  const FIELD = "RevModelDescription";
  const CONCURRENCY = 4;

  const J = async (u) => (await fetch(u, {headers:{Accept:"application/json;odata=nometadata"}})).json();

  // Report the column's real type, so a surprise (Choice with a fixed option
  // list) shows up here rather than as 979 rejected writes.
  const cols = await J(base + "/_api/v2.0/sites/root/lists/" + LIST + "/columns");
  const col  = (cols.value || []).find(c => c.name === FIELD);
  console.log("column:", FIELD, "| displayName:", col && col.displayName,
              "| kind:", col ? Object.keys(col).find(k =>
                ["text","note","choice","number","boolean","dateTime","lookup"].includes(k)) : "?");
  if (col && col.choice) console.log("  NOTE: it is a Choice with options", JSON.stringify(col.choice.choices));

  // ------------------------------------------------------------------- read
  let url = base + "/_api/web/lists(guid'" + LIST + "')/items?$select=Id,Title," + FIELD + "&$top=500";
  let rows = [], guard = 0;
  while (url && guard++ < 20) {
    const j = await J(url);
    rows = rows.concat(j.value || []);
    url = j["odata.nextLink"] || null;
  }
  const clean = (s) => {
    let arr;
    try { arr = JSON.parse(s); } catch (e) { return null; }
    if (!Array.isArray(arr)) return null;
    const vals = arr.map(o => o && o.Value).filter(v => v !== undefined && v !== null && String(v).trim() !== "");
    return vals.length ? vals.join("; ") : "";
  };
  const todo = [];
  for (const r of rows) {
    const v = r[FIELD];
    if (typeof v === "string" && v.includes("@odata.type")) {
      const c = clean(v);
      if (c === null) { console.warn("unparseable on Id " + r.Id + ": " + v.slice(0,80)); continue; }
      todo.push({Id: r.Id, Title: r.Title, from: v, to: c});
    }
  }
  console.log("\nrows scanned: " + rows.length + " | rows holding a blob: " + todo.length);
  const dist = {};
  for (const t of todo) dist[t.to] = (dist[t.to] || 0) + 1;
  console.log("distinct values that will be written:", JSON.stringify(dist));
  console.log("\nsample of 5:");
  for (const t of todo.slice(0,5)) console.log("  " + t.Title + "  ->  " + JSON.stringify(t.to));
  const blanks = todo.filter(t => t.to === "");
  if (blanks.length) console.warn("\n" + blanks.length + " would become EMPTY (no Value in the reference) -- these are SKIPPED");

  if (!APPLY) {
    console.log("\nDRY RUN -- nothing written. Set APPLY = true and paste again.");
    return;
  }

  // ------------------------------------------------------------------ write
  const dg = await (await fetch(base + "/_api/contextinfo", {method:"POST",
                    headers:{Accept:"application/json;odata=nometadata"}})).json();
  const digest = dg.FormDigestValue;
  if (!digest) { console.error("no form digest - are you signed in?"); return; }
  const et = (await J(base + "/_api/web/lists(guid'" + LIST + "')?$select=ListItemEntityTypeFullName"))
               .ListItemEntityTypeFullName;

  const work = todo.filter(t => t.to !== "");
  let ok = 0, fail = 0;
  const errs = [];
  const patch = async (t) => {
    const body = {__metadata:{type:et}};
    body[FIELD] = t.to;
    const r = await fetch(base + "/_api/web/lists(guid'" + LIST + "')/items(" + t.Id + ")", {
      method:"POST",
      headers:{Accept:"application/json;odata=nometadata",
               "Content-Type":"application/json;odata=verbose",
               "X-RequestDigest":digest,
               "X-HTTP-Method":"MERGE", "IF-MATCH":"*"},
      body: JSON.stringify(body)});
    if (r.ok) ok++;
    else { fail++; if (errs.length < 5) errs.push(t.Id + ": " + r.status + " " + (await r.text()).slice(0,160)); }
  };

  console.log("\nwriting " + work.length + " rows ...");
  for (let i = 0; i < work.length; i += CONCURRENCY) {
    await Promise.all(work.slice(i, i + CONCURRENCY).map(patch));
    if ((i / CONCURRENCY) % 25 === 0) console.log("  " + Math.min(i + CONCURRENCY, work.length) + "/" + work.length);
  }
  console.log("written ok=" + ok + " failed=" + fail);
  for (const e of errs) console.error("  " + e);

  // ----------------------------------------------------------- verification
  let u2 = base + "/_api/web/lists(guid'" + LIST + "')/items?$select=Id," + FIELD + "&$top=500";
  let after = [], g2 = 0;
  while (u2 && g2++ < 20) { const j = await J(u2); after = after.concat(j.value || []); u2 = j["odata.nextLink"] || null; }
  const left = after.filter(r => typeof r[FIELD] === "string" && r[FIELD].includes("@odata.type")).length;
  const filled = after.filter(r => r[FIELD] !== null && String(r[FIELD]).trim() !== "").length;
  console.log("\n--- verification (trust this, not the write results) ---");
  console.log("rows still holding a blob: " + left + "   (expect 0)");
  console.log("rows with any value:       " + filled);
})();

/* ---------------------------------------------------------------- UNDO ----
   There is no undo worth writing: the previous value was malformed JSON that
   nobody wants back. Item version history holds it per row if a single row
   ever needs inspecting, and nothing else reads this column.
---------------------------------------------------------------------------- */
