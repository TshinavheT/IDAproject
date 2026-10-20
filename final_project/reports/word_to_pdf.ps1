# Standalone Word -> PDF export (used when the two-pass script stalls on its PDF step):
#   powershell -File reportsword_to_pdf.ps1 -In <path to .docx> -Out <path to .pdf>
param([string]$In, [string]$Out)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  "open " + (Get-Date -Format HH:mm:ss) | Out-File "$Out.log"
  $doc = $word.Documents.Open($In, $false, $true)
  "export " + (Get-Date -Format HH:mm:ss) | Out-File "$Out.log" -Append
  $doc.ExportAsFixedFormat($Out, 17)
  "pages " + $doc.ComputeStatistics(2) | Out-File "$Out.log" -Append
  $doc.Close($false)
  "done " + (Get-Date -Format HH:mm:ss) | Out-File "$Out.log" -Append
} finally { $word.Quit() }
