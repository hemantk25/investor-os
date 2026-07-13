param(
  [switch]$IncludePrivateData
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path ".").Path
$parent = Split-Path -Parent $root
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dest = Join-Path $parent "InvestorOS_Drive_Handoff_$stamp"

$excludeDirs = @(".git", ".venv", ".pytest_cache", ".superpowers", "__pycache__")
if (-not $IncludePrivateData) {
  $excludeDirs += @("data", "briefs", "profile", "report_data")
}

$excludeFiles = @("*.pyc", "*.pyo")

New-Item -ItemType Directory -Force -Path $dest | Out-Null

$args = @($root, $dest, "/E", "/XD") + $excludeDirs + @("/XF") + $excludeFiles + @("/NFL", "/NDL", "/NJH", "/NJS", "/NP")
robocopy @args | Out-Null

if ($LASTEXITCODE -gt 7) {
  throw "robocopy failed with exit code $LASTEXITCODE"
}

if (-not $IncludePrivateData) {
  foreach ($dir in @("data", "briefs", "profile")) {
    $path = Join-Path $dest $dir
    New-Item -ItemType Directory -Force -Path $path | Out-Null
  }
  Set-Content -LiteralPath (Join-Path $dest "data\README.txt") -Value "Place the latest ICICI export here as holdings.xlsx. Optional: add advisory.xlsx." -Encoding UTF8
  Set-Content -LiteralPath (Join-Path $dest "briefs\README.txt") -Value "Generated morning briefs will appear here." -Encoding UTF8
  Set-Content -LiteralPath (Join-Path $dest "profile\README.txt") -Value "Place one-pager.md here before generating Morning Briefs." -Encoding UTF8
}

Write-Host "Clean handoff folder created:"
Write-Host $dest
if ($IncludePrivateData) {
  Write-Host "Private data was included. Share carefully."
} else {
  Write-Host "Private data was excluded. Add holdings.xlsx/profile files manually before use."
}
