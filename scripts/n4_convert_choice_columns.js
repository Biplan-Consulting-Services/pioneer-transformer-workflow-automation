/* N4 -- convert the parent-synced Text columns on Order Items into Choice columns
   that mirror their parent exactly, option list AND FillInChoice.

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
        (if Chrome refuses the paste, type  allow pasting  first)
     3. DRY RUN by default. Read the plan, then set APPLY = true and paste again.
     4. It prints an UNDO block (each column's original SchemaXml) before writing,
        re-reads every column afterwards, and compares the data before and after.

   🔴 RUN THIS ONLY IN THE RUNBOOK'S STAGE 4 WINDOW -- after the final transfer run,
   after that flow is deleted, and BEFORE N3 is enabled at 4.2.

   Why that window and not tonight: a Choice column needs `item/X/Value` on the write.
   The transfer flow still writes plain `item/X` and still has one run left. Convert
   before that run and those columns silently stop landing across all ~1,117 rows --
   no error, no failed run, just empty columns. Convert after it is gone and only N3
   needs changing, which is automatic (see THE OTHER HALF below).

   WHAT IT DOES NOT NEED
     A data cleanup first. That was the blocker in the original plan and it does not
     apply, measured 2026-09-10 against the 09-09 exports:

       9 of the 12 columns  -- every value already an option, nothing out of list
       Model Type           -- 564 rows use legacy shorthand (SUBMERSIBLE, PADMOUNT,
                               MALT + SA, MINPAD) that is NOT in the option list, but
                               the parent is FillInChoice="TRUE". Mirror that and the
                               child accepts them exactly as the parent does.
       Order Type           -- reported 5 bad rows in an earlier pass; that was an
                               escaping artifact. The option is `R&amp;D` in the
                               schema XML and the data holds `R&D`. Clean.

     Making the columns strict is a LATER, separate step, after the parent values are
     phased out. This script mirrors permissiveness; it does not impose strictness.

   TWELVE COLUMNS, NOT TEN
     docs/parent-choice-columns-2026-09-08.md plans 10. Two more qualify and the doc
     never mentions them -- `OrdClientDateStatus` and `OrdOrderStatus`, both clean,
     both Choice on the parent. Rather than trust either number, this script DERIVES
     the set: every Order Items column in the `Parent Sync` group that is Text today
     and whose parent column is Choice. It prints what it found; if that is not 12,
     something changed and you should look before applying.

   THE OTHER HALF -- already done, and automatic
     A Choice column also READS BACK as an object, so the change-guard needs
     `?['X']?['Value']` as well as the write key. Both now come from the platform:
     `gen_n3_flows.py` reads the newest `Order Items *.csv` export and emits the right
     shape per column. So after running this:

         1. re-export Order Items  (the generator reads column types from it)
         2. python scripts/gen_n3_flows.py
         3. python scripts/verify_n3_flows.py
         4. re-stage and paste each N3 flow

     Step 1 is not optional. Regenerate from a stale export and you get plain keys
     against Choice columns, which is the silent failure this whole note is about.
     The generator prints which export it used.
*/

