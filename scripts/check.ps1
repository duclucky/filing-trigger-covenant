param([string]$Only = "")

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$Python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
}

if ($Only -eq "" -or $Only -eq "lint") {
  & $Python scripts/ascii_header_check.py
  if (Get-Command genvm-lint -ErrorAction SilentlyContinue) {
    genvm-lint check contracts/filing_trigger_covenant.py
  } else {
    Write-Host "genvm-lint not on PATH; relying on gltest/static checks"
  }
}

if ($Only -eq "" -or $Only -eq "test") {
  & $Python -m pytest tests/direct -v
}

if ($Only -eq "" -or $Only -eq "deployment") {
  node --test tests/deployment_parser.test.mjs
}
