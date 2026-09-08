/* Creates the view "FRM10-12 Layout" on Order Items -- a mirror of FRM10-12's
   TableOrders column order, left to right.

   Full mapping, with the reason behind every single position:
     docs/frm10-12-order-view-spec.md

   HOW TO RUN
     1. Open the site in the browser, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio
        -- NOT from a SharePoint application page. A batch run from Home.aspx froze
        the renderer mid-request with the write outcome unknown (2026-09-07). Open a
        lightweight page first, e.g.
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/lists/getbytitle('Order Items')/defaultview/viewfields
     2. F12 -> Console. Paste this whole file. Press Enter.
     3. It preflights every field name, creates the view, then READS THE VIEW BACK and
        prints what SharePoint actually stored. Trust the read-back, not the POST.

   WHAT IT DOES / DOES NOT DO
     Creates a NEW view. It never modifies an existing one -- it aborts if a view with
     this title already exists rather than touching it. `Overview` was already lost once
     on this list (2026-09-01 -> 2026-09-04) and SharePoint retains no deleted view
     definitions, so nothing here overwrites.
     Creates it as a personal-scope view? NO -- PersonalView: false, i.e. PUBLIC, which
     is SharePoint's own default and matches every other view on this list. Flip
     PERSONAL to true below if you want to try it privately first.
     SetAsDefaultView: false. The default view is not touched.

   FIELD COUNT -- IS THERE A LIMIT?  (researched, not assumed)
     There is NO documented maximum number of ViewFields in a SharePoint Online view.
     The two enforced limits are:
       1. The LOOKUP COLUMN THRESHOLD: 12 per view, counting Lookup + Person/Group +
          Managed Metadata columns together (Created By / Modified By count too).
          Exceeding it fails the ENTIRE view at render time -- "the number of lookup and
          workflow status columns it contains exceeds the threshold (12) enforced by the
          administrator" -- and on SharePoint Online it CANNOT be raised.
          This view uses 5 of 12: Client, Model, OrderNumber, ModelRevision, RegroupedInto.
       2. The LIST VIEW THRESHOLD: 5,000 items. Not a factor; Order Items holds 1,052.
     So 79 ViewFields is fine, and there is direct proof on this very list:
     the default All Items view already carries 95 fields and renders all 95.
     The cost of a wide view is horizontal scrolling, not a limit -- inherent to the
     goal here, since the workbook is that wide too.

   WHAT WILL LOOK BROKEN AND IS NOT
     28 of these columns are the Ord / Mdl / Rev parent-sync columns created
     EMPTY on 2026-09-07. The N3 sync flows that populate them are not built yet, so
     that whole block renders blank. Four more native columns (Configuration,
     Section Qty, Info+, Technical Notes) exist but were never backfilled from the
     workbook -- see the spec doc; that one is a real gap, not a naming difference.

   ENDPOINT FACTS FOR THIS TENANT -- established by testing, do not deviate
     POST _api/contextinfo                                      OK  (X-RequestDigest)
     POST _api/web/lists/getbytitle('X')/views                  OK  (create)
     GET  _api/web/lists/.../views/getbytitle('X')?$expand=ViewFields   OK (read-back)
     GET  _api/web/lists/.../fields/getbyinternalnameortitle('X')       OK (single field)
     GET  _api/v2.0/sites/root/lists/<id>/columns                OK  ('sites/root' required)
     GET  _api/v2.0/lists/<id>/columns                           FAILS itemNotFound
     GET  _api/web/lists/.../fields?$select=...&$filter=...      FAILS hangs / "Failed to fetch"
                                                                 -- NEVER use the /fields
                                                                    collection query.
*/

