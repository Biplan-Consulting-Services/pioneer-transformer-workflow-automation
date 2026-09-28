<#
.SYNOPSIS
    Applies Archive active's Power Query (.pq) files to a COPY of the workbook, loads new tables,
    refreshes chosen tables one at a time, and saves only if every refresh is healthy.

.DESCRIPTION
    Built for the archive rebuild (plan 2026-09-28): FRM10-12/scripts/Sync-PowerQuery.ps1 has a
    hardcoded folder and must not be used on Archive active.

    Rules it enforces:
      - COPIES ONLY. Refuses any path under Workflow-Automation\workbooks, the live file name
        "Archive active.xlsx", and any file name without WORK / COPY / TEST in it.
      - A query that exists is changed IN PLACE (its .Formula is replaced). Queries and tables are
        never deleted or recreated: TableArchiveFRM10_12 is read by the Nightly Sync by its table id.
      - A query that does not exist is added connection-only, unless -LoadTables names a table for
        it; then a NEW sheet is added with that table.
      - Archive FRM10-12 / FRM11 / FRM13 / BO and their tables are never changed or refreshed unless
        named explicitly. Changing a helper that one of those queries references is refused unless
        that protected query is itself listed in -Queries.
      - -Refresh tables are refreshed one at a time, in the order given; never RefreshAll.
      - A WATCHDOG kills this script's own Excel after -TimeoutSec.
      - SAVE ONLY IF every refresh succeeded, every refreshed table has > 0 rows, and none has fewer
        rows than before. Otherwise the workbook is closed unsaved (and exit code 1).

    The .pq files carry the real query name on their first line ("// Query: <name>"); that line is
    stripped before writing the Formula (Export-PowerQuery.ps1 adds it back on export).

    Output: a short summary plus failures. -Verbose prints every step.

.PARAMETER WorkbookPath
    The workbook copy to change. Required.

.PARAMETER QueryDir
    Folder of .pq files. Default: power-query\Archive-active.

.PARAMETER Queries
    Query names to apply (the "// Query:" names). Only these are added/updated.

.PARAMETER LoadTables
    "Query=Table" pairs: load that query to a new table on a new sheet (skipped if the table exists).

.PARAMETER Refresh
    Table names to refresh, in this order.

.PARAMETER TimeoutSec
    Watchdog: kill Excel after this many seconds. Default 1200.

.PARAMETER Interactive
    Show Excel (for a first sign-in / privacy prompt).

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Apply-ArchivePowerQuery.ps1 `
      -WorkbookPath "C:\...\Archive active WORK.xlsx" `
      -Queries SP_Site,SP_Json,SP_ItemsRaw,SP_ColumnsRaw,AccumulateIntoLocal,ArchiveFetch,ArchiveTyped,ArchiveList,"Archive Order" `
      -LoadTables "Archive Order=TableArchiveOrder" -Refresh TableArchiveOrder
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$WorkbookPath,
    [string]$QueryDir,
    [string[]]$Queries = @(),
    [string[]]$LoadTables = @(),
    [string[]]$Refresh = @(),
    [int]$TimeoutSec = 1200,
    [switch]$Interactive
)
$ErrorActionPreference = "Stop"
# $PSScriptRoot can be empty in a param default under Windows PowerShell 5.1; resolve it here.
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $QueryDir) { $QueryDir = Join-Path $ScriptDir "..\power-query\Archive-active" }
# `powershell -File` passes "a,b,c" as ONE string; split on commas (no name here contains one).
function Split-List([string[]]$xs) { @($xs | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
$Queries = Split-List $Queries; $LoadTables = Split-List $LoadTables; $Refresh = Split-List $Refresh

# ---------------------------------------------------------------- guards: copies only
$RepoRoot  = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir ".."))
$Workbooks = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot "workbooks")).TrimEnd('\') + '\'
if (-not (Test-Path -LiteralPath $WorkbookPath)) { throw "ABORT: $WorkbookPath not found" }
$full = (Resolve-Path -LiteralPath $WorkbookPath).Path
$leaf = [System.IO.Path]::GetFileName($full)
if ($full.StartsWith($Workbooks, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "ABORT: $full is under $Workbooks. Work on a copy outside workbooks\ (this tool never touches the repo's dated copies)."
}
if ($leaf -ieq "Archive active.xlsx") { throw "ABORT: '$leaf' is the live file's name. Work on a renamed copy." }
if ($leaf -notmatch '(?i)WORK|COPY|TEST') {
    throw "ABORT: '$leaf' does not look like a working copy (name must contain WORK, COPY or TEST)."
}

$Protected = @("Archive FRM10-12", "Archive FRM11", "Archive FRM13", "Archive BO")
$ProtectedTables = @("TableArchiveFRM10_12", "TableArchiveFRM11", "TableArchiveFRM13", "TableArchiveBO")

# ---------------------------------------------------------------- read the .pq files
$QueryDir = (Resolve-Path -LiteralPath $QueryDir).Path
$pq = @{}
foreach ($f in Get-ChildItem -LiteralPath $QueryDir -Filter *.pq) {
    $text = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8)
    $name = $f.BaseName
    $m = [regex]::Match($text, '^\uFEFF?//\s*Query:\s*(.+?)\s*\r?\n')
    if ($m.Success) { $name = $m.Groups[1].Value; $text = $text.Substring($m.Length) }
    if ($pq.ContainsKey($name)) { throw "ABORT: two .pq files declare query '$name'" }
    $pq[$name] = $text
}
$missingPq = $Queries | Where-Object { -not $pq.ContainsKey($_) }
if ($missingPq) { throw "ABORT: no .pq file for: $($missingPq -join ', ')" }

$loads = [ordered]@{}
foreach ($pair in $LoadTables) {
    $i = $pair.LastIndexOf('=')
    if ($i -lt 1) { throw "ABORT: -LoadTables entry '$pair' is not 'Query=Table'" }
    $loads[$pair.Substring(0, $i).Trim()] = $pair.Substring($i + 1).Trim()
}
foreach ($q in $loads.Keys) { if ($Queries -notcontains $q) { throw "ABORT: -LoadTables names '$q', which is not in -Queries" } }
$protectedRefresh = $Refresh | Where-Object { $ProtectedTables -contains $_ }
if ($protectedRefresh) { Write-Host "NOTE: refreshing protected table(s) because they were named explicitly: $($protectedRefresh -join ', ')" -ForegroundColor Yellow }

function Say([string]$s) { Write-Verbose $s }
# Excel may store a Formula with different line endings than the file; compare normalised.
function Norm([string]$s) { ($s -replace "`r`n", "`n").TrimEnd() }
$failures = New-Object System.Collections.Generic.List[string]

