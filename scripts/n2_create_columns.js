/* N2 -- create the 48 parent-sync columns on Order Items.

   HOW TO RUN
     1. Open the site in the browser, signed in:
        https://ermcopower.sharepoint.com/sites/PioneerPlanificatio
     2. F12 -> Console. Paste this whole file. Press Enter.
     3. It prints a per-field result, then reads every field back and prints
        what SharePoint actually stored. Trust the read-back, not the POSTs.

   WHAT IT DOES
     Creates each column with createfieldasxml and Options: 8
     (AddFieldInternalNameHint), which makes SharePoint honour the Name
     attribute as the internal name instead of deriving it from DisplayName.
     That is what avoids the create-short-then-rename dance AND the
     32-character truncation -- Protector & Switchgear Item # on this same
     list already became Protector_x0020__x0026__x0020_Sw, stopping mid-word.

     Options deliberately does NOT include 16 (AddFieldToDefaultView).
     Dropping 48 columns into the default view would wreck it.

     Every column lands in the group 'Parent Sync', so they are easy to find
     and easy to remove -- see UNDO at the bottom.

   TYPES ARE REMAPPED ON PURPOSE, not copied from the source list:
     DateTime    -> DateOnly   copying DateTime reintroduces the UTC-midnight
                               bug the whole backfill exists to fix
     Choice      -> Text       a synced Choice silently REJECTS any value
                               outside its option list, per row, inside the
                               sync flow -- the Family failure mode. The
                               source list already enforces the domain.
     Lookup      -> Text       a lookup ID is meaningless across lists;
                               sync the display value
     MultiChoice -> Note       exports as a JSON array, can be long

   These are all EMPTY columns. Creating them changes no data and fires no
   flow. The sync flows (N3) are a separate step and wait for A3.
*/

