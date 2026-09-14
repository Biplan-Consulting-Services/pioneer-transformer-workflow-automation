# -*- coding: utf-8 -*-
"""Port FRM10-12's remaining calculated columns onto `Order Items`.

    python gen_calc_columns.py

Emits, from the formulas read out of the workbook package rather than from any prose:

    scripts/n9_create_calc_columns.js               the five calculated columns, over REST
    sharepoint-lists/formatting/Price.format.json           the three UI columns,
    sharepoint-lists/formatting/NavigationOrder.format.json  as column formatting
    sharepoint-lists/formatting/NavigationModel.format.json

WHAT CHANGED, AND WHY THIS IS NOW POSSIBLE
------------------------------------------
`calculated-columns-plan.md` opens with "none of the 7 columns below can be a plain
SharePoint calculated column", on two walls:

    1. no cross-list lookups        <- THIS WALL IS GONE
    2. no volatile functions, no Hyperlink output

N3 fanned 48 parent columns down onto `Order Items`, so every input Price CAD/USD needs
is now on the same item: `Price`, `Province/State`, `Initial Promised Date`. `BO` is on
the list too, which retires that doc's "needs a BO field created first -- it exists on
neither list today". The two Excel lookup tables never needed to be lists: 13 province
codes that have not changed since 1999, and six rows of FX rate, both inlined below.

Wall 2 stands, and splits the remaining columns cleanly in two:

    UI     Price, Navigation Order, Navigation Model   -- all three are HYPERLINK().
           They were never data. Column formatting renders a link natively, so they
           become formatting, not columns.
    DATA   Price CAD, Price USD                        -- money. Real calculated columns.

`Archived` is excluded: the user says it is deprecated, and the workbook has no formula
left for it anyway (confirmed by scanning the package -- 6 of the 7 flagged columns carry
a calculatedColumnFormula, `Archived` does not).

🔴 THE DEPENDENCY THAT FORCES A DECISION MADE EARLIER TODAY
-----------------------------------------------------------
Price CAD and Price USD both read `Estimated Delivery Date` -- they take `YEAR()` of it
to pick an FX rate. A calculated column can only reference a STORED field.

So: **Price CAD/USD as calculated columns require Estimated Delivery Date to be a stored
column.** Column formatting alone does not satisfy them -- it renders a string into the
page and stores nothing for a formula to read. This closes the open question in
`estimated-delivery-date-today.md` by dependency rather than by preference.

It also rules out storing the UNFLOORED estimate (the zero-daily-write idea): for a unit
whose milestone is in the past, the floored and unfloored values can fall in different
calendar years, which picks a different FX rate and so a different price. Fidelity to the
workbook needs the floored value, which needs the daily pass over the stalled rows.

`n9_create_calc_columns.js` refuses to create the chain until that column exists.

WHERE THE PRICE AND PROVINCE ACTUALLY LIVE -- corrected 2026-09-14
------------------------------------------------------------------
A first pass at this assumed `Order Items` carried BOTH a native `Price` / `Province/
State` / `Initial Promised Date` and an N3-fanned `Ord*` copy, and made choosing between
them a parameter. That was wrong, and `column-reference.md` says so if you read it by
SECTION rather than grepping the whole file: those three columns are on the **`Order`**
list. `Order Items` has exactly one copy of each, the `Ord*` one N3 puts there.

So there is no choice to make -- and the reason the port is possible at all is precisely
that N3 fanned them down. Before that, these were the cross-list lookups that disqualified
the columns. The check at the bottom of this file is now section-aware, because a
whole-document grep is what produced the wrong answer.

UI_LANGUAGE is a real choice. The two navigation columns read Excel's `SelectedLanguage`
defined name, and column formatting cannot see the viewer's UI language.
"""
import json, io, os, re, argparse

# ----------------------------------------------------------------- the choice
UI_LANGUAGE = "FR"               # "FR" or "EN" -- the two navigation columns

