from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from services.blueprint_storage import (
    OFFICIAL_BLUEPRINT_PATH,
    BlueprintRepositoryFactory,
    BlueprintStorageMode,
    BlueprintStoragePolicy,
)


pytestmark = pytest.mark.no_database


def _test_env(*, run_id: str = "prompt18", worker: str = "gw0") -> dict[str, str]:
    return {
        "ENVIRONMENT": "test",
        "LUMINA_TESTING": "true",
        "LUMINA_BLUEPRINT_TEST_RUN_ID": run_id,
        "PYTEST_XDIST_WORKER": worker,
    }


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_runtime_location_is_fixed_and_not_environment_overridable() -> None:
    location = BlueprintStoragePolicy.resolve(
        {
            "ENVIRONMENT": "production",
            "LUMINA_TESTING": "false",
            "BLUEPRINT_PATH": "../../attacker.json",
        }
    )
    assert location.mode is BlueprintStorageMode.RUNTIME_OFFICIAL
    assert location.path == OFFICIAL_BLUEPRINT_PATH
    assert location.cleanup_root is None


def test_test_processes_and_workers_receive_distinct_controlled_files() -> None:
    first = BlueprintStoragePolicy.resolve(_test_env(worker="gw0"), process_id=101)
    second = BlueprintStoragePolicy.resolve(_test_env(worker="gw1"), process_id=101)
    third = BlueprintStoragePolicy.resolve(_test_env(worker="gw0"), process_id=102)
    assert first.is_test_isolated
    assert len({first.path, second.path, third.path}) == 3
    assert all(location.path != OFFICIAL_BLUEPRINT_PATH for location in (first, second, third))


@pytest.mark.parametrize("value", ["../escape", "..", "a/b", "a\\b", ""])
def test_test_storage_rejects_traversal_and_unsafe_segments(value: str) -> None:
    env = _test_env()
    env["LUMINA_BLUEPRINT_TEST_RUN_ID"] = value
    with pytest.raises(RuntimeError, match="server-controlled blueprint"):
        BlueprintStoragePolicy.resolve(env, process_id=103)


def test_qie_reads_and_writes_only_isolated_repository() -> None:
    from services.query_intelligence_engine import QueryIntelligenceEngine

    initial_hash = _sha256(OFFICIAL_BLUEPRINT_PATH)
    repository = BlueprintRepositoryFactory.create(_test_env(), process_id=104)
    if repository.exists():
        repository.location.path.unlink()
    assert not repository.exists()

    engine = QueryIntelligenceEngine(repository)
    assert repository.exists()
    assert len(engine.blueprints) == 2
    engine.execucoes_sem_ia += 1
    engine.save_blueprints()

    stored = repository.read()
    assert stored["global_metrics"]["execucoes_sem_ia"] == 1
    assert _sha256(OFFICIAL_BLUEPRINT_PATH) == initial_hash
    if repository.exists():
        repository.location.path.unlink()


def test_atomic_concurrent_writes_never_mix_documents() -> None:
    repository = BlueprintRepositoryFactory.create(_test_env(), process_id=105)

    def write_document(index: int) -> None:
        repository.write({"writer": index, "values": [index] * 100})

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(write_document, range(20)))

    document = repository.read()
    assert document["values"] == [document["writer"]] * 100
    assert not list(repository.location.path.parent.glob("*.tmp"))
    if repository.exists():
        repository.location.path.unlink()


def test_aborted_temporary_write_cannot_touch_official_repository(monkeypatch) -> None:
    repository = BlueprintRepositoryFactory.create(_test_env(), process_id=106)
    if repository.exists():
        repository.location.path.unlink()
    initial_hash = _sha256(OFFICIAL_BLUEPRINT_PATH)

    def fail_replace(source, destination):
        raise OSError("synthetic interrupted replace")

    monkeypatch.setattr("services.blueprint_storage.os.replace", fail_replace)
    with pytest.raises(OSError, match="synthetic interrupted"):
        repository.write({"never": "published"})

    assert not repository.exists()
    assert _sha256(OFFICIAL_BLUEPRINT_PATH) == initial_hash


def test_api_contracts_do_not_expose_a_blueprint_path() -> None:
    from contracts.smart_cache_materialization_v2 import CacheLookupRequestV2

    fields = set(CacheLookupRequestV2.model_fields)
    assert not {"path", "file", "repository_path", "blueprint_path"} & fields
