<#
.SYNOPSIS
    Refreshes the SharePoint mirror from live SharePoint, then snapshots, journals and checks it.

.DESCRIPTION
    Layout (docs/change-tracking-design-2026-09-24.md, D3):
      sharepoint-lists/mirror/live/SharePoint mirror.xlsx   the one refreshed workbook   (git)
      sharepoint-lists/mirror/live/<Table>.csv              latest refresh, STABLE names (git)
      sharepoint-lists/mirror/snapshots/<yyyy-MM-dd_HHmm>/   <Table>.csv.gz + snapshot.json (NOT git)
      sharepoint-lists/mirror/journal/YYYY-MM.jsonl         what changed                 (git)
      sharepoint-lists/mirror/health/latest.md              is anything wrong            (git)

    Each table is refreshed synchronously, one at a time, so a failure names its table.
    (RefreshAll is safe on THIS workbook; the ban is FRM10-12-specific.)

    Nothing is written unless EVERY requested table refreshed and holds at least one row. A
    zero-row table is a failed read. On failure the workbook is NOT saved and live/ is left as
    it was.

    A full refresh (no -Tables) also writes a snapshot of the real lists + Columns, prunes old
    snapshots (every one for 30 days, then the last of each month, D2), and runs
    mirror_journal.py and mirror_health.py. A -Tables refresh updates live/ only - a partial
    snapshot would make the next journal diff lie.

    A WATCHDOG kills this script's own Excel after -TimeoutSec, so an invisible Excel waiting on
    a sign-in dialog cannot hang forever.

    INTERIM RULE (user, 2026-09-24): run this at the start of every working session and
    immediately before any modification to a list.

.PARAMETER Interactive
    Show Excel. Use when Power Query needs a sign-in (Organizational account); it is cached after.

.PARAMETER Tables
    Refresh only these tables (query names). live/ only; no snapshot, journal or health run.

.PARAMETER NoChecks
    Snapshot but skip journal + health (e.g. when repairing the pipeline itself).

.EXAMPLE
    ./Refresh-SharePointMirror.ps1
    ./Refresh-SharePointMirror.ps1 -Tables Lists
#>
param(
    [string]$MirrorDir    = (Join-Path $PSScriptRoot "..\sharepoint-lists\mirror"),
    [int]$TimeoutSec      = 900,
    [switch]$Interactive,
    [string[]]$Tables,
    [switch]$NoChecks
)
$ErrorActionPreference = "Stop"
$MirrorDir = [System.IO.Path]::GetFullPath($MirrorDir)
$LiveDir   = Join-Path $MirrorDir "live"
$SnapRoot  = Join-Path $MirrorDir "snapshots"
$full      = Join-Path $LiveDir "SharePoint mirror.xlsx"
if (-not (Test-Path -LiteralPath $full)) { throw "ABORT: $full not found - run Build-SharePointMirror.ps1 first" }

# Snapshotted = the real lists + the schema catalog. Diagnostics are live/ only.
$SnapTables = @("Order Items", "Order", "Models", "Model Revisions", "Clients", "Index", "Models SA", "Columns")

Add-Type -Namespace Win32 -Name U -MemberDefinition '[DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr hWnd, out int pid);'

$excel = New-Object -ComObject Excel.Application
$excel.Visible = [bool]$Interactive
$excel.DisplayAlerts = [bool]$Interactive
$excelPid = 0
[Win32.U]::GetWindowThreadProcessId([IntPtr]$excel.Hwnd, [ref]$excelPid) | Out-Null
$watchdog = Start-Job -ScriptBlock {
    param($p, $t) Start-Sleep -Seconds $t
    if (Get-Process -Id $p -ErrorAction SilentlyContinue) { Stop-Process -Id $p -Force; "WATCHDOG: killed Excel $p after $t s" }
} -ArgumentList $excelPid, $TimeoutSec

