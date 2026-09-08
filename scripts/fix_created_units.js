/* Correct two defects in the 4 rows created by create_missing_units.js.

   HOW TO RUN
     1. Open, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser
     2. F12 -> Console. Paste this whole file. Press Enter.
        (if Chrome refuses the paste, type  allow pasting  first)
     3. Read the CONTAMINATION REPORT and the read-back at the end.

   WHAT WENT WRONG -- both found by reading the rows back, not by assuming

   (a) Frame = "Plaspak" on 3 rows that should be BLANK
       Ids 1128 (P1_001-1/1), 1130 (P20004-1/2), 1131 (P20004-2/2).
       The workbook has no Frame for these units. My create script filtered
       empty values out of the payload, so it OMITTED the Frame key -- and
       SharePoint then applied the column's DEFAULT. The transfer flow does not
       hit this because it sends Frame explicitly as null.
       Evidence it is wrong: the post-run export has Frame blank on 735 of
       1,117 rows, so blank is the normal state, not "Plaspak".
       Id 1129 (P20001-1/1) keeps Frame = "Reçu" -- that one is real.

   (b) ClientId is null on P20001-1/1 (Id 1129) and Order P20001 (Id 563)
       The create script resolved client ids from EXISTING Order rows, and no
       existing Order carries CONED, so the lookup silently came back empty.
       CONED does exist in the Clients list (Client_ID "CONE"). This script
       resolves it from the Clients list itself and sets it on both rows.

   ⚠️ A DISTINCTION THAT MATTERS
       Elsewhere in these docs I recorded that "null does not clear a field".
       That was measured against the POWER AUTOMATE SharePoint connector, which
       leaves the existing value when handed null -- that is what kept 844
       stale Pending statuses alive through the run. Raw REST is NOT the same
       code path and a null here is expected to clear. This script does not
       take that on faith: it writes, then reads back, and prints whether Frame
       is actually null. If it is not, it retries with an empty string.

   SAFE: touches only these 5 known ids and only these 2 fields. Re-runnable.
*/