(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const LIST = "Order Items";
  const LIST_ID = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";                 // Order Items
  const VIEW = "FRM10-12 Layout";
  const PERSONAL = false;                       // public, like every other view here
  const ROW_LIMIT = 100;                        // matches Production Floor / Planning

  // Deliberately empty. TableOrders is already filtered upstream (TableOrders.pq drops
  // rows the Archive shows as Location=AN, or LI with a delivery date), so a faithful
  // mirror would filter ItemStatus eq 'Active'. It is left off because this view's job
  // is to prove the column mapping, and a filter hides the rows that would expose a bad
  // one. To add it later, uncomment:
  // const VIEW_QUERY = "<Where><Eq><FieldRef Name='ItemStatus' /><Value Type='Text'>Active</Value></Eq></Where>";
  const VIEW_QUERY = "";

  /* ViewFields, in FRM10-12 TableOrders order (position 1 = column B, leftmost).
     9 of the workbook's 82 columns are not here:
       absent   (3): Lead Time, Ing. Due Date, Duplicate
       excluded (6): Price, Estimated Delivery Date, Price CAD, Price USD,
                     Navigation Order, Navigation Model  -- the native Excel formula
                     columns; TableOrders.pq strips exactly these before it runs.
     Every name below is copied from a real source (the CSV export's ListSchema record,
     N2 field definitions, or the hand-resolved lookup names) -- NEVER retyped. Two of
     them are cut mid-word at 32 characters. */
  const VIEWFIELDS = [
    "Title",                               //  1  renamed       Order
    "Client",                              //  2  direct        Client
    "RevkVA",                              //  3  parent-sync   KVA and KV
    "RevPrimaryVoltage",                   //  4  parent-sync   Primary Voltage
    "RevSecondaryVoltage",                 //  5  parent-sync   Secondary Voltage
    "RevPhases",                           //  6  parent-sync   Phases
    "RevJS",                               //  7  parent-sync   JS #
    "RevModelDescription",                 //  8  parent-sync   Description
    "RevModelType",                        //  9  parent-sync   Type
    "OrdPO",                               // 10  parent-sync   PO
    "OrdOrderDate",                        // 11  parent-sync   Order Date
    "Qty",                                 // 14  direct        Qty
    "Model",                               // 15  renamed       PO Item #
    "RevFamily",                           // 16  parent-sync   Family
    "OrdEngineeringRequired",              // 18  parent-sync   Engineering Required
    "RevDuplicateOrder",                   // 19  parent-sync   Duplicate Order
    "OrdProvinceState",                    // 21  parent-sync   Province/State
    "OrdWETWETP",                          // 22  parent-sync   WET-WETP
    "OrdIndexing",                         // 23  parent-sync   Indexing
    "OrdLDs",                              // 24  parent-sync   LDs
    "OrdInitialPromisedDate",              // 25  parent-sync   Initial Promised Date
    "TrimestrialCustomer",                 // 26  direct        Trimestrial Customer
    "OrdClientDateStatus",                 // 27  parent-sync   Client Date Status
    "Info_x002b_",                         // 28  direct        Info+
    "ProtectorStatus",                     // 29  direct        Protector Status
    "ProtectorSwitchgearPO",               // 30  direct        Protector & Switchgear PO
    "Protector_x0020__x0026__x0020_Sw",    // 31  direct        Protector & Switchgear Item #
    "OrdSalesNotes",                       // 32  parent-sync   Sales Notes
    "Technical_x0020_Notes",               // 33  direct        Technical Notes
    "Location",                            // 34  direct        Location
    "Status",                              // 35  split         Status
    "Witness_x002f_Other",                 // 36  direct        Witness/Other
    "TemperatureRise",                     // 37  direct        Temperature Rise
    "Impulse",                             // 38  direct        Impulse
    "DB",                                  // 39  direct        DB
    "PartialD",                            // 40  direct        Partial D
    "OilAnalysis",                         // 41  direct        Oil Analysis
    "SFRA",                                // 42  direct        SFRA
    "CSA",                                 // 43  direct        CSA
    "RevCoreType",                         // 44  parent-sync   Core
    "CoreStatus",                          // 45  direct        Core Status
    "RevOilType",                          // 46  parent-sync   Oil Type
    "RevOilAmount",                        // 47  parent-sync   Oil Amount
    "ProductionLine",                      // 48  direct        Production Line
    "Configuration",                       // 49  direct        Configuration
    "Section_x0020_Qty",                   // 50  direct        Section Qty
    "RevCable",                            // 51  parent-sync   Cable
    "CoilWinder",                          // 52  direct        Coil Winder
    "RevForm",                             // 53  parent-sync   Form
    "RevCopperLV",                         // 54  parent-sync   Copper (LV)
    "RevWireHV",                           // 55  parent-sync   Wire (HV)
    "RevOvercoil",                         // 56  parent-sync   Overcoil
    "Winder",                              // 57  direct        Winder
    "Time_x0028_days_x0029_",              // 58  direct        Time (days)
    "Tank",                                // 59  direct        Tank
    "TankDeliveryDate",                    // 60  direct        Tank Delivery Date
    "Frame",                               // 61  direct        Frame
    "ISOStack",                            // 62  direct        ISO Stack
    "ISOCoil",                             // 63  direct        ISO Coil
    "LeadAssembly",                        // 64  direct        Lead Assembly
    "CoilingDate",                         // 65  renamed       Coiling Date
    "StackingDate",                        // 66  renamed       Stacking Date
    "AssemblyDate",                        // 67  renamed       Assembly Date
    "DryingDate",                          // 68  renamed       Drying Date
    "Planned_x0020_Tanking_x0020_Date",    // 69  renamed       Tanking Date
    "TestingDate",                         // 70  renamed       Testing Date
    "FinishingDate",                       // 71  renamed       Finishing Date
    "Planned_x0020_Delivery_x0020_Dat",    // 72  renamed       Delivery Date
    "OriginalTankingDate",                 // 73  direct        Original Tanking Date
    "TankingDateChangeJustification",      // 74  direct        Tanking date change justification
    "ManualEstimatedDeliveryDate",         // 76  direct        Manual Estimated Delivery Date
    "BO",                                  // 77  direct        BO
    "OrdPrice",                            // 78  parent-sync   Price Value

    // ---- tail: list-native, no TableOrders counterpart ----
    "OrderNumber",                         // tail        Order Number
    "Unit_x0023_",                         // tail        Unit #
    "SAJob",                               // tail        SA Job
    "ItemStatus",                          // tail        Item Status
    "ModelRevision",                       // tail        Model Revision
    "RegroupedInto",                       // tail        Regrouped Into
  ];

  const j = (r) => r.json();
  const digestOf = async () => (await j(await fetch(base + "/_api/contextinfo", {
    method: "POST", credentials: "include",
    headers: { "Accept": "application/json;odata=nometadata" }
  }))).FormDigestValue;

  console.log("ViewFields requested: " + VIEWFIELDS.length +
              "  (73 mirrored + tail)");
  const dupes = VIEWFIELDS.filter((n, i) => VIEWFIELDS.indexOf(n) !== i);
  if (dupes.length) { console.error("ABORT -- duplicate ViewFields: " + dupes.join(", ")); return; }

  // ---------------------------------------------------------------- preflight 1: name exists?
  // A ViewField naming a nonexistent column is accepted without error and then renders
  // NOTHING -- the exact failure mode a truncated internal name causes. Check every one
  // first, one at a time: the /fields COLLECTION query hangs on this tenant, but
  // getbyinternalnameortitle on a single field works.
  console.log("preflight: resolving " + VIEWFIELDS.length + " field names ...");
  const resolved = [];
  for (const n of VIEWFIELDS) {
    try {
      const r = await fetch(base + "/_api/web/lists/getbytitle('" + LIST +
        "')/fields/getbyinternalnameortitle('" + n + "')?$select=InternalName,Title,TypeAsString,Hidden",
        { credentials: "include", headers: { "Accept": "application/json;odata=nometadata" } });
      if (!r.ok) { resolved.push({ field: n, ok: false, note: "HTTP " + r.status }); continue; }
      const f = await r.json();
      resolved.push({
        field: n, ok: f.InternalName === n,
        display: f.Title, type: f.TypeAsString, hidden: f.Hidden,
        note: f.InternalName === n ? "" : "resolved to '" + f.InternalName + "' -- NOT an internal-name match"
      });
    } catch (e) { resolved.push({ field: n, ok: false, note: String(e) }); }
  }
  console.table(resolved);
  const unresolved = resolved.filter(x => !x.ok);
  if (unresolved.length) {
    console.error("ABORT -- " + unresolved.length + " field name(s) did not resolve on '" +
                  LIST + "'. Nothing was created. Fix the names first:");
    console.table(unresolved);
    return;
  }
  const lookupish = resolved.filter(x =>
    ["Lookup", "LookupMulti", "User", "UserMulti", "TaxonomyFieldType",
     "TaxonomyFieldTypeMulti", "WorkflowStatus"].includes(x.type));
  console.log("lookup-class fields in this view: " + lookupish.length +
              " of 12 (threshold, not raisable on SharePoint Online) -- " +
              lookupish.map(x => x.field).join(", "));
  if (lookupish.length >= 12) {
    console.error("ABORT -- at or over the 12-column lookup threshold. The view would " +
                  "fail to render entirely. Nothing was created.");
    return;
  }

  // ---------------------------------------------------------------- preflight 2: title free?
  const existing = await fetch(base + "/_api/web/lists/getbytitle('" + LIST +
    "')/views/getbytitle('" + VIEW + "')?$select=Title,Id",
    { credentials: "include", headers: { "Accept": "application/json;odata=nometadata" } });
  if (existing.ok) {
    const v = await existing.json();
    console.error("ABORT -- a view titled '" + VIEW + "' already exists (Id " + v.Id +
                  "). This script never modifies an existing view. Rename VIEW above, " +
                  "or run the UNDO block at the bottom first.");
    return;
  }

  // ---------------------------------------------------------------- create
  const digest = await digestOf();
  const body = {
    parameters: {
      __metadata: { type: "SP.ViewCreationInformation" },
      Title: VIEW,
      ViewTypeKind: 1,                 // SP.ViewType.html = 1 (a standard list view).
                                       // NOT 0 -- 0 is ViewType.none.
      PersonalView: PERSONAL,
      SetAsDefaultView: false,
      RowLimit: ROW_LIMIT,
      Paged: true,
      Query: VIEW_QUERY,
      ViewFields: { results: VIEWFIELDS }
    }
  };
  const cr = await fetch(base + "/_api/web/lists/getbytitle('" + LIST + "')/views", {
    method: "POST", credentials: "include",
    headers: {
      "Accept": "application/json;odata=nometadata",
      "Content-Type": "application/json;odata=verbose",
      "X-RequestDigest": digest
    },
    body: JSON.stringify(body)
  });
  const crText = await cr.text();
  console.log("create: HTTP " + cr.status + (cr.ok ? " OK" : " FAILED"));
  if (!cr.ok) { console.error(crText.slice(0, 1200)); return; }

  // Some tenants ignore ViewFields on create and give you the default set. That is why
  // the read-back below exists, and why it re-adds anything missing rather than
  // declaring success.

  // ---------------------------------------------------------------- READ BACK
  // A 200 is not proof. This prints what SharePoint actually stored.
  const rb = await j(await fetch(base + "/_api/web/lists/getbytitle('" + LIST +
    "')/views/getbytitle('" + VIEW +
    "')?$select=Title,Id,ServerRelativeUrl,RowLimit,Paged,PersonalView,DefaultView,ViewQuery&$expand=ViewFields",
    { credentials: "include", headers: { "Accept": "application/json;odata=nometadata" } }));

  // The ViewFields payload comes back in one of three shapes depending on the odata
  // flavour the tenant honours: {Items:[...]}, {results:[...]}, or only a SchemaXml
  // string of <FieldRef Name="..."/> elements. Handle all three -- reading zero fields
  // out of a populated view and then "repairing" all 79 would be the worst outcome here.
  const readFields = (vf) => {
    if (!vf) return null;
    if (Array.isArray(vf)) return vf;
    if (Array.isArray(vf.Items)) return vf.Items;
    if (Array.isArray(vf.results)) return vf.results;
    if (typeof vf.SchemaXml === "string")
      return [...vf.SchemaXml.matchAll(/<FieldRef[^>]*\bName="([^"]+)"/g)].map(m => m[1]);
    return null;
  };
  let storedArr = readFields(rb.ViewFields);
  if (!storedArr) {   // last resort: the dedicated viewfields endpoint, confirmed working here
    const vf2 = await j(await fetch(base + "/_api/web/lists/getbytitle('" + LIST +
      "')/views/getbytitle('" + VIEW + "')/viewfields",
      { credentials: "include", headers: { "Accept": "application/json;odata=nometadata" } }));
    storedArr = readFields(vf2) || [];
    if (!storedArr.length) console.warn("could not read ViewFields back in any known shape " +
      "-- inspect the raw response before trusting anything below, and do NOT let the " +
      "repair pass run.");
  }
  console.log("--- what SharePoint actually stored ---");
  console.log({ Title: rb.Title, Id: rb.Id, Url: rb.ServerRelativeUrl,
                RowLimit: rb.RowLimit, Paged: rb.Paged, PersonalView: rb.PersonalView,
                DefaultView: rb.DefaultView, ViewQuery: rb.ViewQuery,
                ViewFieldCount: storedArr.length });
  console.log("stored ViewFields, in stored order:");
  console.table(storedArr.map((n, i) => ({
    pos: i + 1, stored: n, requested: VIEWFIELDS[i] || "(none)",
    same: n === VIEWFIELDS[i] ? "" : "<-- differs"
  })));

  const missing = VIEWFIELDS.filter(n => !storedArr.includes(n));
  const extra   = storedArr.filter(n => !VIEWFIELDS.includes(n));
  const orderOk = storedArr.length === VIEWFIELDS.length &&
                  storedArr.every((n, i) => n === VIEWFIELDS[i]);
  console.log("requested " + VIEWFIELDS.length + " | stored " + storedArr.length);
  if (missing.length) console.warn("MISSING from the stored view (" + missing.length + "): " + missing.join(", "));
  if (extra.length)   console.warn("EXTRA in the stored view ("   + extra.length   + "): " + extra.join(", "));
  console.log(orderOk
    ? "ORDER: exact match -- the view mirrors TableOrders left to right."
    : "ORDER: DIFFERS from requested. The table above shows where.");

  // Repair pass: only ever ADDS a missing field, and only to the view this script just
  // created. It cannot reorder -- SharePoint appends. If the order is wrong, delete the
  // view (UNDO below) and investigate rather than patching.
  if (missing.length && !storedArr.length) {
    console.error("NOT repairing: the read-back returned zero fields, which almost " +
                  "certainly means the read failed rather than the view being empty. " +
                  "Adding all " + missing.length + " on that basis could duplicate fields.");
  } else if (missing.length) {
    console.log("repair: adding " + missing.length + " missing field(s) ...");
    const d2 = await digestOf();
    for (const n of missing) {
      const r = await fetch(base + "/_api/web/lists/getbytitle('" + LIST +
        "')/views/getbytitle('" + VIEW + "')/viewfields/addviewfield('" + n + "')", {
        method: "POST", credentials: "include",
        headers: { "Accept": "application/json;odata=nometadata", "X-RequestDigest": d2 }
      });
      console.log((r.ok ? "added " : "FAILED " + r.status + " ") + n);
    }
    console.log("re-read the view (rerun the read-back block) to confirm the final order.");
  }

  console.log("view URL: " + location.origin + (rb.ServerRelativeUrl || ""));
  console.log(missing.length || extra.length || !orderOk
    ? "DONE, WITH DIFFERENCES -- read the warnings above before showing this to anyone."
    : "DONE -- " + storedArr.length + " fields stored in the requested order.");
})();


