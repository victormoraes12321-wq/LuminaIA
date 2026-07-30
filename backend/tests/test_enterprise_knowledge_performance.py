from __future__ import annotations

import time
import uuid

import pytest

from contracts.enterprise_knowledge_v2 import (
    KnowledgeAssetType,
    KnowledgeMatchType,
    KnowledgeResolutionCandidateV2,
    KnowledgeResolutionResultV2,
)
from services.enterprise_knowledge.cache import EnterpriseKnowledgeCache
from services.enterprise_knowledge.normalization import normalize_lexical


pytestmark = pytest.mark.no_database


def test_governance_structural_workload_is_bounded() -> None:
    started = time.perf_counter()
    tenant_id = uuid.uuid4()
    assets = [
        {
            "id": uuid.uuid4(),
            "name": f"Termo empresarial {index:04d}",
            "versions": tuple(range(1, 11)),
            "lifecycle": "IN_REVIEW" if index % 20 == 0 else "PUBLISHED",
        }
        for index in range(1000)
    ]
    aliases = tuple(f"alias governado {index:03d}" for index in range(100))

    normalized_query = normalize_lexical("Termo empresarial 0999")
    matches = [
        asset
        for asset in assets
        if normalized_query == normalize_lexical(str(asset["name"]))
    ]
    review_queue = [asset for asset in assets if asset["lifecycle"] == "IN_REVIEW"]
    ordered = sorted(assets, key=lambda asset: str(asset["id"]))
    first_page = ordered[:100]
    cursor = str(first_page[-1]["id"])
    second_page = [asset for asset in ordered if str(asset["id"]) > cursor][:100]

    assert len(assets) == 1000
    assert sum(len(asset["versions"]) for asset in assets) == 10_000
    assert len(aliases) == 100
    assert len(matches) == 1
    assert len(review_queue) == 50
    assert not {asset["id"] for asset in first_page} & {
        asset["id"] for asset in second_page
    }

    candidate = KnowledgeResolutionCandidateV2(
        asset_id=matches[0]["id"],
        version_id=uuid.uuid4(),
        canonical_key="termo.empresarial.0999",
        asset_type=KnowledgeAssetType.BUSINESS_TERM,
        display_name=str(matches[0]["name"]),
        domain="Teste",
        score=1000,
        match_type=KnowledgeMatchType.DISPLAY_EXACT,
        matched_field="display_name",
        matched_text=str(matches[0]["name"]),
        checksum="c" * 64,
    )
    resolution = KnowledgeResolutionResultV2(
        query=normalized_query,
        candidates=[candidate],
        selected=candidate,
    )
    cache = EnterpriseKnowledgeCache(enabled=True, max_entries=1000)
    assert cache.get_resolution(
        tenant_id=tenant_id,
        locale="pt-BR",
        normalized_query=normalized_query,
        effective_at="CURRENT",
    ) is None
    cache.set_resolution(
        tenant_id=tenant_id,
        locale="pt-BR",
        normalized_query=normalized_query,
        effective_at="CURRENT",
        value=resolution,
    )
    assert cache.get_resolution(
        tenant_id=tenant_id,
        locale="pt-BR",
        normalized_query=normalized_query,
        effective_at="CURRENT",
    ) == resolution
    cache.invalidate_tenant(tenant_id)
    assert cache.snapshot()["entries"] == 0

    # This is a smoke bound, not a brittle latency SLO.
    assert time.perf_counter() - started < 5
