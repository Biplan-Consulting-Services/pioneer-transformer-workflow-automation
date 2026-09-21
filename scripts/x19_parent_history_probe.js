/* X19 -- READ-ONLY. Was a unit's parent information ERASED, or NEVER FILLED?

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
        (if Chrome refuses the paste, type  allow pasting  first)
     3. Set ORDER below to the order number you care about.

   Writes nothing. Re-runnable.

   ⚠️ FIELD NAMES ARE PROBED, NOT ASSUMED
     v1 of this script took the synced column names from
     docs/n3-parent-sync-flow-spec.md and the whole $select returned 400 --
     which `j.value||[]` would have turned into "0 rows", reading as
     "nothing wrong" rather than "broken query". So step 1 now asks the list
     which of the candidate names actually exist, prints the rejects, and
     builds the query from the survivors. Same rule the Model Revisions repair
     ended on: read values, never reason about names.

   WHY NOT THE VERSION HISTORY PANE
     - Confirmed on this list: EnableVersioning = TRUE, MajorVersionLimit = 50.
       So history IS kept, and "one entry only" is a real fact about the row,
       not a list setting -- worth knowing before interpreting anything.
     - Past 50 writes SharePoint trims the OLDEST versions first, so v1.0 is
       the first thing to vanish on a row the flows have touched a lot.
     - The pane diffs RENDERED values. A lookup it cannot resolve renders blank,
       so a version that cleared a lookup can display as "nothing changed".
     - The details-pane Activity feed is NOT item version history and can show
       events belonging to something else entirely.
     Hence: read /versions over REST and print the first one verbatim.

   WHAT "PARENT INFORMATION" MEANS HERE -- two things, two mechanisms:
     (a) the LOOKUPS      OrderNumberId / ModelId / ModelRevisionId / ClientId,
                          set at row creation. Empty = invisible to the N3 sync
                          flows, which fan out on `<lookup>Id eq <parent ID>`.
     (b) the synced       Ord* / Mdl* / Rev* columns, written ONLY by the four
         parent columns   N3 flows, which trigger on the PARENT list. Nothing
                          fills them when a CHILD is created; today's values
                          came from the one-off R3 backfill (2026-09-08).
   (b) is why a unit created after that backfill can be permanently blank with
   nothing at all in its history: there was never a write to record.
*/
(async () => {
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI    = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";   // Order Items
  const ORDER = "22169";        // <-- the order number to scope to; "" = whole list
  const RAW   = true;           // dump each unit's first stored version verbatim

  const LOOKUPS = ["OrderNumberId", "ModelId", "ModelRevisionId", "ClientId"];
  // Candidates only. Anything the list rejects is dropped and reported.
  const SYNCED = [
    "OrdOrderNumber", "OrdOrderDate", "OrdOrderStatus", "OrdQty", "OrdPO",
    "MdlModelID", "MdlEstimatedEffort",
    "RevkVA", "RevModelRevionID", "RevFamily", "RevModelType",
    "Order_Number_TextField", "Client_ID_TextField",
  ];

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
  const norm = (v) => (v === null || v === undefined || v === "") ? "" : String(v).trim();
  const items = base + "/_api/web/lists(guid'" + OI + "')/items";

  /* ---- 0. the list's own versioning settings ------------------------------ */
  const list = await J(base + "/_api/web/lists(guid'" + OI + "')"
    + "?$select=Title,EnableVersioning,EnableMinorVersions,MajorVersionLimit,ItemCount,Created");
  console.log("=== list: " + list.Title + " ===");
  console.log("  list Created       " + list.Created
    + "   <-- no item in it can hold a version older than this");
  console.log("  EnableVersioning   " + list.EnableVersioning);
  console.log("  MajorVersionLimit  " + list.MajorVersionLimit);
  console.log("  ItemCount          " + list.ItemCount + "\n");

  /* ---- 1. probe which candidate fields actually exist --------------------- */
  const ok = [], bad = [];
  for (const f of LOOKUPS.concat(SYNCED)) {
    try { await J(items + "?$select=Id," + f + "&$top=1"); ok.push(f); }
    catch (e) { bad.push(f); }
  }
  console.log("=== field probe ===");
  console.log("  usable  (" + ok.length + "): " + ok.join(", "));
  console.log("  REJECTED(" + bad.length + "): " + (bad.join(", ") || "none")
    + (bad.length ? "\n    ^ these internal names do not exist on this list. Do not trust any doc that lists them." : ""));
  const TRACKED = ok;
  const liveLookups = LOOKUPS.filter(f => ok.indexOf(f) >= 0);
  const liveSynced  = SYNCED.filter(f => ok.indexOf(f) >= 0);
  if (!TRACKED.length) { console.error("ABORT: no usable fields."); return; }
  console.log("");

  /* ---- 2. the units of this order ----------------------------------------- */
  const all = await page(items + "?$select=Id,Title,Created,Modified," + TRACKED.join(",") + "&$top=500");
  if (!all.length) { console.error("ABORT: read 0 units."); return; }
  const units = ORDER ? all.filter(u => norm(u.Title).indexOf(ORDER) === 0) : all;
  console.log("=== order " + (ORDER || "(all)") + ": " + units.length + " of " + all.length + " units ===");
  if (!units.length) {
    console.log("  no unit Title starts with " + ORDER + ". Titles look like: "
      + all.slice(0, 5).map(u => u.Title).join(", "));
    return;
  }

  for (const u of units) {
    const lk = liveLookups.filter(f => norm(u[f]));
    const sy = liveSynced.filter(f => norm(u[f]));
    console.log("  Id " + String(u.Id).padStart(5) + "  " + norm(u.Title).padEnd(14)
      + "  created " + String(u.Created).slice(0, 10)
      + "  lookups " + lk.length + "/" + liveLookups.length
      + "  synced " + sy.length + "/" + liveSynced.length
      + (lk.length && !sy.length ? "   <-- lookups set, synced blank = never reached by an N3 run" : "")
      + (!lk.length ? "   <-- NO parent lookup at all = invisible to every sync flow" : ""));
  }
  console.log("");

  /* ---- 3. per unit: every stored version ---------------------------------- */
  for (const u of units) {
    const item = await J(items + "(" + u.Id + ")?$select=Id,Title,Created,Modified,"
      + "Author/Title,Editor/Title,AuthorId,EditorId," + TRACKED.join(",") + "&$expand=Author,Editor");

    console.log("---------------------------------------------------------------");
    console.log("Id " + item.Id + "   " + item.Title);
    console.log("  Created  " + item.Created + "  AuthorId " + item.AuthorId
      + "  " + (item.Author && item.Author.Title));
    console.log("  Modified " + item.Modified + "  EditorId " + item.EditorId
      + "  " + (item.Editor && item.Editor.Title));
    const setNow = TRACKED.filter(f => norm(item[f]));
    console.log("  parent fields populated now: " + (setNow.length ? setNow.join(", ") : "NONE"));

    let versions = [];
    try { versions = await page(items + "(" + u.Id + ")/versions?$top=200"); }
    catch (e) { console.log("  versions: UNREADABLE -- " + e.message); continue; }

    versions = versions.slice().reverse();   // SharePoint returns newest first
    console.log("  versions stored: " + versions.length);

    let everSet = false, clearedAt = null, prev = null;
    for (const v of versions) {
      const ed = v.Editor;
      const who = ed && (ed.LookupValue || ed.Title || ed) || "?";
      const changes = [];
      for (const f of TRACKED) {
        const now = norm(v[f]), was = prev ? norm(prev[f]) : null;
        if (prev && now !== was) changes.push(f + ": " + (was || "(blank)") + " -> " + (now || "(blank)"));
        if (!prev && now) changes.push(f + " = " + now);
      }
      if (TRACKED.some(f => norm(v[f]))) everSet = true;
      if (prev && TRACKED.some(f => norm(prev[f]) && !norm(v[f]))) clearedAt = v.VersionLabel;
      console.log("    v" + v.VersionLabel + "  " + v.Created + "  " + who
        + "  " + (changes.length ? changes.join(" | ") : "(no change in tracked fields)"));
      prev = v;
    }

    let verdict;
    if (clearedAt) verdict = "ERASED -- cleared at v" + clearedAt;
    else if (everSet) verdict = "filled in history and still filled";
    else if (versions.length <= 1) verdict = "NEVER FILLED -- only one version exists, so no write ever touched these fields";
    else verdict = "NEVER FILLED -- blank across all " + versions.length + " versions";
    console.log("  VERDICT: " + verdict);

    if (versions.length) {
      const first = versions[0];
      if (new Date(first.Created) < new Date(list.Created)) {
        console.log("  🔴 IMPOSSIBLE: v" + first.VersionLabel + " is stamped " + first.Created
          + " but the LIST was created " + list.Created
          + " -- that version predates the list it lives in.");
      }
      if (String(first.Created).slice(0, 4) !== String(item.Created).slice(0, 4)) {
        console.log("  ANOMALY: v" + first.VersionLabel + " stamped " + first.Created
          + " vs the item's own Created " + item.Created);
      }
      /* The decisive artifact: what SharePoint actually stores, uninterpreted.
         If the pane shows a date this payload does not contain, the pane is not
         rendering this item's versions and the whole reading is void. */
      if (RAW) {
        console.log("  --- raw v" + first.VersionLabel + ", verbatim ---");
        for (const k of Object.keys(first).sort()) {
          const val = first[k];
          if (val === null || val === "") continue;
          console.log("      " + k.padEnd(34) + " " + (typeof val === "object" ? JSON.stringify(val) : val));
        }
      }
    }
  }
})();
