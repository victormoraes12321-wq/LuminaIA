from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest


pytestmark = pytest.mark.no_database
ROOT = Path(__file__).resolve().parents[2]


def _release_manifest() -> tuple[str, ...]:
    if (ROOT / ".git").exists():
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        return tuple(path for path in result.stdout.decode("utf-8").split("\0") if path)
    return tuple(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
    )


def test_release_manifest_excludes_sensitive_and_runtime_artifacts() -> None:
    manifest = tuple(path.replace("\\", "/").lower() for path in _release_manifest())
    violations: list[str] = []
    for path in manifest:
        parts = path.split("/")
        basename = parts[-1]
        if basename == ".env" or (basename.startswith(".env.") and not basename.endswith(".example")):
            violations.append(path)
        if path.startswith("backend/venv/") or path.startswith("runtime-logs/"):
            violations.append(path)
        if any(part in {"test-results", "playwright-report", "scratch"} for part in parts):
            violations.append(path)
        if path == "backend/reports/postgres_clone_credentials.txt":
            violations.append(path)
    assert violations == []


def test_runtime_source_has_no_personal_absolute_paths() -> None:
    roots = (ROOT / "backend", ROOT / "frontend", ROOT / "scripts")
    suffixes = {".py", ".ts", ".tsx", ".js", ".mjs", ".ps1", ".bat"}
    patterns = ("c:\\users\\", "/home/", "\\desktop\\", "/desktop/")
    excluded = {"tests", "node_modules", ".next", "venv", ".venv"}
    violations: list[str] = []
    for source_root in roots:
        for directory, dirnames, filenames in os.walk(source_root):
            dirnames[:] = [name for name in dirnames if name not in excluded]
            for filename in filenames:
                path = Path(directory) / filename
                if path.suffix.lower() in suffixes:
                    content = path.read_text(encoding="utf-8", errors="ignore").lower()
                    if any(pattern in content for pattern in patterns):
                        violations.append(path.relative_to(ROOT).as_posix())
    assert violations == []


@pytest.mark.parametrize(
    "relative_path",
    (
        "backend/scripts/run_enterprise_stress.py",
        "backend/tests/stress_audit_pipeline.py",
    ),
)
def test_release_scripts_do_not_depend_on_personal_paths(relative_path: str) -> None:
    source = (ROOT / relative_path).read_text(encoding="utf-8").lower()
    assert "c:\\users\\" not in source
    assert "\\desktop\\" not in source
    assert "\\downloads\\" not in source
    assert "\\.gemini\\" not in source
