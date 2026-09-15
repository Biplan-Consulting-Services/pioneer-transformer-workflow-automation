/* X18 -- repair the `Model Revisions` rows whose own `ModelID` is not a revision id.

   DRY RUN by default. Paste into the browser console on the SharePoint site.

   THE DEFECT
     29 revisions hold their MODEL's code in `ModelID` where their own revision id belongs:

         id 20   ModelID = M-HYQU-0006     should be   MR-HYQU-0006-V?

     `ModelID` on `Model Revisions` IS the revision identifier, and the `Model Revision`
     lookup's ShowField resolves to it -- so the Order Items trigger flow reads these rows
     and mirrors whatever they say into `Model_Revision_ID_TextField`. The flow is correct;
     it has been faithfully copying a broken source. Fixing these rows fixes the mirrors by
     the same mechanism, one row per staff edit.

   WHAT IS DERIVABLE AND WHAT IS NOT
     The PREFIX is derivable from the model the revision points at -- insert an `R` after
     the leading `M`:
         M-HYQU-0092    ->  MR-HYQU-0092-V<n>
         MSA-HYQU-0064  ->  MRSA-HYQU-0064-V<n>

     The VERSION is always `-V1`. Stated by the user 2026-09-14: there should not be any
     `-V2` anywhere in this list. That makes the whole id derivable and the repair
     deterministic -- no guessing about suffixes.

     🔑 So the script also CHECKS that rule rather than just trusting it. Two ways it can
     be wrong, both reported before anything is written:
       - an existing healthy revision whose id ends in something other than `-V1`
       - a model with more than one revision, which under a no-V2 rule cannot be right
     Either means the rule has an exception nobody has named, and the run stops.

   HOW TO DRIVE IT
     1. Paste with APPLY = false. Read the table and the sibling lists.
     2. Put anything the proposal got wrong into OVERRIDES, keyed by revision id.
     3. Put anything that should not be touched at all into SKIP.
     4. Set APPLY = true and paste again. It writes, re-reads every row it wrote, and
        compares against exactly what it intended.

   SAFETY
     - refuses to write a value that duplicates another revision's existing ModelID
     - refuses to write anything that does not match its own model's derived prefix,
       unless that row is in OVERRIDES (an override is a deliberate human statement)
     - writes ONE field, `ModelID`, and nothing else
     - verification re-reads each row individually after the write; the write response is
       not treated as proof
*/
(async () => {
  const APPLY = false;
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";

  // revision id -> the exact ModelID to write. Wins over the derived proposal.
  const OVERRIDES = {
    // 20: "MR-HYQU-0006-V2",
  };
  // revision ids to leave completely alone.
  const SKIP = [];

  const raw = async (u, opt) => {
    const c = new AbortController(); const t = setTimeout(()=>c.abort(), 25000);
    try { return await fetch(u, Object.assign({credentials:"include", signal:c.signal,
            headers:{Accept:"application/json;odata=nometadata"}}, opt||{})); }
    finally { clearTimeout(t); }
  };
  const J = async (u) => (await raw(u)).json();
  const page = async (u) => { let o=[],g=0;
    while (u && g++<40){ const j=await J(u); o=o.concat(j.value||[]); u=j["odata.nextLink"]||null; } return o; };
  const s = v => (v == null ? "" : String(v));
  const L = t => base + "/_api/web/lists/getbytitle('" + t + "')";

  const revs = await page(L("Model Revisions") + "/items?$top=2000");
  if (!revs.length) { console.error("ABORT: read 0 revisions -- a zero-row read is a failed read."); return; }
  console.log("revisions read: " + revs.length);

  const prefixOf = r => { const m = s(r.Pioneer_Model_Code_TextField);
    return m ? "MR" + m.slice(1) : null; };
  const looksRight = r => { const p = prefixOf(r);
    return p ? s(r.ModelID).toUpperCase().startsWith(p.toUpperCase() + "-V") : false; };

  const broken = revs.filter(r => !looksRight(r) && !SKIP.includes(r.Id));
  const healthy = revs.filter(looksRight);
  console.log("already correct : " + healthy.length);
  console.log("to repair       : " + broken.length + (SKIP.length ? "   (skipping " + SKIP.length + ")" : ""));
  if (!broken.length) { console.log("Nothing to do."); return; }

  // every ModelID currently in use, so a proposal cannot collide with one
  const taken = new Map();
  for (const r of revs) if (s(r.ModelID)) taken.set(s(r.ModelID).toUpperCase(), r.Id);

  // siblings, so the version number can be judged rather than assumed
  const byModel = new Map();
  for (const r of revs) { const k = s(r.ModelId); if (!k) continue;
    if (!byModel.has(k)) byModel.set(k, []); byModel.get(k).push(r); }

  /* ---- check the "-V1 only" rule before relying on it ---------------------- */
  const notV1 = healthy.filter(r => !/-V1$/i.test(s(r.ModelID)));
  const multi = [...byModel.entries()].filter(([,rs]) => rs.length > 1);
  console.log("
=== the -V1 rule ===");
  console.log("  healthy revisions NOT ending -V1 : " + notV1.length + "   (expect 0)");
  for (const r of notV1.slice(0,15)) console.log("      id " + r.Id + "  " + s(r.ModelID));
  console.log("  models with >1 revision          : " + multi.length + "   (expect 0)");
  for (const [mid, rs] of multi.slice(0,15))
    console.log("      model " + mid + " -> " + rs.map(z => z.Id + ":" + (s(z.ModelID)||"(empty)")).join("  "));
  if (notV1.length || multi.length) {
    console.error("
🔴 The -V1 rule does not hold on this list. Those rows are an exception");
    console.error("   nobody has named, and deriving 29 ids from a rule with unexplained");
    console.error("   counter-examples is how the last three wrong answers happened.");
    console.error("   Resolve them (or SKIP them) before repairing anything.");
    return;
  }
  console.log("  rule holds.");

  const plan = [];
  for (const r of broken) {
    const p = prefixOf(r);
    const sibs = (byModel.get(s(r.ModelId)) || []).filter(x => x.Id !== r.Id);
    let proposed = null, why = "";
    if (OVERRIDES[r.Id]) { proposed = OVERRIDES[r.Id]; why = "OVERRIDE"; }
    else if (!p) { why = "no model code on this revision -- cannot derive, needs an OVERRIDE"; }
    else {
      // Always -V1. There is no -V2 in this list (user, 2026-09-14), so the id is fully
      // determined by the model it points at.
      proposed = p + "-V1";
      why = sibs.length ? "⚠️ " + sibs.length + " sibling(s) -- see the V1 rule check above"
                        : "only revision of this model";
    }
    plan.push({r, proposed, why, sibs, p});
  }

  console.log("\n=== proposed repairs -- READ THIS, the version suffix is a guess ===");
  for (const x of plan) {
    const dup = x.proposed && taken.has(s(x.proposed).toUpperCase());
    console.log("  id " + String(x.r.Id).padEnd(5)
      + "now=" + (s(x.r.ModelID) || "(empty)").padEnd(20)
      + "-> " + (s(x.proposed) || "???").padEnd(22)
      + (dup ? "  🔴 DUPLICATE of revision " + taken.get(s(x.proposed).toUpperCase()) : "")
      + "   [" + x.why + "]");
    if (x.sibs.length) console.log("        siblings: "
      + x.sibs.map(z => z.Id + ":" + (s(z.ModelID) || "(empty)")).join("  "));
  }

  /* -------------------------------------------------------------- validation */
  const problems = [];
  for (const x of plan) {
    if (!x.proposed) { problems.push("id " + x.r.Id + ": no proposal -- add an OVERRIDE"); continue; }
    if (taken.has(s(x.proposed).toUpperCase()))
      problems.push("id " + x.r.Id + ": " + x.proposed + " already belongs to revision " + taken.get(s(x.proposed).toUpperCase()));
    if (!OVERRIDES[x.r.Id] && x.p && !s(x.proposed).toUpperCase().startsWith(x.p.toUpperCase() + "-V"))
      problems.push("id " + x.r.Id + ": " + x.proposed + " does not match its model prefix " + x.p);
  }
  const seen = new Map();
  for (const x of plan) if (x.proposed) {
    const k = s(x.proposed).toUpperCase();
    if (seen.has(k)) problems.push("ids " + seen.get(k) + " and " + x.r.Id + " both propose " + x.proposed);
    seen.set(k, x.r.Id);
  }

  if (problems.length) {
    console.error("\n=== " + problems.length + " problem(s) -- nothing will be written ===");
    for (const p of problems) console.error("  " + p);
    console.error("\nResolve these with OVERRIDES or SKIP, then run again.");
    return;
  }
  console.log("\nvalidation: OK -- no duplicates, no prefix mismatches, no missing proposals.");

  if (!APPLY) {
    console.log("\nDRY RUN -- nothing written. Set APPLY = true once the table above is right.");
    return;
  }

  /* ------------------------------------------------------------------- write */
  const dg = await (await raw(base + "/_api/contextinfo", {method:"POST"})).json();
  let ok = 0, fail = 0;
  for (const x of plan) {
    const resp = await raw(L("Model Revisions") + "/items(" + x.r.Id + ")", {
      method:"POST",
      headers:{Accept:"application/json;odata=nometadata","Content-Type":"application/json;odata=nometadata",
               "X-RequestDigest":dg.FormDigestValue,"IF-MATCH":"*","X-HTTP-Method":"MERGE"},
      body: JSON.stringify({ ModelID: x.proposed })});
    if (resp.ok) ok++; else { fail++; console.error("  write FAILED id " + x.r.Id + ": " + (await resp.text()).slice(0,160)); }
  }
  console.log("\nwritten ok=" + ok + " failed=" + fail);

  /* ------------------------------------------------------------- verification */
  // Re-read every row individually. The write response is not proof: a 204 says the
  // request was accepted, not that the stored value is what we meant.
  console.log("\n=== verification -- re-reading each row ===");
  let good = 0; const badRows = [];
  for (const x of plan) {
    const after = await J(L("Model Revisions") + "/items(" + x.r.Id + ")?$select=Id,ModelID,Pioneer_Model_Code_TextField");
    if (s(after.ModelID) === s(x.proposed)) good++;
    else badRows.push("  id " + x.r.Id + ": wanted " + x.proposed + ", stored " + (s(after.ModelID) || "(empty)"));
  }
  console.log("  stored exactly as intended : " + good + " / " + plan.length);
  for (const b of badRows) console.error(b);

  // and the global check the audit uses, so the two agree
  const after = await page(L("Model Revisions") + "/items?$top=2000&$select=Id,ModelID,Pioneer_Model_Code_TextField");
  const stillBroken = after.filter(r => !looksRight(r));
  console.log("  revisions still not matching their model prefix : " + stillBroken.length
    + "   (expect " + SKIP.length + " -- the skipped ones)");
  for (const r of stillBroken.slice(0,10)) console.log("      id " + r.Id + "  " + (s(r.ModelID)||"(empty)"));

  console.log(good === plan.length && stillBroken.length === SKIP.length
    ? "\nOK. The revisions are repaired."
    : "\nNOT CLEAN -- read the rows above before doing anything else.");
  console.log("\nNOTE: this repairs `Model Revisions`. The 724 Order Items rows whose");
  console.log("Model_Revision_ID_TextField mirror is stale are NOT fixed by this -- the");
  console.log("trigger flow refreshes each one only when that unit is next edited. Run x16");
  console.log("to see the remaining mirror drift and decide whether to backfill it.");
})();
