<#
.SYNOPSIS
    One-time switch of TableArchiveFRM10_12 from a Data Model load to a direct sheet load
    (option 2, docs/archive-build-status-2026-09-28.md). COPIES ONLY.

.DESCRIPTION
    Why: the new viewer-free "Archive FRM10-12" query evaluates cleanly, but Excel's Data Model
    rejects the load ("Column ... is too large for this instance of ... Analysis Services"), and the
    model round-trip is also what turned dates into text on 2026-09-27. Nothing uses the model
    (0 relationships, 0 measures; the one pivot reads the sheet table), so the table is loaded
    straight to the sheet instead, like every other archive table.

    Every archived row is kept. The query reads its own table for history, so the old data is
    handed over first:
      1. the old model-backed table is UNLINKED (it becomes a plain table holding its data) and
         renamed TableArchiveFRM10_12_Seed, its sheet renamed "Archive FRM10-12 seed";
      2. the model plumbing for it is removed (ModelConnection_ExternalData_1 and the query's
         model connection);
      3. a new sheet "Archive FRM10-12" gets a sheet-loaded table TableArchiveFRM10_12 on the
         query; on this first refresh ArchiveFrm1012LocalName points the query at the seed;
      4. checks: rows >= the seed's, exactly the pinned column count;
      5. the seed sheet is deleted, the new sheet takes the old sheet's position, the pivot cache
         that read the table by name is pointed at the new table;
      6. a SECOND refresh proves the steady state (history now from the table itself): row count
         unchanged.
    Saves only if every step passed. The table's internal id changes (it is a new table): the
    Nightly Sync's Excel step must then read the table by NAME (flow v006).

    Prerequisite: the queries are already applied to the copy (Apply-ArchivePowerQuery.ps1,
    including ArchiveFrm1012LocalName).
#>
param(
    [Parameter(Mandatory = $true)][string]$WorkbookPath,
    [int]$PinnedColumns = 111,
    [int]$TimeoutSec = 1800,
    [switch]$Detail
)
$ErrorActionPreference = "Stop"
function Say([string]$m) { if ($Detail) { Write-Host $m } }

$full = (Resolve-Path $WorkbookPath).Path
$leaf = Split-Path $full -Leaf
if ($full -match '\\Workflow-Automation\\workbooks\\' -or $leaf -ieq 'Archive active.xlsx' -or $leaf -notmatch '(?i)WORK|COPY|TEST') {
    throw "REFUSED: $full is not a working copy (name must contain WORK, COPY or TEST, and not live under workbooks\)."
}

Add-Type -Namespace Win32 -Name U2 -MemberDefinition '[DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr hWnd, out int pid);'
$missing = [System.Reflection.Missing]::Value
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$excelPid = 0
[Win32.U2]::GetWindowThreadProcessId([IntPtr]$excel.Hwnd, [ref]$excelPid) | Out-Null
$watchdog = Start-Job -ScriptBlock {
    param($p, $t) Start-Sleep -Seconds $t
    if (Get-Process -Id $p -ErrorAction SilentlyContinue) { Stop-Process -Id $p -Force; "WATCHDOG: killed Excel $p after $t s" }
} -ArgumentList $excelPid, $TimeoutSec

