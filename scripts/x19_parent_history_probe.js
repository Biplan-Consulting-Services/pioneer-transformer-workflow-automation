/* X19 -- READ-ONLY. Per-order forensics: what parent data is missing on these
   units, was it erased or never filled, and which write lost it.

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
     3. Set ORDERS below.

   Writes nothing. Re-runnable.

   🔑 THE SHARPEST TEST IS SIBLING DIVERGENCE, NOT BLANKNESS
     Every unit of one order shares one Order row and one Client row, so all of
     them must carry identical `Ord*` and `Cli*` values. Any disagreement
     between siblings is a defect by definition -- no legitimate process can
     produce it. That catches PARTIAL damage, which a "is it blank" test cannot:
     x21 scanned the whole list for units with an entirely empty group and found
     22169 and 22175 but NOT 22172, even though the client flagged all three.
     A partially-written unit is invisible to a blankness test and obvious to
     this one.

     ⚠️ Only `Ord*` and `Cli*` are order-wide. `Mdl*` and `Rev*` are NOT --
     siblings legitimately differ there, most obviously an SA unit carrying its
     own twin model. Never flag those by divergence.

   WHAT CAUSES THE GAPS (both measured 2026-09-21, see
   docs/n3-fanout-race-2026-09-21.md)
     1. THE FAN-OUT RACE -- the N3 flows read their child set once and the
        writes trail that read by several seconds. Units created in between are
        outside the loop forever. Leaves a clean contiguous TAIL of the order.
     2. SAVE CONFLICT -- all four N3 flows write the same row; two colliding
        gives `{"status":400,"message":"Save Conflict ..."}`. No definition sets
        a retryPolicy and the Logic Apps default retries only 408/429/5xx, so a
        400 is lost for good. Leaves a SCATTER, and different groups missing on
        different siblings.
     Neither self-heals: the flows trigger on the parent, so a missed child
     stays missed until someone edits its Order or Model.

   ⚠️ COLUMN NAMES ARE PROBED, NOT TAKEN FROM A DOC. The N3 spec names
   `OrdOrderNumber` and `OrdQty`; neither exists, and a $select naming them
   returns 400, which `j.value||[]` turns into "0 rows" -- reading as "nothing
   wrong" rather than "broken query".
*/
(async () => {
  const base   = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI     = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const ORDERS = ["22169", "22172", "22175"];   // the orders the client flagged
  const RAW    = false;   // true dumps each flagged unit's first version verbatim

  const GROUPS = { Ord: "Order", Mdl: "Models", Rev: "Model Revisions", Cli: "Clients" };
  const FK = { Ord: "OrderNumberId", Mdl: "ModelId", Rev: "ModelRevisionId", Cli: "ClientId" };
  const ORDER_WIDE = ["Ord", "Cli"];   // groups whose siblings MUST agree

  /* The lookup and its mirror share the group prefix but are not synced
     columns, and they are populated on nearly every row -- including them made
     x21's first run report zero Ord* gaps. The tidier rule (uppercase after the
     prefix) is also wrong: RevkVA has a lowercase k. So: named outright. */
  const NOT_SYNCED = ["OrderNumber", "Order_Number_TextField", "Client", "Client_ID_TextField"];

  /* SharePoint returns `false` whether a Boolean was written false or never
     written, so a Boolean can never be evidence that a write landed. */
  const isEvidence = (v) => typeof v !== "boolean" && v !== null && v !== undefined && String(v).trim() !== "";
  const norm = (v) => (v === null || v === undefined || v === "") ? "" : String(v).trim();
  const cmp  = (v) => (v === null || v === undefined) ? "" : (typeof v === "object" ? JSON.stringify(v) : String(v).trim());

  const J = async (u) => {
    const r = await fetch(u, { credentials: "include",
      headers: { Accept: "application/json;odata=nometadata" } });
    if (!r.ok) throw new Error(r.status + " " + r.statusText);
    return r.json();
  };
  const page = async (u) => {
    let out = [], guard = 0;
    while (u && guard++ < 40) { const j = await J(u); out = out.concat(j.value || []); u = j["odata.nextLink"] || null; }
    return out;
  };
  const items = base + "/_api/web/lists(guid'" + OI + "')/items";

  /* ---- 0. list settings -- needed before any history is interpretable ----- */
  const list = await J(base + "/_api/web/lists(guid'" + OI + "')"
    + "?$select=Title,EnableVersioning,MajorVersionLimit,ItemCount,Created");
  console.log("=== " + list.Title + " ===");
  console.log("  created " + list.Created + "  |  versioning " + list.EnableVersioning
    + "  |  version cap " + list.MajorVersionLimit + " (oldest trimmed first, v1.0 goes first)"
    + "  |  " + list.ItemCount + " items\n");

  /* ---- 1. the real column names, from the platform ----------------------- */
  const cols = await J(base + "/_api/v2.0/sites/root/lists/" + OI + "/columns");
  const all = (cols.value || []).map(c => c.name);
  if (!all.length) { console.error("ABORT: read 0 columns."); return; }
  const inGroup = {};
  for (const g of Object.keys(GROUPS))
    inGroup[g] = all.filter(n => n.indexOf(g) === 0 && n !== g && NOT_SYNCED.indexOf(n) < 0);
  const TRACKED = Object.keys(GROUPS).reduce((a, g) => a.concat(inGroup[g]), []).concat(Object.values(FK));

  /* ---- 2. read the units of the flagged orders --------------------------- */
  const need = ["Id", "Title", "Created", "Modified", "Order_Number_TextField", "SAJob"].concat(TRACKED);
  const rows = {};
  const CHUNK = 18;
  for (let i = 0; i < need.length; i += CHUNK) {
    const sel = ["Id"].concat(need.slice(i, i + CHUNK).filter(f => f !== "Id"));
    try {
      for (const r of await page(items + "?$select=" + sel.join(",") + "&$top=500"))
        rows[r.Id] = Object.assign(rows[r.Id] || {}, r);
    } catch (e) {
      console.log("  chunk failed (" + e.message + "), probing field by field");
      for (const f of sel) {
        if (f === "Id") continue;
        try { for (const r of await page(items + "?$select=Id," + f + "&$top=500"))
                { rows[r.Id] = rows[r.Id] || { Id: r.Id }; rows[r.Id][f] = r[f]; } }
        catch (e2) { console.log("    REJECTED: " + f); }
      }
    }
  }
  const everything = Object.values(rows);
  if (!everything.length) { console.error("ABORT: read 0 units."); return; }

  const flagged = new Set();

  for (const ord of ORDERS) {
    const units = everything.filter(u => norm(u.Title).indexOf(ord) === 0).sort((a, b) => a.Id - b.Id);
    console.log("===============================================================");
    console.log("ORDER " + ord + "   " + units.length + " units");
    if (!units.length) { console.log("  none found\n"); continue; }

    for (const u of units) {
      const per = Object.keys(GROUPS).map(g =>
        g + " " + inGroup[g].filter(f => isEvidence(u[f])).length + "/" + inGroup[g].length).join("  ");
      console.log("  Id " + String(u.Id).padStart(5) + "  " + norm(u.Title).padEnd(14)
        + (u.SAJob === true ? "SA " : "   ")
        + "created " + String(u.Created).slice(0, 19).replace("T", " ") + "   " + per);
    }

    /* ---- 3. sibling divergence on the order-wide groups ------------------ */
    console.log("  --- sibling divergence (Ord*/Cli* must be identical across the order) ---");
    let found = 0;
    for (const g of ORDER_WIDE) {
      for (const f of inGroup[g]) {
        const seen = {};
        for (const u of units) (seen[cmp(u[f])] = seen[cmp(u[f])] || []).push(u.Id);
        const distinct = Object.keys(seen);
        if (distinct.length < 2) continue;
        found++;
        // The majority value is almost certainly the right one; the rest lost a write.
        distinct.sort((a, b) => seen[b].length - seen[a].length);
        console.log("    🔴 " + f);
        for (const v of distinct)
          console.log("         " + (v === "" ? "(blank)" : v.slice(0, 60)).padEnd(62)
            + " ids " + seen[v].join(","));
        for (const v of distinct.slice(1)) for (const id of seen[v]) flagged.add(id);
      }
    }
    if (!found) console.log("    none -- every unit of this order carries the same Ord*/Cli* values");

    /* A group that is entirely empty is damage even without divergence. */
    for (const u of units) for (const g of Object.keys(GROUPS)) {
      if (norm(u[FK[g]]) && !inGroup[g].some(f => isEvidence(u[f]))) {
        console.log("    🔴 Id " + u.Id + " " + norm(u.Title) + ": " + g + "* entirely empty"
          + (g === "Mdl" || g === "Rev" ? "  (check the SA zero-match branch before assuming a lost write)" : ""));
        flagged.add(u.Id);
      }
    }
    console.log("");
  }

  /* ---- 4. history for the flagged units only ----------------------------- */
  console.log("===============================================================");
  console.log("HISTORY for the " + flagged.size + " flagged units\n");
  for (const id of Array.from(flagged).sort((a, b) => a - b)) {
    const item = await J(items + "(" + id + ")?$select=Id,Title,Created,Modified,AuthorId,EditorId,"
      + "Author/Title,Editor/Title&$expand=Author,Editor");
    console.log("---------------------------------------------------------------");
    console.log("Id " + item.Id + "  " + item.Title
      + "\n  created  " + item.Created + "  " + (item.Author && item.Author.Title)
      + "\n  modified " + item.Modified + "  " + (item.Editor && item.Editor.Title));

    let versions = [];
    try { versions = await page(items + "(" + id + ")/versions?$top=200"); }
    catch (e) { console.log("  versions UNREADABLE: " + e.message); continue; }
    versions = versions.slice().reverse();

    let cleared = null, prev = null;
    for (const v of versions) {
      const who = (v.Editor && (v.Editor.LookupValue || v.Editor.Title)) || "?";
      const ch = [];
      for (const f of TRACKED) {
        const now = cmp(v[f]), was = prev ? cmp(prev[f]) : null;
        if (prev && now !== was) ch.push(f + ": " + (was || "(blank)") + " -> " + (now || "(blank)"));
        else if (!prev && isEvidence(v[f])) ch.push(f + " = " + now);
      }
      if (prev && TRACKED.some(f => isEvidence(prev[f]) && !isEvidence(v[f]))) cleared = v.VersionLabel;
      console.log("    v" + v.VersionLabel + "  " + v.Created + "  " + who + "  "
        + (ch.length ? ch.join(" | ") : "(no change in parent fields)"));
      prev = v;
    }
    console.log("  VERDICT: " + (cleared ? "ERASED at v" + cleared
      : versions.length <= 1 ? "NEVER FILLED -- one version, no write ever touched these fields"
      : "NEVER FILLED -- no version of this row ever carried the missing values"));

    if (versions.length && new Date(versions[0].Created) < new Date(list.Created))
      console.log("  🔴 v" + versions[0].VersionLabel + " predates the list itself (" + list.Created + ")");
    if (RAW && versions.length) {
      console.log("  --- raw v" + versions[0].VersionLabel + " ---");
      for (const k of Object.keys(versions[0]).sort()) {
        const val = versions[0][k];
        if (val === null || val === "") continue;
        console.log("      " + k.padEnd(34) + " " + (typeof val === "object" ? JSON.stringify(val) : val));
      }
    }
  }
  console.log("\nA contiguous TAIL of an order = the fan-out race.");
  console.log("A SCATTER, or different groups lost on different siblings = Save Conflict 400.");
})();
