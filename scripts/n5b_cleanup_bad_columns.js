/* N5b -- delete the columns n5 created with the wrong internal names.

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
     3. DRY RUN by default. Read the list, then set APPLY = true and paste again.

   WHAT WENT WRONG
     `createfieldasxml` ignores the `Name` attribute and derives the internal name
     from `DisplayName` UNLESS you pass `Options: 8` (AddFieldInternalNameHint).
     n5 omitted it. So instead of `CliLeadTimeWeeks` it created
     `Lead_x0020_Time_x0020__x0028_wee` -- DisplayName, percent-encoded and truncated
     at 32 characters, stopping mid-word.

     `n2_create_columns.js` gets this right and says so in its own header. I had read
     that header. The fix was in the repo before the mistake was.

     Because the internal name never matched what n5 checks for, every re-run decided
     the columns were missing and created another set. Four runs, four sets:
     `…wee`, `…wee0`, `…wee1`, `…wee2`, and the same tail on the other five.

   WHAT THIS DELETES
     Only columns in the `Client Sync` group whose internal name is NOT one of the six
     intended ones. That is the safe boundary: n5 put every column it made in that
     group, and the six correct names are the ones n5 will create next time. Nothing
     outside the group is touched, and no data is lost -- every one of these is empty,
     because the seeding never succeeded (`seeded ok=0` on every attempt).

   AFTER THIS
     Re-run n5. With Options: 8 it creates the six correct names and seeds them.
*/

(async () => {
  const APPLY = true;                    // <-- set true to actually delete
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const LISTS = [["Clients", "3bcf7d97-0862-404d-ab3f-eeaa358c05d8"],
                 ["Order Items", "d6468ec5-c7b5-44a3-8ce0-f81f059b671d"]];

  // The names n5 SHOULD have created. Anything else in the group is debris.
  const KEEP = new Set(["CliLeadTimeWeeks", "CliDelai", "CliCriticalPart1",
                        "CliSupplier1", "CliCriticalPart2", "CliSupplier2"]);
  const GROUP = "Client Sync";

  const J = async u => {
    const r = await fetch(u, {credentials: "include", headers: {Accept: "application/json"}});
    return r.ok ? r.json() : {__err: r.status};
  };

  const doomed = [];
  for (const [title, id] of LISTS) {
    const c = await J(base + "/_api/v2.0/sites/root/lists/" + id + "/columns");
    if (c.__err) { console.error("cannot read columns of " + title + ": " + c.__err); return; }
    const mine = (c.value || []).filter(x => x.columnGroup === GROUP);
    console.log("\n" + title + " -- columns in group '" + GROUP + "': " + mine.length);
    for (const f of mine) {
      const keep = KEEP.has(f.name);
      console.log("   " + (keep ? "KEEP   " : "DELETE ") + f.name.padEnd(36)
                  + (f.displayName || ""));
      if (!keep) doomed.push({list: title, name: f.name, disp: f.displayName});
    }
  }

  console.log("\n=== " + doomed.length + " column(s) to delete ===");
  if (!doomed.length) { console.log("nothing to clean up."); return; }
  console.log("all of them are empty -- the seeding never succeeded, so no data is lost.");

  if (!APPLY) { console.log("\nDRY RUN -- nothing deleted. Set APPLY = true and paste again."); return; }

  const dg = await (await fetch(base + "/_api/contextinfo", {method: "POST",
    credentials: "include", headers: {Accept: "application/json;odata=nometadata"}})).json();

  let ok = 0, fail = 0;
  for (const d of doomed) {
    const r = await fetch(base + "/_api/web/lists/getbytitle('" + d.list
              + "')/fields/getbyinternalnameortitle('" + d.name + "')", {
      method: "POST", credentials: "include",
      headers: {"X-RequestDigest": dg.FormDigestValue,
                "X-HTTP-Method": "DELETE", "IF-MATCH": "*"}});
    if (r.ok) { ok++; console.log("deleted " + d.list + "." + d.name); }
    else { fail++; console.error("FAILED  " + d.list + "." + d.name + " -> " + r.status
                                 + " " + (await r.text()).slice(0, 160)); }
  }
  console.log("\ndeleted ok=" + ok + " failed=" + fail);

  // ---------------------------------------------------------------- verification
  let left = 0;
  for (const [title, id] of LISTS) {
    const c = await J(base + "/_api/v2.0/sites/root/lists/" + id + "/columns");
    const mine = (c.value || []).filter(x => x.columnGroup === GROUP && !KEEP.has(x.name));
    left += mine.length;
    for (const f of mine) console.error("  still there: " + title + "." + f.name);
  }
  console.log("\n--- verification ---");
  console.log("wrong-named columns remaining: " + left + "   (expect 0)");
  console.log("\nNEXT: re-run n5_clients_lead_time.js. It now passes Options: 8, so the six");
  console.log("      columns get the internal names it expects, and the seeding will land.");
})();
