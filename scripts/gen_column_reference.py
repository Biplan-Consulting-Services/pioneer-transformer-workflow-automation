# -*- coding: utf-8 -*-
"""Emit docs/column-reference.md — every SharePoint column, its type, and the
FRM10-12 column it becomes.

    python scripts/gen_column_reference.py

FOR SOMEBODY WRITING A QUERY AGAINST THESE LISTS
  Three things they need that no single place currently holds:

    internal name   what REST and Power Query actually address. Frequently NOT the
                    display name -- `Planned Tanking Date` is `Planned_x0020_Tanking_x0020_Date`,
                    and every stage's END date is `<Stage>Date`, not `<Stage>EndDate`.
    field type      Text / Note / Choice / Lookup / DateTime / Boolean / Number / Currency
    workbook column what it is called in FRM10-12's `TableOrders`, where different

  The first two come from the list's own `ListSchema`; the third from the viewer's
  `ColumnMap.pq`, which is the mapping the deployed workbook actually uses.

⚠️ TWO TRAPS THE EXPORT SETS, both already cost this project real time

  1. The `ListSchema` record is the CSV's FIRST RECORD, and a csv reader splits it on the
     commas inside its own JSON. Reading `row[0]` gives you the first fragment and
     exactly one `<Field>` tag -- which looks like a schema with one column in it rather
     than like a parsing bug. Join the whole record.

  2. **Lookup columns are absent from a CSV export entirely, values and schema alike.**
     So this reference cannot list them from an export, and any column a query needs
     that does not appear here may still exist as a Lookup. `Order Number`, `Client`,
     `Model` and `Model Revision` on `Order Items` are all lookups. Read those over
     `_api/web/lists(...)/items?$expand=` or through Power Query's own lookup expansion,
     not from a CSV.
"""
import csv, io, glob, json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
csv.field_size_limit(min(2 ** 31 - 1, sys.maxsize))

LISTS = ["Order Items", "Order", "Models", "Model Revisions", "Clients"]
SYSTEM = {"ContentType", "Attachments", "Edit", "LinkTitle", "LinkTitleNoMenu",
          "DocIcon", "ItemChildCount", "FolderChildCount", "AppAuthor", "AppEditor",
          "ComplianceAssetId", "LinkFilename", "LinkFilenameNoMenu", "FileLeafRef",
          "FileDirRef", "FSObjType", "SelectTitle", "InstanceID", "Order", "GUID",
          "WorkflowVersion", "WorkflowInstanceID", "ParentVersionString",
          "ParentLeafName", "Combine", "RepairDocument", "PermMask", "UniqueId",
          "SyncClientId", "ProgId", "ScopeId", "MetaInfo", "owshiddenversion",
          "FileRef", "ServerUrl", "EncodedAbsUrl", "BaseName", "SortBehavior",
          "CheckedOutUserId", "IsCheckedoutToLocal", "CheckoutUser", "VirusStatus",
          "CheckedOutTitle", "NoExecute", "ContentVersion", "AccessPolicy",
          "AppModifiedBy", "AppCreatedBy"}
OUT = os.path.join(ROOT, "docs", "column-reference.md")
COLUMNMAP = os.path.join(os.path.dirname(ROOT), "FRM10-12", "viewer",
                         "power-query", "ColumnMap.pq")

# ColumnMap's Entity names vs the export file names
ENTITY = {"Order Items": "Order Items", "Orders": "Order",
          "Model Revisions": "Model Revisions", "Models": "Models",
          "ClientLeadTimes": "Clients"}


def schema(path):
    """[(internal, display, type)] from the export's ListSchema record."""
    rec = ",".join(next(csv.reader(io.open(path, encoding="utf-8-sig", newline=""))))
    if not rec.startswith("ListSchema="):
        return []
    # Strip backslashes outright rather than un-escaping pairs. The record arrives with
    # a mix of single- and double-escaped quotes depending on the field, so a paired
    # replace leaves `Type=\Note"` on 86 of 150 columns -- which reads as "this column
    # has no type" rather than as a parsing bug. No attribute value here carries a
    # meaningful backslash.
    rec = rec.replace(chr(92), "")
    out = []
    for tag in re.findall(r"<Field\b.*?/?>", rec):
        def attr(a):
            # The opening quote is optional. Between the JSON escaping and the CSV's
            # own quote-doubling, some attributes survive the round trip as
            # `Type=DateTime"` with the leading quote eaten -- 78 of 140 columns on
            # Order Items, which silently read as "no type" until one was printed raw.
            m = re.search(r'(?<![A-Za-z])%s="?([^"]*)"' % a, tag)
            return m.group(1) if m else ""
        name, disp, ty = attr("Name"), attr("DisplayName"), attr("Type")
        # SharePoint's own plumbing: edit-menu anchors, content type, attachments, the
        # per-view link columns. Real on the list, noise in a reference written for
        # somebody building a query, and they outnumber several of the real groups.
        if not name or name.startswith("_") or name in SYSTEM:
            continue
        out.append((name, disp or name, ty or "?"))
    return out