(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const LIST = "Order Items";
  const LIST_ID = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";   // Order Items

  const FIELDS = [
    "<Field Type=\"Text\" DisplayName=\"Order - Order Number\" Name=\"OrdOrderNumber\" StaticName=\"OrdOrderNumber\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Number\" DisplayName=\"Order - Qty\" Name=\"OrdQty\" StaticName=\"OrdQty\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Order - Order Type\" Name=\"OrdOrderType\" StaticName=\"OrdOrderType\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"DateTime\" DisplayName=\"Order - Order Date\" Name=\"OrdOrderDate\" StaticName=\"OrdOrderDate\" Required=\"FALSE\" Group=\"Parent Sync\" Format=\"DateOnly\" />",
    "<Field Type=\"DateTime\" DisplayName=\"Order - Initial Promised Date\" Name=\"OrdInitialPromisedDate\" StaticName=\"OrdInitialPromisedDate\" Required=\"FALSE\" Group=\"Parent Sync\" Format=\"DateOnly\" />",
    "<Field Type=\"URL\" DisplayName=\"Order - Order Folder\" Name=\"OrdOrderFolder\" StaticName=\"OrdOrderFolder\" Required=\"FALSE\" Group=\"Parent Sync\" Format=\"Hyperlink\" />",
    "<Field Type=\"Text\" DisplayName=\"Order - Order Step\" Name=\"OrdOrderStep\" StaticName=\"OrdOrderStep\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Note\" DisplayName=\"Order - Note\" Name=\"OrdNote\" StaticName=\"OrdNote\" Required=\"FALSE\" Group=\"Parent Sync\" NumLines=\"4\" />",
    "<Field Type=\"Text\" DisplayName=\"Order - PO\" Name=\"OrdPO\" StaticName=\"OrdPO\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Currency\" DisplayName=\"Order - Price\" Name=\"OrdPrice\" StaticName=\"OrdPrice\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Order - Province/State\" Name=\"OrdProvinceState\" StaticName=\"OrdProvinceState\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Order - WET-WETP\" Name=\"OrdWETWETP\" StaticName=\"OrdWETWETP\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Order - Indexing\" Name=\"OrdIndexing\" StaticName=\"OrdIndexing\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Order - New model to be created\" Name=\"OrdNewmodeltobecreated\" StaticName=\"OrdNewmodeltobecreated\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Boolean\" DisplayName=\"Order - Engineering Required\" Name=\"OrdEngineeringRequired\" StaticName=\"OrdEngineeringRequired\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Boolean\" DisplayName=\"Order - LDs\" Name=\"OrdLDs\" StaticName=\"OrdLDs\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Order - Client Date Status\" Name=\"OrdClientDateStatus\" StaticName=\"OrdClientDateStatus\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Note\" DisplayName=\"Order - Sales Notes\" Name=\"OrdSalesNotes\" StaticName=\"OrdSalesNotes\" Required=\"FALSE\" Group=\"Parent Sync\" NumLines=\"4\" />",
    "<Field Type=\"Text\" DisplayName=\"Order - Order Status\" Name=\"OrdOrderStatus\" StaticName=\"OrdOrderStatus\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Model - Model_ID\" Name=\"MdlModelID\" StaticName=\"MdlModelID\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Model - Modification_Status\" Name=\"MdlModificationStatus\" StaticName=\"MdlModificationStatus\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Number\" DisplayName=\"Model - Estimated Effort\" Name=\"MdlEstimatedEffort\" StaticName=\"MdlEstimatedEffort\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Model - Latest Model Revision\" Name=\"MdlLatestModelRevision\" StaticName=\"MdlLatestModelRevision\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Model - Parent Model\" Name=\"MdlParentModel\" StaticName=\"MdlParentModel\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Model_Revion_ID\" Name=\"RevModelRevionID\" StaticName=\"RevModelRevionID\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Spec_ID\" Name=\"RevSpecID\" StaticName=\"RevSpecID\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Client_Model_Code\" Name=\"RevClientModelCode\" StaticName=\"RevClientModelCode\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Note\" DisplayName=\"Mod. Rev. - Notes\" Name=\"RevNotes\" StaticName=\"RevNotes\" Required=\"FALSE\" Group=\"Parent Sync\" NumLines=\"4\" />",
    "<Field Type=\"Number\" DisplayName=\"Mod. Rev. - kVA\" Name=\"RevkVA\" StaticName=\"RevkVA\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Model Type\" Name=\"RevModelType\" StaticName=\"RevModelType\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Oil Type\" Name=\"RevOilType\" StaticName=\"RevOilType\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Core Type\" Name=\"RevCoreType\" StaticName=\"RevCoreType\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Number\" DisplayName=\"Mod. Rev. - Phases\" Name=\"RevPhases\" StaticName=\"RevPhases\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Number\" DisplayName=\"Mod. Rev. - Oil Amount\" Name=\"RevOilAmount\" StaticName=\"RevOilAmount\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Cable\" Name=\"RevCable\" StaticName=\"RevCable\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Form\" Name=\"RevForm\" StaticName=\"RevForm\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Copper (LV)\" Name=\"RevCopperLV\" StaticName=\"RevCopperLV\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Wire (HV)\" Name=\"RevWireHV\" StaticName=\"RevWireHV\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Number\" DisplayName=\"Mod. Rev. - Overcoil\" Name=\"RevOvercoil\" StaticName=\"RevOvercoil\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Note\" DisplayName=\"Mod. Rev. - Model Description\" Name=\"RevModelDescription\" StaticName=\"RevModelDescription\" Required=\"FALSE\" Group=\"Parent Sync\" NumLines=\"4\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - JS #\" Name=\"RevJS\" StaticName=\"RevJS\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Spec_Revision\" Name=\"RevSpecRevision\" StaticName=\"RevSpecRevision\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"DateTime\" DisplayName=\"Mod. Rev. - Spec_Date\" Name=\"RevSpecDate\" StaticName=\"RevSpecDate\" Required=\"FALSE\" Group=\"Parent Sync\" Format=\"DateOnly\" />",
    "<Field Type=\"Number\" DisplayName=\"Mod. Rev. - Primary Voltage\" Name=\"RevPrimaryVoltage\" StaticName=\"RevPrimaryVoltage\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Number\" DisplayName=\"Mod. Rev. - Secondary Voltage\" Name=\"RevSecondaryVoltage\" StaticName=\"RevSecondaryVoltage\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Pioneer Model Code\" Name=\"RevPioneerModelCode\" StaticName=\"RevPioneerModelCode\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Duplicate Order\" Name=\"RevDuplicateOrder\" StaticName=\"RevDuplicateOrder\" Required=\"FALSE\" Group=\"Parent Sync\" />",
    "<Field Type=\"Text\" DisplayName=\"Mod. Rev. - Family\" Name=\"RevFamily\" StaticName=\"RevFamily\" Required=\"FALSE\" Group=\"Parent Sync\" />",
  ];

  const dg = await (await fetch(base + "/_api/contextinfo", {
    method: "POST", credentials: "include",
    headers: { "Accept": "application/json;odata=nometadata" }
  })).json();
  const digest = dg.FormDigestValue;

  const results = [];
  for (const xml of FIELDS) {
    const disp = (xml.match(/DisplayName="([^"]*)"/) || [])[1];
    try {
      const r = await fetch(base + "/_api/web/lists/getbytitle('" + LIST + "')/fields/createfieldasxml", {
        method: "POST", credentials: "include",
        headers: {
          "Accept": "application/json;odata=nometadata",
          "Content-Type": "application/json;odata=verbose",
          "X-RequestDigest": digest
        },
        body: JSON.stringify({ parameters: {
          __metadata: { type: "SP.XmlSchemaFieldCreationInformation" },
          SchemaXml: xml, Options: 8 } })
      });
      results.push({ field: disp, ok: r.ok, status: r.status,
                     error: r.ok ? "" : (await r.text()).slice(0, 200) });
    } catch (e) {
      results.push({ field: disp, ok: false, status: 0, error: String(e) });
    }
  }

  console.table(results);
  const bad = results.filter(x => !x.ok);
  console.log(bad.length ? "FAILED: " + bad.length + " of " + results.length
                         : "all " + results.length + " posted OK");

  // Read back what SharePoint actually stored. A POST returning 200 is not
  // proof the field is the type you asked for.
  // NOTE: _api/web/lists/.../fields is UNAVAILABLE on this tenant -- it hangs as a
  // navigation (45s document_idle, 4 times across two days) and returns
  // "Failed to fetch" as a fetch. Use the v2.0 columns endpoint, which works.
  // The "sites/root" segment is required; _api/v2.0/lists/<id> returns itemNotFound.
  const cols = await (await fetch(base + "/_api/v2.0/sites/root/lists/" + LIST_ID + "/columns",
    { credentials: "include", headers: { "Accept": "application/json" } })).json();
  const mine = (cols.value || []).filter(c => c.columnGroup === "Parent Sync")
    .map(c => ({ name: c.name, display: c.displayName,
                 type: Object.keys(c).find(k => ["text","number","dateTime","boolean",
                        "currency","hyperlinkOrPicture","choice","lookup","note"].includes(k)) || "?" }));
  console.log("stored in group 'Parent Sync': " + mine.length + " (expect 48)");
  console.table(mine);
})();


