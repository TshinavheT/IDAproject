# Opens reports\IDA117V_Technical_Report.docx in Microsoft Word, refreshes the table of contents,
# saves the .docx and exports reports\IDA117V_Technical_Report.pdf. Prints the page of every Heading 1/2.
# The work is done on a copy in the local temp folder (Word can hang on OneDrive-synced folders) and copied back.
# Run:  powershell -File reports\export_report_pdf.ps1
$reports = $PSScriptRoot
$work = Join-Path $env:TEMP "ida_report_export"
New-Item -ItemType Directory -Force $work | Out-Null
$docx = Join-Path $work "IDA117V_Technical_Report.docx"
$pdf = Join-Path $work "IDA117V_Technical_Report.pdf"
Copy-Item (Join-Path $reports "IDA117V_Technical_Report.docx") $docx -Force
$log = { param($m) Write-Host ("[{0:HH:mm:ss}] {1}" -f (Get-Date), $m) }
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  & $log "opening"
  $doc = $word.Documents.Open($docx)
  & $log "updating table of contents"
  $doc.Repaginate()
  if ($doc.TablesOfContents.Count -gt 0) { $doc.TablesOfContents.Item(1).Update() }
  $doc.Repaginate()
  $doc.Save()
  & $log "exporting PDF"
  $doc.ExportAsFixedFormat($pdf, 17)
  "Total pages (PDF): " + $doc.ComputeStatistics(2)
  "Words: " + $doc.ComputeStatistics(0)
  $s2 = $doc.Sections.Item(2).Range; $s2.Collapse(1)
  $s3 = $doc.Sections.Item(3).Range; $s3.Collapse(1)
  "Body starts on PDF page " + $s2.Information(3) + "; appendices start on PDF page " + $s3.Information(3)
  # Headings listed from the table of contents entries (fast) rather than looping over every paragraph.
  if ($doc.TablesOfContents.Count -gt 0) {
    foreach ($para in $doc.TablesOfContents.Item(1).Range.Paragraphs) { $line = $para.Range.Text.Trim(); if ($line -ne "") { $line -replace "\s+", " " } }
  }
  $doc.Close($false)
  & $log "done"
} finally { $word.Quit() }
Copy-Item $docx (Join-Path $reports "IDA117V_Technical_Report.docx") -Force
Copy-Item $pdf (Join-Path $reports "IDA117V_Technical_Report.pdf") -Force