SITE = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio"
ORDER_VIEW = SITE + "/Lists/Order/AllItems.aspx?view=7&q="
MODELREV_VIEW = (SITE + "/Lists/Models%20Revisions/AllItems.aspx"
                 "?viewid=5526fc48-6a40-4e8b-a015-7cb3f2c32705&view=7&q=")

# Canadian province/territory codes, inlined from TableCanadianProvince (AL1:AM14).
# Static reference data -- a list would be ceremony around 13 strings.
PROVINCES = ["AB", "BC", "MB", "NB", "NL", "NT", "NS", "NU", "ON", "PE", "QC", "SK", "YT"]

# Table_USD_CAD_Conversion_Rate (AI1:AJ7). XLOOKUP match_mode -1 = exact or next SMALLER,
# so a year above the table takes the last rate; this reproduces that and ALSO clamps
# below the table, where Excel returns #N/A (Price CAD) or a string that then breaks the
# arithmetic (Price USD). Deliberate: a pre-2024 date should price at the oldest known
# rate rather than render an error in a money column.
FX = [(2024, 1.35), (2025, 1.44), (2026, 1.38), (2027, 1.39), (2028, 1.43), (2029, 1.47)]

# (display name, internal name). These are the N3 "Parent Sync" copies, and they are the
# ONLY copies on Order Items -- the originals are on the Order list. See the docstring.
SRC = {"price":    ("Order - Price", "OrdPrice"),
       "province": ("Order - Province/State", "OrdProvinceState"),
       "promised": ("Order - Initial Promised Date", "OrdInitialPromisedDate")}

EDD = ("Estimated Delivery Date", "EstimatedDeliveryDate")
# The lookup, not `Order_Number_TextField`. The mirror is written by the create-or-update
# trigger flow, which is OFF, so it is the one field on the row that may be stale; the
# lookup cannot be. Internal name read off the live flow definition
# (`triggerBody()?['OrderNumber/Value']`) rather than column-reference.md, which states
# outright that lookup columns are absent from it because an export cannot show them.
ORDER_LOOKUP = "OrderNumber"
LOOKUPS = {"OrderNumber", "Client", "Model", "ModelRevision"}
MODELCODE = "RevClientModelCode"      # workbook "PO Item #"

GROUP = "Calculated"


def xesc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def fx_rate_formula(year_col):
    """Nested IF over the FX table, referencing a helper column rather than re-deriving
    the year. Inlining the date cascade instead would repeat a ~100-char expression once
    per rate and push the formula toward SharePoint's length limit for no benefit."""
    expr = str(FX[-1][1])
    for yr, rate in reversed(FX[1:-1]):
        expr = 'IF([%s]=%d,%s,%s)' % (year_col, yr, rate, expr)
    expr = 'IF([%s]<=%d,%s,%s)' % (year_col, FX[0][0], FX[0][1], expr)
    return 'IF([%s]=0,0,%s)' % (year_col, expr)


