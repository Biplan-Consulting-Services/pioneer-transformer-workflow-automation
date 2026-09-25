/* X27 -- RESTORE a rollback plan (E10 Layer C2). Compare-and-set, list-agnostic.

   The plan comes from:  python scripts/plan_rollback.py <selectors>   (writes plan-*.json)

   HOW TO RUN
     1. Open https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser signed in.
     2. F12 -> Console. Either paste the plan into PLAN below, or first run
            window.x27plan = <paste the plan JSON>
        and set  const PLAN = window.x27plan;
     3. Paste this whole file. It runs DRY by default and writes nothing. Read the plan,
        then set DRY = false and paste again.
     4. Refresh the mirror afterwards (scripts/Refresh-SharePointMirror.ps1): the journal then
        shows the restore as its own batch.

   COMPARE-AND-SET
     For each entry {list, id, field, expect, restore}: the field is written ONLY if the row
     still holds `expect`. A row that changed since the journal saw it is reported as a
     CONFLICT and left alone - a later legitimate edit is never overwritten. A row that
     already holds `restore` is skipped as already restored.

   ⚠️ Restoring a PARENT row (Order, Models, Model Revisions, Clients) fires the N3 sync flows,
      which push the restored value to the units. Restoring Order Items rows fires the
      Order Items trigger flow when it is ON. The plan's `warnings` say which applies.
   ⚠️ Deleted rows are not recreated here - the recycle bin keeps their Id and history.
*/
(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const DRY = true;       // <-- set false to actually write
  const VERBOSE = false;  // true = a line per row
  const PLAN = null;      // <-- paste the plan here, or: const PLAN = window.x27plan;

  const LOG = [];
  const say = (s) => { LOG.push(s); if (VERBOSE) console.log(s); };
  const beat = (phase, i, n) => { if (!VERBOSE && i > 0 && i % 100 === 0) console.log("  " + phase + " " + i + "/" + n + "..."); };
  const X27 = { dry: DRY, log: LOG };
  if (typeof window !== "undefined") window.x27 = X27;

  const BACKOFF_MS = 2000, TRIES = 6;
  const SLEEP = (ms) => new Promise(res => setTimeout(res, ms));
  const J = async (u, opt) => {
    for (let attempt = 1; ; attempt++) {
      const r = await fetch(u, Object.assign({ credentials: "include",
        headers: { Accept: "application/json;odata=nometadata" } }, opt || {}));
      if (r.ok) return r.status === 204 ? {} : r.json();
      if ((r.status === 429 || r.status === 503 || r.status === 504) && attempt < TRIES) {
        const ra = Number(r.headers && r.headers.get ? r.headers.get("Retry-After") : NaN);
        const wait = ra > 0 ? ra * 1000 : BACKOFF_MS * Math.pow(2, attempt - 1);
        console.log("  (" + r.status + " throttled - retry " + attempt + "/" + (TRIES - 1) + " in " + Math.round(wait / 1000) + " s)");
        await SLEEP(wait);
        continue;
      }
      const err = new Error(r.status + " " + r.statusText + " " + (await r.text()).slice(0, 300));
      err.status = r.status;
      throw err;
    }
  };
  /* The mirror's string form of a value: null -> "", booleans True/False (Excel), numbers
     plainly. Plan values and live values are both compared through this. */
  const norm = (v) => {
    if (v === null || v === undefined) return "";
    if (typeof v === "boolean") return v ? "True" : "False";
    if (typeof v === "number") return String(v);
    if (typeof v === "object") return JSON.stringify(v);
    return String(v);
  };

  if (PLAN === undefined) { console.error("ABORT: PLAN is undefined - the window variable it points at was never set."); return; }
  if (!PLAN || !Array.isArray(PLAN.entries)) { console.error("ABORT: no plan. Paste plan_rollback.py's JSON into PLAN (or window.x27plan)."); return; }
  const entries = PLAN.entries.filter(e => !e.unsupported);
  if (!entries.length) { console.error("ABORT: the plan holds 0 restorable entries. A zero-row plan is a failed plan."); return; }
  for (const e of entries) {
    if (!e.list || typeof e.id !== "number" || !e.field || !("expect" in e) || !("restore" in e)) {
      console.error("ABORT: malformed entry " + JSON.stringify(e).slice(0, 200)); return;
    }
  }
  const rows = new Map();   // "list|id" -> [entries]
  for (const e of entries) { const k = e.list + "|" + e.id; if (!rows.has(k)) rows.set(k, []); rows.get(k).push(e); }
  const lists = [...new Set(entries.map(e => e.list))];
  console.log("MODE: RESTORE " + (DRY ? "(DRY)" : "(APPLY - WRITES)") + ", " + entries.length + " fields on "
    + rows.size + " rows in " + lists.join(", ") + (PLAN.counts && PLAN.counts.unsupported ? " (" + PLAN.counts.unsupported + " unsupported entries NOT restored)" : ""));
  for (const w of (PLAN.warnings || [])) console.log("⚠️ " + w);

  const guid = {};
  for (const l of lists) guid[l] = (await J(base + "/_api/web/lists/getbytitle('" + l.replace(/'/g, "''") + "')?$select=Id")).Id;
  const itemUrl = (l, id) => base + "/_api/web/lists(guid'" + guid[l] + "')/items(" + id + ")";

  // ---- compare
  const plan = [], conflicts = [], already = [], gone = [];
  let ri = 0;
  for (const [k, es] of rows) {
    beat("reading rows", ri++, rows.size);
    const l = es[0].list, id = es[0].id;
    let cur;
    try { cur = await J(itemUrl(l, id) + "?$select=" + es.map(e => e.field).join(",")); }
    catch (e) { if (e.status === 404) { gone.push({ list: l, id }); continue; } throw e; }
    const write = {}, expect = {};
    for (const e of es) {
      const now = norm(cur[e.field]);
      if (now === norm(e.expect)) { write[e.field] = e.restore; expect[e.field] = e.expect; }
      else if (now === norm(e.restore)) already.push({ list: l, id, field: e.field });
      else conflicts.push({ list: l, id, title: e.title, field: e.field, expect: e.expect, now: cur[e.field] });
    }
    const n = Object.keys(write).length;
    say("--- " + l + " " + id + ": " + n + " to restore");
    if (n) plan.push({ list: l, id, title: es[0].title, write, expect });
  }
  X27.plan = plan; X27.conflicts = conflicts; X27.already = already; X27.gone = gone;
  const nf = plan.reduce((a, p) => a + Object.keys(p.write).length, 0);
  console.log("\n=== RESTORE" + (DRY ? " (DRY)" : "") + ": " + nf + " fields on " + plan.length + " rows to write; "
    + already.length + " already restored; " + conflicts.length + " CONFLICTS (changed since - left alone); "
    + gone.length + " rows gone ===");
  if (conflicts.length) {
    console.log("⚠️ conflicts - these rows changed after the journal saw them, NOT touched" + (conflicts.length > 10 ? " (first 10; all in window.x27.conflicts)" : "") + ":");
    console.table(conflicts.slice(0, 10));
  }
  if (gone.length) console.log("⚠️ rows no longer exist (recycle bin?): " + gone.slice(0, 10).map(g => g.list + " " + g.id).join(", "));
  if (DRY) {
    if (plan.length) console.log("sample (first " + Math.min(10, plan.length) + " of " + plan.length + "; all in window.x27.plan):");
    for (const p of plan.slice(0, 10)) console.log("  " + p.list + " " + p.id + "  " + Object.keys(p.write).map(f =>
      f + " " + JSON.stringify(p.expect[f]) + " -> " + JSON.stringify(p.write[f])).join(", "));
    console.log("DRY RUN - nothing written. Set DRY = false and paste again. copy(window.x27) for the full detail.");
    return;
  }
  if (!plan.length) { console.log("Nothing to write."); return; }

  const digest = await J(base + "/_api/contextinfo", { method: "POST" }).then(j => j.FormDigestValue).catch(() => null);
  if (!digest) { console.error("ABORT: no form digest, cannot write."); return; }
  let failed = 0;
  for (let pi = 0; pi < plan.length; pi++) {
    const p = plan[pi];
    beat("writing", pi, plan.length);
    try {
      await J(itemUrl(p.list, p.id), { method: "POST",
        headers: { Accept: "application/json;odata=nometadata", "Content-Type": "application/json;odata=nometadata",
                   "X-RequestDigest": digest, "X-HTTP-Method": "MERGE", "IF-MATCH": "*" },
        body: JSON.stringify(p.write) });
      say("  wrote " + p.list + " " + p.id);
    } catch (e) { failed++; p.failed = e.message; console.log("  🔴 FAILED " + p.list + " " + p.id + ": " + e.message); }
  }

  console.log("\n=== read-back ===");
  let bad = 0; const unverified = [];
  for (let pi = 0; pi < plan.length; pi++) {
    const p = plan[pi];
    if (p.failed) continue;
    beat("reading back", pi, plan.length);
    let after;
    try { after = await J(itemUrl(p.list, p.id) + "?$select=" + Object.keys(p.write).join(",")); }
    catch (e) { unverified.push({ list: p.list, id: p.id, error: e.message.slice(0, 120) }); continue; }
    for (const f of Object.keys(p.write)) {
      if (norm(after[f]) !== norm(p.write[f])) {
        bad++; console.log("  🔴 " + p.list + " " + p.id + " " + f + ": wanted " + JSON.stringify(p.write[f]) + " got " + JSON.stringify(after[f]));
      }
    }
  }
  X27.unverified = unverified;
  if (unverified.length) console.log("⚠️ writes done, verification INCOMPLETE for " + unverified.length
    + " rows - refresh the mirror to verify; do NOT re-run the restore.");
  console.log((bad || failed) ? "\n🔴 " + failed + " rows failed to write, " + bad + " fields did not land."
    : "\n✅ every restored field verified" + (unverified.length ? " (of those re-read)." : "."));
})();
