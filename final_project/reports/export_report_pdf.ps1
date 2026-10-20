# Two-pass export of the merged report (no Word TOC field: Word hangs exporting one).
#   1. build the .docx and record the displayed page of every Heading 1/2 in reports/report_headings.json
#   2. rebuild with a contents page listing those pages, and export the PDF
# Each Word step runs in its own PowerShell process (reusing Word in one process can hang).
# Run from anywhere:  powershell -File reports\export_report_pdf.ps1
param([string]$Step = "all")
$reports = $PSScriptRoot
$root = Split-Path $reports -Parent
# A fresh folder per run: Word can hang when exporting into a folder used by an earlier (killed) Word session.
if ($env:IDA_REPORT_WORK) { $work = $env:IDA_REPORT_WORK } else { $work = Join-Path $env:TEMP ("ida_report_" + (Get-Date -Format "yyyyMMdd_HHmmss")); $env:IDA_REPORT_WORK = $work }
New-Item -ItemType Directory -Force $work | Out-Null
$docx = Join-Path $work "IDA117V_Technical_Report.docx"
$pdf = Join-Path $work "IDA117V_Technical_Report.pdf"
$headingsJson = Join-Path $reports "report_headings.json"

function Open-Doc { $w = New-Object -ComObject Word.Application; $w.Visible = $false; $w.DisplayAlerts = 0; return $w }

if ($Step -eq "headings") {
  $word = Open-Doc
  try {
    $doc = $word.Documents.Open($docx, $false, $true)
    $items = @()
    foreach ($p in $doc.Paragraphs) {
      $lvl = $p.OutlineLevel
      if ($lvl -eq 1 -or $lvl -eq 2) {
        $t = $p.Range.Text.Trim()
        if ($t -ne "") { $items += [pscustomobject]@{ level = [int]$lvl; text = $t; page = [int]$p.Range.Information(1); abs = [int]$p.Range.Information(3) } }
      }
    }
    $items | ConvertTo-Json | Out-File $headingsJson -Encoding utf8
    $doc.Close($false)
  } finally { $word.Quit() }
  exit 0
}
if ($Step -eq "pdf") {
  $word = Open-Doc
  try {
    $doc = $word.Documents.Open($docx, $false, $true)
    $doc.ExportAsFixedFormat($pdf, 17)
    "Total PDF pages: " + $doc.ComputeStatistics(2)
    $doc.Close($false)
  } finally { $word.Quit() }
  exit 0
}

$env:OUT_DOCX = $docx
Push-Location $root
node reports/build_full_report.js
powershell -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath -Step headings
Get-Process WINWORD -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep -Seconds 3  # let the first Word instance exit fully
node reports/build_full_report.js
powershell -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath -Step pdf
Pop-Location
Copy-Item $docx (Join-Path $reports "IDA117V_Technical_Report.docx") -Force
Copy-Item $pdf (Join-Path $reports "IDA117V_Technical_Report.pdf") -Force
Get-Content $headingsJson -Raw | ConvertFrom-Json | Where-Object { $_.level -eq 1 } | ForEach-Object { "{0,3}  {1}" -f $_.page, $_.text }
