[CmdletBinding()]
param(
    [ValidateSet('all', 'numerical', 'continuity', 'typo', 'impossible', 'causality', 'multiview')]
    [string]$Selection = 'all'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'backend/.venv is required; create it from backend/requirements.txt.'
}

$targets = @{
    numerical = 'backend/tests/test_rc1_numerical_corpus.py'
    continuity = 'backend/tests/test_rc1_continuity_corpus.py'
    typo = 'backend/tests/test_rc1_language_safety_corpus.py::test_typo_corpus'
    impossible = 'backend/tests/test_rc1_language_safety_corpus.py::test_impossible_corpus'
    causality = 'backend/tests/test_rc1_language_safety_corpus.py::test_causality_corpus'
    multiview = 'backend/tests/test_rc1_multiview_corpus.py'
}

Push-Location $repoRoot
try {
    & $python scripts/export_rc1_corpora.py --check
    if ($Selection -eq 'all') {
        & $python -m pytest @($targets.Values) backend/tests/test_rc1_corpus_determinism.py -q
    } else {
        & $python -m pytest $targets[$Selection] -q
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