/* ---------------------------------------------------------------- UNDO --
   Deletes the view this script created, by title. Safe: a view holds no data, and this
   script only ever created a NEW view, so nothing staff built is at risk. It refuses to
   delete the default view.

   Paste the block below (without the comment markers) to roll back.

(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const LIST = "Order Items";
  const VIEW = "FRM10-12 Layout";
  const r0 = await fetch(base + "/_api/web/lists/getbytitle('" + LIST +
    "')/views/getbytitle('" + VIEW + "')?$select=Title,Id,DefaultView",
    { credentials: "include", headers: { "Accept": "application/json;odata=nometadata" } });
  if (!r0.ok) { console.log("nothing to undo -- no view titled '" + VIEW + "' (HTTP " + r0.status + ")"); return; }
  const v = await r0.json();
  if (v.DefaultView) { console.error("REFUSING -- '" + VIEW + "' is the DEFAULT view. Not deleting."); return; }
  const dg = await (await fetch(base + "/_api/contextinfo", { method: "POST",
    credentials: "include", headers: { "Accept": "application/json;odata=nometadata" } })).json();
  const r = await fetch(base + "/_api/web/lists/getbytitle('" + LIST +
    "')/views/getbytitle('" + VIEW + "')", {
    method: "POST", credentials: "include",
    headers: { "X-RequestDigest": dg.FormDigestValue, "X-HTTP-Method": "DELETE", "IF-MATCH": "*" } });
  console.log((r.ok ? "deleted view " : "FAILED " + r.status + " ") + VIEW + " (Id " + v.Id + ")");
  // Confirm the delete -- a 200 is not proof here either.
  const r2 = await fetch(base + "/_api/web/lists/getbytitle('" + LIST +
    "')/views/getbytitle('" + VIEW + "')?$select=Title",
    { credentials: "include", headers: { "Accept": "application/json;odata=nometadata" } });
  console.log(r2.ok ? "STILL PRESENT -- the delete did not take." : "confirmed gone (HTTP " + r2.status + ")");
})();
---------------------------------------------------------------------- */
