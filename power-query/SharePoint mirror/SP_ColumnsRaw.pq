// A list's column definitions from _api/v2.0 - the one metadata route that works on
// this tenant. `_api/web/lists/.../fields` HANGS here (four 45 s timeouts on record);
// do not "simplify" to it.
//   listId: the list GUID (no braces)
// Returns the raw v2.0 column records as a one-column table [Column].
(listId as text) as table =>
let
    Doc   = Json.Document(Web.Contents(SP_Site, [
                RelativePath = "_api/v2.0/sites/root/lists/" & listId & "/columns",
                Headers = [Accept = "application/json"]])),
    Cols  = Doc[value],
    Out   = if List.Count(Cols) = 0
            then error Error.Record("SP_ColumnsRaw", "Read 0 columns for list " & listId)
            else Table.FromList(Cols, Splitter.SplitByNothing(), {"Column"})
in
    Out
