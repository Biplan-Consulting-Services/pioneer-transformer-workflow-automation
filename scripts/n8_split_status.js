/* N8 -- split the composite Status column into Step Status + Status Date.

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
        (if Chrome refuses the paste, type  allow pasting  first)
     3. DRY RUN by default: it creates NOTHING and writes NOTHING, just prints
        the parse. Read it, then set APPLY = true and paste again.

   WHAT Status LOOKS LIKE
     A composite of a status prefix, a French month abbreviation and a day:
       TE-Se-4  =  Terminé, 4 September
     247 of 1,121 rows carry one; 33 distinct values.

   THE CODE TABLE IS AUTHORITATIVE, NOT INFERRED
     Read out of FRM10-12's own List sheet, TableValidationStatusCode (N18:P26),
     which even documents the format in its Code column (TE-Se-7):

       Attente        AT        Terminé        TE
       En cours       EC        Bobine 1       B1
       Réparation     RE        Bobine 2       B2
       Manque Pièces  BO        Bobine 3       B3

     ⚠️ THE PREFIXES COLLIDE WITH THE LOCATION CODES. In the Status column
     BO means Manque Pièces; in the Location column BO means Bobinage. TE is
     Terminé here but Test there, and RE is Réparation in both. Only the column
     tells you which table applies -- never map one with the other's table.

     Observed in the data: TE 180, EC 58, B1 5, B2 2, B3 2. AT, RE and BO do not
     currently occur but are handled.

   THE 'Jui' AMBIGUITY -- resolved from data, not guessed
     "Jui" is ambiguous: juin and juillet both begin jui. The roadmap planned to
     flag these for a human. That is not necessary: each unit's own stage dates
     settle it. For all 19 rows the reference date lands 0-1 days from the JULY
     reading, several of them EXACTLY on it (21786-9/14 ref 07-24 -> 07-24,
     21912-1/10 ref 07-06 -> 07-06). All 19 are juillet.

     The reference uses ONLY the six stages the transfer flow maintains, and only
     dates in the past. Tanking/Delivery End Date are deliberately excluded:
     they are the fabricated, future-dated copies of the plan that X1 clears, so
     they are worthless as a reference. Checked both ways -- including them gave
     the same answer, but the clean reference is the one to rely on.

   YEAR
     Assumed 2026, and the parse is coherent with it: every resolved date lands
     in 2026-07-06 .. 2026-09-04 (Jul 19, Aug 86, Sep 142), which is what a
     "current production status" should look like against a 2026-09-08 today.

   COLUMN TYPES
     Step Status -> CHOICE, with the 8 options generated from PREFIX below.
       ⚠️ THIS REVERSES AN EARLIER DECISION IN THIS FILE, on purpose (user,
       2026-09-08). It previously said TEXT, citing N2's rule that a Choice
       "silently REJECTS any value outside its option list, per row" -- the
       Family failure mode. That rule is real but it is about columns a FLOW
       WRITES with values from an open-ended external source. Step Status is
       neither:
         - the closed vocabulary is 8 values from FRM10-12's own authoritative
           TableValidationStatusCode, and only 5 occur in the data at all;
         - after this one-time script, NOTHING writes it but staff. The
           transfer flow must not (see docs/n8-transfer-flow-interaction-
           2026-09-08.md) and the Status Date stamp writes the DATE, not this.
       So the rejection hazard has no path in, and Choice buys what Text
       cannot: a dropdown instead of free text, no typos, and real grouping,
       filtering and colour formatting in the views staff actually use.
       🔑 The options are BUILT FROM PREFIX, the same table the parse uses, so
       the option list and the values written cannot drift apart. A hand-typed
       second copy is exactly how a Choice write starts failing per-row.
       FillInChoice is FALSE -- "allow custom values" would give back the free
       text this change exists to remove.
     Status Date -> DateTime with DateOnly. Never DateTime-with-time: that is
       what reintroduces the UTC-midnight day-early bug.
     Neither is added to the default view.

   NO UNIT LIST IS EMBEDDED. The script re-parses from the live list, so it
   cannot drift against a stale array and stays correct if a Status is edited.
*/

