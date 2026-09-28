// Query: LocationCodes
// VERBATIM COPY of FRM10-12/viewer/power-query/LocationCodes.pq below this line. Do not edit here: edit the viewer file and re-copy. scripts/check_frm1012_map.py fails on any drift.
// The Location vocabulary: two-letter code <-> display name, in one place.
//
// This exists as its own query rather than a literal inside ApplyColumnMap because it is
// a SHARED vocabulary, and shared vocabularies in this estate have a history of drifting
// into independent copies (see Workflow-Automation/CLAUDE.md on ImportFromIndex, which
// exists at three different lengths in three workbooks). Anything that needs the mapping
// should reference this query by name.
//
// Direction matters. The Order Items transfer flow converts code -> display name on the
// way INTO SharePoint ('XT' becomes 'Extérieur'), so the list stores display names. Every
// downstream consumer that predates the migration reads CODES:
//
//   * FRM11's "Rows to purge" computes
//         List.Contains({"XT","TE","FI","LI"}, [Location.1])
//         or ([Location.1] = "TA" and Text.Contains([Status.1], "TE"))
//     -- live production M code, and the reason this inversion is not cosmetic. A viewer
//     that hands FRM11 'Extérieur' where it expects 'XT' does not error; it silently stops
//     purging the rows that are already tanked, and 8 outside companies get the supplier
//     reports built from the result.
//   * BO Manager reads the same code form.
//
// So the viewer's job is to hand back what the workbook always produced: the code.
//
// The 12 pairs are read out of the transfer flow's own MappedLocation Compose action
// (v006), not retyped from a doc -- that action IS the forward map, so inverting it is
// exact by construction rather than by transcription.
//
// Verified 2026-09-09 against the live Order Items export (1,117 rows):
//   * the inverse is injective -- 12 codes, 12 distinct display names, no collisions
//   * every one of the 9 distinct non-blank Location values present on the list inverts
//     (Extérieur 55, Bobinage 55, Livraison 36, Finition 25, Tanking 25, Four 18,
//      Assemblage 16, Test 15, Stacking 2; 870 blank)
//   * round-trip holds for all 12: CodeOf(NameOf(c)) = c
//   * the three codes FRM11 needs that never appear in live data -- IS, ENT, RE -- are
//     still carried, because "not currently in use" is not "cannot appear".
let
    Source = Table.FromRecords({
        [Code = "IS",  Name = "Isolation"],
        [Code = "BO",  Name = "Bobinage"],
        [Code = "ST",  Name = "Stacking"],
        [Code = "AS",  Name = "Assemblage"],
        [Code = "FO",  Name = "Four"],
        [Code = "TA",  Name = "Tanking"],
        [Code = "TE",  Name = "Test"],
        [Code = "FI",  Name = "Finition"],
        [Code = "LI",  Name = "Livraison"],
        [Code = "ENT", Name = "Entrepôt"],
        [Code = "XT",  Name = "Extérieur"],
        [Code = "RE",  Name = "Réparation"]
    }, type table [Code = text, Name = text])
in
    Source
