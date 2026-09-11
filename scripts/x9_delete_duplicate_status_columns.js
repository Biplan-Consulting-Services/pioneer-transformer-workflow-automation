/* X9 -- delete the duplicate Step Status / Status Date / Step Status Stamped columns.

   HOW TO RUN
     1. Open the site in the browser, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio
     2. F12 -> Console. Paste this whole file. Press Enter.
     3. It runs a DRY RUN first and changes nothing. Read it.
     4. Set APPLY = true and paste again.

   WHAT IS WRONG
     Order Items carries two of each, confirmed over REST 2026-09-11 04:2x:

       StepStatus          "Step Status"          Choice(8)   has the data
       StepStatus0         "Step Status"          Choice(8)   EMPTY
       StatusDate0         "Status Date"          DateTime    EMPTY
       StepStatusStamped0  "Step Status Stamped"  text        EMPTY

     SharePoint appends 0 to the INTERNAL name when a second column is created
     with a display name already in use. The display names are identical, so in
     list settings, the column picker and the view editor the two are
     indistinguishable -- which is how a staff member types into the empty one
     and watches the value disappear from every view and report. Same shape as
     the duplicate `Unit ID` that turned up in the views earlier tonight.

   HOW IT HAPPENED, so a third run does not make StepStatus1
     `n8_split_status.js` was re-run at cutover (runbook 2.5, mandatory -- the
     transfer flow rewrites the composite Status and leaves the split pair
     stale). Its header says column creation "skips what exists". It does not:
     it POSTs the field and reports whatever comes back, and this time all three
     POSTs reported `200 created` against columns that already existed from the
     2026-09-09 run. n8 needs an existence check before the POST, and until it
     has one, EVERY re-run leaves another set behind. Recorded on the roadmap.

   ⚠️ WHY THIS DELETES BY INTERNAL NAME AND NOT FROM THE UI
     The UI offers only display names, and both entries read "Step Status".
     Picking the wrong one destroys 262 rows of real production status that was
     just reconstructed and verified against the workbook. So: internal name
     only, and each target is proven EMPTY over REST immediately before its
     delete, in the same run -- not trusted from this comment.
*/

(async () => {
  const APPLY = true;                   // <-- set true to delete
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI    = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";   // Order Items

  // The suffixed twins, and the sibling each must NOT be confused with.
  const TARGETS = [
    { del: "StepStatus0",        keep: "StepStatus"        },
    { del: "StatusDate0",        keep: "StatusDate"        },
    { del: "StepStatusStamped0", keep: "StepStatusStamped" },
  ];

  const j = async (url, opt) => {
    const r = await fetch(url, opt);
    const t = await r.text();
    if (!r.ok) throw new Error(r.status + " " + t.slice(0, 300));
    return t ? JSON.parse(t) : null;
  };
  const H = { accept: "application/json;odata=nometadata" };

  const digest = async () => (await j(base + "/_api/contextinfo",
    { method: "POST", headers: H })).FormDigestValue;

  // How many rows hold a value in this field? Counted, not sampled: `$top=1`
  // answers "any", and "any" is not the question when the next step is a delete.
  const countNonNull = async (name) => {
    let n = 0, url = base + "/_api/web/lists(guid'" + OI + "')/items"
      + "?$select=Id," + name + "&$filter=" + name + " ne null&$top=2000";
    while (url) {
      const r = await j(url, { headers: H });
      n += (r.value || []).length;
      url = r["odata.nextLink"] || null;
    }
    return n;
  };

  console.log("=== checking each target is empty, and its sibling is not ===");
  const plan = [];
  for (const t of TARGETS) {
    let dn, kn;
    try { dn = await countNonNull(t.del); }
    catch (e) { console.log("  " + t.del + " -- cannot read: " + e.message); continue; }
    try { kn = await countNonNull(t.keep); }
    catch (e) { console.log("  " + t.keep + " -- cannot read: " + e.message); continue; }

    const safe = dn === 0;
    console.log("  " + t.del.padEnd(20) + " rows=" + String(dn).padStart(5)
      + "   |  keep " + t.keep.padEnd(18) + " rows=" + String(kn).padStart(5)
      + "   " + (safe ? "SAFE to delete" : "🔴 HOLDS DATA -- NOT deleting"));
    if (safe) plan.push(t.del);
  }

  if (!plan.length) { console.log("\nnothing safe to delete."); return; }
  if (!APPLY) {
    console.log("\nDRY RUN -- nothing deleted. Would delete: " + plan.join(", "));
    console.log("Set APPLY = true and paste again.");
    return;
  }

  console.log("\n=== deleting ===");
  const d = await digest();
  for (const name of plan) {
    // Re-prove emptiness inside the apply pass. The dry run may have been read
    // minutes ago and this is not an undoable operation.
    const again = await countNonNull(name);
    if (again !== 0) { console.log("  " + name + " now holds " + again + " rows -- SKIPPED"); continue; }
    try {
      await fetch(base + "/_api/web/lists(guid'" + OI + "')/fields/getbyinternalnameortitle('" + name + "')",
        { method: "POST", headers: Object.assign({}, H, {
            "X-RequestDigest": d, "X-HTTP-Method": "DELETE", "IF-MATCH": "*" }) })
        .then(r => { if (!r.ok) throw new Error(r.status); });
      console.log("  deleted " + name);
    } catch (e) { console.log("  FAILED " + name + ": " + e.message); }
  }

  console.log("\n--- verification (trust this, not the delete results) ---");
  const f = await fetch(base + "/_api/v2.0/sites/root/lists/" + OI + "/columns",
    { headers: { accept: "application/json" } }).then(r => r.json());
  const left = (f.value || []).filter(c =>
    /^(StepStatus|StatusDate)/i.test(c.name || ""));
  left.forEach(c => console.log("  " + (c.name || "").padEnd(20)
    + " display=" + JSON.stringify(c.displayName)));
  console.log("\nexpect exactly three: StepStatus, StatusDate, StepStatusStamped");
  console.log("Then re-export Order Items and re-run verify_status_split.py.");
})();
