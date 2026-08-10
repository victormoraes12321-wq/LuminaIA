from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_database
ROOT = Path(__file__).resolve().parents[2]


def _tree_digest() -> str:
    base = ROOT / "docs" / "contracts" / "security_rollout_v2"
    files = sorted(base.rglob("*.json"))
    return hashlib.sha256(b"".join(path.relative_to(base).as_posix().encode() + b"\0" + path.read_bytes() for path in files)).hexdigest()


def test_schema_and_golden_exports_are_reproducible() -> None:
    script = ROOT / "scripts" / "export_security_rollout_v2_contracts.py"
    subprocess.run([str(ROOT / "backend" / ".venv" / "Scripts" / "python.exe"), str(script)], check=True, cwd=ROOT)
    first = _tree_digest()
    subprocess.run([str(ROOT / "backend" / ".venv" / "Scripts" / "python.exe"), str(script)], check=True, cwd=ROOT)
    second = _tree_digest()
    assert first == second
    manifest = json.loads((ROOT / "docs" / "contracts" / "security_rollout_v2" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_count"] == 26
    assert manifest["golden_count"] == 4
