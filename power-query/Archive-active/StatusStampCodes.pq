// Query: StatusStampCodes
// VERBATIM COPY of FRM10-12/viewer/power-query/StatusStampCodes.pq below this line. Do not edit here: edit the viewer file and re-copy. scripts/check_frm1012_map.py fails on any drift.
// The alphabet of FRM10-12's composite Status stamp: `TE-Se-4`.
//
//     TE   step prefix          <- Kind = "step",  Key = the Step Status display name
//     Se   month abbreviation   <- Kind = "month", Key = the month number, 1-12
//     4    day of month         <- not a lookup, taken straight off Status Date
//
// Consumed by TableOrders.pq, which rebuilds `Status` from `Step Status` + `Status Date`.
//
// ---------------------------------------------------------------------------------------
// WHY THE COMPOSITE IS NOW DERIVED, AND TEMPORARY
//
// `Order Items` carries three status columns after N8:
//   Step Status   Choice, the display name        <- staff edit this
//   Status Date   Date only                       <- and this
//   Status        the composite stamp             <- nobody edits this any more
//
// Until cutover the transfer flow copied the composite out of Excel on every run. After
// cutover that flow is DELETED, so nothing maintains it -- it would freeze at whatever the
// final run wrote, silently, while staff carried on updating the split pair.
//
// So the viewer rebuilds it. The split pair is the truth (user, 2026-09-09); the composite
// is a compatibility shim that keeps FRM10-12's shape byte-identical for FRM09 / FRM11 /
// FRM13 / BO Manager, and it is phased out with FRM10-12 itself.
//
// ---------------------------------------------------------------------------------------
// 🔑 FRM11 READS THE PREFIX ONLY, which is what makes this safe
//
// `power-query/FRM11/Rows to purge.pq`:
//     ([Location.1] = "TA" and Text.Contains([Status.1], "TE"))
// It never parses the date half. The prefix is an exact reverse lookup, so the part
// anything actually depends on reconstructs losslessly.
//
// ⚠️ The DATE half does not round-trip, and that is accepted rather than overlooked. The
// abbreviations collide -- "Ma" is mars AND mai, "Jui" is juin AND juillet -- which is
// exactly the ambiguity N8 had to resolve from each unit's own stage dates when it parsed
// these. Emitting is a choice of convention, not a recovery of information. Fine here
// because the flow is ONE-WAY: the viewer writes this into the Excel mirror, never back to
// SharePoint, and nothing re-parses it.
//
// ---------------------------------------------------------------------------------------
// TWO DIFFERENT SOURCES, recorded because they age differently
//
//   steps   FRM10-12's own List sheet, TableValidationStatusCode -- the table its
//           data-validation dropdown uses, so it is the vocabulary staff pick from. If a
//           step is ever added there, add it here.
//   months  the abbreviations N8's parser recognises (scripts/n8_split_status.js, MONTH),
//           which is the closest thing to a written-down convention for what staff typed.
//           N8 has no entry for 5/6/7 -- it resolves "jui" from each unit's stage dates --
//           so those three are this file's own choice, and only affect display.
let
    Source = Table.FromRecords({
        [Kind = "step",  Key = "Attente",       Code = "AT"],
        [Kind = "step",  Key = "En cours",      Code = "EC"],
        [Kind = "step",  Key = "Réparation",    Code = "RE"],
        [Kind = "step",  Key = "Manque Pièces", Code = "BO"],
        [Kind = "step",  Key = "Terminé",       Code = "TE"],
        [Kind = "step",  Key = "Bobine 1",      Code = "B1"],
        [Kind = "step",  Key = "Bobine 2",      Code = "B2"],
        [Kind = "step",  Key = "Bobine 3",      Code = "B3"],

        [Kind = "month", Key = "1",  Code = "Ja"],
        [Kind = "month", Key = "2",  Code = "Fé"],
        [Kind = "month", Key = "3",  Code = "Ma"],
        [Kind = "month", Key = "4",  Code = "Av"],
        [Kind = "month", Key = "5",  Code = "Mai"],   // this file's choice, see above
        [Kind = "month", Key = "6",  Code = "Jui"],   // this file's choice, see above
        [Kind = "month", Key = "7",  Code = "Jui"],   // this file's choice, see above
        [Kind = "month", Key = "8",  Code = "Ao"],
        [Kind = "month", Key = "9",  Code = "Se"],
        [Kind = "month", Key = "10", Code = "Oc"],
        [Kind = "month", Key = "11", Code = "No"],
        [Kind = "month", Key = "12", Code = "De"]
    }, type table [Kind = text, Key = text, Code = text])
in
    Source
