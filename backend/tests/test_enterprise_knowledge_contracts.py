from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from contracts.enterprise_knowledge_v2 import (
    BusinessTermContentV2,
    KnowledgeAssetType,
    KnowledgeBindingStatus,
    KnowledgeMatchType,
    KnowledgePermission,
    KnowledgeResolutionCandidateV2,
    KnowledgeResolutionResultV2,
    KnowledgeRolloutMode,
    MetricKnowledgeContentV2,
)
from models.user import UserRole
from services.enterprise_knowledge.cache import EnterpriseKnowledgeCache
from services.enterprise_knowledge.errors import KnowledgeAccessDeniedError
from services.enterprise_knowledge.legacy_adapter import LegacyBusinessKnowledgeAdapter
from services.enterprise_knowledge.metric_binding import (
    official_formula_fingerprint,
    validate_metric_binding,
)
from services.enterprise_knowledge.normalization import (
    compute_checksum,
    csv_safe,
    normalize_lexical,
)
from services.enterprise_knowledge.permissions import require_permission
from services.enterprise_knowledge.runtime import EnterpriseKnowledgeRuntime
from services.metric_registry import METRIC_DEFINITIONS


pytestmark = pytest.mark.no_database


def term(**changes: object) -> BusinessTermContentV2:
    values: dict[str, object] = {
        "kind": KnowledgeAssetType.BUSINESS_TERM,
        "canonical_name": "faturamento",
        "display_name": "Faturamento",
        "definition": "Receita comercial reconhecida.",
        "domain": "Vendas",
        "short_description": "Receita comercial.",
        "full_description": "Receita comercial reconhecida conforme política.",
        "aliases": ["receita de vendas"],
    }
    values.update(changes)
    return BusinessTermContentV2.model_validate(values)


def metric(**changes: object) -> MetricKnowledgeContentV2:
    definition = METRIC_DEFINITIONS["faturamento_comercial"]
    values: dict[str, object] = {
        "kind": KnowledgeAssetType.METRIC,
        "canonical_metric_id": "faturamento_comercial",
        "display_name": "Faturamento comercial",
        "definition": "Receita comercial governada.",
        "purpose": "Mensurar vendas comerciais.",
        "unit": "BRL",
        "display_format": "currency",
        "aggregation_semantics": "SUM",
        "grain": definition.grain,
        "frequency": "DAILY",
        "authoritative_source": definition.source,
        "formula_reference": definition.key,
        "formula_fingerprint": official_formula_fingerprint(definition),
    }
    values.update(changes)
    return MetricKnowledgeContentV2.model_validate(values)


def test_contract_rejects_unknown_fields_and_active_html() -> None:
    with pytest.raises(ValidationError):
        BusinessTermContentV2.model_validate({**term().model_dump(), "unexpected": "value"})
    with pytest.raises(ValidationError, match="active HTML"):
        term(definition="<script>alert(1)</script>")
    with pytest.raises(ValidationError, match="null bytes"):
        term(definition="invalid\x00text")


def test_checksum_is_canonical_and_content_sensitive() -> None:
    assert compute_checksum({"b": 2, "a": 1}) == compute_checksum({"a": 1, "b": 2})
    assert compute_checksum(term()) != compute_checksum(term(definition="Outra definição."))
    assert len(compute_checksum(term())) == 64


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Faturação Líquida", "faturacao liquida"),
        ("  Receita---de   Vendas  ", "receita de vendas"),
        ("TICKET MÉDIO", "ticket medio"),
    ],
)
def test_normalization_is_deterministic(raw: str, expected: str) -> None:
    assert normalize_lexical(raw) == expected


def test_permission_matrix_is_explicit_and_consulta_is_read_only() -> None:
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()
    require_permission(
        tenant_id=tenant_id,
        user_id=user_id,
        role=UserRole.CONSULTA,
        permission=KnowledgePermission.READ,
    )
    with pytest.raises(KnowledgeAccessDeniedError):
        require_permission(
            tenant_id=tenant_id,
            user_id=user_id,
            role=UserRole.CONSULTA,
            permission=KnowledgePermission.CREATE,
        )
    require_permission(
        tenant_id=tenant_id,
        user_id=user_id,
        role=UserRole.ADMIN,
        permission=KnowledgePermission.PUBLISH,
    )


def test_metric_binding_preserves_registry_authority() -> None:
    valid = validate_metric_binding(asset_type=KnowledgeAssetType.METRIC, content=metric())
    assert valid.status is KnowledgeBindingStatus.VALID

    conflict = validate_metric_binding(
        asset_type=KnowledgeAssetType.METRIC,
        content=metric(formula_fingerprint="0" * 64),
    )
    assert conflict.status is KnowledgeBindingStatus.CONFLICT
    assert conflict.reason_code == "FORMULA_FINGERPRINT_MISMATCH"

    missing = validate_metric_binding(
        asset_type=KnowledgeAssetType.METRIC,
        content=metric(canonical_metric_id="metrica_inexistente"),
    )
    assert missing.status is KnowledgeBindingStatus.MISSING_REGISTRY_ENTRY


