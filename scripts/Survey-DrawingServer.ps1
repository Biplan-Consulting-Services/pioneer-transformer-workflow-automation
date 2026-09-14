<#
.SYNOPSIS
  Read-only survey of the engineering drawing file server, to answer the Phase 0
  questions in docs/engineering-document-control.md before anything is migrated.

.DESCRIPTION
  Run this on a machine that can reach the drawing share. It NEVER writes to, renames,
  moves or opens anything on the source - it reads directory metadata only. All output
  lands in this repo's reports/ folder.

  It answers four questions that decide the migration design, and that cannot be
  answered by guessing:

    1. HOW BIG IS IT      file count, total size, clients, model codes, order folders.

    2. WILL THE PATHS FIT SharePoint refuses a decoded path over 400 characters. The
                          question is not how long the paths are TODAY, it is how long
                          they become once re-rooted under the target site + library,
                          which is usually LONGER than the UNC path it replaces. This
                          script computes the projected URL per file and lists every
                          one that would be rejected.

    3. WILL THE NAMES FIT SharePoint rejects  " * : < > ? / \ |  , leading/trailing
                          spaces, a trailing period, the ~$ prefix, the _vti_ substring,
                          and the reserved DOS device names. A migration that hits one
                          of these mid-run leaves a half-moved tree.

                          HONESTY NOTE: on a Windows source the character check will
                          almost always report zero, because Windows forbids those same
                          characters itself. Do not read that zero as reassurance - it
                          is checked because the source might one day be a NAS or a Mac
                          share, which do allow them. The checks that genuinely earn
                          their keep here are path length, the ~$ Office lock files
                          (real, common, and NOT drawings - exclude them from any
                          migration), reserved device names, and trailing space/period.

                          Separately: the blue-folder sheet's own document labels DO
                          contain forbidden characters - "Base Mod./ Tank Mod.",
                          "Formulaire: Points a surveiller". Those are list-item titles
                          and folder names we will CREATE, not files we will move, so
                          they need sanitising on a different code path. This script
                          cannot see them.

    4. IS THERE A CONVENTION
                          The whole index layer depends on extracting a stable document
                          identity and a revision from each file. This scores the names
                          against the version patterns actually seen in the wild and
                          reports the match rate, rather than assuming the convention
                          holds. "Mostly, with exceptions" was the expectation - this
                          measures the exceptions.

  It also counts, per document stem, how many versions are present. That is the check
  on whether old revisions still exist anywhere: today only the latest is kept at the
  model-code root, so a stem with one version is the norm and anything higher is a
  place where history survived.

.PARAMETER Root
  The drawing tree, e.g. \\fileserver\Engineering\Clients  or  E:\Dessins

.PARAMETER TargetUrlBase
  Where it is going, used to project the post-migration URL length.

.PARAMETER OutDir
  Defaults to this repo's reports/ folder.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\Survey-DrawingServer.ps1 -Root "\\fileserver\Engineering"

.NOTES
  LONG PATHS: Windows PowerShell 5.1 cannot enumerate past 260 characters without the
  \\?\ prefix, which this adds automatically. If enumeration still fails on some
  branch, the script reports it as an unreadable path rather than dying - and that
  failure is itself a finding worth having, because it means paths over the limit
  already exist.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $Root,

    [string] $TargetUrlBase = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/Engineering Drawings",

    [string] $OutDir
)

$ErrorActionPreference = 'Stop'

if (-not $OutDir) {
    $repo = Split-Path -Parent $PSScriptRoot
    $OutDir = Join-Path $repo 'reports'
}
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }

