/* X21 -- READ-ONLY. How many units are missing their synced parent data, and
   which orders are they on?

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.

   Writes nothing. Re-runnable. Whole-list scan; takes a few seconds.

   WHY
     Two independent defects produce the SAME symptom -- a unit whose parent
     lookups are set but whose Ord* / Mdl* / Rev* columns are blank, with nothing
     in its version history because no write ever happened:

       1. THE FAN-OUT RACE. The N3 flows read their child set ONCE
          (`Get_units_of_this_parent`) and the `Apply to each` writes trail that
          read by several seconds. A unit created in between is outside the loop
          forever. Measured on order 22169: units created 17:40:12-25 were
          skipped by a read that ran at 17:40:07-12, while units created up to
          17:40:07 were written at 17:40:13-22.
          See docs/n3-fanout-race-2026-09-21.md.

       2. SAVE CONFLICT. All four N3 flows write to the SAME Order Items row,
          so two of them firing off one order collide on `Update item`:
            {"status":400,"message":"Save Conflict ... changes conflict with
             those made concurrently by another user"}
          🔴 None of the four definitions sets a `retryPolicy`, and the Logic
          Apps default retries only 408/429/5xx -- a 400 is a client error and
          is NOT retried. So the write is lost permanently, the run is marked
          Failed, and nobody is watching run history.

     Neither self-heals: the N3 flows trigger on the PARENT, so a missed child
     stays missed until somebody happens to edit its Order or Model.

   ⚠️ COLUMN NAMES ARE READ FROM THE PLATFORM, NOT FROM A DOC.
     docs/n3-parent-sync-flow-spec.md lists `OrdOrderNumber` and `OrdQty`, and
     neither exists on the list -- a $select naming them returns 400, which
     `j.value||[]` would turn into "0 rows" and read as "nothing wrong". This
     uses the _api/v2.0 columns endpoint, the one route confirmed to work on
     this tenant (_api/web/lists/.../fields HANGS here -- four 45s timeouts).
*/
(async () => {
  const base   = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI     = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const GROUPS = { Ord: "Order", Mdl: "Models", Rev: "Model Revisions", Cli: "Clients" };
  const FK     = { Ord: "OrderNumberId", Mdl: "ModelId", Rev: "ModelRevisionId", Cli: "ClientId" };

  /* 🔴 A prefix match is NOT enough, and the first run of this script proved it.
     `OrderNumber` and `Order_Number_TextField` both begin with "Ord", and
     `Client` / `Client_ID_TextField` both begin with "Cli" -- but they are the
     LOOKUP and its mirror, not N3 synced columns, and they are populated on
     essentially every row. Sweeping them into the group made "every column in
     this group is blank" impossible to satisfy, so Ord* and Cli* reported
     0 and 1 gaps when the real answer was unknown.
     The obvious fix -- require an uppercase letter after the prefix -- is wrong
     too: `RevkVA` has a lowercase k. So the exclusions are named outright. */
  const NOT_SYNCED = ["OrderNumber", "Order_Number_TextField", "Client", "Client_ID_TextField"];

  /* A Boolean column cannot distinguish "never written" from "written false",
     and SharePoint hands back `false` either way -- so counting one as
     populated hides a gap. They are excluded from the evidence test below. */
  const isEvidence = (v) => typeof v !== "boolean" && v !== null && v !== undefined && String(v).trim() !== "";

  /* The one column per group that a healthy unit essentially always carries.
     Sanity numbers from docs/n3-parent-sync-flow-spec.md after the R3 run:
     MdlModelID 1,008 · RevkVA 1,006 · OrdOrderNumber 1,013 of 1,117 rows. */
  const SENTINEL = { Ord: "OrdOrderDate", Mdl: "MdlModelID", Rev: "RevkVA", Cli: "CliLeadTimeWeeks" };

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

  /* ---- 1. the real column names ------------------------------------------ */
  const cols = await J(base + "/_api/v2.0/sites/root/lists/" + OI + "/columns");
  const all = (cols.value || []).map(c => c.name);
  if (!all.length) { console.error("ABORT: read 0 columns."); return; }
  const inGroup = {}, dropped = [];
  for (const g of Object.keys(GROUPS)) {
    inGroup[g] = all.filter(n => {
      if (n.indexOf(g) !== 0 || n === g) return false;
      if (NOT_SYNCED.indexOf(n) >= 0) { dropped.push(n); return false; }
      return true;
    });
  }
  console.log("=== synced parent columns found on the list ===");
  for (const g of Object.keys(GROUPS))
    console.log("  " + g + "* (" + GROUPS[g] + "): " + inGroup[g].length + "   " + inGroup[g].join(", "));
  console.log("  excluded as lookup/mirror, not N3 synced: " + dropped.join(", "));
  console.log("");

  /* ---- 2. read every unit, chunking $select to stay under URL limits ------ */
  const need = ["Id", "Title", "Created", "Order_Number_TextField"]
    .concat(Object.values(FK))
    .concat(Object.keys(GROUPS).reduce((a, g) => a.concat(inGroup[g]), []));
  const CHUNK = 18;
  const rows = {};
  for (let i = 0; i < need.length; i += CHUNK) {
    const sel = ["Id"].concat(need.slice(i, i + CHUNK).filter(f => f !== "Id"));
    let part;
    try { part = await page(items + "?$select=" + sel.join(",") + "&$top=500"); }
    catch (e) {
      // Narrow it down rather than losing the whole chunk to one bad name.
      console.log("  chunk failed (" + e.message + "), probing it field by field");
      part = [];
      for (const f of sel) {
        if (f === "Id") continue;
        try {
          const one = await page(items + "?$select=Id," + f + "&$top=500");
          for (const r of one) { rows[r.Id] = rows[r.Id] || { Id: r.Id }; rows[r.Id][f] = r[f]; }
        } catch (e2) { console.log("    REJECTED: " + f); }
      }
      continue;
    }
    for (const r of part) { rows[r.Id] = Object.assign(rows[r.Id] || {}, r); }
  }
  const units = Object.values(rows);
  if (!units.length) { console.error("ABORT: read 0 units."); return; }
  console.log("units read: " + units.length + "\n");

  /* ---- 3. a gap = the lookup is SET but every column of that group is blank */
  const gaps = {};
  for (const g of Object.keys(GROUPS)) {
    if (!inGroup[g].length) continue;
    gaps[g] = units.filter(u => norm(u[FK[g]]) && !inGroup[g].some(f => isEvidence(u[f])));
  }

  console.log("=== gaps: lookup set, not one non-Boolean column in the group populated ===");
  for (const g of Object.keys(gaps)) {
    const linked = units.filter(u => norm(u[FK[g]])).length;
    console.log("  " + g + "*  " + String(gaps[g].length).padStart(5) + " of " + linked
      + " units that HAVE a " + GROUPS[g] + " lookup");
  }
  console.log("");

  /* A second, more sensitive reading. The strict test above misses a unit that
     got SOME of its group -- a partial write, or a conflict that landed one
     flow and lost another. The sentinel catches those; it over-reports when a
     parent genuinely has no value, so the two numbers are shown side by side
     rather than one replacing the other. */
  console.log("=== sentinel check: lookup set but the group's key column blank ===");
  for (const g of Object.keys(gaps)) {
    const s = SENTINEL[g];
    if (inGroup[g].indexOf(s) < 0) { console.log("  " + g + "*  sentinel " + s + " not on this list -- skipped"); continue; }
    const miss = units.filter(u => norm(u[FK[g]]) && !isEvidence(u[s]));
    const extra = miss.filter(m => gaps[g].indexOf(m) < 0);
    console.log("  " + g + "*  " + String(miss.length).padStart(5) + " missing " + s
      + (extra.length ? "   (" + extra.length + " of them have SOME group data = partial write: "
          + extra.slice(0, 25).map(u => u.Id).join(",") + (extra.length > 25 ? ",…" : "") + ")" : ""));
  }
  console.log("");

  /* ---- 4. group the damage by order, so it can be fixed an order at a time */
  const orderOf = (u) => norm(u.Order_Number_TextField) || ("lookupId " + norm(u.OrderNumberId));
  for (const g of Object.keys(gaps)) {
    if (!gaps[g].length) continue;
    const by = {};
    for (const u of gaps[g]) (by[orderOf(u)] = by[orderOf(u)] || []).push(u);
    const keys = Object.keys(by).sort();
    console.log("=== " + g + "* missing, " + gaps[g].length + " units across " + keys.length + " orders ===");
    for (const k of keys) {
      const list = by[k].sort((a, b) => a.Id - b.Id);
      const total = units.filter(u => orderOf(u) === k).length;
      const dates = list.map(u => String(u.Created).slice(0, 10));
      console.log("  order " + k.padEnd(10) + " " + String(list.length).padStart(3) + " of " + String(total).padStart(3)
        + " units   created " + dates[0] + (dates[0] === dates[dates.length - 1] ? "" : ".." + dates[dates.length - 1])
        + (list.length < total ? "   <-- PARTIAL: same order, some units fine = race or save conflict" : "")
        + "\n      ids " + list.map(u => u.Id).join(",")
        + "\n      " + list.map(u => norm(u.Title)).join(", "));
    }
    console.log("");
  }

  /* A whole order missing is a different animal from a partial one: partial
     means the flow ran and lost some rows, whole means it never ran at all. */
  console.log("=== read this before fixing ===");
  console.log("  PARTIAL orders  -> the flow ran and lost rows. Race, or a Save Conflict 400.");
  console.log("  WHOLE orders    -> the flow never fanned out to this order at all.");
  console.log("  Per the N3 spec, a re-run will NOT repair these: the connector leaves the");
  console.log("  existing value when handed null, and these are blank rather than wrong.");
  console.log("  They need an explicit write.");
})();