(async () => {
  const APPLY = false;                    // <-- set true to create + populate
  const base  = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI    = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";   // Order Items
  const YEAR  = 2026;
  const TODAY = new Date(Date.UTC(2026,8,8));
  const CONC  = 8;

  const PREFIX = {AT:"Attente", EC:"En cours", RE:"Réparation", BO:"Manque Pièces",
                  TE:"Terminé", B1:"Bobine 1", B2:"Bobine 2", B3:"Bobine 3"};
  const MONTH  = {ja:1, fe:2, "fé":2, ma:3, av:4, ao:8, se:9, oc:10, no:11, de:12};
  const REAL   = ["CoilingDate","StackingDate","AssemblyDate","DryingDate","TestingDate","FinishingDate"];

  // Option list generated from PREFIX -- never hand-typed, so it cannot drift
  // from the values the parse produces. Order follows PREFIX; it is cosmetic
  // and can be reordered later in column settings without touching data.
  const esc = (t) => t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  const CHOICES = Object.values(PREFIX);
  const FIELDS = [
    '<Field Type="Choice" DisplayName="Step Status" Name="StepStatus" StaticName="StepStatus" ' +
      'Required="FALSE" Group="Status Split" Format="Dropdown" FillInChoice="FALSE"><CHOICES>' +
      CHOICES.map(c => "<CHOICE>" + esc(c) + "</CHOICE>").join("") +
      '</CHOICES></Field>',
    '<Field Type="DateTime" Format="DateOnly" DisplayName="Status Date" Name="StatusDate" StaticName="StatusDate" Required="FALSE" Group="Status Split" />',
    // 🔑 THE MIRROR, and it is load-bearing -- see the block comment below.
    '<Field Type="Text" DisplayName="Step Status Stamped" Name="StepStatusStamped" StaticName="StepStatusStamped" Required="FALSE" Group="Status Split" MaxLength="40" />'
  ];

  /* WHY A THIRD COLUMN, AND WHY N8 MUST FILL IT
     The Status Date auto-stamp has to answer "did Step Status just change?", and a
     SharePoint trigger hands over the item's CURRENT state only -- there is no previous
     value, and a trigger condition cannot see one either. So the flow compares Step
     Status against a text mirror of what it last stamped. That is not a new trick here:
     the trigger flow ALREADY does exactly this for four fields, comparing
     OrderNumber/Value against Order_Number_TextField and so on. Same idiom, one more
     field.

     🔴 And N8 must write it, or the first run of that flow DESTROYS this migration.
     If Step Status is filled and Step Status Stamped is left empty, then on the next
     touch of each of these 247 rows the flow sees a change, stamps TODAY, and the
     migrated status dates -- the whole point of N8 -- are gone. Writing the mirror here
     means every migrated row starts already in agreement, so the stamp stays quiet until
     a human actually changes a status. */

  const J = async (u) => (await fetch(u,{headers:{Accept:"application/json;odata=nometadata"}})).json();
  const dg = await (await fetch(base+"/_api/contextinfo",{method:"POST",
                    headers:{Accept:"application/json;odata=nometadata"}})).json();
  const digest = dg.FormDigestValue;
  if (!digest) { console.error("no form digest - are you signed in?"); return; }

  // ------------------------------------------------------------------ read
  let url = base + "/_api/web/lists(guid'" + OI + "')/items?$select=Id,Title,Status," +
            REAL.join(",") + "&$top=500";
  let rows = [], g = 0;
  while (url && g++ < 10) { const j = await J(url); rows = rows.concat(j.value||[]); url = j["odata.nextLink"]||null; }
  console.log("rows read: " + rows.length);

  const iso = (y,m,d) => {
    const dt = new Date(Date.UTC(y,m-1,d));
    if (dt.getUTCMonth() !== m-1 || dt.getUTCDate() !== d) return null;   // e.g. Feb 31
    return dt.toISOString().slice(0,10);
  };
  const refOf = (r) => {
    let best = null;
    for (const c of REAL) {
      if (!r[c]) continue;
      const dt = new Date(r[c]);
      if (isNaN(dt) || dt > TODAY) continue;                              // past only
      if (!best || dt > best) best = dt;
    }
    return best;
  };

  const plan = [], problems = [];
  for (const r of rows) {
    const raw = (r.Status || "").trim();
    if (!raw) continue;
    // A BARE STEP PREFIX with no date stamp -- "b2", "B3". Found 2026-09-09 on 3 rows
    // (21832-1/11, 21995-1/2, 21998-3/3), all coil stages. Staff recorded WHICH stage the
    // unit is at without dating it, which is a legitimate thing to have written: the step
    // is real information and the date simply was not given.
    //
    // So take the step and leave Status Date blank. Inventing a date would be worse than
    // leaving it empty -- there is nothing to derive one from, and a fabricated stage date
    // is exactly the class of value X1 spent today deleting.
    //
    // Case-insensitive on purpose: two of the three are lowercase ("b2") and the code
    // table is uppercase.
    const bare = /^([A-Za-z][A-Za-z0-9])$/.exec(raw);
    if (bare) {
      const bpre = bare[1].toUpperCase(), bstep = PREFIX[bpre];
      if (!bstep) { problems.push([r.Title, raw, "unknown bare prefix "+bpre]); continue; }
      plan.push({Id:r.Id, Title:r.Title, raw, step:bstep, date:null, note:"", bare:true});
      continue;
    }

    const m = /^([A-Za-z0-9]{2})-([A-Za-zéÉ]{2,4})-(\d{1,2})$/.exec(raw);
    if (!m) { problems.push([r.Title, raw, "does not match PREFIX-Month-Day or a bare prefix"]); continue; }
    const pre = m[1].toUpperCase(), mon = m[2].toLowerCase(), day = parseInt(m[3],10);
    const step = PREFIX[pre];
    if (!step) { problems.push([r.Title, raw, "unknown status prefix "+pre]); continue; }
    let date = null, note = "";
    if (mon === "jui") {
      const juin = iso(YEAR,6,day), juil = iso(YEAR,7,day), ref = refOf(r);
      if (ref && (juin || juil)) {
        const pick = [juin,juil].filter(Boolean)
          .map(s => [s, Math.abs(new Date(s) - ref)])
          .sort((a,b) => a[1]-b[1])[0];
        date = pick[0];
        note = "jui->" + (date.slice(5,7)==="07" ? "juillet" : "juin") +
               " (ref " + ref.toISOString().slice(0,10) + ", " + Math.round(pick[1]/86400000) + "d)";
      } else {
        problems.push([r.Title, raw, "jui ambiguous and no real past stage date to compare"]);
        continue;
      }
    } else {
      const mm = MONTH[mon];
      if (!mm) { problems.push([r.Title, raw, "unknown month "+mon]); continue; }
      date = iso(YEAR,mm,day);
      if (!date) { problems.push([r.Title, raw, "invalid day for that month"]); continue; }
    }
    plan.push({Id:r.Id, Title:r.Title, raw, step, date, note});
  }

  const byStep = {}, byMonth = {};
  for (const p of plan) {
    byStep[p.step]=(byStep[p.step]||0)+1;
    const k = p.date ? p.date.slice(0,7) : "(no date given)";
    byMonth[k]=(byMonth[k]||0)+1;
  }
  console.log("\n=== parse ===");
  console.log("  rows with a Status : " + (plan.length + problems.length));
  console.log("  parsed             : " + plan.length);
  console.log("  PROBLEMS           : " + problems.length);
  console.log("  by step status     : " + JSON.stringify(byStep));
  console.log("  by month           : " + JSON.stringify(byMonth));
  const bareRows = plan.filter(p=>p.bare);
  if (bareRows.length) {
    console.log("  bare prefix, no date: " + bareRows.length
                + "   (Step Status set, Status Date left blank -- no date was given)");
    for (const p of bareRows) console.log("     " + p.Title + " " + JSON.stringify(p.raw) + " -> " + p.step);
  }
  const jui = plan.filter(p=>p.note && !p.bare);
  console.log("  'jui' rows resolved: " + jui.length);
  for (const p of jui.slice(0,6)) console.log("     " + p.Title + " " + p.raw + " -> " + p.date + "  " + p.note);
  for (const p of problems) console.warn("  PROBLEM " + p[0] + " " + JSON.stringify(p[1]) + " : " + p[2]);

  if (!APPLY) { console.log("\nDRY RUN -- no columns created, nothing written. Set APPLY = true."); return; }

  // ---------------------------------------------------- create the columns
  console.log("\n=== creating columns ===");
  const cols = await J(base + "/_api/v2.0/sites/root/lists/" + OI + "/columns");
  const have = new Set((cols.value||[]).map(c=>c.name));
  for (const xml of FIELDS) {
    const name = /Name="([^"]+)"/.exec(xml)[1];
    if (have.has(name)) { console.log("  " + name + " already exists - skipped"); continue; }
    const r = await fetch(base + "/_api/web/lists(guid'" + OI + "')/fields/createfieldasxml", {
      method:"POST",
      headers:{Accept:"application/json;odata=nometadata","Content-Type":"application/json;odata=verbose",
               "X-RequestDigest":digest},
      // Options 8 = AddFieldInternalNameHint, so Name is honoured as the internal
      // name instead of being derived from DisplayName (and truncated at 32).
      // 16 (AddFieldToDefaultView) is deliberately NOT set.
      body: JSON.stringify({parameters:{SchemaXml:xml, Options:8}})});
    console.log("  " + name + " -> " + r.status + (r.ok ? " created" : " FAILED " + (await r.text()).slice(0,200)));
  }
  const back = await J(base + "/_api/v2.0/sites/root/lists/" + OI + "/columns");
  const now = new Set((back.value||[]).map(c=>c.name));
  if (!now.has("StepStatus") || !now.has("StatusDate") || !now.has("StepStatusStamped")) {
    console.error("  columns not present after create - stopping before the write"); return; }
  console.log("  read-back: both columns present");

  // ---- Choice guard: a Choice write of a value that is not an option FAILS,
  // per row, so prove every value the plan will write is actually an option
  // BEFORE writing 247 rows. Also catches the case where an earlier run of
  // this script created Step Status as Text.
  const col = (back.value||[]).find(c => c.name === "StepStatus") || {};
  const opts = (col.choice && col.choice.choices) || null;
  if (!opts) {
    console.warn("  ⚠ Step Status is NOT a Choice column (an earlier run created it as Text?).");
    console.warn("    The write below still works, but you lose the dropdown and the validation.");
    console.warn("    Convert it in column settings - SharePoint preserves existing values.");
  } else {
    const want = [...new Set(plan.map(p => p.step))];
    const missing = want.filter(v => !opts.includes(v));
    console.log("  Step Status options (" + opts.length + "): " + opts.join(" | "));
    console.log("  distinct values to write (" + want.length + "): " + want.join(" | "));
    if (missing.length) {
      console.error("  *** STOPPING: these values are not options, every such row would fail: "
                    + missing.join(", "));
      return;
    }
    console.log("  all values to write are valid options - safe to proceed");
  }

  // ------------------------------------------------------------- populate
  const et = (await J(base+"/_api/web/lists(guid'"+OI+"')?$select=ListItemEntityTypeFullName"))
               .ListItemEntityTypeFullName;
  let ok=0, fail=0; const errs=[];
  const patch = async (p) => {
    const r = await fetch(base+"/_api/web/lists(guid'"+OI+"')/items("+p.Id+")",{method:"POST",
      headers:{Accept:"application/json;odata=nometadata","Content-Type":"application/json;odata=verbose",
               "X-RequestDigest":digest,"X-HTTP-Method":"MERGE","IF-MATCH":"*"},
      // StepStatusStamped is written EQUAL to StepStatus on purpose: it starts the row
      // already in agreement, so the auto-stamp flow does not see a change and overwrite
      // the date this script just migrated.
      body: JSON.stringify({__metadata:{type:et}, StepStatus:p.step, StatusDate:p.date,
                            StepStatusStamped:p.step})});
    if (r.ok) ok++; else { fail++; if (errs.length<5) errs.push(p.Title+": "+r.status+" "+(await r.text()).slice(0,140)); }
  };
  console.log("\npopulating " + plan.length + " rows ...");
  for (let i=0;i<plan.length;i+=CONC) await Promise.all(plan.slice(i,i+CONC).map(patch));
  console.log("written ok=" + ok + " failed=" + fail);
  for (const e of errs) console.error("  " + e);

  // ---------------------------------------------------------- verification
  let u2 = base+"/_api/web/lists(guid'"+OI+"')/items?$select=Id,Title,Status,StepStatus,StatusDate,StepStatusStamped&$top=500";
  let after=[], g2=0;
  while (u2 && g2++<10) { const j=await J(u2); after=after.concat(j.value||[]); u2=j["odata.nextLink"]||null; }
  const withStatus = after.filter(r=>(r.Status||"").trim()!=="");
  // A dateless row is correctly split when Step Status is set and Status Date is blank,
  // so the two are counted separately rather than demanding both on every row.
  const stepSet = withStatus.filter(r=>(r.StepStatus||"")!=="");
  const filled  = withStatus.filter(r=>(r.StepStatus||"")!=="" && r.StatusDate);
  const mirrored = withStatus.filter(r=>(r.StepStatus||"")===(r.StepStatusStamped||""));
  const badTime = after.filter(r=>r.StatusDate && !/T0[45]:00:00Z$/.test(r.StatusDate));
  console.log("\n--- verification (trust this, not the write results) ---");
  console.log("rows with a composite Status : " + withStatus.length);
  console.log("...with Step Status set      : " + stepSet.length + "   (expect the same number)");
  console.log("...with a Status Date too    : " + filled.length
              + "   (expect the same MINUS the bare-prefix rows, which have no date)");
  console.log("StatusDate NOT stored at 04:00Z/05:00Z: " + badTime.length + "   (expect 0)");
  console.log("StepStatusStamped == StepStatus       : " + mirrored.length + " / " + withStatus.length +
              "   (must be ALL, or the auto-stamp flow overwrites these dates)");
  for (const r of badTime.slice(0,3)) console.error("  " + r.Title + " " + r.StatusDate);
})();

/* ---------------------------------------------------------------- UNDO ----
   Removes both columns and everything in them. The composite Status column is
   never modified by this script, so the source data is untouched either way.

(async () => {
  const base="https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI="d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const dg=await (await fetch(base+"/_api/contextinfo",{method:"POST",
                  headers:{Accept:"application/json;odata=nometadata"}})).json();
  for (const n of ["StepStatus","StatusDate"]) {
    const r=await fetch(base+"/_api/web/lists(guid'"+OI+"')/fields/getbyinternalnameortitle('"+n+"')",
      {method:"POST",headers:{"X-RequestDigest":dg.FormDigestValue,"X-HTTP-Method":"DELETE","IF-MATCH":"*"}});
    console.log(n+" -> "+r.status);
  }
})();
---------------------------------------------------------------------------- */
