// Query: ArchiveFrm1012Source
//
// The FRM10-12 archive rows SharePoint sends today, built BY THE MAP: one output column per
// ArchiveFrm1012Map row (except the `archive` row, Last Synchronisation Date, which
// AccumulateIntoLocal stamps), in map order. Values are raw here; `Archive FRM10-12` types
// them after accumulating. No per-column steps: every column is one map row evaluated by
// one of the rules below, so adding or re-sourcing a column is a map edit.
//
// Two phases, because four rules read values other rows build:
//   phase 1  copy, multichoice, marker, yn, loccode, ec, default, legacy, bo
//   phase 2  status, ingdue, navorder, navmodel   (Arg refs to phase-1 TargetColumns or
//            to "<List>.<field>" source fields)
let
    Map = Table.Buffer(Table.Sort(ArchiveFrm1012Map, {{"Position", Order.Ascending}})),
    Units = ArchiveFrm1012Joined,

    ComputedRules = {"status", "ingdue", "navorder", "navmodel"},
    SourceLists = {"Order Items", "Order", "Model Revisions", "Clients"},
    Produced = List.Select(Table.ToRecords(Map), each [Rule] <> "archive"),
    Phase1 = List.Select(Produced, each not List.Contains(ComputedRules, [Rule])),
    Phase2 = List.Select(Produced, each List.Contains(ComputedRules, [Rule])),
    Phase1Names = List.Transform(Phase1, each [TargetColumn]),
    Phase2Names = List.Transform(Phase2, each [TargetColumn]),
    OutputNames = List.Transform(Produced, each [TargetColumn]),

    // --- vocabularies, as records for O(1) lookups (verbatim viewer copies) ---
    LocMap = Record.FromList(LocationCodes[Code], LocationCodes[Name]),
    Steps = Table.SelectRows(StatusStampCodes, each [Kind] = "step"),
    Months = Table.SelectRows(StatusStampCodes, each [Kind] = "month"),
    StepMap = Record.FromList(Steps[Code], Steps[Key]),
    MonthMap = Record.FromList(Months[Code], Months[Key]),

    // --- helpers ---
    // Blank for the D2 rule: nothing, empty/whitespace text, or false (a SharePoint Yes/No
    // defaults to false, and TableArchiveBO's untouched OK boxes are false too).
    IsBlank = (v as any) as logical =>
        v = null or v = false or (v is text and Text.Trim(v) = ""),

    ToDate = (v as any) as nullable date =>
        if v = null then null
        else if v is date then v
        else if v is datetime then DateTime.Date(v)
        else if v is datetimezone then DateTime.Date(DateTimeZone.RemoveZone(v))
        else if v is text then
            (let p = Text.Split(Text.BeforeDelimiter(Text.BeforeDelimiter(Text.Trim(v), "T"), " "), "-")
             in  #date(Number.From(p{0}), Number.From(p{1}), Number.From(p{2})))
        else error Error.Record("ArchiveFrm1012Source.NotADate", "Not a date", v),

    MultiChoice = (v as any) as any =>
        let
            items =
                if v = null then {}
                else if v is list then v
                else if v is text and Text.StartsWith(Text.Trim(v), "[") then Json.Document(v)
                else {v},
            texts = List.Select(List.Transform(items, each if _ = null then null else Text.From(_)), each _ <> null and _ <> "")
        in
            if List.IsEmpty(texts) then null else Text.Combine(texts, ", "),

    Ref = (row as record, built as record, token as text) as any =>
        if List.AnyTrue(List.Transform(SourceLists, (l) => Text.StartsWith(token, l & ".")))
        then Record.Field(row, token)
        else Record.Field(built, token),

    // --- phase 1: one value per map row ---
    Eval1 = (row as record, m as record) as any =>
        let
            target = m[TargetColumn],
            src = if List.Contains(SourceLists, m[SourceList]) then Record.Field(row, m[SourceList] & "." & m[SourceField]) else null,
            rule = m[Rule]
        in
            if rule = "copy" then src
            else if rule = "multichoice" then MultiChoice(src)
            else if rule = "marker" then (if src = true then m[Arg] else null)
            else if rule = "yn" then (if src = true then "Y" else null)
            // Unmapped names pass through: losing a Location silently is worse than an odd one.
            else if rule = "loccode" then (if src = null then null else Record.FieldOrDefault(LocMap, Text.From(src), src))
            // ONLY "In Progress" is a marker; stale "Pending" values mean nothing.
            else if rule = "ec" then (if Record.Field(row, m[Arg]) = "In Progress" then "EC" else src)
            else if rule = "default" then (if src = null then Number.From(m[Arg], "en-US") else src)
            else if rule = "legacy" then Record.Field(row, "Previous." & target)
            else if rule = "bo" then
                (let
                    cands = {src, Record.Field(row, "TableArchiveBO." & target), Record.Field(row, "Previous." & target)},
                    filled = List.Select(cands, each not IsBlank(_)),
                    present = List.Select(cands, each _ <> null)
                in
                    if not List.IsEmpty(filled) then filled{0}
                    else if not List.IsEmpty(present) then present{0}
                    else null)
            else error Error.Record("ArchiveFrm1012Source.UnknownRule", "Unknown rule """ & rule & """ for column " & target, m),

    // --- phase 2: rules reading other values ---
    Eval2 = (row as record, built as record, m as record) as any =>
        let
            args = List.Transform(Text.Split(m[Arg], ";"), each Ref(row, built, _)),
            rule = m[Rule]
        in
            if rule = "status" then
                (let
                    step = if args{0} = null then null else Record.FieldOrDefault(StepMap, Text.From(args{0}), null),
                    when = ToDate(args{1}),
                    mon = if when = null then null else Record.FieldOrDefault(MonthMap, Text.From(Date.Month(when)), null)
                in
                    // A stale stamp beats a silently blanked one (viewer TableOrders.pq).
                    if step = null or mon = null then args{2}
                    else step & "-" & mon & "-" & Text.From(Date.Day(when)))
            else if rule = "ingdue" then
                (try Date.AddDays(ToDate(if args{0} <> null then args{0} else args{1}), -1 * ((args{2} + 4) * 7)) otherwise null)
            else if rule = "navorder" then
                (if args{0} = null or not Text.Contains(Text.From(args{0}), "-") then null
                 else "Ouvrir commande " & Text.BeforeDelimiter(Text.From(args{0}), "-"))
            else if rule = "navmodel" then
                (if IsBlank(args{0}) then null else "Ouvrir modèle " & Text.From(args{0}))
            else error Error.Record("ArchiveFrm1012Source.UnknownRule", "Unknown rule """ & rule & """ for column " & m[TargetColumn], m),

    BuildRow = (row as record) as list =>
        let
            built = Record.FromList(List.Transform(Phase1, each Eval1(row, _)), Phase1Names),
            computed = Record.FromList(List.Transform(Phase2, each Eval2(row, built, _)), Phase2Names),
            full = built & computed
        in
            Record.FieldValues(Record.SelectFields(full, OutputNames)),

    Rows = Table.FromRows(List.Transform(Table.ToRecords(Units), BuildRow), OutputNames)
in
    Rows
