/* X24 -- create `Status Date Stamped`, then bring all three stamps level with the row.

   DRY RUN by default: it writes nothing until APPLY = true.
   Paste into the browser console on the SharePoint site.

   🔴 RUN THIS WHILE THE TRIGGER FLOW IS OFF, and before v007 is enabled. Same reason as
   x11: once the flow is on, its first poll acts on every stale stamp before anything can
   stop it.

   WHY
     v007 of the trigger flow decides what staff did by comparing each value against the
     stamp the flow last left beside it:
       StepStatus vs StepStatusStamped \
       Location   vs LocationStamped    >  differ -> "the step moved" -> Status Date = today
       StatusDate vs StatusDateStamped  -> differ -> "staff typed the date" -> keep it
     A stamp that is merely STALE reads as a real edit. So a blank `LocationStamped`
     (57 rows on 09-16) would stamp today over a real hand-entered date on that unit's
     next edit. Levelling every stamp to the row's own values means the flow only reacts
     to edits made FROM NOW ON.

   WHAT IT WRITES
     1. the column, if missing: StatusDateStamped, Text(10), group 'Status Split', created
        with Options 8 so the internal name is exactly that, and NOT added to any view.
     2. per row, only the stamps that differ:
          StepStatusStamped = StepStatus
          LocationStamped   = Location
          StatusDateStamped = StatusDate as yyyy-MM-dd in Eastern time, or '' when blank
        Never StatusDate, StepStatus or Location themselves -- the verification reads all
        three before and after and diffs them.

   The yyyy-MM-dd must match what v007 computes, `formatDateTime(StatusDate,'yyyy-MM-dd')`.
   REST returns a date-only value as local midnight in UTC (T04:00Z / T05:00Z), which is the
   same calendar date either way -- but this converts through Eastern rather than slicing,
   so a value stored any other way is caught as a mismatch rather than silently shifted.
*/
(async () => {
  const APPLY = false;
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const CONC = 4;
  const H    = {Accept:"application/json;odata=nometadata"};

  const J = async u => { const r = await fetch(u, {credentials:"include", headers:H});
    if (!r.ok) throw new Error(r.status + " " + (await r.text()).slice(0,200)); return r.json(); };
  const page = async (u) => { let o=[],g=0;
    while (u && g++<30){ const j=await J(u); o=o.concat(j.value||[]); u=j["odata.nextLink"]||null; } return o; };
  const digest = async () => (await (await fetch(base + "/_api/contextinfo", {method:"POST",
    credentials:"include", headers:H})).json()).FormDigestValue;

  const s = v => (v == null ? "" : String(v));
  const eastDay = v => {
    if (!s(v)) return "";
    const d = new Date(new Date(v).toLocaleString("en-US", {timeZone:"America/Toronto"}));
    return d.getFullYear() + "-" + String(d.getMonth()+1).padStart(2,"0") + "-" + String(d.getDate()).padStart(2,"0");
  };
  const items = "/_api/web/lists(guid'" + OI + "')/items";

  // ---------------------------------------------------------------- 1. the column
  // Probe by $select, not by /fields -- the fields endpoint hangs on this tenant.
  let hasCol = true;
  try { await J(base + items + "?$select=Id,StatusDateStamped&$top=1"); }
  catch (e) { if (/^400/.test(e.message)) hasCol = false; else throw e; }
  console.log("StatusDateStamped column : " + (hasCol ? "exists" : "MISSING"));

  if (!hasCol) {
    if (!APPLY) { console.log("DRY RUN -- would create it. Row counts below assume it is blank.\n"); }
    else {
      const xml = '<Field Type="Text" DisplayName="Status Date Stamped" Name="StatusDateStamped" '
                + 'StaticName="StatusDateStamped" Required="FALSE" Group="Status Split" MaxLength="10" />';
      const r = await fetch(base + "/_api/web/lists(guid'" + OI + "')/fields/createfieldasxml", {
        method:"POST", credentials:"include",
        headers:{ Accept:"application/json;odata=nometadata",
                  "Content-Type":"application/json;odata=verbose",
                  "X-RequestDigest": await digest() },
        body: JSON.stringify({ parameters: { __metadata:{ type:"SP.XmlSchemaFieldCreationInformation" },
                                             SchemaXml: xml, Options: 8 } })
      });
      if (!r.ok) { console.error("ABORT: column create failed: " + (await r.text()).slice(0,300)); return; }
      await J(base + items + "?$select=Id,StatusDateStamped&$top=1");   // throws if the name is not what we asked for
      console.log("  created, internal name confirmed StatusDateStamped\n");
      hasCol = true;
    }
  }

  // ---------------------------------------------------------------- 2. the stamps
  const SEL = "Id,Title,StepStatus,StepStatusStamped,Location,LocationStamped,StatusDate"
            + (hasCol ? ",StatusDateStamped" : "");
  const read = () => page(base + items + "?$select=" + SEL + "&$top=500");
  const before = await read();
  if (!before.length) { console.error("ABORT: read 0 units. A zero-row read is a failed read."); return; }

  const want = u => {
    const w = {};
    if (s(u.StepStatus) !== s(u.StepStatusStamped))  w.StepStatusStamped = s(u.StepStatus);
    if (s(u.Location)   !== s(u.LocationStamped))    w.LocationStamped   = s(u.Location);
    if (eastDay(u.StatusDate) !== s(u.StatusDateStamped)) w.StatusDateStamped = eastDay(u.StatusDate);
    return w;
  };
  const todo = before.map(u => ({u, w: want(u)})).filter(x => Object.keys(x.w).length);
  const count = k => todo.filter(x => k in x.w).length;

  console.log("units read          : " + before.length);
  console.log("StepStatusStamped   : " + count("StepStatusStamped") + " to level");
  console.log("LocationStamped     : " + count("LocationStamped") + " to level");
  console.log("StatusDateStamped   : " + count("StatusDateStamped") + " to level   (units with a date: "
              + before.filter(u => s(u.StatusDate)).length + ")");
  console.log("rows to write       : " + todo.length + "\n");
  console.table(todo.slice(0, 30).map(({u, w}) => ({unit: u.Title, ...w,
    statusDate: s(u.StatusDate).slice(0,10) + "  <- MUST NOT CHANGE"})));
  if (todo.length > 30) console.log("  ... and " + (todo.length - 30) + " more");

  if (!todo.length) { console.log("Nothing to do -- every stamp is level."); return; }
  if (!APPLY) { console.log("\nDRY RUN -- nothing written. Confirm the trigger flow is OFF, then set APPLY = true."); return; }

  const dg = await digest();
  let ok = 0, fail = 0; const errs = [];
  const patch = async ({u, w}) => {
    const r = await fetch(base + items + "(" + u.Id + ")", {
      method:"POST", credentials:"include",
      headers:{ Accept:"application/json;odata=nometadata",
                "Content-Type":"application/json;odata=nometadata",
                "X-RequestDigest": dg, "IF-MATCH":"*", "X-HTTP-Method":"MERGE" },
      body: JSON.stringify(w)     // stamps only
    });
    if (r.ok) ok++; else { fail++; errs.push(u.Title + ": " + (await r.text()).slice(0,160)); }
  };
  console.log("\nwriting " + todo.length + " rows ...");
  for (let i=0;i<todo.length;i+=CONC) await Promise.all(todo.slice(i,i+CONC).map(patch));
  console.log("written ok=" + ok + " failed=" + fail);
  for (const e of errs) console.error("  " + e);

  // ---------------------------------------------------------------- verification
  // Trust this, not the write results.
  const after = await read();
  const byId = new Map(after.map(u => [u.Id, u]));
  const still = after.filter(u => Object.keys(want(u)).length);
  let moved = 0;
  for (const b of before) {
    const a = byId.get(b.Id);
    if (!a) { console.error("  row " + b.Title + " disappeared"); moved++; continue; }
    for (const f of ["StatusDate", "StepStatus", "Location"])
      if (s(a[f]) !== s(b[f])) { moved++; console.error("  " + f + " MOVED on " + b.Title + ": " + s(b[f]) + " -> " + s(a[f])); }
  }
  console.log("\n--- verification ---");
  console.log("stamps still off level : " + still.length + "   (expect 0)");
  console.log("real values CHANGED    : " + moved + "   (expect 0 -- this is the one that matters)");
  if (still.length) console.table(still.slice(0, 20).map(u => ({unit: u.Title, ...want(u)})));
  console.log(still.length === 0 && moved === 0
    ? "\nOK. v007 can be pasted and enabled; it will only react to edits made from now on."
    : "\nNOT CLEAN. Do NOT enable the trigger flow until this reads 0 / 0.");
})();
