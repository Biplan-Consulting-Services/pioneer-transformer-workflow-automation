/* X26 -- READ-ONLY. Board E6 (decision 6): were LDs / Engineering Required on these Orders
   BLANKED, CLEARED on purpose, or NEVER SET?

   HOW TO RUN
     Open https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     signed in, F12 -> Console, paste this whole file, Enter. Writes nothing.
     Then `copy(window.x26)` and paste the result back.

   WHY A SNIPPET AND NOT THE CSV
     Both columns are Yes/No (Boolean). A Boolean that was never set is NULL over REST, which
     x25 reports as blank -- but the 2026-09-11 0339 CSV export has 416 False + 41 True and ZERO
     blanks, so the export cannot tell "null" from "False". Only the live value and the item's
     version history can. This reads both.

   WHAT IT PRINTS
     1. List-wide: how many Orders hold true / false / NULL on each column now.
     2. Per listed order: the live value, and every version's value with who and when.
        A version where the value goes true -> null with a human editor = cleared on purpose.
        Null in every version = never set (the unit's value came from somewhere else).
*/
(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const ORD  = "6fe35dfe-2b7d-455a-abe3-056abb386733";
  const ORDERS = ["21982", "21665", "21661", "21981", "22022", "22023", "22024", "22025", "22026",
                  "22027", "22028", "22029", "22030", "21664", "21932",          // LDs: units true
                  "21499", "21523",                                              // LDs: units false
                  "22111", "22088", "22046", "22047", "22048", "22049", "22050",
                  "22051", "22052", "22053",                                     // EngReq: units false
                  "21613", "21749"];                                             // reverse
  const H = { Accept: "application/json;odata=nometadata" };
  const J = async (u) => {
    const r = await fetch(u, { credentials: "include", headers: H });
    if (!r.ok) throw new Error(r.status + " on " + u.slice(0, 160) + " :: " + (await r.text()).slice(0, 200));
    return r.json();
  };
  const page = async (u) => {
    let o = [], g = 0;
    while (u && g++ < 40) { const j = await J(u); o = o.concat(j.value || []); u = j["odata.nextLink"] || null; }
    return o;
  };
  const show = (v) => v === null || v === undefined ? "NULL" : String(v);

  const rows = await page(base + "/_api/web/lists(guid'" + ORD + "')/items?$select="
    + "Id,Order_x0020_Number1,LDs,EngineeringRequired,Modified&$top=500");
  if (!rows.length) { console.error("ABORT: read 0 Orders. A zero-row read is a failed read."); return; }

  const counts = {};
  for (const c of ["LDs", "EngineeringRequired"]) {
    counts[c] = { true: 0, false: 0, NULL: 0 };
    for (const r of rows) counts[c][show(r[c])]++;
  }
  console.log("=== 1. list-wide, " + rows.length + " Orders ===");
  console.table(counts);

  const byNum = new Map();
  for (const r of rows) {
    const k = String(r.Order_x0020_Number1 || "").trim();
    byNum.set(k, (byNum.get(k) || []).concat(r));
  }

  const out = [];
  console.log("\n=== 2. per order: live value + version history ===");
  for (const num of ORDERS) {
    const hit = byNum.get(num) || [];
    if (hit.length !== 1) { console.log(num + ": " + hit.length + " Orders carry this number - skipped"); out.push({ order: num, error: hit.length + " matches" }); continue; }
    const r = hit[0];
    let versions = [];
    try {
      versions = await page(base + "/_api/web/lists(guid'" + ORD + "')/items(" + r.Id + ")/versions?$top=100");
    } catch (e) { console.log(num + ": versions unreadable - " + e.message); }
    const hist = versions.map(v => ({
      version: v.VersionLabel, modified: v.Modified,
      editor: (v.Editor && (v.Editor.LookupValue || v.Editor.Email)) || "",
      LDs: show(v.LDs), EngineeringRequired: show(v.EngineeringRequired),
    }));
    const row = { order: num, id: r.Id, liveLDs: show(r.LDs), liveEngReq: show(r.EngineeringRequired),
                  modified: r.Modified, versions: hist.length,
                  LDsEverSet: hist.some(h => h.LDs !== "NULL"), EngReqEverSet: hist.some(h => h.EngineeringRequired !== "NULL") };
    out.push(Object.assign({ history: hist }, row));
    console.log("--- " + num + " (id " + r.Id + ")  live LDs=" + row.liveLDs + "  EngReq=" + row.liveEngReq
                + "  versions=" + hist.length);
    console.table(hist);
  }
  console.log("\n=== summary ===");
  console.table(out.map(({ history, ...rest }) => rest));
  window.x26 = { counts, orders: out };
  console.log("copy(window.x26) puts the full result on the clipboard.");
})();