(async () => {
  const APPLY = false;                     // <-- set true to actually convert
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const LIST  = "Order Items";
  const IDS = {
    "Order Items":     "d6468ec5-c7b5-44a3-8ce0-f81f059b671d",
    "Order":           "6fe35dfe-2b7d-455a-abe3-056abb386733",
    "Models":          "b43a5140-0f9d-4ac1-9019-43b897074224",
    "Model Revisions": "e2ff8703-b590-4648-b181-9b47cf3883ba",
  };
  // The "<Parent> - <Column>" display-name convention N2 used for the 48.
  const PREFIX = [["Order - ", "Order"], ["Model - ", "Models"],
                  ["Mod. Rev. - ", "Model Revisions"]];

  // ---------------------------------------------------------------- helpers
  const J = async (u, ms) => {
    // _api/web/lists/.../fields HANGS on this tenant (two 45s timeouts, twice, on
    // two separate days). Every call here is bounded so a hang reports instead of
    // freezing the console.
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), ms || 25000);
    try {
      const r = await fetch(u, {credentials: "include", signal: ac.signal,
                                headers: {Accept: "application/json;odata=nometadata"}});
      if (!r.ok) return {__err: r.status + " " + (await r.text()).slice(0, 200)};
      return await r.json();
    } catch (e) {
      return {__err: String(e && e.name === "AbortError" ? "TIMED OUT" : e)};
    } finally { clearTimeout(t); }
  };
  const cols = async (name) => {
    // v2.0 is the read path that works here. The "sites/root" segment is required.
    const j = await J(base + "/_api/v2.0/sites/root/lists/" + IDS[name] + "/columns");
    if (j.__err) { console.error("reading " + name + " columns: " + j.__err); return null; }
    return j.value || [];
  };
  const xe = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                           .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

  // ------------------------------------------------------------- read schemas
  const OI = await cols("Order Items");
  if (!OI || !OI.length) { console.error("ABORT: read 0 Order Items columns."); return; }
  const P = {};
  for (const n of ["Order", "Models", "Model Revisions"]) {
    P[n] = await cols(n);
    if (!P[n] || !P[n].length) { console.error("ABORT: read 0 columns from " + n); return; }
  }
  const byDisp = {};
  for (const n of Object.keys(P)) {
    byDisp[n] = new Map();
    for (const c of P[n]) byDisp[n].set((c.displayName || "").trim(), c);
  }
  console.log("columns read -- Order Items " + OI.length + ", Order " + P["Order"].length
              + ", Models " + P["Models"].length + ", Model Revisions " + P["Model Revisions"].length);

  // ------------------------------------------------------------- the candidates
  const plan = [], skipped = [];
  for (const c of OI) {
    if (c.columnGroup !== "Parent Sync") continue;
    const dn = (c.displayName || "").trim();
    const hit = PREFIX.find(p => dn.startsWith(p[0]));
    if (!hit) { skipped.push([dn, "display name does not follow the convention"]); continue; }
    const parent = byDisp[hit[1]].get(dn.slice(hit[0].length).trim());
    if (!parent) { skipped.push([dn, "no matching column on " + hit[1]]); continue; }
    if (!parent.choice) continue;                    // parent is not a Choice: nothing to do
    if (c.choice) { skipped.push([dn, "already a Choice column"]); continue; }
    if (!c.text)  { skipped.push([dn, "child is neither Text nor Choice -- look at it"]); continue; }
    plan.push({name: c.name, disp: dn, parentList: hit[1], parentName: parent.name,
               choices: parent.choice.choices || [],
               fill: !!parent.choice.allowTextEntry});
  }

  console.log("\n=== plan : " + plan.length + " columns to convert ===");
  console.log("  (the doc plans 10; 12 is expected -- OrdClientDateStatus and"
            + " OrdOrderStatus were missed by it)");
  for (const p of plan) {
    console.log("  " + p.name.padEnd(24) + " <- " + p.parentList.padEnd(16)
                + " opts=" + String(p.choices.length).padEnd(3)
                + " fill-in=" + (p.fill ? "TRUE " : "FALSE") + "  " + p.choices.join(" | "));
  }
  if (skipped.length) {
    console.log("\n  skipped:");
    for (const s of skipped) console.log("     " + s[0] + " -- " + s[1]);
  }
  if (!plan.length) { console.log("\nnothing to convert."); return; }

  // ------------------------------- does the DATA fit the option lists it will get?
  // A Choice column does not validate rows that already exist, so this cannot fail
  // the conversion -- but a value that is not an option and cannot be filled in will
  // be REJECTED on the next write, per row, silently. That is worth seeing first.
  console.log("\n=== data check : values that are not options ===");
  const sel = ["Id"].concat(plan.map(p => p.name)).join(",");
  let rows = [], url = base + "/_api/web/lists(guid'" + IDS[LIST] + "')/items?$select="
                        + sel + "&$top=500", guard = 0;
  while (url && guard++ < 20) {
    const j = await J(url, 40000);
    if (j.__err) { console.error("ABORT: reading rows: " + j.__err); return; }
    rows = rows.concat(j.value || []);
    url = j["odata.nextLink"] || null;
  }
  if (!rows.length) { console.error("ABORT: read 0 rows -- broken query, not an empty list."); return; }
  console.log("rows read: " + rows.length);
  const before = new Map();
  let anyRisk = false;
  for (const p of plan) {
    const opts = new Set(p.choices);
    const vals = new Map();
    for (const r of rows) {
      const v = (r[p.name] == null ? "" : String(r[p.name])).trim();
      before.set(p.name + "|" + r.Id, v);
      if (v) vals.set(v, (vals.get(v) || 0) + 1);
    }
    const bad = [...vals].filter(([v]) => !opts.has(v));
    const n = bad.reduce((a, b) => a + b[1], 0);
    if (!bad.length) { console.log("  " + p.name.padEnd(24) + " clean"); continue; }
    const ok = p.fill;
    if (!ok) anyRisk = true;
    console.log("  " + p.name.padEnd(24) + n + " rows not in the option list -- "
                + (ok ? "OK, parent is fill-in so the child will be too"
                      : "🔴 child will be STRICT: these rows will be rejected on write")
                + "   " + bad.slice(0, 5).map(b => b[0] + "(" + b[1] + ")").join(", "));
  }
  if (anyRisk) {
    console.log("\n🔴 At least one column would be strict with values outside its list.");
    console.log("   Those rows keep displaying, but the next sync write for them FAILS,");
    console.log("   per row, with nothing reporting it. Fix the values or the option list");
    console.log("   before applying.");
    if (APPLY) { console.error("refusing to apply while that is true."); return; }
  }

  if (!APPLY) { console.log("\nDRY RUN -- nothing changed. Set APPLY = true and paste again."); return; }

  // --------------------------------------------------- capture UNDO, then convert
  const dg = await (await fetch(base + "/_api/contextinfo", {method: "POST",
    credentials: "include", headers: {Accept: "application/json;odata=nometadata"}})).json();

  const fieldUrl = n => base + "/_api/web/lists/getbytitle('" + LIST
                        + "')/fields/getbyinternalnameortitle('" + n + "')";
  console.log("\n=== UNDO : original SchemaXml, paste into the UNDO block below ===");
  const undo = [];
  for (const p of plan) {
    const f = await J(fieldUrl(p.name));
    if (f.__err || !f.SchemaXml) {
      console.error("ABORT before writing anything: cannot read SchemaXml for "
                    + p.name + " (" + (f.__err || "no SchemaXml in response") + ").");
      console.error("Without it there is no rollback, so nothing is converted.");
      return;
    }
    undo.push({name: p.name, SchemaXml: f.SchemaXml});
    p.old = f.SchemaXml;
  }
  console.log(JSON.stringify(undo));

  let ok = 0, fail = 0;
  for (const p of plan) {
    // Preserve ID / Name / StaticName / DisplayName / Group / Required EXACTLY.
    // A changed internal name silently breaks every flow mapping and every Power
    // Query rename -- and a SharePoint rename does not change it back.
    const keep = {};
    for (const k of ["ID", "Name", "StaticName", "DisplayName", "Group", "Required",
                     "Description"]) {
      const m = p.old.match(new RegExp('(?<![A-Za-z])' + k + '="([^"]*)"'));
      if (m) keep[k] = m[1];
    }
    if (keep.Name !== p.name || !keep.ID) {
      console.error("SKIP " + p.name + ": could not read ID/Name back out of its SchemaXml");
      fail++; continue;
    }
    const attrs = ['Type="Choice"', 'Format="Dropdown"',
                   'FillInChoice="' + (p.fill ? "TRUE" : "FALSE") + '"']
      .concat(["ID", "Name", "StaticName", "DisplayName", "Group", "Required", "Description"]
        .filter(k => keep[k] != null).map(k => k + '="' + xe(keep[k]) + '"'));
    const xml = "<Field " + attrs.join(" ") + "><CHOICES>"
      + p.choices.map(c => "<CHOICE>" + xe(c) + "</CHOICE>").join("")
      + "</CHOICES></Field>";

    const r = await fetch(fieldUrl(p.name), {
      method: "POST", credentials: "include",
      headers: {Accept: "application/json;odata=nometadata",
                "Content-Type": "application/json;odata=verbose",
                "X-RequestDigest": dg.FormDigestValue,
                "X-HTTP-Method": "MERGE", "IF-MATCH": "*"},
      body: JSON.stringify({__metadata: {type: "SP.Field"}, SchemaXml: xml})});
    if (r.ok) { ok++; console.log("converted " + p.name); }
    else { fail++; console.error("FAILED " + p.name + " -> " + r.status + " "
                                 + (await r.text()).slice(0, 300)); }
  }
  console.log("\nconverted ok=" + ok + " failed=" + fail);

  // ------------------------------------------------------------- verification
  console.log("\n--- verification (trust this, not the write results) ---");
  const after = await cols("Order Items");
  const idx = new Map((after || []).map(c => [c.name, c]));
  let bad = 0;
  for (const p of plan) {
    const c = idx.get(p.name);
    if (!c || !c.choice) { console.error("  NOT a Choice column: " + p.name); bad++; continue; }
    const co = same((c.choice.choices || []).slice().sort(), p.choices.slice().sort());
    const fi = !!c.choice.allowTextEntry === p.fill;
    if (!co || !fi) {
      bad++;
      console.error("  " + p.name + " converted but " + (!co ? "options differ " : "")
                    + (!fi ? "fill-in differs" : ""));
    } else console.log("  " + p.name.padEnd(24) + "Choice, " + c.choice.choices.length
                       + " options, fill-in=" + c.choice.allowTextEntry);
  }

  // did any DATA change? a type conversion should preserve every stored value
  let rows2 = [], u2 = base + "/_api/web/lists(guid'" + IDS[LIST] + "')/items?$select="
                       + sel + "&$top=500", g2 = 0;
  while (u2 && g2++ < 20) {
    const j = await J(u2, 40000);
    if (j.__err) { console.error("could not re-read rows: " + j.__err); break; }
    rows2 = rows2.concat(j.value || []);
    u2 = j["odata.nextLink"] || null;
  }
  let lost = 0, changed = 0;
  for (const r of rows2) for (const p of plan) {
    const now = (r[p.name] == null ? "" : String(r[p.name])).trim();
    const was = before.get(p.name + "|" + r.Id);
    if (was === undefined) continue;
    if (was && !now) lost++;
    else if (was !== now) changed++;
  }
  console.log("\nrows re-read      : " + rows2.length);
  console.log("values blanked    : " + lost + "    (expect 0)");
  console.log("values altered    : " + changed + "  (expect 0)");
  console.log("columns wrong     : " + bad + "    (expect 0)");
  console.log("\nNEXT: re-export Order Items, then");
  console.log("      python scripts/gen_n3_flows.py && python scripts/verify_n3_flows.py");
  console.log("      -- the generator reads column types from that export, so it must be fresh.");
})();

