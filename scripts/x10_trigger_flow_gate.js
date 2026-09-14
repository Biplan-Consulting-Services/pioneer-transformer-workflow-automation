/* X10 -- read-only. The gate that has to pass before the Order Items create-or-update
   trigger flow is re-enabled with v004, and the test units to exercise it with.

   Read-only: it writes nothing. Paste into the browser console on the SharePoint site
   and press Enter.

   WHY THIS EXISTS
     HANDOVER-2026-09-11 names two preconditions for turning the flow back on and gives
     no way to check either:

       1. "Re-run the StepStatusStamped = StepStatus check. It was 262/262 at 05:55."
          The only thing that ever printed that number is n8_split_status.js, whose
          verification block sits AFTER its early return on DRY RUN -- so the only way
          to re-read the gate with that script is to let it write. That is the wrong
          shape for a precondition.

       2. "Test on a unit that has no model -- one of the 203, not a healthy one."
          Nothing anywhere says WHICH. (And it is not 203: this script measured 16 with
          all three lookups empty on 2026-09-14. The 203 came from the *_TextField
          mirrors, off since 2026-08-21.) Picking one by hand out of ~1,190 rows is how
          the happy path gets tested again.

   WHAT IT CHECKS

     GATE A -- StepStatusStamped == StepStatus on every row that has a Step Status.
       If a row's mirror has drifted, v004's Condition_StatusDate fires on the next poll
       and re-stamps Status Date to TODAY. 246 rows carry a historical date. This is the
       only thing standing between them and a bulk overwrite, and unlike the rest of the
       flow's behaviour it cannot be undone by turning the flow off again.

     GATE B -- model-less units whose *_TextField mirror is NOT empty.
       These are the rows where v004's coalesce on the write actually does work. With a
       bare `@outputs('Get_Client')?['body/Client_ID']` the skipped Get passes null;
       R14 says this connector ignores a null rather than clearing the field, so the
       expected count here is the number of rows relying on R14 being right. Zero means
       the coalesce is belt-and-braces. Non-zero means it is load-bearing, and says how
       much data was riding on an observed connector behaviour.

     TEST UNITS -- model-less units that already satisfy Gate A, so a deliberate Step
       Status change on one produces a clean, attributable stamp. It prints the three
       lookup ids as nulls so you can see at a glance that it really is model-less.
*/
(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const J = async u => (await fetch(u, {credentials:"include",
              headers:{Accept:"application/json;odata=nometadata"}})).json();
  const page = async (u) => { let o=[],g=0;
    while (u && g++<30){ const j=await J(u); o=o.concat(j.value||[]); u=j["odata.nextLink"]||null; } return o; };

  const SEL = ["Id","Title","Status","StepStatus","StatusDate","StepStatusStamped",
               "ClientId","ModelId","ModelRevisionId",
               "Client_ID_TextField","Model_ID_TextField",
               "Model_Revision_ID_TextField","Order_Number_TextField"].join(",");

  const units = await page(base+"/_api/web/lists(guid'"+OI+"')/items?$select="+SEL+"&$top=500");
  if (!units.length) { console.error("ABORT: read 0 units. A zero-row read is a failed read, not a clean list."); return; }
  console.log("units read: " + units.length + "\n");

  const s = v => (v == null ? "" : String(v));
  const empty = v => s(v).trim() === "";

  /* ---------------------------------------------------------------- GATE A */
  const withStep = units.filter(u => !empty(u.StepStatus));
  const drifted  = withStep.filter(u => s(u.StepStatus) !== s(u.StepStatusStamped));
  const dated    = drifted.filter(u => u.StatusDate);

  console.log("=== GATE A -- StepStatusStamped == StepStatus ===");
  console.log("  rows with a Step Status : " + withStep.length);
  console.log("  mirror matches          : " + (withStep.length - drifted.length) + " / " + withStep.length);
  console.log("  DRIFTED                 : " + drifted.length + "   (must be 0)");
  if (drifted.length) {
    console.error("  " + dated.length + " of them already hold a Status Date that would be OVERWRITTEN with today.");
    for (const u of drifted.slice(0, 15))
      console.error("    " + s(u.Title).padEnd(14)
        + "step=" + s(u.StepStatus).padEnd(22)
        + "stamped=" + s(u.StepStatusStamped).padEnd(22)
        + "date=" + s(u.StatusDate).slice(0,10));
    if (drifted.length > 15) console.error("    ... and " + (drifted.length - 15) + " more");
    console.error("  GATE A FAILS. Re-mirror these before enabling the flow.");
  } else {
    console.log("  GATE A PASSES.");
  }

  /* ------------------------------------------------- the model-less units */
  const isNull = v => v == null || v === "";
  const modelless = units.filter(u => isNull(u.ClientId) && isNull(u.ModelId) && isNull(u.ModelRevisionId));
  const partial = units.filter(u => !modelless.includes(u)
                   && (isNull(u.ClientId) || isNull(u.ModelId) || isNull(u.ModelRevisionId)));

  console.log("\n=== the units the flow used to fail on ===");
  console.log("  all three lookups empty : " + modelless.length
    + "   (recorded as 203 in the handover -- that was the stale _TextField mirrors)");
  console.log("  SOME but not all empty  : " + partial.length
    + (partial.length ? "   <-- not the documented shape; v004 guards each get separately so these are handled, but they were never counted before" : ""));
  for (const u of partial.slice(0, 10))
    console.log("    " + s(u.Title).padEnd(14) + "Client=" + s(u.ClientId).padEnd(6)
      + "Model=" + s(u.ModelId).padEnd(6) + "Rev=" + s(u.ModelRevisionId));

  /* ---------------------------------------------------------------- GATE B */
  const MIRRORS = [["ClientId","Client_ID_TextField"],
                   ["ModelId","Model_ID_TextField"],
                   ["ModelRevisionId","Model_Revision_ID_TextField"]];
  console.log("\n=== GATE B -- a lookup is empty but its mirror is not ===");
  let riding = 0;
  for (const [lk, mir] of MIRRORS) {
    const rows = units.filter(u => isNull(u[lk]) && !empty(u[mir]));
    riding += rows.length;
    console.log("  " + mir.padEnd(28) + "populated on " + String(rows.length).padStart(4)
      + " rows whose " + lk + " is empty");
    for (const u of rows.slice(0, 5))
      console.log("      " + s(u.Title).padEnd(14) + mir + " = " + s(u[mir]));
  }
  console.log(riding === 0
    ? "  Zero. The coalesce on Update_item is belt-and-braces, not load-bearing."
    : "  " + riding + " values were relying on R14 (connector ignores a null). v004's coalesce is load-bearing.");

  /* ------------------------------------------------------------ test units */
  console.log("\n=== test units for v004 -- pick one of these, NOT a healthy unit ===");
  const cands = modelless.filter(u => !empty(u.StepStatus) && s(u.StepStatus) === s(u.StepStatusStamped));
  if (!cands.length) {
    console.log("  none: no model-less unit has a Step Status that already matches its mirror.");
    console.log("  Next best -- model-less with no Step Status at all (set one, expect a stamp):");
    for (const u of modelless.filter(u => empty(u.StepStatus)).slice(0, 5))
      console.log("    unit " + s(u.Title).padEnd(14) + "id " + u.Id);
  } else {
    for (const u of cands.slice(0, 5))
      console.log("  unit " + s(u.Title).padEnd(14) + "id " + String(u.Id).padEnd(6)
        + "step=" + s(u.StepStatus).padEnd(22)
        + "date=" + (s(u.StatusDate).slice(0,10) || "(none)").padEnd(12)
        + "lookups=" + [u.ClientId,u.ModelId,u.ModelRevisionId].map(v=>isNull(v)?"-":v).join("/"));
    console.log("\n  Change Step Status on one of these and wait one poll (5 min).");
    console.log("  EXPECT: the run succeeds, Status Date becomes today, Step Status Stamped");
    console.log("  follows the new value, and the run graph shows Get_Client and Get_Model");
    console.log("  SKIPPED rather than failed. A failed Get means a guard did not match the");
    console.log("  empty shape SharePoint actually sends -- read the trigger body and widen it.");
  }
})();