/* ---------------------------------------------------------------- UNDO --
   Deletes every column in the 'Parent Sync' group. Safe while they are
   empty; once the sync flows have written data this destroys it.

(async () => {
  const base = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const LIST = "Order Items";
  const LIST_ID = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";   // Order Items
  const dg = await (await fetch(base + "/_api/contextinfo", { method: "POST",
    credentials: "include", headers: { "Accept": "application/json;odata=nometadata" } })).json();
  // Enumerate via the v2.0 columns endpoint -- _api/web/.../fields is unavailable
  // on this tenant. Getting this wrong would have left the rollback broken.
  const cols = await (await fetch(base + "/_api/v2.0/sites/root/lists/" + LIST_ID + "/columns",
    { credentials: "include", headers: { "Accept": "application/json" } })).json();
  const mine = (cols.value || []).filter(c => c.columnGroup === "Parent Sync");
  console.log("about to delete " + mine.length + " columns in group 'Parent Sync'");
  for (const f of mine) {
    const r = await fetch(base + "/_api/web/lists/getbytitle('" + LIST +
      "')/fields/getbyinternalnameortitle('" + f.name + "')", {
      method: "POST", credentials: "include",
      headers: { "X-RequestDigest": dg.FormDigestValue, "X-HTTP-Method": "DELETE",
                 "IF-MATCH": "*" } });
    console.log((r.ok ? "deleted " : "FAILED " + r.status + " ") + f.name);
  }
})();
---------------------------------------------------------------------- */
