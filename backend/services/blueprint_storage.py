"""Server-controlled storage policy for the legacy query blueprints.

The operational repository location is fixed. Test processes are forced onto
an isolated file below the operating-system temporary directory, so a test
cannot read or mutate ``services/blueprints.json`` during collection/runtime.
"""
from __future__ import annotations

import atexit
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from threading import Lock, RLock
from typing import Mapping


OFFICIAL_BLUEPRINT_PATH = Path(__file__).resolve().with_name("blueprints.json")
_TEST_STORAGE_ROOT = (Path(tempfile.gettempdir()) / "luminaai-blueprints").resolve()
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_cleanup_lock = Lock()
_registered_cleanup_paths: set[Path] = set()
_repository_locks_guard = Lock()
_repository_locks: dict[Path, RLock] = {}


class BlueprintStorageMode(str, Enum):
    RUNTIME_OFFICIAL = "RUNTIME_OFFICIAL"
    TEST_ISOLATED = "TEST_ISOLATED"


@dataclass(frozen=True)
class BlueprintStorageLocation:
    mode: BlueprintStorageMode
    path: Path
    cleanup_root: Path | None = None

    @property
    def is_test_isolated(self) -> bool:
        return self.mode is BlueprintStorageMode.TEST_ISOLATED


class BlueprintStoragePolicy:
    """Resolve a storage location exclusively from trusted process state."""

    @staticmethod
    def _safe_segment(value: str, *, name: str) -> str:
        candidate = value.strip()
        if not _SAFE_SEGMENT.fullmatch(candidate) or candidate in {".", ".."}:
            raise RuntimeError(f"Invalid server-controlled blueprint {name}")
        return candidate

    @classmethod
    def resolve(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        process_id: int | None = None,
    ) -> BlueprintStorageLocation:
        env = environ or os.environ
        is_test = (
            str(env.get("ENVIRONMENT", "")).strip().lower() == "test"
            and str(env.get("LUMINA_TESTING", "")).strip().lower()
            in {"1", "true", "yes", "on"}
        )
        if not is_test:
            return BlueprintStorageLocation(
                mode=BlueprintStorageMode.RUNTIME_OFFICIAL,
                path=OFFICIAL_BLUEPRINT_PATH,
            )

        run_id = cls._safe_segment(
            env.get("LUMINA_BLUEPRINT_TEST_RUN_ID", "isolated"), name="run id"
        )
        worker_id = cls._safe_segment(
            env.get("PYTEST_XDIST_WORKER", "main"), name="worker id"
        )
        pid = int(process_id if process_id is not None else os.getpid())
        process_segment = cls._safe_segment(str(pid), name="process id")
        process_root = (_TEST_STORAGE_ROOT / run_id / worker_id / process_segment).resolve()
        if _TEST_STORAGE_ROOT not in process_root.parents:
            raise RuntimeError("Blueprint test storage escaped its controlled root")
        return BlueprintStorageLocation(
            mode=BlueprintStorageMode.TEST_ISOLATED,
            path=process_root / "blueprints.json",
            cleanup_root=process_root,
        )


class BlueprintJsonRepository:
    def __init__(self, location: BlueprintStorageLocation):
        self.location = location
        self._write_lock = _repository_lock(self.location.path)
        self.location.path.parent.mkdir(parents=True, exist_ok=True)
        if location.cleanup_root is not None:
            _register_cleanup(location.cleanup_root)

    def exists(self) -> bool:
        return self.location.path.is_file()

    def read(self) -> dict[str, object]:
        return json.loads(self.location.path.read_text(encoding="utf-8"))

    def write(self, data: dict[str, object]) -> None:
        """Atomically replace the repository file in its controlled directory."""
        with self._write_lock:
            serialized = json.dumps(data, indent=2, ensure_ascii=False)
            fd, temporary_name = tempfile.mkstemp(
                prefix=".blueprints-", suffix=".tmp", dir=self.location.path.parent
            )
            temporary_path = Path(temporary_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write(serialized)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary_path, self.location.path)
            finally:
                temporary_path.unlink(missing_ok=True)


class BlueprintRepositoryFactory:
    @staticmethod
    def create(
        environ: Mapping[str, str] | None = None,
        *,
        process_id: int | None = None,
    ) -> BlueprintJsonRepository:
        return BlueprintJsonRepository(
            BlueprintStoragePolicy.resolve(environ, process_id=process_id)
        )


def _register_cleanup(path: Path) -> None:
    with _cleanup_lock:
        if path in _registered_cleanup_paths:
            return
        _registered_cleanup_paths.add(path)
        atexit.register(_cleanup_test_path, path)


def _repository_lock(path: Path) -> RLock:
    resolved = path.resolve()
    with _repository_locks_guard:
        return _repository_locks.setdefault(resolved, RLock())


def _cleanup_test_path(path: Path) -> None:
    resolved = path.resolve()
    if _TEST_STORAGE_ROOT not in resolved.parents:
        return
    shutil.rmtree(resolved, ignore_errors=True)