def calc_fields():
    pd, _ = SRC["price"]
    vd, vi = SRC["province"]
    md, mi = SRC["promised"]
    _, pi = SRC["price"]
    ed, ei = EDD

    date_cascade = 'IF(ISBLANK([%s]),[%s],[%s])' % (ed, md, ed)

    return [
        # Split out so each piece is independently readable and checkable in a view.
        dict(disp="Is Canadian", name="IsCanadian", rtype="Boolean", refs=[vi],
             formula="=" + "OR(%s)" % ",".join('[%s]="%s"' % (vd, p) for p in PROVINCES),
             why="TableCanadianProvince, inlined. Non-Canadian orders are priced in USD."),

        dict(disp="Fx Year", name="FxYear", rtype="Number", dec=0, refs=[ei, mi],
             formula="=IF(AND(ISBLANK([%s]),ISBLANK([%s])),0,YEAR(%s))" % (ed, md, date_cascade),
             why="Excel's two-deep cascade: Estimated Delivery Date, else Initial Promised "
                 "Date. 0 means neither is set -- Excel yields the string 'Invalid date for "
                 "conversion' here and then errors on YEAR(); 0 is the same condition, "
                 "testable."),

        dict(disp="Fx Rate", name="FxRate", rtype="Number", dec=4, refs=["FxYear"],
             formula="=" + fx_rate_formula("Fx Year"),
             why="THE ONE PLACE TO EDIT WHEN A NEW YEAR'S RATE IS AGREED. Update FX in "
                 "gen_calc_columns.py and re-run; do not hand-edit the column."),

        dict(disp="Price CAD", name="PriceCAD", rtype="Currency", dec=2,
             refs=["IsCanadian", pi, "FxRate"],
             formula='=IF([Is Canadian],[%s],IF([Fx Rate]=0,"",[%s]*[Fx Rate]))' % (pd, pd),
             why="Canadian order: the price is already CAD. Otherwise it is USD, converted."),

        dict(disp="Price USD", name="PriceUSD", rtype="Currency", dec=2,
             refs=["IsCanadian", pi, "FxRate"],
             formula='=IF([Is Canadian],IF([Fx Rate]=0,"",[%s]/[Fx Rate]),[%s])' % (pd, pd),
             why="The mirror image. Excel multiplies by (1/rate); dividing is the same "
                 "value without the intermediate rounding."),
    ]


def schema_xml(f):
    extra = ""
    if f["rtype"] in ("Number", "Currency"):
        extra += ' Decimals="%d"' % f.get("dec", 2)
    if f["rtype"] == "Currency":
        extra += ' LCID="1033"'
    refs = "".join('<FieldRef Name="%s" />' % r for r in f["refs"])
    return ('<Field Type="Calculated" DisplayName="%s" Name="%s" StaticName="%s" '
            'Required="FALSE" Group="%s" ResultType="%s"%s>'
            '<Formula>%s</Formula><FieldRefs>%s</FieldRefs></Field>'
            % (f["disp"], f["name"], f["name"], GROUP, f["rtype"], extra,
               xesc(f["formula"]), refs))


def link(href_expr, text_expr, title):
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/sp/v2/column-formatting.schema.json",
        "elmType": "a",
        "txtContent": "=" + text_expr,
        "attributes": {"target": "_blank", "title": title},
        "style": {"text-decoration": "none", "white-space": "nowrap"},
        "customRowAction": None,
        "href": "=" + href_expr,
    }


def ui_formats():
    order = "[$%s.lookupValue]" % ORDER_LOOKUP
    code = "[$%s]" % MODELCODE
    pd, _ = SRC["price"]
    open_order = "'Ouvrir commande '" if UI_LANGUAGE == "FR" else "'Navigate to Order '"
    open_model = "'Ouvrir " + "modèle '" if UI_LANGUAGE == "FR" else "'Navigate to model '"

    return {
        # Applied to the EXISTING Price column, which is why this one is strictly better
        # than the Excel original: Excel's HYPERLINK() replaced the number with a link and
        # lost it as a value. Formatting paints over a column that still holds real
        # currency, so Price stays sortable, filterable and summable AND gets the link.
        "Price": (link("'%s' + %s" % (ORDER_VIEW, order),
                       "'$' + toLocaleString(Number([$%s]))" % SRC["price"][1],
                       "Ouvrir la commande dans la liste Order"),
                  "formats the existing '%s' column -- no new column needed" % pd),

        "NavigationOrder": (link("'%s' + %s" % (ORDER_VIEW, order),
                                 "%s + %s" % (open_order, order),
                                 "Ouvrir la commande dans la liste Order"),
                            "needs an empty Text column named 'Navigation Order'"),

        "NavigationModel": (link("'%s' + %s" % (MODELREV_VIEW, code),
                                 "%s + %s" % (open_model, code),
                                 "Ouvrir la revision de modele"),
                            "needs an empty Text column named 'Navigation Model'"),
    }


