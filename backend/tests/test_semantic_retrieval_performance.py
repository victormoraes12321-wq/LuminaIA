from __future__ import annotations

from time import perf_counter

import pytest

from services.semantic_retrieval.normalization import normalize_semantic_text
from services.semantic_retrieval.representation import (
    DeterministicFeatureEmbeddingProvider,
)


pytestmark = pytest.mark.no_database


def test_one_thousand_local_representations_are_bounded_and_offline() -> None:
    provider = DeterministicFeatureEmbeddingProvider(dimension=64)
    assert provider.provider_info().network_required is False
    started = perf_counter()
    checksums = {
        provider.encode_query(
            normalize_semantic_text(f"metrica sintetica {index:05d}")
        ).checksum
        for index in range(1_000)
    }
    elapsed = perf_counter() - started
    assert len(checksums) == 1_000
    assert elapsed < 20


def test_ten_thousand_aliases_normalize_deterministically_without_model() -> None:
    started = perf_counter()
    first = [
        normalize_semantic_text(f"alias sintetico {index:05d}").checksum
        for index in range(10_000)
    ]
    second = [
        normalize_semantic_text(f"alias sintetico {index:05d}").checksum
        for index in range(10_000)
    ]
    elapsed = perf_counter() - started
    assert first == second
    assert len(set(first)) == 10_000
    assert elapsed < 30