if (-not (Test-Path -LiteralPath $Root)) {
    throw "Root not reachable: $Root"
}
$rootFull = (Resolve-Path -LiteralPath $Root).ProviderPath.TrimEnd('\')

# \\?\ lets 5.1 walk past 260 chars. UNC needs the \\?\UNC\ form, not \\?\\\server.
if ($rootFull.StartsWith('\\')) {
    $walkRoot = '\\?\UNC\' + $rootFull.Substring(2)
} else {
    $walkRoot = '\\?\' + $rootFull
}

Write-Host "Surveying $rootFull" -ForegroundColor Cyan
Write-Host "  projecting against $TargetUrlBase"
Write-Host "  (read-only - nothing on the source is modified)"
Write-Host ""

# --- walk -------------------------------------------------------------------
$files = @()
$unreadable = @()
try {
    $files = Get-ChildItem -LiteralPath $walkRoot -Recurse -File -Force -ErrorAction SilentlyContinue -ErrorVariable walkErrors
    foreach ($e in $walkErrors) { $unreadable += $e.TargetObject }
} catch {
    throw "Enumeration failed outright: $($_.Exception.Message)"
}

if ($files.Count -eq 0) { throw "No files found under $rootFull" }

# --- rules ------------------------------------------------------------------
# SharePoint / OneDrive rejected characters. # and % are allowed on modern tenants.
$illegalChars = '["*:<>?/\\|]'
$reservedNames = @('CON','PRN','AUX','NUL','COM0','COM1','COM2','COM3','COM4','COM5',
                   'COM6','COM7','COM8','COM9','LPT0','LPT1','LPT2','LPT3','LPT4',
                   'LPT5','LPT6','LPT7','LPT8','LPT9')
$MAX_URL = 400

# Version patterns, most specific first. Each must capture the stem in group 1 and the
# version token in group 2 so the same regex both identifies and strips it.
$versionPatterns = [ordered]@{
    'Rev letter (_RevC / -Rev C)'  = '^(.*?)[ _-]*rev[ _-]*([A-Z]{1,2})$'
    'Rev number (_Rev03)'          = '^(.*?)[ _-]*rev[ _-]*(\d{1,3})$'
    'R + digits (_R03)'            = '^(.*?)[ _-]+R(\d{1,3})$'
    'v + digits (_v3 / v03)'       = '^(.*?)[ _-]*v[ _-]*(\d{1,3})$'
    'Trailing _digits (_3)'        = '^(.*?)[_ ]+(\d{1,3})$'
    'Trailing -digits (-3)'        = '^(.*?)-(\d{1,3})$'
    'Bare trailing letter (A/B/C)' = '^(.*?)[ _-]+([A-Z])$'
}

# --- per-file analysis ------------------------------------------------------
$rows = New-Object System.Collections.ArrayList
$stemVersions = @{}

foreach ($f in $files) {
    # strip the \\?\ (and \\?\UNC\) prefix back off before measuring anything
    $full = $f.FullName -replace '^\\\\\?\\UNC\\', '\\' -replace '^\\\\\?\\', ''
    $rel  = $full.Substring($rootFull.Length).TrimStart('\')
    $projected = ($TargetUrlBase.TrimEnd('/') + '/' + ($rel -replace '\\', '/'))

    $name = $f.Name
    $base = [System.IO.Path]::GetFileNameWithoutExtension($name)

    # name problems - checked per path SEGMENT, since a folder name breaks a move
    # just as surely as a file name does
    $problems = New-Object System.Collections.ArrayList
    foreach ($seg in ($rel -split '\\')) {
        if ($seg -match $illegalChars)          { [void]$problems.Add('illegal-char') }
        if ($seg -ne $seg.Trim())               { [void]$problems.Add('lead/trail-space') }
        if ($seg.EndsWith('.'))                 { [void]$problems.Add('trailing-period') }
        if ($seg.StartsWith('~$'))              { [void]$problems.Add('tilde-dollar') }
        if ($seg -like '*_vti_*')               { [void]$problems.Add('_vti_') }
        $segBase = [System.IO.Path]::GetFileNameWithoutExtension($seg)
        if ($reservedNames -contains $segBase.ToUpper()) { [void]$problems.Add('reserved-name') }
    }

    # version convention
    $matchedAs = ''
    $stem = $base
    $version = ''
    foreach ($k in $versionPatterns.Keys) {
        $m = [regex]::Match($base, $versionPatterns[$k], 'IgnoreCase')
        if ($m.Success) {
            $matchedAs = $k
            $stem = $m.Groups[1].Value.Trim()
            $version = $m.Groups[2].Value
            break
        }
    }

    if ($f.Extension -match '^\.pdf$') {
        $sk = ($stem + '|' + (Split-Path $rel -Parent)).ToLower()
        if (-not $stemVersions.ContainsKey($sk)) { $stemVersions[$sk] = New-Object System.Collections.ArrayList }
        [void]$stemVersions[$sk].Add($version)
    }

    [void]$rows.Add([pscustomobject]@{
        RelativePath  = $rel
        Name          = $name
        Extension     = $f.Extension.ToLower()
        SizeKB        = [math]::Round($f.Length / 1KB, 1)
        Modified      = $f.LastWriteTime.ToString('yyyy-MM-dd')
        Depth         = ($rel -split '\\').Count
        ProjectedUrl  = $projected
        ProjectedLen  = $projected.Length
        TooLong       = ($projected.Length -gt $MAX_URL)
        NameProblems  = (($problems | Select-Object -Unique) -join ';')
        VersionScheme = $matchedAs
        Stem          = $stem
        Version       = $version
    })
}

# --- aggregate --------------------------------------------------------------
$pdfs      = @($rows | Where-Object { $_.Extension -eq '.pdf' })
$tooLong   = @($rows | Where-Object { $_.TooLong })
$badNames  = @($rows | Where-Object { $_.NameProblems -ne '' })
$noVersion = @($pdfs | Where-Object { $_.VersionScheme -eq '' })
$multi     = @($stemVersions.GetEnumerator() | Where-Object { $_.Value.Count -gt 1 })

$topClients = @($rows | ForEach-Object { ($_.RelativePath -split '\\')[0] } |
                Group-Object | Sort-Object Count -Descending)

$inv = Join-Path $OutDir 'drawing-server-inventory.csv'
$rows | Export-Csv -LiteralPath $inv -NoTypeInformation -Encoding UTF8

# --- report -----------------------------------------------------------------
$sb = New-Object System.Text.StringBuilder
function Add-Line([string]$s) { [void]$sb.AppendLine($s) }

Add-Line "# Drawing server survey"
Add-Line ""
Add-Line ("Source: ``{0}``" -f $rootFull)
Add-Line ("Projected against: ``{0}``" -f $TargetUrlBase)
Add-Line ("Run: {0}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm'))
Add-Line ""
Add-Line "## 1. Size"
Add-Line ""
Add-Line ("- Files: **{0:N0}** ({1:N0} PDF)" -f $rows.Count, $pdfs.Count)
Add-Line ("- Total size: **{0:N1} GB**" -f (($rows | Measure-Object SizeKB -Sum).Sum / 1MB))
Add-Line ("- Top-level folders: **{0}**" -f $topClients.Count)
Add-Line ("- Max folder depth: **{0}**" -f (($rows | Measure-Object Depth -Maximum).Maximum))
if ($unreadable.Count -gt 0) {
    Add-Line ("- !! **{0} paths could not be read** - likely already over the Windows limit" -f $unreadable.Count)
}
Add-Line ""
Add-Line "Extensions present:"
Add-Line ""
Add-Line "| ext | count |"
Add-Line "|---|---|"
foreach ($g in ($rows | Group-Object Extension | Sort-Object Count -Descending | Select-Object -First 12)) {
    Add-Line ("| ``{0}`` | {1:N0} |" -f $g.Name, $g.Count)
}
Add-Line ""
Add-Line "## 2. Path length (limit $MAX_URL)"
Add-Line ""
Add-Line ("- Longest projected URL: **{0}** characters" -f (($rows | Measure-Object ProjectedLen -Maximum).Maximum))
Add-Line ("- Would be **rejected**: **{0:N0}** files" -f $tooLong.Count)
if ($tooLong.Count -gt 0) {
    Add-Line ""
    Add-Line "Worst 15:"
    Add-Line ""
    Add-Line "| len | path |"
    Add-Line "|---|---|"
    foreach ($r in ($tooLong | Sort-Object ProjectedLen -Descending | Select-Object -First 15)) {
        Add-Line ("| {0} | ``{1}`` |" -f $r.ProjectedLen, $r.RelativePath)
    }
    Add-Line ""
    Add-Line "**These must be shortened before migration, or the folder depth flattened.**"
}
Add-Line ""
Add-Line "## 3. Name problems"
Add-Line ""
Add-Line ("- Files with a SharePoint-illegal path segment: **{0:N0}**" -f $badNames.Count)
if ($badNames.Count -gt 0) {
    Add-Line ""
    Add-Line "| problem | count |"
    Add-Line "|---|---|"
    foreach ($g in ($badNames | ForEach-Object { $_.NameProblems -split ';' } | Group-Object | Sort-Object Count -Descending)) {
        Add-Line ("| {0} | {1:N0} |" -f $g.Name, $g.Count)
    }
    Add-Line ""
    Add-Line "Examples:"
    Add-Line ""
    foreach ($r in ($badNames | Select-Object -First 12)) {
        Add-Line ("- ``{0}`` - {1}" -f $r.RelativePath, $r.NameProblems)
    }
}
Add-Line ""
Add-Line "## 4. Is there a filename convention?"
Add-Line ""
Add-Line ("PDFs where a version token was recognised: **{0:N0} of {1:N0}** ({2:P0})" -f `
    ($pdfs.Count - $noVersion.Count), $pdfs.Count, `
    $(if ($pdfs.Count) { ($pdfs.Count - $noVersion.Count) / $pdfs.Count } else { 0 }))
Add-Line ""
Add-Line "| scheme | count |"
Add-Line "|---|---|"
foreach ($g in ($pdfs | Group-Object VersionScheme | Sort-Object Count -Descending)) {
    $label = $g.Name
    if ($label -eq '') { $label = '(none recognised)' }
    Add-Line ("| {0} | {1:N0} |" -f $label, $g.Count)
}
Add-Line ""
Add-Line "**The dominant scheme is the one the indexer parses; everything else is the exception list.**"
if ($noVersion.Count -gt 0) {
    Add-Line ""
    Add-Line "Unrecognised examples:"
    Add-Line ""
    foreach ($r in ($noVersion | Select-Object -First 15)) {
        Add-Line ("- ``{0}``" -f $r.Name)
    }
}
Add-Line ""
Add-Line "## 5. Did old revisions survive anywhere?"
Add-Line ""
Add-Line ("Document stems with more than one version present in the same folder: **{0:N0}**" -f $multi.Count)
Add-Line ""
Add-Line "Today only the latest is kept at the model-code root, so a low number here confirms"
Add-Line "that history is genuinely gone and baselines can only start from now. A high number"
Add-Line "means some history survived and is worth migrating as real revisions."
if ($multi.Count -gt 0) {
    Add-Line ""
    foreach ($m in ($multi | Select-Object -First 12)) {
        Add-Line ("- ``{0}`` - {1} versions: {2}" -f ($m.Key -split '\|')[0], $m.Value.Count, (($m.Value | Sort-Object) -join ', '))
    }
}
Add-Line ""
Add-Line "## Top-level folders"
Add-Line ""
Add-Line "| folder | files |"
Add-Line "|---|---|"
foreach ($g in ($topClients | Select-Object -First 25)) {
    Add-Line ("| {0} | {1:N0} |" -f $g.Name, $g.Count)
}

$rpt = Join-Path $OutDir 'drawing-server-survey.md'
[System.IO.File]::WriteAllText($rpt, $sb.ToString(), (New-Object System.Text.UTF8Encoding $false))

Write-Host ""
Write-Host ("Files surveyed : {0:N0} ({1:N0} PDF)" -f $rows.Count, $pdfs.Count) -ForegroundColor Green
Write-Host ("Over 400 chars : {0:N0}" -f $tooLong.Count)   -ForegroundColor $(if ($tooLong.Count) { 'Yellow' } else { 'Green' })
Write-Host ("Bad names      : {0:N0}" -f $badNames.Count)  -ForegroundColor $(if ($badNames.Count) { 'Yellow' } else { 'Green' })
Write-Host ("No version     : {0:N0}" -f $noVersion.Count) -ForegroundColor $(if ($noVersion.Count) { 'Yellow' } else { 'Green' })
Write-Host ""
Write-Host "wrote $rpt"
Write-Host "wrote $inv"