CREATOR_HEAD = """/* N9 -- create the five calculated columns ported from FRM10-12.
   GENERATED by scripts/gen_calc_columns.py -- regenerate, do not hand-edit.

   Paste into the browser console on the SharePoint site.

   DRY RUN by default: it creates nothing until APPLY = true.

   IT REFUSES TO RUN until `Estimated Delivery Date` exists as a STORED column on the
   list. Fx Year reads it, and Price CAD / Price USD read Fx Year, so creating the chain
   first would give three columns that silently evaluate against a field that is not
   there. A calculated column cannot read a column-formatting result -- that renders in
   the browser and is never stored. See docs/estimated-delivery-date-today.md.
*/
(async () => {
  const APPLY = false;
  const base = "%(site)s";
  const LIST = "Order Items";
  const EDD_INTERNAL = "%(edd)s";

  const J = async u => (await fetch(u, {credentials:"include",
              headers:{Accept:"application/json;odata=nometadata"}})).json();

  const FIELDS = %(fields)s;

  // ---------------------------------------------------------------- preflight
  const f = await J(base + "/_api/web/lists/getbytitle('" + LIST + "')/fields"
              + "?$select=InternalName,TypeAsString&$top=500");
  if (!f.value || !f.value.length) { console.error("ABORT: read 0 fields."); return; }
  const have = new Map(f.value.map(x => [x.InternalName, x.TypeAsString]));

  const edd = have.get(EDD_INTERNAL);
  if (!edd) {
    console.error("ABORT: '" + EDD_INTERNAL + "' does not exist on " + LIST + ".");
    console.error("  Fx Year reads it and the two price columns read Fx Year.");
    console.error("  Create it as a STORED column first -- a calculated column cannot");
    console.error("  read a column-formatting result.");
    return;
  }
  if (edd === "Calculated") {
    console.error("ABORT: '" + EDD_INTERNAL + "' is a Calculated column.");
    console.error("  It uses TODAY(), which SharePoint evaluates only on write, so it");
    console.error("  freezes at last save. That is the bug this whole port exists past.");
    return;
  }
  console.log("Estimated Delivery Date present, type " + edd + " -- ok\\n");

  const dup = FIELDS.filter(x => have.has(x.name));
  if (dup.length) {
    console.error("ABORT: already present: " + dup.map(d => d.name).join(", "));
    console.error("  Delete them first, or this creates duplicates with a 0 suffix --");
    console.error("  the x9 cleanup exists because that already happened once.");
    return;
  }
  for (const x of FIELDS)
    for (const r of x.refs)
      if (!have.has(r) && !FIELDS.some(y => y.name === r))
        { console.error("ABORT: " + x.name + " references missing field " + r); return; }

  console.table(FIELDS.map(x => ({ field: x.name, type: x.rtype, formula: x.formula })));
  if (!APPLY) { console.log("\\nDRY RUN -- nothing created. Set APPLY = true."); return; }
"""