$failures = New-Object System.Collections.Generic.List[string]
$saved = $false
try {
    $wb = $excel.Workbooks.Open($full, 0)
    function Find-Table([string]$name) {
        foreach ($ws in $wb.Worksheets) { foreach ($lo in $ws.ListObjects) { if ($lo.Name -eq $name) { return $lo } } }
        return $null
    }
    if (-not ($wb.Queries | Where-Object { $_.Name -eq 'ArchiveFrm1012LocalName' })) {
        throw "ABORT: query ArchiveFrm1012LocalName is missing - apply the queries first (Apply-ArchivePowerQuery.ps1)."
    }
    $old = Find-Table 'TableArchiveFRM10_12'
    if (-not $old) { throw "ABORT: TableArchiveFRM10_12 not found." }
    if (Find-Table 'TableArchiveFRM10_12_Seed') { throw "ABORT: a TableArchiveFRM10_12_Seed already exists - start from a clean copy." }
    $oldSheet = $old.Parent
    $oldSheetName = $oldSheet.Name
    $oldIndex = $oldSheet.Index
    $seedRows = $old.ListRows.Count
    $seedCols = $old.ListColumns.Count
    Write-Host ("old table: {0} rows x {1} cols on sheet '{2}' (source type {3})" -f $seedRows, $seedCols, $oldSheetName, $old.SourceType)

    # 1. unlink -> plain table with its data, renamed to the seed
    $old.Unlink()
    if ($old.SourceType -ne 1) { throw "ABORT: unlink did not produce a plain table (source type $($old.SourceType))." }
    $old.Name = 'TableArchiveFRM10_12_Seed'
    $oldSheet.Name = 'Archive FRM10-12 seed'
    if ($old.ListRows.Count -ne $seedRows) { throw "ABORT: the seed lost rows on unlink ($seedRows -> $($old.ListRows.Count))." }
    Say "  unlinked and renamed to TableArchiveFRM10_12_Seed ($seedRows rows kept)"

    # 2. remove the model plumbing for this table
    foreach ($cn in @('ModelConnection_ExternalData_1', 'Query - Archive FRM10-12')) {
        foreach ($c in @($wb.Connections)) { if ($c.Name -eq $cn) { $c.Delete(); Say "  connection deleted: $cn" } }
    }
    foreach ($t in @($wb.Model.ModelTables)) { if ($t.Name -eq 'Archive FRM10-12') { $failures.Add("the Data Model still holds 'Archive FRM10-12' after removing its connections") } }

    # 3. new sheet-loaded table on a new sheet, right after the seed sheet
    $ws = $wb.Worksheets.Add($missing, $oldSheet)
    $ws.Name = 'Archive FRM10-12'
    $conn = "OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=`$Workbook`$;Location=`"Archive FRM10-12`";Extended Properties=`"`""
    $lo = $ws.ListObjects.Add(0, $conn, $missing, 1, $ws.Range("A1"))
    $lo.Name = 'TableArchiveFRM10_12'
    $qt = $lo.QueryTable
    $qt.CommandType = 2
    $qt.CommandText = "SELECT * FROM [Archive FRM10-12]"
    $qt.BackgroundQuery = $false
    $qt.RefreshOnFileOpen = $false
    try { $qt.WorkbookConnection.Name = 'Query - Archive FRM10-12' } catch { Say "  (could not rename the new connection: $($_.Exception.Message))" }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try { $qt.Refresh($false) | Out-Null } catch { $failures.Add("first refresh (history from the seed) failed: $($_.Exception.Message)") }
    $rows1 = if ($lo.DataBodyRange) { $lo.ListRows.Count } else { 0 }
    $cols1 = $lo.ListColumns.Count
    Write-Host ("first refresh (from seed): {0} rows x {1} cols in {2:n0} s" -f $rows1, $cols1, $sw.Elapsed.TotalSeconds)
    if ($failures.Count -eq 0) {
        if ($rows1 -lt $seedRows) { $failures.Add("new table has $rows1 rows, fewer than the seed's $seedRows") }
        if ($cols1 -ne $PinnedColumns) { $failures.Add("new table has $cols1 columns, expected $PinnedColumns") }
    }

    # 4b. date display. The Data Model used to hand dates back with a date format; a sheet-loaded
    #     table writes them into General cells, where a date shows as its serial (2024-02-01 ->
    #     45323). Set the archive's date format once on every date column and keep it across
    #     refreshes (PreserveFormatting). Same format and the same free-text exceptions as the
    #     refresher's enforceDateFormats / isDateColumnName.
    if ($failures.Count -eq 0) {
        $textWithDate = @('Client Date Status', 'Tanking date change justification', 'Tanking Date Status', 'Tanking Date Change Justification')
        $formatted = 0
        foreach ($col in $lo.ListColumns) {
            $n = [string]$col.Name
            if ($n -match '(?i)date' -and $textWithDate -notcontains $n -and $col.DataBodyRange) {
                $col.DataBodyRange.NumberFormat = 'yyyy\-mm\-dd;@'
                $formatted++
            }
        }
        $qt.PreserveFormatting = $true
        Say "  date format set on $formatted column(s); PreserveFormatting on"
    }

    if ($failures.Count -eq 0) {
        # 5. retire the seed, restore the sheet position, repoint the pivot
        $ws.Move($oldSheet)                      # new sheet goes where the old one was
        foreach ($s in @($wb.Worksheets)) {
            foreach ($pt in @($s.PivotTables())) {
                $src = try { [string]$pt.PivotCache().SourceData } catch { "" }
                if ($src -match 'TableArchiveFRM10_12') {
                    $pt.ChangePivotCache($wb.PivotCaches().Create(1, 'TableArchiveFRM10_12')) | Out-Null
                    Say "  pivot '$($pt.Name)' on '$($s.Name)' now reads TableArchiveFRM10_12"
                }
            }
        }
        $oldSheet.Delete()
        if (Find-Table 'TableArchiveFRM10_12_Seed') { $failures.Add("the seed table still exists after deleting its sheet") }

        # 6. steady state: history now comes from the table itself
        $sw.Restart()
        try { $qt.Refresh($false) | Out-Null } catch { $failures.Add("second refresh (history from itself) failed: $($_.Exception.Message)") }
        $rows2 = if ($lo.DataBodyRange) { $lo.ListRows.Count } else { 0 }
        Write-Host ("second refresh (from itself): {0} rows x {1} cols in {2:n0} s" -f $rows2, $lo.ListColumns.Count, $sw.Elapsed.TotalSeconds)
        if ($failures.Count -eq 0 -and $rows2 -ne $rows1) { $failures.Add("second refresh changed the row count ($rows1 -> $rows2)") }
    }

    if ($failures.Count -gt 0) {
        Write-Host "NOT SAVED - $($failures.Count) failure(s):" -ForegroundColor Red
        foreach ($f in $failures) { Write-Host "  $f" -ForegroundColor Red }
    } else {
        $wb.Save(); $saved = $true
        Write-Host "saved $full (sheet '$($lo.Parent.Name)' at position $($lo.Parent.Index), table TableArchiveFRM10_12 loaded to the sheet)"
    }
}
finally {
    if ($wb) { $wb.Close($false) | Out-Null }
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
    Stop-Job $watchdog -ErrorAction SilentlyContinue; Receive-Job $watchdog -ErrorAction SilentlyContinue | Write-Host
    Remove-Job $watchdog -Force -ErrorAction SilentlyContinue
}
if (-not $saved) { exit 1 }
exit 0
