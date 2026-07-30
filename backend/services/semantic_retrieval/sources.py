from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from contracts.semantic_retrieval_v2 import (
    SemanticDataClassification,
    SemanticDocumentType,
    SemanticEntityType,
    SemanticPermission,
    SemanticSourceType,
)
from services.enterprise_knowledge.repository import EnterpriseKnowledgeRepository
from services.metric_registry import METRIC_DEFINITIONS
from services.semantic_retrieval.checksums import checksum_for


@dataclass(frozen=True)
class SemanticSourceRecord:
    canonical_id: str
    document_type: SemanticDocumentType
    entity_type: SemanticEntityType
    display_label: str
    aliases: tuple[str, ...]
    description: str
    domain: str
    source_type: SemanticSourceType
    source_id: str
    source_version: str
    source_checksum: str
    classification: SemanticDataClassification
    permission_requirement: SemanticPermission | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    deprecated: bool = False
    code: str | None = None
    related_canonical_ids: tuple[str, ...] = ()
    unit: str | None = None
    allowed_dimensions: tuple[str, ...] = ()


@dataclass(frozen=True)
class SemanticSourceSnapshot:
    source_type: SemanticSourceType
    source_id: str
    source_version: str
    source_checksum: str
    tenant_scoped: bool
    records: tuple[SemanticSourceRecord, ...]
    watermark: str | None = None


class SemanticIndexSourceProvider(Protocol):
    async def load(
        self,
        *,
        tenant_id: uuid.UUID,
        at: datetime,
    ) -> SemanticSourceSnapshot: ...


def _entity_type(asset_type: str, content: dict) -> SemanticEntityType:
    if asset_type in {"METRIC", "KPI"}:
        return SemanticEntityType.METRIC
    if asset_type == "DIMENSION":
        return SemanticEntityType.DIMENSION
    if asset_type == "ENTITY":
        value = str(content.get("canonical_entity_id") or content.get("display_name") or "")
        folded = value.casefold()
        mapping = (
            ("filial", SemanticEntityType.BRANCH),
            ("unidade", SemanticEntityType.BRANCH),
            ("produto", SemanticEntityType.PRODUCT),
            ("cliente", SemanticEntityType.CUSTOMER),
            ("fornecedor", SemanticEntityType.SUPPLIER),
            ("vendedor", SemanticEntityType.SELLER),
            ("regiao", SemanticEntityType.REGION),
            ("cidade", SemanticEntityType.CITY),
            ("estado", SemanticEntityType.STATE),
        )
        for token, entity_type in mapping:
            if token in folded:
                return entity_type
    return SemanticEntityType.BUSINESS_CONCEPT


def _document_type(asset_type: str) -> SemanticDocumentType:
    mapping = {
        "BUSINESS_TERM": SemanticDocumentType.BUSINESS_TERM,
        "METRIC": SemanticDocumentType.METRIC,
        "KPI": SemanticDocumentType.KPI,
        "DIMENSION": SemanticDocumentType.DIMENSION,
        "ENTITY": SemanticDocumentType.ENTITY_TYPE,
        "BUSINESS_RULE": SemanticDocumentType.BUSINESS_RULE,
        "ALIAS_SET": SemanticDocumentType.ALIAS,
        "CALENDAR_POLICY": SemanticDocumentType.CALENDAR_POLICY,
        "SEMANTIC_RELATION": SemanticDocumentType.RELATION,
    }
    return mapping.get(asset_type, SemanticDocumentType.SYSTEM_CONCEPT)


def _content_label(asset_type: str, canonical_key: str, content: dict) -> str:
    return str(
        content.get("display_name")
        or content.get("canonical_name")
        or content.get("canonical_metric_id")
        or content.get("canonical_dimension_id")
        or content.get("canonical_entity_id")
        or canonical_key
    )


def _content_description(content: dict) -> str:
    return str(
        content.get("definition")
        or content.get("statement")
        or content.get("description")
        or content.get("short_description")
        or content.get("display_name")
        or "Conceito empresarial publicado."
    )[:4000]


