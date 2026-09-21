/* X19 -- READ-ONLY. Was a unit's parent information ERASED, or NEVER FILLED?

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
        (if Chrome refuses the paste, type  allow pasting  first)
     3. Read the VERDICT line per unit.

   Writes nothing. Re-runnable.

   WHY THIS EXISTS RATHER THAN THE VERSION HISTORY PANEL
     The modern list "Version history" pane is not a reliable witness here:

     - If `EnableVersioning` is FALSE on the list, SharePoint shows exactly ONE
       entry -- the current state -- stamped with the item's `Modified` /
       `Editor`. It looks like "one modification, nothing changed" no matter how
       many times the row was actually written. This script prints the list's
       versioning settings FIRST so that reading is never in doubt.
     - `MajorVersionLimit` is 50 on these lists (N5). Past 50 writes SharePoint
       trims the OLDEST versions, so v1.0 -- the creation -- is the first thing
       to disappear on a row the flows have touched a lot.
     - The pane diffs rendered values, so a field going from empty to empty, or
       a lookup whose target it cannot resolve, shows as "nothing changed".

     So: read /versions over REST and diff the parent fields ourselves.

   WHAT "PARENT INFORMATION" MEANS ON Order Items -- it is TWO different things,
   filled by two different mechanisms, and they fail for different reasons:

     (a) the LOOKUPS      OrderNumberId / ModelId / ModelRevisionId / ClientId
                          set when the row is created. If these are empty the
                          unit is invisible to the N3 sync flows entirely --
                          they fan out with `<lookup>Id eq <parent ID>`.
     (b) the 47 SYNCED    Ord* / Mdl* / Rev* columns, written ONLY by the four
         parent columns   N3 flows, which trigger on the PARENT list. Nothing
                          fills them when a CHILD is created. Their current
                          values came from the one-off R3 backfill (2026-09-08).

   (b) is why a unit created after that backfill can be permanently blank while
   nothing at all appears in its history: there was never a write to record.
*/
(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";   // Order Items

  // Leave empty to auto-pick the affected units. Or set explicit ids, e.g. [1128, 1163].
  const UNITS = [];
  const MAX_AUTO = 10;          // how many auto-picked units to probe in detail
  const RAW = true;             // dump the first version's stored object verbatim

  const LOOKUPS = ["OrderNumberId", "ModelId", "ModelRevisionId", "ClientId"];

  // A representative slice of the synced parent columns, one per parent list.
  // Enough to tell "filled then cleared" from "never filled" without pulling 47.
  const SYNCED = [
    "OrdOrderNumber", "OrdOrderDate", "OrdOrderStatus", "OrdQty",
    "MdlModelID", "MdlEstimatedEffort",
    "RevkVA", "RevModelRevionID", "RevFamily",
  ];

  const TRACKED = LOOKUPS.concat(SYNCED);

  const J = async (u) => {
    const r = await fetch(u, { credentials: "include",
      headers: { Accept: "application/json;odata=nometadata" } });
    if (!r.ok) throw new Error(r.status + " " + r.statusText + "  <- " + u);
    return r.json();
  };
  const page = async (u) => {
    let out = [], guard = 0;
    while (u && guard++ < 40) { const j = await J(u); out = out.concat(j.value || []); u = j["odata.nextLink"] || null; }
    return out;
  };
  const norm = (v) => (v === null || v === undefined || v === "") ? "" : String(v).trim();

  /* ---- 0. the list's own versioning settings -------------------------------
     Without this every reading of a version history below is a guess. */
  const list = await J(base + "/_api/web/lists(guid'" + OI + "')"
    + "?$select=Title,EnableVersioning,EnableMinorVersions,MajorVersionLimit,ItemCount");
  console.log("=== list: " + list.Title + " ===");
  console.log("  EnableVersioning   " + list.EnableVersioning
    + (list.EnableVersioning === false
        ? "   <-- NO HISTORY IS KEPT. The single entry the pane shows is the CURRENT"
          + "\n                            state, stamped with Modified/Editor. It is not a creation record."
        : ""));
  console.log("  MajorVersionLimit  " + list.MajorVersionLimit
    + "   <-- past this, the OLDEST versions (incl. v1.0) are trimmed");
  console.log("  ItemCount          " + list.ItemCount + "\n");

  /* ---- 1. pick the units --------------------------------------------------- */
  let targets = UNITS;
  if (!targets.length) {
    const all = await page(base + "/_api/web/lists(guid'" + OI + "')/items"
      + "?$select=Id,Title,Created,Modified," + TRACKED.join(",") + "&$top=500");
    if (!all.length) { console.error("ABORT: read 0 units -- a failed $select returns 400 and reads as zero rows."); return; }
    console.log("units read: " + all.length);

    const noLookups = all.filter(u => LOOKUPS.every(f => !norm(u[f])));
    const noSynced  = all.filter(u => SYNCED.every(f => !norm(u[f])));
    const bothBlank = all.filter(u => LOOKUPS.every(f => !norm(u[f])) && SYNCED.every(f => !norm(u[f])));

    console.log("  every parent LOOKUP empty        " + noLookups.length);
    console.log("  every sampled SYNCED col empty   " + noSynced.length);
    console.log("  both                             " + bothBlank.length);

    // Lookups set but synced columns blank == created after the backfill and
    // never reached by an N3 run. That is the structural gap, not data loss.
    const missedByN3 = all.filter(u => LOOKUPS.some(f => norm(u[f])) && SYNCED.every(f => !norm(u[f])));
    console.log("  lookups SET but synced blank     " + missedByN3.length
      + "   <-- created after the R3 backfill, no parent edit since");
    if (missedByN3.length) {
      const d = missedByN3.map(u => String(u.Created).slice(0, 10)).sort();
      console.log("       their Created range: " + d[0] + " .. " + d[d.length - 1]);
    }

    const pool = noSynced.length ? noSynced : noLookups;
    targets = pool.slice(0, MAX_AUTO).map(u => u.Id);
    console.log("\nprobing " + targets.length + " of " + pool.length + " affected units in detail\n");
  }

  /* ---- 2. per unit: current state, then every version ---------------------- */
  for (const id of targets) {
    const item = await J(base + "/_api/web/lists(guid'" + OI + "')/items(" + id + ")"
      + "?$select=Id,Title,Created,Modified,Author/Title,Editor/Title," + TRACKED.join(",")
      + "&$expand=Author,Editor");

    console.log("---------------------------------------------------------------");
    console.log("Id " + item.Id + "   " + item.Title);
    console.log("  Created  " + item.Created + "   by " + (item.Author && item.Author.Title));
    console.log("  Modified " + item.Modified + "  by " + (item.Editor && item.Editor.Title));
    const setNow = TRACKED.filter(f => norm(item[f]));
    console.log("  parent fields populated now: " + (setNow.length ? setNow.join(", ") : "NONE"));

    let versions = [];
    try {
      versions = await page(base + "/_api/web/lists(guid'" + OI + "')/items(" + id + ")/versions?$top=200");
    } catch (e) {
      console.log("  versions: UNREADABLE -- " + e.message);
      continue;
    }
    // SharePoint returns newest first; walk oldest -> newest so diffs read forward.
    versions = versions.slice().reverse();
    console.log("  versions stored: " + versions.length);

    let everSet = false, clearedAt = null, prev = null;
    for (const v of versions) {
      const who = v.Editor && (v.Editor.LookupValue || v.Editor) || "?";
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

    // The question the user actually asked.
    let verdict;
    if (clearedAt) verdict = "ERASED -- cleared at v" + clearedAt;
    else if (everSet) verdict = "was filled at some point and is still filled in history; check trimming";
    else if (list.EnableVersioning === false) verdict = "NEVER FILLED (but versioning is OFF -- history cannot corroborate)";
    else if (versions.length <= 1) verdict = "NEVER FILLED -- the row has only its creation version, no write ever touched these fields";
    else verdict = "NEVER FILLED -- present across all " + versions.length + " versions, blank in every one";
    console.log("  VERDICT: " + verdict);

    // The anomaly worth naming out loud.
    if (versions.length) {
      const first = versions[0];
      if (String(first.Created).slice(0, 4) !== String(item.Created).slice(0, 4)) {
        console.log("  ANOMALY: v" + first.VersionLabel + " is stamped " + first.Created
          + " but the item's own Created is " + item.Created
          + " -- the version stamp does not come from this row's creation.");
      }

      /* The decisive artifact. If the pane shows a date the REST payload does
         not contain, the pane is rendering something other than this item's
         versions and the whole reading has to be thrown out. Nothing here is
         interpreted -- it is what SharePoint actually stores. */
      if (RAW) {
        console.log("  --- raw v" + first.VersionLabel + ", verbatim ---");
        for (const k of Object.keys(first).sort()) {
          const v = first[k];
          if (v === null || v === "") continue;
          console.log("      " + k.padEnd(34) + " " + (typeof v === "object" ? JSON.stringify(v) : v));
        }
      }
    }
  }
})();
