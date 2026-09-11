<#
.SYNOPSIS
  Turn the generated handbook HTML into .docx and .pdf via Word.

.DESCRIPTION
  Run gen_handbook_docs.py first; this consumes what it writes into dist/.

  There is no pandoc on this machine, so Word itself is the converter. It opens HTML
  natively and both save targets are one call each. Notes that cost time to rediscover:

    - Visible:$false and DisplayAlerts 0, or a hidden "save changes?" dialog blocks the
      whole script until someone notices Word is sitting in the taskbar.
    - Open the file with ReadOnly so a crashed earlier run cannot leave a lock that makes
      the next one silently open a copy.
    - ExportAsFixedFormat, not SaveAs wdFormatPDF: only the former sets bookmarks from
      the headings, which is what gives the PDF a navigation pane.
    - The COM object is released and Word quit in a finally block. A leaked WINWORD.EXE
      holds the output files open and the next run fails on the SaveAs.

  Output lands beside the HTML in dist/, named for the SharePoint guides folder.
#>
[CmdletBinding()]
param(
    [string]$DistPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'dist')
)

$ErrorActionPreference = 'Stop'

$wdFormatXMLDocument   = 16   # .docx
$wdExportFormatPDF     = 17
$wdExportOptimizeForPrint = 0
$wdExportAllDocument   = 0
$wdExportDocumentContent = 0
$wdExportCreateHeadingBookmarks = 1

function Set-PageDiscipline {
    <#
      Stop headings and tables being cut in half by a page boundary.

      This has to happen HERE, on the imported document, not in the CSS. Word's HTML
      import accepts `page-break-before` but silently discards `page-break-after: avoid`,
      so a heading lands at the foot of a page with everything it introduces overleaf.
      The CSS still carries the rule for anyone opening the .html directly in a browser;
      Word gets it as real paragraph properties.

      OutlineLevel is the locale-independent way to find a heading. Style names are not:
      this machine's Word is English, but the FR document is equally likely to be opened
      in a French install where the style reads "Titre 2".
    #>
    param($doc)

    # Per paragraph, not $doc.Content.ParagraphFormat in one go: setting it on a range
    # that spans tables does not reliably reach the paragraphs inside them, and the
    # first version of this left a body paragraph cut in half by a page break while
    # reporting success.
    $kept = 0
    foreach ($p in $doc.Paragraphs) {
        $p.KeepTogether = $true          # this paragraph is never split across pages
        $p.WidowControl = $true
        # a heading stays with what follows it; 10 is wdOutlineLevelBodyText
        if ($p.OutlineLevel -lt 10) { $p.KeepWithNext = $true; $kept++ }
    }

    # tables: no row split, and the header row repeats if a long one does span pages
    foreach ($t in $doc.Tables) {
        $t.Rows.AllowBreakAcrossPages = $false
        if ($t.Rows.Count -gt 0) { $t.Rows.Item(1).HeadingFormat = $true }
    }

    return $kept
}

$html = Get-ChildItem -Path $DistPath -Filter '*.html' -File
if (-not $html) { throw "No .html in $DistPath. Run gen_handbook_docs.py first." }

# Check the targets are writable BEFORE opening Word. A PDF left open in Acrobat locks
# the file, and the failure surfaces as a COM exception from SaveAs halfway through the
# batch, having already overwritten the other document. Naming the offender costs a
# millisecond and saves working out which of four files is the problem.
$locked = @()
foreach ($f in $html) {
    foreach ($ext in '.docx', '.pdf') {
        $t = Join-Path $DistPath ($f.BaseName + $ext)
        if (Test-Path $t) {
            try { [IO.File]::OpenWrite($t).Close() } catch { $locked += $t }
        }
    }
}
if ($locked) {
    throw ("Close these before running, something has them open (Acrobat? Word?):" +
           [Environment]::NewLine + ($locked -join [Environment]::NewLine))
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
    foreach ($f in $html) {
        $base = Join-Path $DistPath $f.BaseName
        $docx = "$base.docx"
        $pdf  = "$base.pdf"

        # not ReadOnly: Set-PageDiscipline edits the document. The .html is never written
        # back, because Close below passes SaveChanges = false.
        $doc = $word.Documents.Open($f.FullName, $false, $false)
        try {
            $kept = Set-PageDiscipline $doc
            $doc.SaveAs([ref]$docx, [ref]$wdFormatXMLDocument)
            $doc.ExportAsFixedFormat($pdf, $wdExportFormatPDF, $false,
                                     $wdExportOptimizeForPrint, $wdExportAllDocument,
                                     1, 1, $wdExportDocumentContent, $true, $true,
                                     $wdExportCreateHeadingBookmarks)
            $pages = $doc.ComputeStatistics(2)                    # wdStatisticPages
            "{0,-52} {1,2} pages, {2,3} headings kept with their text" -f $f.BaseName, $pages, $kept
        }
        finally {
            $doc.Close([ref]$false)
            [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc)
        }
    }
}
finally {
    $word.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    [GC]::Collect()
}

''
'Drop the .pdf (and the .docx if you want it editable) in the SharePoint guides folder.'