class EnterpriseKnowledgeSemanticSourceProvider:
    def __init__(self, repository: EnterpriseKnowledgeRepository, *, locale: str = "pt-BR") -> None:
        self.repository = repository
        self.locale = locale

    async def load(
        self,
        *,
        tenant_id: uuid.UUID,
        at: datetime,
    ) -> SemanticSourceSnapshot:
        pairs = await self.repository.list_effective_published(
            tenant_id=tenant_id,
            at=at,
        )
        version_ids = tuple(version.id for _, version in pairs)
        aliases = await self.repository.aliases_for_versions(
            tenant_id=tenant_id,
            version_ids=version_ids,
            locale=self.locale,
        )
        records: list[SemanticSourceRecord] = []
        for asset, version in pairs:
            content = dict(version.content)
            asset_aliases = {
                str(value)
                for value in content.get("aliases", [])
                if isinstance(value, str)
            }
            asset_aliases.update(row.alias for row in aliases.get(version.id, []))
            canonical_id = str(
                content.get("canonical_metric_id")
                or content.get("canonical_dimension_id")
                or content.get("canonical_entity_id")
                or content.get("canonical_name")
                or content.get("canonical_target_key")
                or asset.canonical_key
            )
            related = content.get("related_terms") or content.get("relationships") or []
            records.append(
                SemanticSourceRecord(
                    canonical_id=canonical_id,
                    document_type=_document_type(asset.asset_type),
                    entity_type=_entity_type(asset.asset_type, content),
                    display_label=_content_label(
                        asset.asset_type, asset.canonical_key, content
                    ),
                    aliases=tuple(sorted(asset_aliases)),
                    description=_content_description(content),
                    domain=asset.domain,
                    source_type=SemanticSourceType.ENTERPRISE_KNOWLEDGE,
                    source_id=str(asset.id),
                    source_version=str(version.version_number),
                    source_checksum=version.checksum,
                    classification=SemanticDataClassification.TENANT_BUSINESS_METADATA,
                    valid_from=version.effective_from,
                    valid_to=version.effective_to,
                    related_canonical_ids=tuple(
                        sorted(str(item) for item in related if isinstance(item, str))
                    ),
                    unit=str(content.get("unit")) if content.get("unit") else None,
                    allowed_dimensions=tuple(
                        str(item) for item in content.get("allowed_dimensions", [])
                    ),
                )
            )
        manifest_checksum = checksum_for(
            [
                {
                    "asset_id": str(asset.id),
                    "version_id": str(version.id),
                    "version": version.version_number,
                    "checksum": version.checksum,
                }
                for asset, version in pairs
            ]
        )
        return SemanticSourceSnapshot(
            source_type=SemanticSourceType.ENTERPRISE_KNOWLEDGE,
            source_id="enterprise-knowledge-published",
            source_version=max(
                (str(version.version_number) for _, version in pairs),
                default="0",
            ),
            source_checksum=manifest_checksum,
            tenant_scoped=True,
            records=tuple(records),
        )


class MetricRegistrySemanticSourceProvider:
    async def load(
        self,
        *,
        tenant_id: uuid.UUID,
        at: datetime,
    ) -> SemanticSourceSnapshot:
        del at
        records: list[SemanticSourceRecord] = []
        for key, definition in sorted(METRIC_DEFINITIONS.items()):
            if not definition.supported:
                continue
            source_checksum = checksum_for(definition.to_payload())
            records.append(
                SemanticSourceRecord(
                    canonical_id=key,
                    document_type=SemanticDocumentType.METRIC,
                    entity_type=SemanticEntityType.METRIC,
                    display_label=definition.label,
                    aliases=(),
                    description=(
                        definition.notes[0]
                        if definition.notes
                        else f"Metrica oficial {definition.label}."
                    ),
                    domain="sales",
                    source_type=SemanticSourceType.METRIC_REGISTRY,
                    source_id=key,
                    source_version="2026-07-20-rb-devolucao-transferencias",
                    source_checksum=source_checksum,
                    classification=SemanticDataClassification.TENANT_BUSINESS_METADATA,
                    unit=None,
                )
            )
        return SemanticSourceSnapshot(
            source_type=SemanticSourceType.METRIC_REGISTRY,
            source_id="metric-registry",
            source_version="2026-07-20-rb-devolucao-transferencias",
            source_checksum=checksum_for(
                {
                    key: checksum_for(value.to_payload())
                    for key, value in sorted(METRIC_DEFINITIONS.items())
                }
            ),
            tenant_scoped=True,
            records=tuple(records),
        )


class SyntheticAnalyticalEntitySourceProvider:
    """Injected test/offline source. Runtime does not discover physical columns."""

    def __init__(
        self,
        *,
        source_id: str,
        source_version: str,
        records_by_tenant: dict[uuid.UUID, tuple[SemanticSourceRecord, ...]],
        watermark: str | None = None,
    ) -> None:
        self.source_id = source_id
        self.source_version = source_version
        self.records_by_tenant = records_by_tenant
        self.watermark = watermark

    async def load(
        self,
        *,
        tenant_id: uuid.UUID,
        at: datetime,
    ) -> SemanticSourceSnapshot:
        del at
        records = self.records_by_tenant.get(tenant_id, ())
        if any(record.source_type != SemanticSourceType.ANALYTICAL_ENTITY for record in records):
            raise ValueError("analytical entity provider returned an invalid source type")
        return SemanticSourceSnapshot(
            source_type=SemanticSourceType.ANALYTICAL_ENTITY,
            source_id=self.source_id,
            source_version=self.source_version,
            source_checksum=checksum_for(records),
            tenant_scoped=True,
            records=records,
            watermark=self.watermark,
        )