/* ---------------------------------------------------------------- UNDO ----
   Restores each column's original SchemaXml, turning them back into Text.

(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const LIST = "Order Items";
  const MADE = [];   // <- paste the UNDO array printed above
  const dg = await (await fetch(base + "/_api/contextinfo", {method:"POST",
    credentials:"include", headers:{Accept:"application/json;odata=nometadata"}})).json();
  let ok = 0;
  for (const m of MADE) {
    const r = await fetch(base + "/_api/web/lists/getbytitle('" + LIST +
      "')/fields/getbyinternalnameortitle('" + m.name + "')", {
      method:"POST", credentials:"include",
      headers:{Accept:"application/json;odata=nometadata",
               "Content-Type":"application/json;odata=verbose",
               "X-RequestDigest":dg.FormDigestValue,
               "X-HTTP-Method":"MERGE","IF-MATCH":"*"},
      body:JSON.stringify({__metadata:{type:"SP.Field"}, SchemaXml:m.SchemaXml})});
    if (r.ok) ok++; else console.error(m.name + " -> " + r.status + " " + (await r.text()).slice(0,200));
  }
  console.log("restored " + ok + " of " + MADE.length);
  console.log("then re-export Order Items and regenerate the N3 flows.");
})();
---------------------------------------------------------------------------- */
