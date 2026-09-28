// Query: ArchiveBOConflicts
//
// D2's conflict list: every unit and BO column where the Order Items value and
// TableArchiveBO's value are BOTH non-blank and DIFFERENT. The archive takes the Order Items
// value (rule 1 of `Archive FRM10-12`); this lists what that overrode, for the user.
// Connection-only (load it to a sheet only to review). Empty once TableArchiveBO is removed.
//
// Values are compared as text after normalising the shapes that differ only in form:
// dates as yyyy-MM-dd (TableArchiveBO holds datetimes, Order Items dates), numbers as
// invariant text (TableArchiveBO's PO Intern is a number, Order Items' is text), text trimmed.
let
    BORows = Table.ToRecords(Table.SelectRows(ArchiveFrm1012Map, each [Rule] = "bo")),
    Units = ArchiveFrm1012Joined,

    IsBlank = (v as any) as logical => v = null or v = false or (v is text and Text.Trim(v) = ""),
    Norm = (v as any) as text =>
        if v is date then Date.ToText(v, "yyyy-MM-dd", "en-US")
        else if v is datetime then Date.ToText(DateTime.Date(v), "yyyy-MM-dd", "en-US")
        else if v is number then Number.ToText(v, null, "en-US")
        else if v is logical then (if v then "TRUE" else "FALSE")
        else Text.Trim(Text.From(v)),

    PerUnit = (row as record) as list =>
        List.Transform(
            List.Select(BORows, (m) =>
                let
                    sp = Record.Field(row, m[SourceList] & "." & m[SourceField]),
                    arc = Record.Field(row, "TableArchiveBO." & m[TargetColumn])
                in
                    not IsBlank(sp) and not IsBlank(arc) and Norm(sp) <> Norm(arc)),
            (m) => {
                Record.Field(row, "Order Items.Title"),
                m[TargetColumn],
                Norm(Record.Field(row, m[SourceList] & "." & m[SourceField])),
                Norm(Record.Field(row, "TableArchiveBO." & m[TargetColumn]))
            }),

    Conflicts = #table(
        type table [Order = text, Column = text, #"Order Items (kept)" = text, #"TableArchiveBO (overridden)" = text],
        List.Combine(List.Transform(Table.ToRecords(Units), PerUnit)))
in
    Conflicts
