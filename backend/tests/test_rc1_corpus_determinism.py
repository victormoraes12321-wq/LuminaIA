from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "export_rc1_corpora.py"


def _exporter():
    spec = importlib.util.spec_from_file_location("export_rc1_corpora", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_corpus_export_is_deterministic_and_manifest_is_current() -> None:
    exporter = _exporter()
    first = exporter.serialized_manifest()
    second = exporter.serialized_manifest()
    manifest = exporter.MANIFEST.read_text(encoding="utf-8")
    assert first == second == manifest
    parsed = json.loads(manifest)
    assert len(parsed["combined_sha256"]) == 64