def test_cache_key_is_tenant_scoped_and_returns_copies() -> None:
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    assert EnterpriseKnowledgeCache.key(
        tenant_id=tenant_a,
        locale="pt-BR",
        normalized_query="faturamento",
        publication_epoch="abc",
    ) != EnterpriseKnowledgeCache.key(
        tenant_id=tenant_b,
        locale="pt-BR",
        normalized_query="faturamento",
        publication_epoch="abc",
    )
    cache = EnterpriseKnowledgeCache(enabled=True)
    candidate = KnowledgeResolutionCandidateV2(
        asset_id=uuid.uuid4(),
        version_id=uuid.uuid4(),
        canonical_key="faturamento",
        asset_type=KnowledgeAssetType.BUSINESS_TERM,
        display_name="Faturamento",
        domain="Vendas",
        score=1000,
        match_type=KnowledgeMatchType.CANONICAL_EXACT,
        matched_field="canonical_key",
        matched_text="faturamento",
        checksum="a" * 64,
    )
    resolution = KnowledgeResolutionResultV2(
        query="faturamento",
        candidates=[candidate],
        selected=candidate,
    )
    cache.set_resolution(
        tenant_id=tenant_a,
        locale="pt-BR",
        normalized_query="faturamento",
        effective_at="CURRENT",
        value=resolution,
    )
    hit = cache.get_resolution(
        tenant_id=tenant_a,
        locale="pt-BR",
        normalized_query="faturamento",
        effective_at="CURRENT",
    )
    assert hit == resolution
    assert hit is not resolution
    assert cache.get_resolution(
        tenant_id=tenant_b,
        locale="pt-BR",
        normalized_query="faturamento",
        effective_at="CURRENT",
    ) is None
    cache.invalidate_tenant(tenant_a)
    assert cache.get_resolution(
        tenant_id=tenant_a,
        locale="pt-BR",
        normalized_query="faturamento",
        effective_at="CURRENT",
    ) is None
    assert cache.snapshot() == {
        "entries": 0,
        "query_keys": 0,
        "hits": 1,
        "misses": 2,
        "invalidations": 1,
    }


@pytest.mark.asyncio
async def test_runtime_modes_preserve_ambiguity_and_provenance() -> None:
    from unittest.mock import AsyncMock

    tenant_id = uuid.uuid4()
    user = object()
    candidate = KnowledgeResolutionCandidateV2(
        asset_id=uuid.uuid4(),
        version_id=uuid.uuid4(),
        canonical_key="faturamento",
        asset_type=KnowledgeAssetType.METRIC,
        display_name="Faturamento",
        domain="Vendas",
        score=950,
        match_type=KnowledgeMatchType.ALIAS_EXACT,
        matched_field="alias",
        matched_text="receita",
        checksum="b" * 64,
    )
    resolution = KnowledgeResolutionResultV2(
        query="receita",
        candidates=[candidate],
        selected=candidate,
    )
    service = AsyncMock()
    service.resolve.return_value = resolution

    legacy = EnterpriseKnowledgeRuntime(service, mode=KnowledgeRolloutMode.LEGACY_ONLY)
    assert await legacy.resolve(user=user, query="receita") is None
    service.resolve.assert_not_awaited()

    shadow = EnterpriseKnowledgeRuntime(service, mode=KnowledgeRolloutMode.SHADOW_READ)
    assert await shadow.resolve(user=user, query="receita") is None

    runtime = EnterpriseKnowledgeRuntime(service, mode=KnowledgeRolloutMode.V2_READ)
    facts = await runtime.facts_for_context(user=user, query="receita")
    assert facts[0]["canonical_id"] == "faturamento"
    assert facts[0]["provenance_version_id"] == str(candidate.version_id)
    assert "sql" not in facts[0]
    assert str(tenant_id) not in facts[0]


def test_legacy_adapter_never_invents_owner_or_publication() -> None:
    missing_owner = LegacyBusinessKnowledgeAdapter.convert_concept(
        tenant_id=uuid.uuid4(),
        owner_user_id=None,
        name="Faturamento",
        description="Receita.",
        domain="Vendas",
        aliases=[],
    )
    assert missing_owner.draft is None
    assert missing_owner.warnings == ("LEGACY_OWNER_REQUIRED",)

    converted = LegacyBusinessKnowledgeAdapter.convert_concept(
        tenant_id=uuid.uuid4(),
        owner_user_id=uuid.uuid4(),
        name="Faturamento",
        description="Receita.",
        domain="Vendas",
        aliases=["receita"],
    )
    assert converted.draft is not None
    assert converted.draft.content.kind is KnowledgeAssetType.BUSINESS_TERM


@pytest.mark.parametrize("value", ["=1+1", "+cmd", "-10", "@SUM(A1)", "\tformula"])
def test_csv_formula_injection_is_neutralized(value: str) -> None:
    assert csv_safe(value).startswith("'")
