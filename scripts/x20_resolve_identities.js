/* X20 -- READ-ONLY. Who are the identities stamped on these lists, really?

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
        (if Chrome refuses the paste, type  allow pasting  first)

   Writes nothing. Re-runnable.

   WHY
     A name in Created By / Modified By is NOT proof that person did anything.
     SharePoint stores an integer (`AuthorId` / `EditorId`) and renders it by
     looking the id up in the site's hidden **User Information List**. That list:

       - keeps former employees FOREVER, long after the AAD account is deleted;
       - is populated per SITE COLLECTION, so it carries identities from whoever
         has ever touched this site -- this tenant is `ermcopower`, shared with
         the parent company, so a name unknown at Pioneer Granby is expected;
       - carries app/service principals (Power Automate connections, Power Apps,
         the SharePoint app-only token) that render as an ordinary person -- the
         CONNECTION OWNER, not whoever triggered the flow;
       - has its own `Created` date, which is when that identity FIRST appeared
         in this site -- often years before the row it is stamped on.

     So "a person who is not in the company, dated 2023" has mundane candidates
     that must be eliminated before anything is treated as corruption.

   IT ALSO CLOSES AN OPEN QUESTION
     docs/model-revision-modelid-repair-2026-09-14.md leaves this hanging:
     "`EditorId 106` accounts for 43 of 45 [corrupt Model Revisions rows]".
     Nobody has ever resolved 106 to a name. If 106 is the same identity stamped
     on the parent-less Order Items rows, the two anomalies are one anomaly.
*/
(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const LISTS = {
    "Order Items":     "d6468ec5-c7b5-44a3-8ce0-f81f059b671d",
    "Order":           "6fe35dfe-2b7d-455a-abe3-056abb386733",
    "Models":          "b43a5140-0f9d-4ac1-9019-43b897074224",
    "Model Revisions": "e2ff8703-b590-4648-b181-9b47cf3883ba",
  };

  const NAME_HINT = "dalpe";   // substring to hunt for, lowercased
  const SUSPECT_IDS = [106];   // ids to resolve explicitly (from the x17 histogram)

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

  /* ---- 1. every identity the site knows ----------------------------------- */
  const users = await page(base + "/_api/web/siteusers"
    + "?$select=Id,Title,LoginName,Email,PrincipalType,IsSiteAdmin&$top=500");
  if (!users.length) { console.error("ABORT: read 0 site users."); return; }
  const byId = {};
  for (const u of users) byId[u.Id] = u;
  console.log("=== site users known to this site collection: " + users.length + " ===\n");

  // What kind of principal is it? This is the part that separates a human from
  // a flow's connection owner from a service account.
  const kind = (u) => {
    const l = (u.LoginName || "");
    if (u.PrincipalType === 4) return "SECURITY GROUP";
    if (u.PrincipalType === 8) return "SP GROUP";
    if (l.indexOf("|system") >= 0 || u.Title === "System Account") return "SYSTEM ACCOUNT";
    if (l.indexOf("c:0(.s|true") === 0) return "EVERYONE";
    if (l.indexOf("i:0i.t|") === 0) return "EXTERNAL / GUEST";
    if (l.indexOf("c:0t.c|tenant|") === 0) return "AAD GROUP";
    if (l.indexOf("|app@sharepoint") >= 0 || l.indexOf("c:0i.t|") === 0) return "APP PRINCIPAL";
    if (l.indexOf("i:0#.f|membership|") === 0) return "AAD user";
    return "? " + l.slice(0, 30);
  };

  /* The UIL row's own Created tells you when the identity first touched this
     site -- frequently the year that shows up on a puzzling old stamp. */
  let uil = [];
  try {
    uil = await page(base + "/_api/web/lists/getbytitle('User Information List')/items"
      + "?$select=Id,Title,EMail,Created,Modified,Deleted&$top=500");
  } catch (e) {
    console.log("(User Information List not readable directly: " + e.message + ")\n");
  }
  const uilById = {}; for (const r of uil) uilById[r.Id] = r;

  const show = (id) => {
    const u = byId[id], r = uilById[id];
    if (!u && !r) return "  id " + id + "  <-- NOT IN THE SITE USER LIST (orphaned stamp)";
    const t = (u && u.Title) || (r && r.Title) || "?";
    return "  id " + String(id).padStart(4) + "  " + t.padEnd(28)
      + "  " + (u ? kind(u) : "not in siteusers -- DELETED USER, row kept in UIL")
      + "\n        email   " + ((u && u.Email) || (r && r.EMail) || "(none)")
      + "\n        login   " + ((u && u.LoginName) || "(n/a)")
      + (r ? "\n        UIL row created " + r.Created
             + (r.Deleted ? "   *** MARKED DELETED ***" : "") : "");
  };

  /* ---- 2. hunt the name --------------------------------------------------- */
  console.log("=== identities matching \"" + NAME_HINT + "\" ===");
  const hits = users.filter(u => ((u.Title || "") + " " + (u.Email || "") + " " + (u.LoginName || ""))
    .toLowerCase().indexOf(NAME_HINT) >= 0);
  const uilHits = uil.filter(r => ((r.Title || "") + " " + (r.EMail || ""))
    .toLowerCase().indexOf(NAME_HINT) >= 0 && !hits.some(h => h.Id === r.Id));
  if (!hits.length && !uilHits.length) console.log("  none in siteusers or the UIL");
  for (const u of hits) console.log(show(u.Id));
  for (const r of uilHits) console.log(show(r.Id) + "\n        ^ present in UIL but NOT in siteusers = account removed from the site");
  console.log("");

  console.log("=== explicitly resolved suspect ids ===");
  for (const id of SUSPECT_IDS) console.log(show(id));
  console.log("");

  /* ---- 3. who is actually stamped on each list ---------------------------- */
  for (const name of Object.keys(LISTS)) {
    let rows = [];
    try {
      rows = await page(base + "/_api/web/lists(guid'" + LISTS[name] + "')/items"
        + "?$select=Id,Created,Modified,AuthorId,EditorId&$top=500");
    } catch (e) { console.log("=== " + name + ": unreadable -- " + e.message + "\n"); continue; }
    if (!rows.length) { console.log("=== " + name + ": 0 rows read -- a failed $select returns 400 and reads as zero.\n"); continue; }

    console.log("=== " + name + "  (" + rows.length + " rows) ===");
    for (const f of ["AuthorId", "EditorId"]) {
      const h = {};
      for (const r of rows) { const k = r[f] == null ? "(null)" : r[f]; h[k] = (h[k] || 0) + 1; }
      const ranked = Object.keys(h).sort((a, b) => h[b] - h[a]);
      console.log("  " + f + ":");
      for (const id of ranked) {
        const u = byId[id], r = uilById[id];
        const t = (u && u.Title) || (r && r.Title) || "UNRESOLVED";
        console.log("    " + String(h[id]).padStart(5) + "  id " + String(id).padStart(4)
          + "  " + t.padEnd(28) + (u ? kind(u) : (r ? "deleted user" : "<-- NOT RESOLVABLE")));
      }
    }

    // Rows whose Modified year predates their Created year are impossible by
    // ordinary editing -- those stamps were written, not earned.
    const impossible = rows.filter(r => r.Created && r.Modified
      && new Date(r.Modified) < new Date(new Date(r.Created).getTime() - 60000));
    if (impossible.length) {
      console.log("  🔴 " + impossible.length + " rows have Modified EARLIER than Created:");
      for (const r of impossible.slice(0, 15)) {
        const e = byId[r.EditorId];
        console.log("      Id " + r.Id + "  Created " + r.Created + "  Modified " + r.Modified
          + "  Editor " + ((e && e.Title) || r.EditorId));
      }
    }
    console.log("");
  }
})();