CREATOR_TAIL = """
  const dg = await (await fetch(base + "/_api/contextinfo", { method:"POST",
    credentials:"include", headers:{Accept:"application/json;odata=nometadata"} })).json();

  const results = [];
  // Sequential on purpose: Fx Rate references Fx Year and the price columns reference
  // both, and SharePoint rejects a FieldRef to a field that does not exist yet.
  for (const x of FIELDS) {
    try {
      const r = await fetch(base + "/_api/web/lists/getbytitle('" + LIST
        + "')/fields/createfieldasxml", {
        method:"POST", credentials:"include",
        headers:{ Accept:"application/json;odata=nometadata",
                  "Content-Type":"application/json;odata=verbose",
                  "X-RequestDigest": dg.FormDigestValue },
        body: JSON.stringify({ parameters: {
          __metadata:{ type:"SP.XmlSchemaFieldCreationInformation" },
          SchemaXml: x.xml, Options: 8 } })
      });
      results.push({ field:x.name, ok:r.ok, status:r.status,
                     error: r.ok ? "" : (await r.text()).slice(0,300) });
      if (!r.ok) break;   // a later field references this one; stop rather than cascade
    } catch (e) { results.push({ field:x.name, ok:false, status:0, error:String(e) }); break; }
  }
  console.table(results);

  // Read back. A 200 is not proof SharePoint stored the ResultType you asked for --
  // it silently accepts and downgrades some combinations.
  const after = await J(base + "/_api/web/lists/getbytitle('" + LIST + "')/fields"
                  + "?$select=InternalName,TypeAsString,OutputType&$top=500");
  const made = (after.value||[]).filter(x => FIELDS.some(y => y.name === x.InternalName));
  console.log("\\n--- read back (trust this, not the POST results) ---");
  console.table(made.map(x => ({ field:x.InternalName, type:x.TypeAsString, output:x.OutputType })));
})();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default="docs/column-reference.md")
    ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    fields = calc_fields()
    for f in fields:
        f["xml"] = schema_xml(f)

    # ------------------------------------------------------------------ verify
    # Section-aware on purpose: column-reference.md documents five lists, and a
    # whole-file grep happily "finds" an Order-list column and calls it an Order Items
    # one. That is exactly the mistake this file's docstring records.
    known, sec = set(), None
    for ln in io.open("docs/column-reference.md", encoding="utf-8"):
        h = re.match(r"^## (.+)$", ln)
        if h:
            sec = h.group(1).strip()
            continue
        m = re.match(r"^\|\s*`([^`]+)`\s*\|", ln)
        if m and sec == "Order Items":
            known.add(m.group(1))
    known |= LOOKUPS      # real columns, absent from the doc by its own admission
    made = {f["name"] for f in fields}
    # EstimatedDeliveryDate is deliberately allowed to be absent here: it is the one
    # prerequisite this port cannot create for itself, and the generated script gates on
    # it at run time with an explanation. Generating the chain while it is missing is
    # correct; CREATING it would not be.
    for f in fields:
        for r in f["refs"]:
            assert r in known or r in made or r == EDD[1], \
                "%s references %s, which is neither on the list nor created here" % (f["name"], r)
        assert f["name"] not in known, "%s already exists on the list" % f["name"]
    for k in ("price", "province", "promised"):
        assert SRC[k][1] in known, "source column %s not on the list" % SRC[k][1]
    assert ORDER_LOOKUP in known, "%s not on the list" % ORDER_LOOKUP
    assert MODELCODE in known, "%s not on the list" % MODELCODE
    assert EDD[1] not in known, \
        "Estimated Delivery Date already exists -- re-check the chain before creating it"

    js = (CREATOR_HEAD % {"site": SITE, "edd": EDD[1],
                          "fields": json.dumps(
                              [{"name": f["name"], "rtype": f["rtype"], "refs": f["refs"],
                                "formula": f["formula"], "xml": f["xml"]} for f in fields],
                              indent=4)}) + CREATOR_TAIL
    io.open("scripts/n9_create_calc_columns.js", "w", encoding="utf-8").write(js)

    os.makedirs("sharepoint-lists/formatting", exist_ok=True)
    fmts = ui_formats()
    for name, (doc, note) in fmts.items():
        io.open("sharepoint-lists/formatting/%s.format.json" % name, "w",
                encoding="utf-8").write(json.dumps(doc, indent=2) + "\n")

    print("source columns    : %s" % ", ".join(v[1] for v in SRC.values()))
    print("navigation labels : %s" % UI_LANGUAGE)
    print("\nwrote scripts/n9_create_calc_columns.js")
    for f in fields:
        print("  %-14s %-9s %s" % (f["disp"], f["rtype"], f["formula"][:88]))
    print("\nwrote sharepoint-lists/formatting/")
    for name, (_, note) in fmts.items():
        print("  %-18s %s" % (name + ".json", note))
    print("\n  every FieldRef resolves, no column collides with an existing one,")
    print("  and Estimated Delivery Date is confirmed absent (the creator gates on it).")


if __name__ == "__main__":
    main()
