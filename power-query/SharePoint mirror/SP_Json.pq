// GET a SharePoint REST path under SP_Site and parse the JSON.
//
// Web.Contents is called with the FIXED base URL and a RelativePath/Query, never a
// concatenated URL. That keeps one credential (the site, Organizational account)
// for every call, and lets a refresh from COM run without the "dynamic data source"
// error.
//
// odata=nometadata: the same shape the console scripts (x22/x25) read - internal
// field names, lookups as <Name>Id integers, dates as ISO text with Z.
(relativePath as text, optional query as nullable record) as any =>
let
    Raw = Web.Contents(
        SP_Site,
        [
            RelativePath = relativePath,
            Query = if query = null then [] else query,
            Headers = [Accept = "application/json;odata=nometadata"]
        ]
    ),
    Parsed = Json.Document(Raw)
in
    Parsed
