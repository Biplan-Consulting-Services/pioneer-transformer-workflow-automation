<#
.SYNOPSIS
    Pulls every Power Query (M) definition OUT of a workbook into one .pq file per
    query. The missing counterpart to FRM10-12/scripts/Sync-PowerQuery.ps1, which
    only pushes .pq files IN.

.DESCRIPTION
    Uses the same Excel COM surface as Sync-PowerQuery.ps1 ($wb.Queries, .Name,
    .Formula), so the two round-trip: export here, edit the .pq, push back with
    Sync-PowerQuery.ps1 -Apply.

    READ-ONLY. The workbook is opened with ReadOnly:$true, never saved, and
    nothing is refreshed. That matters on FRM10-12 specifically, where a generic
    RefreshAll wipes the native formula columns -- this script must never grow a
    refresh step.

    Files are named after the query with characters illegal in a filename replaced
    by '_'; the real query name is written as a comment on the first line, so a
    round-trip through Sync-PowerQuery.ps1 does not depend on the filename.

.PARAMETER WorkbookPath
    Workbook to read. Required.

.PARAMETER OutputPath
    Directory to write .pq files into. Created if missing. Defaults to a folder
    named "<workbook basename> power-query" beside the workbook.

.PARAMETER ListOnly
    Print the query names and their M length, write nothing.

.EXAMPLE
    ./Export-PowerQuery.ps1 -WorkbookPath "..\workbooks\PRO1.FRM11 - Planification Approbation Cuve.xlsx" -ListOnly

.EXAMPLE
    ./Export-PowerQuery.ps1 -WorkbookPath "..\workbooks\PRO1.FRM11 - Planification Approbation Cuve.xlsx"
#>
param(
    [Parameter(Mandatory = $true)][string]$WorkbookPath,
    [string]$OutputPath,
    [switch]$ListOnly
)

$ErrorActionPreference = 'Stop'
$WorkbookPath = (Resolve-Path $WorkbookPath).Path

if (-not $OutputPath) {
    $base = [System.IO.Path]::GetFileNameWithoutExtension($WorkbookPath)
    $OutputPath = Join-Path ([System.IO.Path]::GetDirectoryName($WorkbookPath)) "$base power-query"
}
if (-not $ListOnly -and -not (Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
}

Write-Host "Workbook: $WorkbookPath"
Write-Host ("Mode: " + $(if ($ListOnly) { "LIST ONLY" } else { "EXPORT -> $OutputPath" }))
Write-Host ""

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

$written = 0
try {
    # ReadOnly, no link update, no add-ins prompt. Never save this workbook.
    $wb = $excel.Workbooks.Open($WorkbookPath, 0, $true)
    try {
        $queries = $wb.Queries
        Write-Host "$($queries.Count) quer$(if ($queries.Count -eq 1) {'y'} else {'ies'})"
        Write-Host ""

        for ($i = 1; $i -le $queries.Count; $i++) {
            $q = $queries.Item($i)
            $name = $q.Name
            $m = $q.Formula

            if ($ListOnly) {
                Write-Host ("  {0,-40} {1,7} chars" -f $name, $m.Length)
                continue
            }

            $safe = $name
            foreach ($c in [System.IO.Path]::GetInvalidFileNameChars()) {
                $safe = $safe.Replace($c, '_')
            }
            $file = Join-Path $OutputPath "$safe.pq"

            # First line records the real query name so the filename is not load-bearing.
            $content = "// Query: $name" + [Environment]::NewLine + $m
            [System.IO.File]::WriteAllText($file, $content, (New-Object System.Text.UTF8Encoding $false))
            Write-Host ("  {0,-40} -> {1}" -f $name, (Split-Path $file -Leaf))
            $written++
        }
    }
    finally {
        # Close WITHOUT saving, always.
        $wb.Close($false)
    }
}
finally {
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}

Write-Host ""
if ($ListOnly) { Write-Host "Nothing written (-ListOnly)." }
else { Write-Host "$written .pq file(s) written to $OutputPath" }