$nowLocal = Get-Date
$asOf = $nowLocal.ToUniversalTime().ToString("yyyy-MM-ddTHH:mmZ")
$snapName = $nowLocal.ToString("yyyy-MM-dd_HHmm")
$results = @()
$written = @{}
try {
    $wb = $excel.Workbooks.Open($full)
    $los = @()
    foreach ($ws in $wb.Worksheets) { foreach ($lo in $ws.ListObjects) { if ($lo.Name -like "Mirror_*") { $los += $lo } } }
    if ($los.Count -eq 0) { throw "ABORT: no query tables in the workbook - run Build-SharePointMirror.ps1" }
    if ($Tables) {
        $want = $Tables | ForEach-Object { "Mirror_" + ($_ -replace '[^A-Za-z0-9]', '_') }
        $unknown = $want | Where-Object { $los.Name -notcontains $_ }
        if ($unknown) { throw "ABORT: no such table(s): $($unknown -join ', '). Run Build-SharePointMirror.ps1 after adding a query." }
        $los = @($los | Where-Object { $want -contains $_.Name })
    }

    foreach ($lo in $los) {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $err = $null
        try { $lo.QueryTable.BackgroundQuery = $false; $lo.QueryTable.Refresh($false) | Out-Null }
        catch { $err = $_.Exception.Message }
        $rows = if ($lo.DataBodyRange) { $lo.ListRows.Count } else { 0 }
        $results += [pscustomobject]@{ table = ($lo.Name -replace '^Mirror_', ''); rows = $rows; cols = $lo.ListColumns.Count; sec = [math]::Round($sw.Elapsed.TotalSeconds, 1); error = $err }
    }
    $results | Format-Table -AutoSize | Out-String | Write-Host

    $bad = $results | Where-Object { $_.error -or $_.rows -eq 0 }
    if ($bad) {
        Write-Host "ABORT: $($bad.Count) table(s) failed or read 0 rows - nothing written, workbook NOT saved." -ForegroundColor Red
        foreach ($b in $bad) { Write-Host ("  {0}: {1}" -f $b.table, $(if ($b.error) { $b.error } else { "0 rows" })) -ForegroundColor Red }
        if ($bad | Where-Object { $_.error -match 'redential|sign|authenticat|401|403' }) {
            Write-Host "  -> looks like sign-in. Run once with -Interactive and pick 'Organizational account' when Excel asks." -ForegroundColor Yellow
        }
        exit 1
    }

    $wb.Save()
    $inv = [System.Globalization.CultureInfo]::InvariantCulture
    $utf8bom = New-Object System.Text.UTF8Encoding($true)
    foreach ($lo in $los) {
        $name = ($lo.Name -replace '^Mirror_', '')
        foreach ($q in $wb.Queries) { if (("Mirror_" + ($q.Name -replace '[^A-Za-z0-9]', '_')) -eq $lo.Name) { $name = $q.Name } }
        $v = $lo.Range.Value2
        $nr = $v.GetLength(0); $nc = $v.GetLength(1)
        $sb = New-Object System.Text.StringBuilder
        for ($r = 1; $r -le $nr; $r++) {
            $cells = New-Object string[] $nc
            for ($c = 1; $c -le $nc; $c++) {
                $x = $v[$r, $c]
                $s = if ($null -eq $x) { "" } elseif ($x -is [double]) { $x.ToString("R", $inv) } else { [string]$x }
                $cells[$c - 1] = '"' + $s.Replace('"', '""') + '"'
            }
            [void]$sb.Append([string]::Join(",", $cells)).Append("`r`n")
        }
        $text = $sb.ToString()
        $safe = $name -replace '[\\/:*?"<>|]', '_'
        [System.IO.File]::WriteAllText((Join-Path $LiveDir "$safe.csv"), $text, $utf8bom)
        $written[$name] = @{ text = $text; rows = $nr - 1 }
        Write-Host ("live/{0}.csv  ({1} rows)" -f $safe, ($nr - 1))
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

if ($Tables) { Write-Host "partial refresh (-Tables): live/ updated; no snapshot, journal or health run."; exit 0 }

# ---- snapshot (D3): gz per real table + snapshot.json
$snapDir = Join-Path $SnapRoot $snapName
if (Test-Path -LiteralPath $snapDir) { throw "ABORT: snapshot $snapDir already exists (two refreshes in one minute?)" }
New-Item -ItemType Directory -Force -Path $snapDir | Out-Null
$counts = [ordered]@{}
foreach ($t in $SnapTables) {
    if (-not $written.ContainsKey($t)) { throw "ABORT: $t was not refreshed - cannot snapshot a partial set" }
    $bytes = $utf8bom.GetPreamble() + $utf8bom.GetBytes($written[$t].text)
    $fs = [System.IO.File]::Create((Join-Path $snapDir "$t.csv.gz"))
    try { $gz = New-Object System.IO.Compression.GZipStream($fs, [System.IO.Compression.CompressionMode]::Compress); $gz.Write($bytes, 0, $bytes.Length); $gz.Close() }
    finally { $fs.Close() }
    $counts[$t] = $written[$t].rows
}
@{ asOf = $asOf; localStamp = $snapName; tables = $counts; source = "Refresh-SharePointMirror.ps1" } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $snapDir "snapshot.json") -Encoding UTF8
Write-Host "snapshot  snapshots/$snapName  (asOf $asOf)"

# ---- retention (D2): all snapshots for 30 days, then the last of each month
$cut = $nowLocal.AddDays(-30)
$all = Get-ChildItem -LiteralPath $SnapRoot -Directory | Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}_\d{4}$' } | Sort-Object Name
$old = $all | Where-Object { [datetime]::ParseExact($_.Name, "yyyy-MM-dd_HHmm", $inv) -lt $cut }
$keepMonthly = $old | Group-Object { $_.Name.Substring(0, 7) } | ForEach-Object { $_.Group | Select-Object -Last 1 }
$prune = $old | Where-Object { $keepMonthly -notcontains $_ }
foreach ($p in $prune) { Remove-Item -LiteralPath $p.FullName -Recurse -Force }
if ($prune) { Write-Host "retention: pruned $($prune.Count) snapshot(s) older than 30 days (kept the last of each month)" }

if ($NoChecks) { Write-Host "-NoChecks: journal + health skipped."; exit 0 }

# ---- journal + health
$py = Join-Path $PSScriptRoot "mirror_journal.py"
& python $py
if ($LASTEXITCODE -ne 0) { Write-Host "journal FAILED (exit $LASTEXITCODE)" -ForegroundColor Red; exit $LASTEXITCODE }
& python (Join-Path $PSScriptRoot "mirror_health.py")
exit $LASTEXITCODE