# ---------------------------------------------------------------- Excel + watchdog
Add-Type -Namespace Win32 -Name U -MemberDefinition '[DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr hWnd, out int pid);'
$missing = [System.Reflection.Missing]::Value
$excel = New-Object -ComObject Excel.Application
$excel.Visible = [bool]$Interactive
$excel.DisplayAlerts = [bool]$Interactive
$excelPid = 0
[Win32.U]::GetWindowThreadProcessId([IntPtr]$excel.Hwnd, [ref]$excelPid) | Out-Null
$watchdog = Start-Job -ScriptBlock {
    param($p, $t) Start-Sleep -Seconds $t
    if (Get-Process -Id $p -ErrorAction SilentlyContinue) { Stop-Process -Id $p -Force; "WATCHDOG: killed Excel $p after $t s" }
} -ArgumentList $excelPid, $TimeoutSec

$saved = $false
$results = @()
try {
    $wb = $excel.Workbooks.Open($full, 0)
    Say "opened $full"
    try { Say ("Queries.FastCombine (ignore privacy levels) = " + $wb.Queries.FastCombine) } catch {}

    function Get-Tables {
        $h = [ordered]@{}
        foreach ($ws in $wb.Worksheets) { foreach ($lo in $ws.ListObjects) { $h[$lo.Name] = $lo } }
        $h
    }
    function Rows($lo) { if ($lo.DataBodyRange) { $lo.ListRows.Count } else { 0 } }

    $tablesBefore = Get-Tables
    $existingQ = @{}
    foreach ($x in $wb.Queries) { $existingQ[$x.Name] = $x }

    # ---- guard: never change a helper a protected query depends on (unless that query is listed)
    function Test-Refers([string]$formula, [string]$qname) {
        $pat = '(?<![A-Za-z0-9_])' + [regex]::Escape($qname) + '(?![A-Za-z0-9_])'
        return ($formula -match $pat) -or ($formula.Contains('#"' + $qname + '"'))
    }
    # everything a protected query depends on, transitively (text match on query names)
    $deps = @{}
    foreach ($p in $Protected) {
        if (-not $existingQ.ContainsKey($p) -or $Queries -contains $p) { continue }
        $todo = New-Object System.Collections.Generic.Queue[string]; $todo.Enqueue($p)
        while ($todo.Count -gt 0) {
            $cur = $todo.Dequeue()
            foreach ($x in $existingQ.Keys) {
                if ($x -ne $cur -and -not $deps.ContainsKey($x) -and (Test-Refers $existingQ[$cur].Formula $x)) { $deps[$x] = $p; $todo.Enqueue($x) }
            }
        }
    }
    foreach ($name in $Queries) {
        if (-not $existingQ.ContainsKey($name) -or (Norm $existingQ[$name].Formula) -eq (Norm $pq[$name])) { continue }
        if ($deps.ContainsKey($name)) {
            throw "ABORT: '$name' would change, and protected query '$($deps[$name])' depends on it. List '$($deps[$name])' in -Queries to accept that."
        }
    }

    # ---- queries: in place, or added
    $added = 0; $updated = 0; $same = 0
    foreach ($name in $Queries) {
        $m = $pq[$name]
        if ($existingQ.ContainsKey($name)) {
            if ((Norm $existingQ[$name].Formula) -ne (Norm $m)) { $existingQ[$name].Formula = $m; $updated++; Say "  query updated  $name" }
            else { $same++; Say "  query same     $name" }
        } else {
            $wb.Queries.Add($name, $m) | Out-Null; $added++; Say "  query added    $name"
        }
    }

    # ---- new tables on new sheets
    $newTables = 0
    foreach ($q in $loads.Keys) {
        $tbl = $loads[$q]
        if ((Get-Tables).Contains($tbl)) { Say "  table exists   $tbl (left as is)"; continue }
        $sheetName = ($q -replace '[\[\]\*\?/\\:]', '_')
        if ($sheetName.Length -gt 31) { $sheetName = $sheetName.Substring(0, 31) }
        foreach ($ws in $wb.Worksheets) { if ($ws.Name -ieq $sheetName) { throw "ABORT: sheet '$sheetName' already exists but holds no table '$tbl'" } }
        $ws = $wb.Worksheets.Add($missing, $wb.Worksheets.Item($wb.Worksheets.Count))
        $ws.Name = $sheetName
        $conn = "OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=`$Workbook`$;Location=`"$q`";Extended Properties=`"`""
        $lo = $ws.ListObjects.Add(0, $conn, $missing, 1, $ws.Range("A1"))
        $lo.Name = $tbl
        $qt = $lo.QueryTable
        $qt.CommandType = 2
        $qt.CommandText = "SELECT * FROM [$q]"
        $qt.BackgroundQuery = $false
        $qt.RefreshOnFileOpen = $false
        $newTables++
        Say "  table added    $tbl (sheet '$sheetName')"
    }

    # ---- refresh, one table at a time
    $all = Get-Tables
    $unknown = $Refresh | Where-Object { -not $all.Contains($_) }
    if ($unknown) { throw "ABORT: no such table(s) to refresh: $($unknown -join ', ')" }
    foreach ($t in $Refresh) {
        $lo = $all[$t]
        $before = if ($tablesBefore.Contains($t)) { Rows $lo } else { 0 }
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $err = $null
        try {
            $qt = $null
            try { $qt = $lo.QueryTable } catch {}
            if ($qt) { $qt.BackgroundQuery = $false; $qt.Refresh($false) | Out-Null }
            else { $lo.TableObject.Refresh() | Out-Null }   # tables loaded through the data model
        } catch { $err = $_.Exception.Message }
        $after = Rows $lo
        $r = [pscustomobject]@{ table = $t; before = $before; after = $after; cols = $lo.ListColumns.Count; sec = [math]::Round($sw.Elapsed.TotalSeconds, 1); error = $err }
        $results += $r
        Say ("  refreshed {0}: {1} -> {2} rows, {3} cols, {4}s{5}" -f $t, $before, $after, $r.cols, $r.sec, $(if ($err) { "  ERROR $err" } else { "" }))
        if ($err) { $failures.Add("$t : refresh failed: $err") }
        elseif ($after -eq 0) { $failures.Add("$t : 0 rows after refresh (a zero-row read is a failed read)") }
        elseif ($after -lt $before) { $failures.Add("$t : shrank from $before to $after rows") }
    }

    # ---- no table may have disappeared
    $tablesAfter = Get-Tables
    foreach ($t in $tablesBefore.Keys) { if (-not $tablesAfter.Contains($t)) { $failures.Add("$t : table no longer exists") } }

    Write-Host ("queries: {0} added, {1} updated, {2} unchanged; tables added: {3}" -f $added, $updated, $same, $newTables)
    if ($results) { $results | Format-Table table, before, after, cols, sec -AutoSize | Out-String | Write-Host }

    if ($failures.Count -gt 0) {
        Write-Host "NOT SAVED - $($failures.Count) failure(s):" -ForegroundColor Red
        foreach ($f in $failures) { Write-Host "  $f" -ForegroundColor Red }
    } else {
        $wb.Save()
        $saved = $true
        Write-Host "saved $full"
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
