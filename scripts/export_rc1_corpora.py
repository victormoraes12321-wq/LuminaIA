"""Create or verify the deterministic RC-01.1 corpus manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "backend" / "tests" / "fixtures" / "rc1"
MANIFEST = CORPUS_DIR / "manifest.json"
CORPUS_FILES = ("continuity.json", "language_safety.json", "numerical_truth.json")


def canonical_bytes(path: Path) -> bytes:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def build_manifest() -> dict[str, object]:
    files: list[dict[str, object]] = []
    combined = hashlib.sha256()
    for name in CORPUS_FILES:
        content = canonical_bytes(CORPUS_DIR / name)
        digest = hashlib.sha256(content).hexdigest()
        combined.update(name.encode())
        combined.update(b"\0")
        combined.update(content)
        files.append({"name": name, "sha256": digest, "canonical_bytes": len(content)})
    return {
        "contract": "lumina.rc-acceptance-corpora/1.0",
        "algorithm": "sha256-canonical-json",
        "files": files,
        "combined_sha256": combined.hexdigest(),
    }


def serialized_manifest() -> str:
    return json.dumps(build_manifest(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated = serialized_manifest()
    if args.write:
        MANIFEST.write_text(generated, encoding="utf-8", newline="\n")
    if args.check:
        if not MANIFEST.exists() or MANIFEST.read_text(encoding="utf-8") != generated:
            raise SystemExit("RC corpus manifest is stale; run with --write")
    print(build_manifest()["combined_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