def column_map():
    """{(entity, sharepoint display name) -> workbook column}."""
    if not os.path.exists(COLUMNMAP):
        return {}
    s = io.open(COLUMNMAP, encoding="utf-8").read()
    out = {}
    for e, sf, wf, ty in re.findall(
            r'\[Entity = "([^"]+)", SourceField = "([^"]+)", '
            r'WorkbookField = "([^"]+)", Type = "([^"]+)"', s):
        out[(ENTITY.get(e, e), sf)] = (wf, ty)
    return out


def main():
    cmap = column_map()
    lines = [
        "# SharePoint columns, their types, and the FRM10-12 column each becomes",
        "",
        "Generated by `scripts/gen_column_reference.py` — re-run it rather than editing,",
        "and re-export the list first or it describes a list that has changed.",
        "",
        "**Read the internal name column.** It is what REST and Power Query address, and it",
        "is often not the display name. Two families in particular:",
        "",
        "- `Planned Tanking Date` is `Planned_x0020_Tanking_x0020_Date` — spaces and other",
        "  characters are encoded, and the internal name is truncated at 32 characters.",
        "- 🔴 **Every stage's END date is `<Stage>Date`, not `<Stage>EndDate`.** The columns",
        "  were created as *Coiling Date* and renamed to *Coiling End Date* when the Start",
        "  Dates were added, and **a SharePoint rename does not change the internal name.**",
        "  The Start Dates, created later, genuinely are `<Stage>StartDate` — so the two",
        "  halves of the same pair follow different rules. This has broken two scripts.",
        "",
        "🔴 **Lookup columns are missing from this document**, because they are absent from a",
        "CSV export entirely — values and schema alike. On `Order Items` that means",
        "`Order Number`, `Client`, `Model` and `Model Revision`. Read them with",
        "`$expand=` over REST, or let Power Query expand them; do not conclude from this",
        "page that they do not exist.",
        "",
    ]

    for name in LISTS:
        g = sorted(glob.glob(os.path.join(ROOT, "sharepoint-lists", "%s 2*.csv" % name)))
        if not g:
            lines += ["## %s" % name, "", "_no export found_", ""]
            continue
        cols = schema(g[-1])
        counts = collections.Counter(t for _, _, t in cols)
        lines += [
            "## %s" % name, "",
            "`%s` · %d columns in the schema · %s" % (
                os.path.basename(g[-1]), len(cols),
                " · ".join("%s %d" % (t, n) for t, n in counts.most_common())),
            "",
            "| internal name (use this) | display name | type | FRM10-12 column |",
            "|---|---|---|---|",
        ]
        for internal, disp, ty in sorted(cols, key=lambda c: c[1].lower()):
            wf = cmap.get((name, disp))
            wb = "`%s`" % wf[0] if wf else ("same" if wf is None and False else "—")
            if wf and wf[0] == disp:
                wb = "same name"
            lines.append("| `%s` | %s | %s | %s |" % (internal, disp, ty, wb))
        lines.append("")

    mapped = sum(1 for k in cmap)
    lines += [
        "---",
        "",
        "## What the FRM10-12 column means here",
        "",
        "Taken from `FRM10-12/viewer/power-query/ColumnMap.pq`, the mapping the **deployed**",
        "workbook uses — %d entries across all entities. A dash means the column is not in"
        % mapped,
        "`TableOrders`: it exists on the list but the workbook never showed it.",
        "",
        "⚠️ `TableOrders` is a **join of several lists**, not a view of one. A unit row",
        "carries its own `Order Items` fields plus columns pulled from its Order, its Model",
        "Revision and its Client. So a workbook column can come from any of the sections",
        "above, and the same display name can appear on more than one list.",
        "",
        "## If you are writing a query against these lists",
        "",
        "- **The lists are the source of truth, not the workbook.** `Revue/FRM10-12.xlsx` is",
        "  a read-only mirror rebuilt from them, and it is refreshed on a schedule by a",
        "  person rather than continuously.",
        "- **Do not read the workbook to get at list data.** Query the lists directly;",
        "  `FRM10-12/viewer/power-query/sharepoint-lists/*.pq` shows how, including lookup",
        "  expansion.",
        "- **`Order Items` is the per-unit list** (1,189 rows). `Order` is per order (457).",
        "  A unit's id looks like `21865-1/5` — order number, unit number, order quantity.",
        "- Columns prefixed `Order -`, `Model -`, `Mod. Rev. -` and `Client -` on",
        "  `Order Items` are **automatically maintained copies** of a parent's value. Read",
        "  them freely; never write them.",
        "",
    ]

    io.open(OUT, "w", encoding="utf-8", newline="\r\n").write("\n".join(lines))
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    for name in LISTS:
        g = sorted(glob.glob(os.path.join(ROOT, "sharepoint-lists", "%s 2*.csv" % name)))
        if g:
            print("   %-18s %3d columns" % (name, len(schema(g[-1]))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
