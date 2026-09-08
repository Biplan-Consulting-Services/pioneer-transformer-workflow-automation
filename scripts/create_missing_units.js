/* Create the 4 live units the transfer flow skipped -- and their 2 missing parent Orders.

   HOW TO RUN
     1. Open the site in the browser, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio
     2. F12 -> Console. Paste this whole file. Press Enter.
     3. It prints what it created, then READS EVERY ROW BACK and prints what
        SharePoint actually stored. Trust the read-back, not the POSTs.

   WHY THESE SIX WERE MISSING -- fully diagnosed 2026-09-08, no guesswork:
     P1_001-1/1, P20001-1/1   parent Order row DOES NOT EXIST
     P20004-1/2, P20004-2/2   parent Order row is AMBIGUOUS: P20004 appears
                              TWICE in Order (Id 487 PIONEER TRANSFORMERS,
                              Id 488 ERMCO), so ResolvedOrderId cannot resolve
                              and RecordSkippedOrder fires. P20004 is the ONLY
                              duplicated order number in the entire 445-row
                              list, and its 2 units are EXACTLY the 2 that were
                              otherwise unexplained. That closes it.
                              🔴 STILL UNRESOLVED: repointing the units at 488
                              does NOT stop the skip. The flow resolves P20004
                              by NAME and will still find two rows. One of them
                              has to go before the flow can ever pick these up
                              -- Id 487 is the candidate: wrong client, and now
                              zero units attached.
     20877R1-1/1, P20002-1/1  also parentless, but they carry NO status, NO
                              location and NO tanking date -- dormant, so they
                              are deliberately NOT created here.

   WHY IT MATTERS THIS MORNING
     P1_001-1/1 is at Location BO (Bobinage) and P20001-1/1 at TA (Tanking) --
     both PHYSICALLY IN THE SHOP. P20004-1/2 and -2/2 tank Sep 28 and 29.
     If staff stop using the workbook while these are absent, four live units
     become invisible.

   HOW THE VALUES WERE DERIVED
     Not hand-picked. Every field is computed from TableOrders using the SAME
     rules the flow uses, read out of the live v006 definition:
       - dates are written as a BARE yyyy-mm-dd, which a Date-Only column
         stores as site-local midnight (04:00/05:00Z). Verified correct on the
         1,013 rows the run wrote. NEVER send a full instant here -- that is
         exactly the day-early bug the whole backfill existed to fix.
       - Location via the flow's own MappedLocation table (BO -> Bobinage,
         TA -> Tanking)
       - {Stage}Status is DERIVED, not copied: blank -> null, 'ec' -> In
         Progress, anything else -> Completed
       - Tank / ISO Coil / ISO Stack / Lead Assembly are BOOLEANS set from cell
         PRESENCE -- the workbook marks them with x, r or y, not true/false
       - BO comes from BO Manager's TableBO, never from TableOrders.BO
     Every Choice value below was validated against that column's own option
     list before this file was written (Location, Core Status, Production Line,
     Frame, Item Status, BO, and the stage statuses).

   ⚠️ OMITTING A FIELD IS NOT THE SAME AS SENDING NULL
     Learned the hard way on the first run of this script: three rows came back
     with Frame = "Plaspak" because the payloads simply left Frame out, and
     SharePoint then applied the COLUMN DEFAULT. The transfer flow does not hit
     this because it sends every mapped field explicitly, null included.
     NULLS below is therefore the list of fields that must be sent AS NULL
     rather than omitted, for any row where the workbook has no value.
     See scripts/fix_created_units.js, which repaired those three rows.

   SAFE TO RE-RUN: it checks each Title first and skips anything already
   present, so it cannot create duplicates. UNDO is at the bottom.
*/

