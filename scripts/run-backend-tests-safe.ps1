$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "backend\venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Python do ambiente virtual nao encontrado em backend\venv."
}

& $python (Join-Path $PSScriptRoot "run_backend_tests_safe.py") @args
exit $LASTEXITCODE
