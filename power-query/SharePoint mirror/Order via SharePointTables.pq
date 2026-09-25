// SIDE-BY-SIDE ONLY - not a mirror. The same Order list through SharePoint.Tables
// (the connector FRM10-12 uses), kept so the mirror's acceptance test can SEE what
// that connector does to dates instead of assuming.
//
// For each date column it records the value exactly as Power Query holds it, and the
// M type it arrived as. Compare with the `Order` query (raw REST text, e.g.
// Order 559 Order_x0020_Date = "2026-09-01T00:00:00Z"):
//   - datetimezone with the Z kept      -> SharePoint.Tables is safe for E7-type checks
//   - datetime (no zone) / shifted hour -> it normalises; only the REST mirror can see E7
let
    Source   = SharePoint.Tables(SP_Site, [Implementation = "2.0"]),
    Items    = Source{[Title = "Order"]}[Items],
    Wanted   = {"ID", "Order Number", "Order Date", "Initial Promised Date", "Created", "Modified"},
    Keep     = Table.SelectColumns(Items, List.Intersect({Wanted, Table.ColumnNames(Items)})),
    Kind     = (v) => if v = null then "null"
                      else if Value.Is(v, type datetimezone) then "datetimezone"
                      else if Value.Is(v, type datetime) then "datetime"
                      else if Value.Is(v, type date) then "date"
                      else if Value.Is(v, type text) then "text"
                      else "other",
    Show     = (v) => if v = null then null
                      else if Value.Is(v, type datetimezone) then DateTimeZone.ToText(v, "yyyy-MM-ddTHH:mm:sszzz")
                      else if Value.Is(v, type datetime) then DateTime.ToText(v, "yyyy-MM-ddTHH:mm:ss")
                      else if Value.Is(v, type date) then Date.ToText(v, "yyyy-MM-dd")
                      else Text.From(v),
    DateCols = List.Intersect({{"Order Date", "Initial Promised Date", "Created", "Modified"}, Table.ColumnNames(Keep)}),
    WithKind = List.Accumulate(DateCols, Keep, (t, c) =>
                   Table.AddColumn(t, c & " [M type]", each Kind(Record.Field(_, c)), type text)),
    AsText   = Table.TransformColumns(WithKind, List.Transform(DateCols, each {_, Show, type nullable text}))
in
    AsText
