// Query: ArchiveFetch
//
// THE one SharePoint read of the archive. Every archive query reads the five main lists from
// here and nowhere else; no other archive query calls SP_ItemsRaw (ArchiveTyped makes one extra
// call only for a lookup whose target is NOT one of these five - none today).
//
//   ArchiveFetch[Items][<title>]    that list's raw REST items (SP_ItemsRaw), Table.Buffer'ed
//   ArchiveFetch[Columns][<title>]  that list's column catalog (SP_ColumnsRaw, _api/v2.0), buffered
//   ArchiveFetch[ListIds][<title>]  that list's GUID
//   ArchiveFetch[TitleById]         lower-case GUID -> list title, for every list on the site
//   ArchiveFetch[Users]             _api/web/siteusers (Id, Email, Title), for person columns
//
// Each field is a record FIELD, so it is evaluated lazily and at most ONCE per evaluation: a
// refresh of `Archive Order` reads Order plus the lists its lookups point at, and each of those
// exactly once, however many lookups reuse it. (Excel evaluates each loaded table separately,
// so refreshing five tables = up to five evaluations; Power Query's own web cache may serve the
// repeats.)
//
// Never SharePoint.Tables: it shifts date-only values a day early (CLAUDE.md, 2026-09-24).
let
    Titles    = {"Order Items", "Order", "Models", "Model Revisions", "Clients"},
    AllLists  = List.Buffer(SP_Json("_api/web/lists", [#"$select" = "Id,Title"])[value]),
    TitleById = Record.FromList(List.Transform(AllLists, each [Title]),
                                List.Transform(AllLists, each Text.Lower([Id]))),
    IdOf      = (t as text) as text =>
                    let hit = List.Select(AllLists, each [Title] = t)
                    in  if List.Count(hit) = 1 then hit{0}[Id]
                        else error Error.Record("ArchiveFetch", "List '" & t & "' found " & Text.From(List.Count(hit)) & " times on the site (expected once)."),
    Items     = (t as text) as table => Table.Buffer(SP_ItemsRaw("lists(guid'" & IdOf(t) & "')")),
    Catalog   = (t as text) as list  => List.Buffer(SP_ColumnsRaw(IdOf(t))[Column]),

    // Record literals, not Record.FromList: literal fields are lazy, so an unused list is never read.
    Out = [
        Titles    = Titles,
        TitleById = TitleById,
        ListIds   = [#"Order Items" = IdOf("Order Items"), Order = IdOf("Order"), Models = IdOf("Models"),
                     #"Model Revisions" = IdOf("Model Revisions"), Clients = IdOf("Clients")],
        Items     = [#"Order Items" = Items("Order Items"), Order = Items("Order"), Models = Items("Models"),
                     #"Model Revisions" = Items("Model Revisions"), Clients = Items("Clients")],
        Columns   = [#"Order Items" = Catalog("Order Items"), Order = Catalog("Order"), Models = Catalog("Models"),
                     #"Model Revisions" = Catalog("Model Revisions"), Clients = Catalog("Clients")],
        Users     = List.Buffer(SP_Json("_api/web/siteusers", [#"$select" = "Id,Email,Title"])[value])
    ]
in
    Out