(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";   // Order Items
  const ORD  = "6fe35dfe-2b7d-455a-abe3-056abb386733";   // Order

  // Internal names below were read from each list's own column metadata --
  // they are NOT guessable. Order Number really is Order_x0020_Number1, and
  // Initial Promised Date really is truncated to ...Dat.
  const ORDERS = {
    "P1_001": {
      Title: "P1_001", Order_x0020_Number1: "P1_001", OrderStatus: "Active",
      Order_x0020_Date: "2026-04-27", Initial_x0020_Promised_x0020_Dat: "2026-08-30",
      Lead_x0020_Time: 26, Qty: 1, Order_x0020_Type1: "R&D"
    },
    "P20001": {
      Title: "P20001", Order_x0020_Number1: "P20001", OrderStatus: "Active",
      Order_x0020_Date: "2025-08-11", Initial_x0020_Promised_x0020_Dat: "2026-09-30",
      Lead_x0020_Time: 24, PO: "ERMCO", Qty: 1, Indexing: "N",
      Province_x002F_State: "QC", Order_x0020_Type1: "R&D"
    }
  };
  const ORDER_CLIENT = { "P1_001": "PIONEER TRANSFORMERS", "P20001": "CONED" };

  const UNITS = {
    "P1_001-1/1": {
      Title: "P1_001-1/1", Unit_x0023_: 1, Qty: 1, SAJob: false,
      Order_Number_TextField: "P1_001", ItemStatus: "Active", Status: "TE-Se-4",
      Location: "Bobinage", CoreStatus: "Reçu", ProductionLine: "Power",
      CoilWinder: "103", Winder: "100-104",
      Tank: false, ISOCoil: true, ISOStack: true, LeadAssembly: false,
      CoilingDate: "2026-06-25", CoilingStatus: "Completed",
      Planned_x0020_Tanking_x0020_Date: "2026-08-28",
      OriginalTankingDate: "2026-07-06",
      TankingDateChangeJustification:
        "Repoussé car façade avec embossage long à se procurer (gomex)",
      BO: "OK"
    },
    "P20001-1/1": {
      Title: "P20001-1/1", Unit_x0023_: 1, Qty: 1, SAJob: false,
      Order_Number_TextField: "P20001", ItemStatus: "Active", Status: "TE-Se-4",
      Location: "Tanking", CoreStatus: "Reçu", ProductionLine: "Power",
      Frame: "Reçu", CoilWinder: "103", Winder: "100-104",
      Tank: true, ISOCoil: true, ISOStack: true, LeadAssembly: true,
      CoilingDate: "2026-07-01", CoilingStatus: "Completed",
      StackingDate: "2026-07-09", StackingStatus: "Completed",
      AssemblyDate: "2026-07-15", AssemblyStatus: "Completed",
      DryingDate: "2026-07-15", DryingStatus: "Completed",
      Planned_x0020_Tanking_x0020_Date: "2026-07-20",
      OriginalTankingDate: "2026-07-06",
      TankingDateChangeJustification:
        "Prototype / manque OLG flange pour continuer chez Metelec    ÉCHEC TEST HUILE",
      BO: "OK"
    },
    "P20004-1/2": {
      Title: "P20004-1/2", Unit_x0023_: 1, Qty: 2, SAJob: false,
      Order_Number_TextField: "P20004", ItemStatus: "Active",
      ProductionLine: "Power / Ligne 1", Winder: "100-104",
      Tank: false, ISOCoil: false, ISOStack: false, LeadAssembly: false,
      Planned_x0020_Tanking_x0020_Date: "2026-09-28",
      OriginalTankingDate: "2026-09-28",
      TankingDateChangeJustification:
        "Prototype / stop production attente du P20001",
      BO: "BO"
    },
    "P20004-2/2": {
      Title: "P20004-2/2", Unit_x0023_: 2, Qty: 2, SAJob: false,
      Order_Number_TextField: "P20004", ItemStatus: "Active",
      CoreStatus: "Entrepôt SN", ProductionLine: "Power / Ligne 1",
      Winder: "100-104",
      Tank: false, ISOCoil: false, ISOStack: false, LeadAssembly: false,
      Planned_x0020_Tanking_x0020_Date: "2026-09-29",
      OriginalTankingDate: "2026-09-29",
      TankingDateChangeJustification:
        "Prototype / stop production attente du P20001"
    }
  };

  // P20004 -> Order Id 488, client ERMCO. USER DECISION, 2026-09-08 08:30.
  //
  // ⚠️ THIS CONTRADICTS THE WORKBOOK, on purpose. TableOrders gives both P20004
  // units Client = PIONEER TRANSFORMERS, which is why the first run of this
  // script pointed them at Id 487. The user overrode that: P20004 is ERMCO's.
  // The row data supports them -- 487 carries Client PIONEER TRANSFORMERS with
  // Order Date 06-23 (matching the workbook), while 488 carries Client ERMCO
  // dated 06-25 and has NO units attached. That reads as 487 being created from
  // the workbook with the wrong client and 488 being the correction.
  //
  // Consequence to be aware of: the workbook still says PIONEER TRANSFORMERS,
  // so if the transfer flow ever resolves Client from TableOrders it will try
  // to write it back. Fix the workbook, or retire Id 487 (see below).
  const UNIT_ORDER  = { "P1_001-1/1": "P1_001", "P20001-1/1": "P20001",
                        "P20004-1/2": 488, "P20004-2/2": 488 };
  const UNIT_CLIENT = { "P1_001-1/1": "PIONEER TRANSFORMERS",
                        "P20001-1/1": "CONED",
                        "P20004-1/2": "ERMCO",
                        "P20004-2/2": "ERMCO" };

  // Fields that carry a column DEFAULT on Order Items and must therefore be
  // sent as an explicit null when the workbook has no value -- omitting them
  // lets SharePoint fill in the default. Frame is the one that caught us.
  const NULLS = ["Frame", "Location", "Status", "CoreStatus", "ProductionLine",
                 "CoilWinder", "Winder", "BO"];

  const J = async (u) => (await fetch(u, {headers:{Accept:"application/json;odata=nometadata"}})).json();
  const dg = await (await fetch(base + "/_api/contextinfo", {method:"POST",
                    headers:{Accept:"application/json;odata=nometadata"}})).json();
  const digest = dg.FormDigestValue;
  if (!digest) { console.error("no form digest - are you signed in to this site?"); return; }

  const etOf = async (id) =>
    (await J(base + "/_api/web/lists(guid'" + id + "')?$select=ListItemEntityTypeFullName"))
      .ListItemEntityTypeFullName;
  const ET_ORD = await etOf(ORD), ET_OI = await etOf(OI);

  const post = async (listId, et, obj) => {
    const b = Object.assign({}, obj, {__metadata:{type:et}});
    const r = await fetch(base + "/_api/web/lists(guid'" + listId + "')/items", {
      method:"POST",
      headers:{Accept:"application/json;odata=nometadata",
               "Content-Type":"application/json;odata=verbose",
               "X-RequestDigest":digest},
      body: JSON.stringify(b)});
    if (!r.ok) return {error: r.status + " " + (await r.text()).slice(0,400)};
    return await r.json();
  };

  // Resolve ClientId from Order rows that already carry the right client --
  // a direct Clients-list query came back empty, so this is the reliable route.
  const ex = await J(base + "/_api/web/lists(guid'" + ORD +
    "')/items?$select=Id,Order_x0020_Number1,ClientId,Client/Title&$expand=Client&$top=999");
  const cmap = {}, onum = {};
  for (const r of (ex.value || [])) {
    const n = ((r.Client && r.Client.Title) || "").trim().toUpperCase();
    if (n && !(n in cmap)) cmap[n] = r.ClientId;
    const k = (r.Order_x0020_Number1 || "").trim();
    if (k) (onum[k] = onum[k] || []).push(r.Id);
  }
  console.log("resolved ClientIds:", JSON.stringify({
    "PIONEER TRANSFORMERS": cmap["PIONEER TRANSFORMERS"], "CONED": cmap["CONED"]}));

  // ------------------------------------------------------------------ ORDERS
  const madeOrders = {};
  for (const [num, row] of Object.entries(ORDERS)) {
    if (onum[num] && onum[num].length) {
      console.log("order " + num + " already exists (Id " + onum[num].join(",") + ") - skipped");
      madeOrders[num] = onum[num][0];
      continue;
    }
    const body = Object.assign({}, row);
    const cid = cmap[(ORDER_CLIENT[num] || "").toUpperCase()];
    if (cid) body.ClientId = cid;
    const res = await post(ORD, ET_ORD, body);
    if (res.error) console.error("ORDER " + num + " FAILED: " + res.error);
    else { madeOrders[num] = res.Id; console.log("created order " + num + " -> Id " + res.Id); }
  }

  // ------------------------------------------------------------------- UNITS
  const titleFilter = Object.keys(UNITS)
    .map(t => "Title eq '" + t.replace(/'/g, "''") + "'").join(" or ");
  const have = await J(base + "/_api/web/lists(guid'" + OI +
    "')/items?$select=Id,Title&$filter=" + encodeURIComponent(titleFilter));
  const present = new Set((have.value || []).map(r => r.Title));
  const madeUnits = {};
  for (const [title, row] of Object.entries(UNITS)) {
    if (present.has(title)) { console.log("unit " + title + " already exists - skipped"); continue; }
    const body = Object.assign({}, row);
    for (const f of NULLS) if (!(f in body)) body[f] = null;   // never omit these
    const oref = UNIT_ORDER[title];
    const oid  = (typeof oref === "number") ? oref : madeOrders[oref];
    if (oid) body.OrderNumberId = oid;
    else console.warn("unit " + title + ": no parent Order id - creating WITHOUT the Order Number lookup");
    const cid = cmap[(UNIT_CLIENT[title] || "").toUpperCase()];
    if (cid) body.ClientId = cid;
    const res = await post(OI, ET_OI, body);
    if (res.error) console.error("UNIT " + title + " FAILED: " + res.error);
    else { madeUnits[title] = res.Id; console.log("created unit " + title + " -> Id " + res.Id); }
  }

  // -------------------------------------------------------------- READ BACK
  console.log("\n--- read-back: what SharePoint actually stored ---");
  const back = await J(base + "/_api/web/lists(guid'" + OI +
    "')/items?$select=Id,Title,Unit_x0023_,Qty,ItemStatus,Location,Status,CoreStatus," +
    "ProductionLine,Frame,Tank,ISOCoil,ISOStack,LeadAssembly,CoilingDate,CoilingStatus," +
    "Planned_x0020_Tanking_x0020_Date,OriginalTankingDate,BO,Order_Number_TextField," +
    "OrderNumberId,ClientId&$filter=" + encodeURIComponent(titleFilter));
  for (const r of (back.value || [])) console.log(JSON.stringify(r));
  console.log("\nrows now present: " + (back.value || []).length + " of " + Object.keys(UNITS).length);
  console.log("CHECK the dates read back as 04:00:00Z or 05:00:00Z, never 00:00:00Z.");
  console.log("UNDO ids -- orders: " + JSON.stringify(madeOrders) +
              "  units: " + JSON.stringify(madeUnits));
})();

/* ---------------------------------------------------------------- UNDO ----
   Paste the ids printed above into the two arrays and run this to remove
   exactly what was created. Deletes go to the site recycle bin.

(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const ORD  = "6fe35dfe-2b7d-455a-abe3-056abb386733";
  const UNIT_IDS  = [];   // <- unit ids printed above
  const ORDER_IDS = [];   // <- order ids printed above
  const dg = await (await fetch(base + "/_api/contextinfo", {method:"POST",
                    headers:{Accept:"application/json;odata=nometadata"}})).json();
  for (const [list, ids] of [[OI, UNIT_IDS], [ORD, ORDER_IDS]])
    for (const id of ids) {
      const r = await fetch(base + "/_api/web/lists(guid'" + list + "')/items(" + id + ")", {
        method:"POST",
        headers:{"X-RequestDigest":dg.FormDigestValue, "X-HTTP-Method":"DELETE", "IF-MATCH":"*"}});
      console.log(list.slice(0,8) + " " + id + " -> " + r.status);
    }
})();
---------------------------------------------------------------------------- */
