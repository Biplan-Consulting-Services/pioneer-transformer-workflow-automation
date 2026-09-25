<#
.SYNOPSIS
    Refreshes workbooks/SharePoint mirror.xlsx from live SharePoint and writes one CSV per
    table to sharepoint-lists/mirror/{Table} {yyyy-MM-dd} {HHmm}.csv.

.DESCRIPTION
    Each table is refreshed synchronously, one at a time, so a failure names its table.
    (RefreshAll is safe on THIS workbook; the RefreshAll ban is FRM10-12-specific. Per-table
    refresh is used for the error attribution, not for safety.)

    Nothing is written unless EVERY table refreshed and holds at least one row. A zero-row
    table is a failed read. On failure the workbook is NOT saved, so the last good data stays.

    CSVs go to sharepoint-lists/mirror/, not sharepoint-lists/: their headers are INTERNAL
    names, and the scripts that read "the newest export" there expect display names.
    load_exports.load() reads these files too (no ListSchema record -> plain DictReader).
    The previous CSV of each table is moved to sharepoint-lists/mirror/Archive/.

    A WATCHDOG kills this script's own Excel after -TimeoutSec. Without it an invisible
    Excel sitting on a sign-in dialog would hang forever.

.PARAMETER Interactive
    Show Excel. Use for the FIRST refresh: Power Query asks for credentials once
    (Organizational account), then caches them for every later silent run.

.EXAMPLE
    ./Refresh-SharePointMirror.ps1 -Interactive     # first time
    ./Refresh-SharePointMirror.ps1                  # every time after
#>
param(
    [string]$WorkbookPath = (Join-Path $PSScriptRoot "..\workbooks\SharePoint mirror.xlsx"),
    [string]$OutDir       = (Join-Path $PSScriptRoot "..\sharepoint-lists\mirror"),
    [int]$TimeoutSec      = 900,
    [switch]$Interactive
)
$ErrorActionPreference = "Stop"
$full = [System.IO.Path]::GetFullPath($WorkbookPath)
if (-not (Test-Path -LiteralPath $full)) { throw "ABORT: $full not found - run Build-SharePointMirror.ps1 first" }
$OutDir = [System.IO.Path]::GetFullPath($OutDir)
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "Archive") | Out-Null

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

$stamp = Get-Date -Format "yyyy-MM-dd HHmm"
$results = @()
$saved = $false
try {
    $wb = $excel.Workbooks.Open($full)
    $tables = @()
    foreach ($ws in $wb.Worksheets) { foreach ($lo in $ws.ListObjects) { if ($lo.Name -like "Mirror_*") { $tables += $lo } } }
    if ($tables.Count -eq 0) { throw "ABORT: no query tables in the workbook - run Build-SharePointMirror.ps1" }

    foreach ($lo in $tables) {
        $name = $lo.Name -replace '^Mirror_', ''
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $err = $null
        try { $lo.QueryTable.BackgroundQuery = $false; $lo.QueryTable.Refresh($false) | Out-Null }
        catch { $err = $_.Exception.Message }
        $rows = if ($lo.DataBodyRange) { $lo.ListRows.Count } else { 0 }
        $results += [pscustomobject]@{ table = $name; rows = $rows; cols = $lo.ListColumns.Count; sec = [math]::Round($sw.Elapsed.TotalSeconds, 1); error = $err }
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

    $wb.Save(); $saved = $true
    $inv = [System.Globalization.CultureInfo]::InvariantCulture
    foreach ($lo in $tables) {
        $name = ($lo.Name -replace '^Mirror_', '')
        # restore the query's real name for the file ("Order_Items" -> "Order Items")
        foreach ($c in $wb.Queries) { if (("Mirror_" + ($c.Name -replace '[^A-Za-z0-9]', '_')) -eq $lo.Name) { $name = $c.Name } }
        $safe = $name -replace '[\\/:*?"<>|]', '_'
        $pattern = '^' + [regex]::Escape($safe) + ' \d{4}-\d{2}-\d{2} \d{4}\.csv$'
        Get-ChildItem -LiteralPath $OutDir -Filter *.csv | Where-Object { $_.Name -match $pattern } |
            ForEach-Object { Move-Item -LiteralPath $_.FullName -Destination (Join-Path $OutDir "Archive") -Force }

        $v = $lo.Range.Value2
        $nr = $v.GetLength(0); $nc = $v.GetLength(1)
        $path = Join-Path $OutDir "$safe $stamp.csv"
        $w = New-Object System.IO.StreamWriter($path, $false, (New-Object System.Text.UTF8Encoding($true)))
        try {
            for ($r = 1; $r -le $nr; $r++) {
                $cells = New-Object string[] $nc
                for ($c = 1; $c -le $nc; $c++) {
                    $x = $v[$r, $c]
                    $s = if ($null -eq $x) { "" } elseif ($x -is [double]) { $x.ToString("R", $inv) } else { [string]$x }
                    $cells[$c - 1] = '"' + $s.Replace('"', '""') + '"'
                }
                $w.WriteLine([string]::Join(",", $cells))
            }
        } finally { $w.Close() }
        Write-Host ("wrote {0}  ({1} rows)" -f $path, ($nr - 1))
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
