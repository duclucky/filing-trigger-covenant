param([string]$Only = "")

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

if ($Only -eq "" -or $Only -eq "lint") {
  .\.venv\Scripts\python.exe scripts/ascii_header_check.py
  if (Get-Command genvm-lint -ErrorAction SilentlyContinue) {
    genvm-lint check contracts/filing_trigger_covenant.py
  } else {
    Write-Host "genvm-lint not on PATH; relying on gltest/static checks"
  }
}

if ($Only -eq "" -or $Only -eq "test") {
  .\.venv\Scripts\python.exe -m pytest tests/direct -v
}