(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const OI   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";   // Order Items
  const ORD  = "6fe35dfe-2b7d-455a-abe3-056abb386733";   // Order

  const CLEAR_FRAME = [1128, 1130, 1131];
  const UNIT_1129    = 1129;      // P20001-1/1  -> needs CONED
  const ORDER_563    = 563;       // P20001      -> needs CONED
  // what create_missing_units.js MEANT to set on each row, for the
  // contamination check below
  const INTENDED = {
    1128: ["Title","Unit_x0023_","Qty","SAJob","Order_Number_TextField","ItemStatus","Status",
           "Location","CoreStatus","ProductionLine","CoilWinder","Winder","Tank","ISOCoil",
           "ISOStack","LeadAssembly","CoilingDate","CoilingStatus",
           "Planned_x0020_Tanking_x0020_Date","OriginalTankingDate",
           "TankingDateChangeJustification","BO","OrderNumberId","ClientId"],
    1129: ["Title","Unit_x0023_","Qty","SAJob","Order_Number_TextField","ItemStatus","Status",
           "Location","CoreStatus","ProductionLine","Frame","CoilWinder","Winder","Tank","ISOCoil",
           "ISOStack","LeadAssembly","CoilingDate","CoilingStatus","StackingDate","StackingStatus",
           "AssemblyDate","AssemblyStatus","DryingDate","DryingStatus",
           "Planned_x0020_Tanking_x0020_Date","OriginalTankingDate",
           "TankingDateChangeJustification","BO","OrderNumberId","ClientId"],
    1130: ["Title","Unit_x0023_","Qty","SAJob","Order_Number_TextField","ItemStatus",
           "ProductionLine","Winder","Tank","ISOCoil","ISOStack","LeadAssembly",
           "Planned_x0020_Tanking_x0020_Date","OriginalTankingDate",
           "TankingDateChangeJustification","BO","OrderNumberId","ClientId"],
    1131: ["Title","Unit_x0023_","Qty","SAJob","Order_Number_TextField","ItemStatus","CoreStatus",
           "ProductionLine","Winder","Tank","ISOCoil","ISOStack","LeadAssembly",
           "Planned_x0020_Tanking_x0020_Date","OriginalTankingDate",
           "TankingDateChangeJustification","OrderNumberId","ClientId"]
  };
  // fields SharePoint always populates itself - not contamination
  const SYSTEM = new Set(["Id","ID","GUID","Created","Modified","AuthorId","EditorId","Attachments",
    "ContentTypeId","odata.etag","OData__UIVersionString","FileSystemObjectType","ServerRedirectedEmbedUri",
    "ServerRedirectedEmbedUrl","ComplianceAssetId","OData__ColorTag","Order","_ComplianceFlags",
    "_ComplianceTag","_ComplianceTagWrittenTime","_ComplianceTagUserId","AppAuthorId","AppEditorId",
    "CheckoutUserId","OData__CopySource","ParentVersionStringId","ParentLeafNameId"]);

  const J = async (u) => (await fetch(u, {headers:{Accept:"application/json;odata=nometadata"}})).json();
  const dg = await (await fetch(base + "/_api/contextinfo", {method:"POST",
                    headers:{Accept:"application/json;odata=nometadata"}})).json();
  const digest = dg.FormDigestValue;
  if (!digest) { console.error("no form digest - are you signed in?"); return; }
  const etOf = async (id) =>
    (await J(base + "/_api/web/lists(guid'" + id + "')?$select=ListItemEntityTypeFullName"))
      .ListItemEntityTypeFullName;
  const ET_OI = await etOf(OI), ET_ORD = await etOf(ORD);

  const merge = async (listId, et, id, patch) => {
    const r = await fetch(base + "/_api/web/lists(guid'" + listId + "')/items(" + id + ")", {
      method:"POST",
      headers:{Accept:"application/json;odata=nometadata",
               "Content-Type":"application/json;odata=verbose",
               "X-RequestDigest":digest, "X-HTTP-Method":"MERGE", "IF-MATCH":"*"},
      body: JSON.stringify(Object.assign({__metadata:{type:et}}, patch))});
    return r.ok ? {ok:true} : {error: r.status + " " + (await r.text()).slice(0,240)};
  };

  // ------------------------------------------- CONTAMINATION REPORT (before)
  console.log("--- CONTAMINATION REPORT: fields set that were never intended ---");
  for (const id of [1128,1129,1130,1131]) {
    const row = await J(base + "/_api/web/lists(guid'" + OI + "')/items(" + id + ")");
    const want = new Set(INTENDED[id]);
    const extra = Object.keys(row).filter(k =>
      !SYSTEM.has(k) && !want.has(k) && !/^OData_/.test(k) &&
      row[k] !== null && row[k] !== "" && row[k] !== false &&
      !(Array.isArray(row[k]) && row[k].length === 0));
    console.log("  Id " + id + " (" + row.Title + "): " +
      (extra.length ? extra.map(k => k + "=" + JSON.stringify(row[k])).join(", ") : "clean"));
  }

  // ------------------------------------------------------------ (a) Frame
  console.log("\n--- clearing Frame on " + CLEAR_FRAME.join(", ") + " ---");
  for (const id of CLEAR_FRAME) {
    let res = await merge(OI, ET_OI, id, {Frame: null});
    if (res.error) console.error("  " + id + " null FAILED: " + res.error);
    let back = await J(base + "/_api/web/lists(guid'" + OI + "')/items(" + id + ")?$select=Id,Title,Frame");
    if (back.Frame !== null && String(back.Frame).trim() !== "") {
      console.warn("  " + id + ": null did not clear it (still " + JSON.stringify(back.Frame) + ") - retrying with \"\"");
      res = await merge(OI, ET_OI, id, {Frame: ""});
      if (res.error) console.error("  " + id + " \"\" FAILED: " + res.error);
      back = await J(base + "/_api/web/lists(guid'" + OI + "')/items(" + id + ")?$select=Id,Title,Frame");
    }
    console.log("  " + id + " " + back.Title + " -> Frame = " + JSON.stringify(back.Frame));
  }

  // ------------------------------------------------------------ (b) CONED
  console.log("\n--- resolving CONED from the Clients list ---");
  const cl = await J(base + "/_api/web/lists/getbytitle('Clients')/items?$top=999");
  let conedId = null, matched = null;
  for (const r of (cl.value || [])) {
    for (const [k, v] of Object.entries(r)) {
      if (typeof v === "string" && v.trim().toUpperCase() === "CONED") { conedId = r.Id; matched = k; break; }
    }
    if (conedId) break;
  }
  console.log("  Clients rows: " + (cl.value || []).length + " | CONED Id: " + conedId + " (matched on field '" + matched + "')");
  if (!conedId) {
    console.error("  could NOT resolve CONED - leaving ClientId null. Fields on a sample Clients row: " +
      JSON.stringify(Object.keys((cl.value || [])[0] || {})));
  } else {
    for (const [list, et, id, label] of [[OI, ET_OI, UNIT_1129, "unit P20001-1/1"],
                                         [ORD, ET_ORD, ORDER_563, "order P20001"]]) {
      const res = await merge(list, et, id, {ClientId: conedId});
      if (res.error) console.error("  " + label + " FAILED: " + res.error);
      else {
        const back = await J(base + "/_api/web/lists(guid'" + list + "')/items(" + id + ")?$select=Id,ClientId");
        console.log("  " + label + " (Id " + id + ") -> ClientId = " + back.ClientId);
      }
    }
  }

  // -------------------------------------------------------------- READ BACK
  console.log("\n--- final read-back of all 4 units ---");
  const fin = await J(base + "/_api/web/lists(guid'" + OI +
    "')/items?$select=Id,Title,Frame,ClientId,OrderNumberId,Location,Status,CoreStatus," +
    "CoilingDate,Planned_x0020_Tanking_x0020_Date,BO&$filter=" +
    encodeURIComponent([1128,1129,1130,1131].map(i => "Id eq " + i).join(" or ")));
  for (const r of (fin.value || [])) console.log("  " + JSON.stringify(r));
  console.log("\nExpect: Frame null on 1128/1130/1131, \"Reçu\" on 1129; ClientId 74 on 1128/1130/1131");
  console.log("and the CONED id on 1129. Every date still 04:00:00Z or 05:00:00Z.");
})();
