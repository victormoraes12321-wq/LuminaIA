"""Deterministic planning and authority-bridged dashboard runtime."""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Protocol, cast

from pydantic import JsonValue, TypeAdapter

from sqlalchemy.ext.asyncio import AsyncSession

from contracts.dashboard_backend_v2 import (
    DashboardCacheIndicatorV2,
    DashboardEffectiveFilterV2,
    DashboardRuntimePlanV2,
    DashboardRuntimeProvenanceV2,
    DashboardRuntimeRequestV2,
    DashboardRuntimeResultV2,
    DashboardRuntimeStatusV2,
    DashboardRuntimeWarningV2,
    DashboardScalarDataV2,
    DashboardTabularCellV2,
    DashboardTabularDataV2,
    DashboardTabularRowV2,
    DashboardTypedDataV2,
    DashboardWidgetResultStatusV2,
    DashboardWidgetRuntimePlanV2,
    DashboardWidgetRuntimeResultV2,
)
from contracts.dashboard_blueprint_v2 import DashboardBlueprintV2
from contracts.safe_analytical_postgresql_v2 import AnalyticalQueryBudgetV2, AnalyticalQuerySpecV2
from contracts.safe_analytical_postgresql_v2 import (
    AnalyticalDimensionSelectV2,
    AnalyticalFilterExpressionV2,
    AnalyticalFilterGroupV2,
    AnalyticalFilterOperatorV2,
    AnalyticalMetricSelectV2,
    AnalyticalPaginationV2,
)
from contracts.validation_provenance_v2 import ValidationContextV2, ValidationRequestV2
from models.dashboard_backend_v2 import DashboardPublicationModelV2, DashboardRevisionModelV2
from services.safe_analytical_postgresql.execution_service import SafeAnalyticalPostgreSQLService
from services.validation_provenance.pipeline import GovernedValidationPipeline

from .application import DashboardActorContextV2, DashboardAuditServiceV2, _blueprint_from_json, resolve_resource_capabilities
from .errors import DashboardBackendError
from .integrity import checksum
from .policy import DashboardAccessPolicyServiceV2
from .repositories import DashboardAccessRepositoryV2, DashboardAuditRepositoryV2, DashboardPublicationRepositoryV2, DashboardRepositoryV2, DashboardRevisionRepositoryV2, DashboardRuntimeRepositoryV2


def _canonical_value(value: str | int | Decimal | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return format(value, "f")
    normalized = str(value).strip()
    if isinstance(value, str) and (
        any(token in normalized for token in (";", "--", "/*", "*/", "\x00"))
        or re.search(r"\b(?:select\s+.+\s+from|drop\s+table|insert\s+into|delete\s+from|update\s+.+\s+set)\b", normalized, re.IGNORECASE)
    ):
        raise DashboardBackendError("DASHBOARD_FILTER_INVALID", "Conteúdo de filtro não permitido.", 422)
    return normalized


def _validate_filter(filter_definition: object, values: tuple[str | int | Decimal | bool, ...]) -> tuple[str, ...]:
    if len(values) > filter_definition.maximum_selections:
        raise DashboardBackendError("DASHBOARD_FILTER_INVALID", "Filtro excede maximum_selections.", 422)
    filter_type = filter_definition.filter_type
    if filter_type == "BOOLEAN" and (len(values) != 1 or not isinstance(values[0], bool)):
        raise DashboardBackendError("DASHBOARD_FILTER_INVALID", "Filtro booleano exige bool.", 422)
    if filter_type == "NUMBER_RANGE" and (len(values) != 2 or any(isinstance(value, (str, bool)) for value in values)):
        raise DashboardBackendError("DASHBOARD_FILTER_INVALID", "Range numérico exige dois números.", 422)
    if filter_type == "RELATIVE_PERIOD" and any(str(value) not in filter_definition.allowed_period_ids for value in values):
        raise DashboardBackendError("DASHBOARD_FILTER_INVALID", "Período relativo não autorizado.", 422)
    if filter_type == "STATUS_SELECT" and any(str(value) not in filter_definition.allowed_status_ids for value in values):
        raise DashboardBackendError("DASHBOARD_FILTER_INVALID", "Status não autorizado.", 422)
    if filter_type == "SEARCH":
        if len(values) != 1 or not isinstance(values[0], str) or not filter_definition.minimum_query_length <= len(values[0]) <= filter_definition.maximum_query_length:
            raise DashboardBackendError("DASHBOARD_FILTER_INVALID", "Texto de busca fora dos limites.", 422)
    return tuple(_canonical_value(value) for value in values)


class DashboardRuntimePlanningServiceV2:
    MAXIMUM_WIDGETS = 64
    MAXIMUM_RESULT_SIZE = 100_000

    def plan(
        self,
        *, actor: DashboardActorContextV2, publication: DashboardPublicationModelV2,
        revision: DashboardRevisionModelV2, blueprint: DashboardBlueprintV2,
        request: DashboardRuntimeRequestV2,
    ) -> DashboardRuntimePlanV2:
        if request.publication_id is not None and request.publication_id != str(publication.id):
            raise DashboardBackendError("DASHBOARD_PUBLICATION_CONFLICT", "Publicação solicitada não é a ativa.", 409)
        if request.blueprint_checksum is not None and request.blueprint_checksum != revision.blueprint_checksum:
            raise DashboardBackendError("DASHBOARD_REVISION_STALE", "Checksum do runtime está obsoleto.", 409)
        filter_map = {item.filter_id: item for item in blueprint.filters}
        supplied = {item.filter_id: item for item in request.filters}
        if len(supplied) != len(request.filters) or set(supplied) - set(filter_map):
            raise DashboardBackendError("DASHBOARD_FILTER_INVALID", "Filtro desconhecido ou duplicado.", 422)
        effective_filters: list[DashboardEffectiveFilterV2] = []
        for filter_id, definition in filter_map.items():
            selected = supplied.get(filter_id)
            if selected is not None:
                values = _validate_filter(definition, selected.values)
            elif definition.default.mode == "EXPLICIT":
                values = tuple(_canonical_value(cast(object, value)) for value in definition.default.canonical_values)
            elif definition.required:
                raise DashboardBackendError("DASHBOARD_FILTER_INVALID", f"Filtro obrigatório ausente: {filter_id}.", 422)
            else:
                continue
            effective_filters.append(DashboardEffectiveFilterV2(filter_id=filter_id, canonical_target_id=definition.canonical_target_id, canonical_values=values))

        interaction_map = {item.interaction_id: item for item in blueprint.interactions if item.enabled}
        action_map = {
            "CROSS_FILTER": "CROSS_FILTER", "DRILLDOWN": "DRILLDOWN", "RESET": "RESET_FILTERS",
            "SORTING": "SORT", "PAGINATION": "PAGINATE", "PROVENANCE": "OPEN_PROVENANCE",
            "EXPAND": "EXPAND_WIDGET",
        }
        for request_interaction in request.interactions:
            declared = interaction_map.get(request_interaction.interaction_id)
            if declared is None or declared.source_widget_id != request_interaction.source_widget_id or declared.interaction_type != action_map[request_interaction.action]:
                raise DashboardBackendError("DASHBOARD_INTERACTION_INVALID", "Interação não declarada no blueprint publicado.", 422)
            if request_interaction.target_widget_id is not None:
                targets = getattr(declared, "target_widget_ids", ())
                if request_interaction.target_widget_id not in targets:
                    raise DashboardBackendError("DASHBOARD_INTERACTION_INVALID", "Target da interação não autorizado.", 422)

        widget_map = {item.identity.widget_id: item for item in blueprint.widgets}
        requested_ids = request.requested_widget_ids or tuple(widget_map)
        if len(set(requested_ids)) != len(requested_ids) or not set(requested_ids).issubset(widget_map):
            raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Widget solicitado não existe.", 422)
        binding_map = {item.binding_id: item for item in blueprint.data_bindings}
        permission_scope = checksum({"role": actor.global_role, "user": actor.user_id})
        classification_rank = {
            "PUBLIC_METADATA": 0, "TENANT_METADATA": 1,
            "TENANT_BUSINESS_DATA": 2, "RESTRICTED_BUSINESS_DATA": 3,
            "PERSONAL_DATA": 4, "SENSITIVE_PERSONAL_DATA": 5,
        }
        widget_plans: list[DashboardWidgetRuntimePlanV2] = []
        for widget_id in requested_ids:
            widget = widget_map[widget_id]
            binding_id = getattr(widget, "binding_id", None)
            if not binding_id:
                continue
            binding = binding_map[binding_id]
            effective_classification = max(
                (blueprint.governance.classification.value, binding.classification.value),
                key=classification_rank.__getitem__,
            )
            entities = tuple(entity_id for entity in binding.entities for entity_id in entity.canonical_entity_ids)
            period = binding.period.model_dump(mode="json")
            comparison = binding.comparison.model_dump(mode="json") if binding.comparison else None
            filters_for_binding = tuple(item for item in effective_filters if item.filter_id in {entry.filter_id for entry in binding.filters})
            group_basis = {
                "binding": binding.model_dump(mode="json"), "filters": filters_for_binding,
                "permission": permission_scope, "classification": effective_classification,
                "freshness": binding.freshness.value,
            }
            execution_group = f"group.{checksum(group_basis)[:24]}"
            analytical_cache_fingerprint = checksum({
                "semantic_checksum": revision.semantic_checksum,
                "group": group_basis,
            })
            basis = {
                "widget_id": widget_id, "publication": str(publication.id), "revision": str(revision.id),
                "binding": group_basis, "semantic_checksum": revision.semantic_checksum,
            }
            widget_plans.append(DashboardWidgetRuntimePlanV2(
                widget_id=widget_id, binding_id=binding_id, analytical_dataset_id=binding.analytical_dataset_id, widget_type=widget.widget_type,
                expected_result_shape=binding.expected_result_shape.value,
                metric_ids=tuple(metric.metric_id for metric in binding.metrics),
                dimension_ids=tuple(dimension.dimension_id for dimension in binding.dimensions),
                entity_ids=entities, canonical_period=period, comparison=comparison,
                effective_filters=filters_for_binding, completeness=binding.completeness.value,
                freshness=binding.freshness.value, classification_ceiling=effective_classification,
                permission_scope=permission_scope, cache_preference=binding.cache_preference.value,
                materialization_preference=binding.materialization_preference.value,
                execution_group=execution_group, analytical_cache_fingerprint=analytical_cache_fingerprint,
                plan_checksum=checksum(basis),
            ))
        plan_basis = {
            "dashboard": str(publication.dashboard_id), "publication": str(publication.id),
            "revision": str(revision.id), "blueprint_checksum": revision.blueprint_checksum,
            "tenant": actor.tenant_id, "access": permission_scope,
            "filters": effective_filters, "widget_plans": widget_plans,
        }
        groups = tuple(dict.fromkeys(item.execution_group for item in widget_plans))
        return DashboardRuntimePlanV2(
            dashboard_id=str(publication.dashboard_id), publication_id=str(publication.id), revision_id=str(revision.id),
            blueprint_checksum=revision.blueprint_checksum, tenant_reference=actor.tenant_id,
            user_access_scope=permission_scope, effective_filters=tuple(effective_filters), effective_period=None,
            widget_plans=tuple(widget_plans), execution_groups=groups,
            cache_decisions=tuple(f"{item.widget_id}:BACKEND_DECIDES" for item in widget_plans),
            dependencies=tuple(sorted({metric for item in widget_plans for metric in item.metric_ids})),
            deadline_at=datetime.now(timezone.utc) + timedelta(milliseconds=request.deadline_ms),
            maximum_widgets=self.MAXIMUM_WIDGETS, maximum_result_size=self.MAXIMUM_RESULT_SIZE,
            provenance_required=True, plan_checksum=checksum(plan_basis),
        )


@dataclass(frozen=True, slots=True)
class ResolvedWidgetQueryV2:
    spec: AnalyticalQuerySpecV2
    metric_fingerprints: tuple[str, ...]
    analytical_catalog_version: str
    source_sync_version: str
    source_watermark: str
    tenant_proof: dict[str, object]
    materialization_definition_id: str | None = None


class DashboardWidgetQueryResolverV2(Protocol):
    """MetricRegistry/catalog authority resolves canonical plan IDs to an existing query spec."""
    async def resolve(self, *, actor: DashboardActorContextV2, plan: DashboardWidgetRuntimePlanV2) -> ResolvedWidgetQueryV2: ...


class GovernedCatalogWidgetQueryResolverV2:
    """Resolve against Safe PostgreSQL's governed catalog; compilation stays in that authority."""
    def __init__(self, safe_service: SafeAnalyticalPostgreSQLService | None = None):
        self.safe_service = safe_service or SafeAnalyticalPostgreSQLService()

    async def resolve(self, *, actor: DashboardActorContextV2, plan: DashboardWidgetRuntimePlanV2) -> ResolvedWidgetQueryV2:
        snapshot = self.safe_service.get_catalog_snapshot()
        dataset = snapshot.datasets.get(plan.analytical_dataset_id)
        if dataset is None:
            raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Dataset canônico não publicado no catálogo analítico.", 503)
        missing_metrics = set(plan.metric_ids) - set(dataset.metric_bindings)
        missing_dimensions = set(plan.dimension_ids) - set(dataset.dimension_bindings)
        filter_dimensions = {item.canonical_target_id for item in plan.effective_filters}
        if missing_metrics or missing_dimensions or not filter_dimensions.issubset(dataset.dimension_bindings):
            raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Binding não resolvido pelas autoridades governadas.", 503)
        period = cast(dict[str, object], plan.canonical_period)
        start: str | None = None
        end: str | None = None
        if period.get("period_type") == "FIXED":
            start, end = str(period["start_date"]), str(period["end_date"])
        elif period.get("period_type") not in {"INHERITED_DASHBOARD", "FILTER_DRIVEN"}:
            raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Período requer autoridade temporal explícita.", 503)
        expected_shape = {
            "SCALAR": "SCALAR", "COMPARISON": "TABLE", "TIME_SERIES": "SERIES",
            "GROUPED_SERIES": "SERIES", "RANKING": "RANKING", "TABLE": "TABLE",
            "STATUS_SUMMARY": "TABLE", "FACT_SET": "TABLE",
        }[plan.expected_result_shape]
        spec = AnalyticalQuerySpecV2(
            spec_id=f"dashboard.{plan.plan_checksum[:48]}", dataset_id=plan.analytical_dataset_id,
            metrics=[AnalyticalMetricSelectV2(metric_id=item) for item in plan.metric_ids],
            dimensions=[AnalyticalDimensionSelectV2(dimension_id=item) for item in plan.dimension_ids],
            group_by_dimensions=list(plan.dimension_ids),
            filter_group=AnalyticalFilterGroupV2(
                expressions=[AnalyticalFilterExpressionV2(dimension_id=item.canonical_target_id, operator=AnalyticalFilterOperatorV2.IN, values=list(item.canonical_values)) for item in plan.effective_filters]
            ) if plan.effective_filters else None,
            pagination=AnalyticalPaginationV2(limit=500), time_window_start=start, time_window_end=end,
            expected_shape=expected_shape,
        )
        return ResolvedWidgetQueryV2(
            spec=spec,
            metric_fingerprints=tuple(dataset.metric_bindings[item].formula_fingerprint for item in plan.metric_ids),
            analytical_catalog_version=snapshot.catalog_version,
            source_sync_version=dataset.version, source_watermark="catalog-authority",
            tenant_proof={"tenant_id": actor.tenant_id, "strategy": dataset.tenant_strategy.value, "proof_id": checksum({"tenant": actor.tenant_id, "dataset": dataset.canonical_dataset_id})},
        )


@dataclass(frozen=True, slots=True)
class CertifiedWidgetPayloadV2:
    data: DashboardTypedDataV2
    fact_references: tuple[str, ...]
    certification_reference: str
    source_freshness: str
    warnings: tuple[str, ...]
    cache_indicator: DashboardCacheIndicatorV2 = DashboardCacheIndicatorV2.MISS


class DashboardWidgetAuthorityV2(Protocol):
    async def execute(self, *, actor: DashboardActorContextV2, plan: DashboardWidgetRuntimePlanV2) -> CertifiedWidgetPayloadV2: ...


def _typed_data(result: object, expected_shape: str) -> DashboardTypedDataV2:
    rows = result.rows
    if expected_shape == "SCALAR" and rows:
        first = next(iter(rows[0].values.values()), None)
        if isinstance(first, Decimal):
            return DashboardScalarDataV2(value=first, unit="registry-defined")
        if isinstance(first, int) and not isinstance(first, bool):
            return DashboardScalarDataV2(value=Decimal(first), unit="registry-defined")
    typed_rows: list[DashboardTabularRowV2] = []
    for row in rows:
        cells: list[DashboardTabularCellV2] = []
        for key, value in row.values.items():
            if isinstance(value, Decimal):
                cells.append(DashboardTabularCellV2(column_id=key, decimal_value=value))
            elif isinstance(value, int) and not isinstance(value, bool):
                cells.append(DashboardTabularCellV2(column_id=key, decimal_value=Decimal(value)))
            else:
                cells.append(DashboardTabularCellV2(column_id=key, text_value="" if value is None else str(value)))
        typed_rows.append(DashboardTabularRowV2(cells=tuple(cells)))
    return DashboardTabularDataV2(rows=tuple(typed_rows))


class ExistingAnalyticalAuthoritiesWidgetExecutorV2:
    """Bridge; it delegates SQL compilation/execution and certification to existing authorities."""
    def __init__(self, resolver: DashboardWidgetQueryResolverV2, *, safe_service: SafeAnalyticalPostgreSQLService | None = None, validation_pipeline: GovernedValidationPipeline | None = None, smart_cache_pipeline: object | None = None, materialization_enabled: bool = False):
        self.resolver = resolver
        self.safe_service = safe_service or SafeAnalyticalPostgreSQLService()
        self.validation_pipeline = validation_pipeline or GovernedValidationPipeline()
        self.smart_cache_pipeline = smart_cache_pipeline
        self.materialization_enabled = materialization_enabled

    async def execute(self, *, actor: DashboardActorContextV2, plan: DashboardWidgetRuntimePlanV2) -> CertifiedWidgetPayloadV2:
        resolved = await self.resolver.resolve(actor=actor, plan=plan)
        cached = await self._lookup_cache(actor=actor, plan=plan, resolved=resolved)
        if cached is not None:
            return cached
        budget = AnalyticalQueryBudgetV2(maximum_rows=500, maximum_result_bytes=5_000_000, maximum_timeout_seconds=10.0)
        analytical_result = await self.safe_service.execute_query(resolved.spec, tenant_id=actor.tenant_id, user_id=actor.user_id, budget=budget)
        if analytical_result.error is not None or not analytical_result.validation.is_valid:
            raise DashboardBackendError("DASHBOARD_WIDGET_EXECUTION_FAILED", "A autoridade analítica rejeitou o resultado.", 503)
        certification = await self.validation_pipeline.execute(ValidationRequestV2(
            context=ValidationContextV2(tenant_id=uuid.UUID(actor.tenant_id), user_id=uuid.UUID(actor.user_id), roles=[actor.global_role], permissions=[], request_id=plan.plan_checksum),
            result_payload={"query_fingerprint": plan.plan_checksum, "rows": analytical_result.model_dump(mode="json")["rows"], "statistics": analytical_result.statistics.model_dump(mode="json")},
            tenant_proof=resolved.tenant_proof,
        ))
        if certification.overall_status.value not in {"VALID", "VALID_WITH_WARNINGS", "PARTIAL"}:
            raise DashboardBackendError("DASHBOARD_CERTIFICATION_INVALID", "Resultado sem certificação válida.", 503)
        payload = CertifiedWidgetPayloadV2(
            data=_typed_data(analytical_result, plan.expected_result_shape),
            fact_references=tuple(str(fact.fact_id) for fact in certification.facts),
            certification_reference=str(certification.certification_id), source_freshness=resolved.source_watermark,
            warnings=tuple(certification.warnings),
        )
        await self._write_cache(actor=actor, plan=plan, resolved=resolved, payload=payload)
        return payload

    async def _lookup_cache(self, *, actor: DashboardActorContextV2, plan: DashboardWidgetRuntimePlanV2, resolved: ResolvedWidgetQueryV2) -> CertifiedWidgetPayloadV2 | None:
        if self.smart_cache_pipeline is None or plan.cache_preference == "BYPASS":
            return None
        from contracts.smart_cache_materialization_v2 import CacheDecision, CacheScopeV2
        scope = CacheScopeV2(tenant_id=actor.tenant_id, user_id=actor.user_id, role=actor.global_role, permission_fingerprint=plan.permission_scope, classification_ceiling=plan.classification_ceiling)
        lookup = await self.smart_cache_pipeline.lookup_certified_analytical_result(
            scope=scope, canonical_query_fingerprint=plan.analytical_cache_fingerprint,
            analytical_catalog_version=resolved.analytical_catalog_version,
            metric_fingerprints=list(resolved.metric_fingerprints),
            filter_structure_fingerprint=checksum(plan.effective_filters),
            canonical_period_fingerprint=checksum(plan.canonical_period),
            source_sync_version=resolved.source_sync_version, source_watermark=resolved.source_watermark,
        )
        if lookup.decision is not CacheDecision.HIT or lookup.entry is None or not lookup.entry.verify_checksum():
            if self.materialization_enabled and resolved.materialization_definition_id:
                snapshot = await self.smart_cache_pipeline.mat_repo.get_published_snapshot(actor.tenant_id, resolved.materialization_definition_id)
                if snapshot is not None and snapshot.freshness == "FRESH" and snapshot.certification_status == "VALID" and checksum(snapshot.payload_json) == snapshot.payload_checksum:
                    return self._payload_from_json(snapshot.payload_json, DashboardCacheIndicatorV2.MATERIALIZATION_HIT)
            return None
        return self._payload_from_json(lookup.entry.payload_ref.payload_data, DashboardCacheIndicatorV2.HIT)

    @staticmethod
    def _payload_from_json(payload: dict[str, object], indicator: DashboardCacheIndicatorV2) -> CertifiedWidgetPayloadV2:
        try:
            data = TypeAdapter(DashboardTypedDataV2).validate_json(json.dumps(payload["data"], ensure_ascii=False))
            return CertifiedWidgetPayloadV2(
                data=data, fact_references=tuple(cast(list[str], payload.get("fact_references", []))),
                certification_reference=str(payload["certification_reference"]),
                source_freshness=str(payload["source_freshness"]),
                warnings=tuple(cast(list[str], payload.get("warnings", []))), cache_indicator=indicator,
            )
        except (KeyError, TypeError, ValueError):
            raise DashboardBackendError("DASHBOARD_CERTIFICATION_INVALID", "Payload de cache certificado inválido.", 503)

    async def _write_cache(self, *, actor: DashboardActorContextV2, plan: DashboardWidgetRuntimePlanV2, resolved: ResolvedWidgetQueryV2, payload: CertifiedWidgetPayloadV2) -> None:
        if self.smart_cache_pipeline is None or plan.cache_preference == "BYPASS":
            return
        from contracts.smart_cache_materialization_v2 import (
            CacheEligibilityRequestV2, CacheScopeV2, CacheType, CertificationStatus,
            DataClassification, FreshnessStatus,
        )
        serialized = cast(dict[str, JsonValue], json.loads(json.dumps({
            "data": payload.data.model_dump(mode="json"), "fact_references": payload.fact_references,
            "certification_reference": payload.certification_reference,
            "source_freshness": payload.source_freshness, "warnings": payload.warnings,
        }, ensure_ascii=False)))
        has_pii = plan.classification_ceiling in {"PERSONAL_DATA", "SENSITIVE_PERSONAL_DATA"}
        scope = CacheScopeV2(tenant_id=actor.tenant_id, user_id=actor.user_id, role=actor.global_role, permission_fingerprint=plan.permission_scope, classification_ceiling=plan.classification_ceiling)
        await self.smart_cache_pipeline.write_certified_analytical_result(
            scope=scope, canonical_query_fingerprint=plan.analytical_cache_fingerprint,
            analytical_catalog_version=resolved.analytical_catalog_version,
            metric_fingerprints=list(resolved.metric_fingerprints), payload=serialized,
            certification_id=payload.certification_reference, tenant_proof_id=str(resolved.tenant_proof.get("proof_id", checksum(resolved.tenant_proof))),
            eligibility=CacheEligibilityRequestV2(
                cache_type=CacheType.CERTIFIED_ANALYTICAL_RESULT, certification_status=CertificationStatus.VALID,
                tenant_proof_valid=True, query_fingerprint_valid=True, result_checksum_valid=True,
                metric_fingerprints_valid=bool(resolved.metric_fingerprints), source_freshness=FreshnessStatus.FRESH,
                is_complete=True, has_pii=has_pii, is_row_level=plan.expected_result_shape in {"TABLE", "FACT_SET"},
                data_classification=DataClassification.CONFIDENTIAL if plan.classification_ceiling != "PUBLIC_METADATA" else DataClassification.PUBLIC,
                payload_size_bytes=len(json.dumps(serialized, ensure_ascii=False).encode("utf-8")),
            ),
            source_sync_version=resolved.source_sync_version, source_watermark=resolved.source_watermark,
            dependency_tags=[f"dashboard-semantic:{plan.analytical_cache_fingerprint}", *[f"metric:{item}" for item in plan.metric_ids]],
        )


class DashboardWidgetExecutionServiceV2:
    def __init__(self, authority: DashboardWidgetAuthorityV2):
        self.authority = authority

    async def execute(self, *, actor: DashboardActorContextV2, publication: DashboardPublicationModelV2, revision: DashboardRevisionModelV2, plan: DashboardWidgetRuntimePlanV2) -> DashboardWidgetRuntimeResultV2:
        generated = datetime.now(timezone.utc)
        payload = await self.authority.execute(actor=actor, plan=plan)
        warning_contracts = tuple(DashboardRuntimeWarningV2(code="AUTHORITY_WARNING", message=warning[:500], severity="WARNING", widget_id=plan.widget_id) for warning in payload.warnings)
        provenance = DashboardRuntimeProvenanceV2(
            publication_id=str(publication.id), blueprint_version=revision.blueprint_version, revision_id=str(revision.id),
            binding_id=plan.binding_id, effective_filters=plan.effective_filters,
            period_summary=checksum(plan.canonical_period)[:24], metric_definition_references=plan.metric_ids,
            validation_status="PARTIAL" if warning_contracts else "CERTIFIED",
            source_freshness=payload.source_freshness, cache_indicator=payload.cache_indicator,
            warnings=warning_contracts,
        )
        basis = {"plan": plan.plan_checksum, "data": payload.data, "certification": payload.certification_reference}
        return DashboardWidgetRuntimeResultV2(
            widget_id=plan.widget_id, binding_id=plan.binding_id, status=DashboardWidgetResultStatusV2.COMPLETE,
            expected_result_shape=plan.expected_result_shape, data=payload.data,
            fact_references=payload.fact_references, certification_reference=payload.certification_reference,
            provenance=provenance, completeness=plan.completeness, freshness=plan.freshness,
            truncated=False, partial=False, warnings=warning_contracts, cache_indicator=payload.cache_indicator,
            generated_at=generated, checksum=checksum(basis),
        )


class DashboardRuntimeExecutionServiceV2:
    def __init__(self, session: AsyncSession, authority: DashboardWidgetAuthorityV2):
        self.publications = DashboardPublicationRepositoryV2(session)
        self.revisions = DashboardRevisionRepositoryV2(session)
        self.dashboards = DashboardRepositoryV2(session)
        self.access = DashboardAccessRepositoryV2(session)
        self.runtime_repository = DashboardRuntimeRepositoryV2(session)
        self.audit = DashboardAuditServiceV2(DashboardAuditRepositoryV2(session))
        self.planning = DashboardRuntimePlanningServiceV2()
        self.widgets = DashboardWidgetExecutionServiceV2(authority)

    async def load_and_plan(self, *, actor: DashboardActorContextV2, dashboard_id: str, request: DashboardRuntimeRequestV2) -> tuple[DashboardRuntimePlanV2, DashboardPublicationModelV2, DashboardRevisionModelV2]:
        dashboard = await self.dashboards.get(actor.tenant_id, dashboard_id)
        if dashboard.lifecycle != "PUBLISHED":
            raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Somente dashboard publicado pode executar.", 409)
        capabilities = await resolve_resource_capabilities(
            self.access, actor=actor, dashboard=dashboard,
        )
        from contracts.dashboard_backend_v2 import DashboardCapabilityBackendV2
        if DashboardCapabilityBackendV2.EXECUTE not in capabilities:
            raise DashboardBackendError("DASHBOARD_NOT_FOUND", "Dashboard não encontrado.", 404)
        policy = await self.access.get_policy(actor.tenant_id, dashboard_id)
        role_rank = {"CONSULTA": 0, "GESTOR": 1, "ADMIN": 2}
        if role_rank.get(actor.global_role, -1) < role_rank[policy.minimum_role]:
            raise DashboardBackendError("DASHBOARD_NOT_FOUND", "Dashboard não encontrado.", 404)
        classification_rank = {"PUBLIC_METADATA": 0, "TENANT_METADATA": 1, "TENANT_BUSINESS_DATA": 2, "RESTRICTED_BUSINESS_DATA": 3, "PERSONAL_DATA": 4, "SENSITIVE_PERSONAL_DATA": 5}
        user_ceiling = {"CONSULTA": 2, "GESTOR": 3, "ADMIN": 5}.get(actor.global_role, -1)
        if classification_rank[dashboard.classification] > user_ceiling or classification_rank[dashboard.classification] > classification_rank[policy.classification_ceiling]:
            raise DashboardBackendError("DASHBOARD_CLASSIFICATION_BLOCKED", "Classificação acima do teto autorizado.", 403)
        active = await self.publications.active(actor.tenant_id, dashboard_id)
        if active is None:
            raise DashboardBackendError("DASHBOARD_PUBLICATION_NOT_FOUND", "Dashboard sem publicação ativa.", 404)
        _, publication = active
        revision = await self.revisions.get(actor.tenant_id, dashboard_id, str(publication.revision_id))
        blueprint = _blueprint_from_json(revision.blueprint_json)
        if role_rank.get(actor.global_role, -1) < role_rank[blueprint.audience.minimum_role]:
            raise DashboardBackendError("DASHBOARD_NOT_FOUND", "Dashboard não encontrado.", 404)
        return self.planning.plan(actor=actor, publication=publication, revision=revision, blueprint=blueprint, request=request), publication, revision

    async def execute(self, *, actor: DashboardActorContextV2, dashboard_id: str, request: DashboardRuntimeRequestV2, idempotency_key: str) -> DashboardRuntimeResultV2:
        plan, publication, revision = await self.load_and_plan(actor=actor, dashboard_id=dashboard_id, request=request)
        from .integrity import idempotency_fingerprint
        scope, request_checksum = idempotency_fingerprint(tenant_id=actor.tenant_id, user_id=actor.user_id, operation="RUNTIME_EXECUTE", resource_id=dashboard_id, key=idempotency_key, payload=request)
        execution = await self.runtime_repository.create_execution(id=uuid.uuid4(), dashboard_id=uuid.UUID(dashboard_id), tenant_id=uuid.UUID(actor.tenant_id), publication_id=publication.id, user_id=uuid.UUID(actor.user_id), plan_checksum=plan.plan_checksum, status="STARTED", widget_count=len(plan.widget_plans), completed_widget_count=0, failed_widget_count=0, warnings_count=0, idempotency_scope=scope, request_checksum=request_checksum)
        replayed_execution = execution.status != "STARTED"
        if not replayed_execution:
            await self.audit.append(
                actor=actor, dashboard_id=dashboard_id,
                event_type="DASHBOARD_RUNTIME_STARTED",
                resource_reference=str(execution.id),
                metadata={"widget_count": len(plan.widget_plans)},
            )
        started = execution.started_at
        results: list[DashboardWidgetRuntimeResultV2] = []
        group_results: dict[str, DashboardWidgetRuntimeResultV2] = {}
        warnings: list[DashboardRuntimeWarningV2] = []
        failed = 0
        for widget_plan in plan.widget_plans:
            try:
                shared = group_results.get(widget_plan.execution_group)
                if shared is None:
                    result = await self.widgets.execute(actor=actor, publication=publication, revision=revision, plan=widget_plan)
                    group_results[widget_plan.execution_group] = result
                else:
                    shared_provenance = shared.provenance.model_copy(update={"binding_id": widget_plan.binding_id})
                    result = shared.model_copy(update={
                        "widget_id": widget_plan.widget_id, "binding_id": widget_plan.binding_id,
                        "expected_result_shape": widget_plan.expected_result_shape,
                        "provenance": shared_provenance,
                        "checksum": checksum({"shared": shared.checksum, "widget": widget_plan.widget_id}),
                    })
                results.append(result)
                if not replayed_execution:
                    await self.runtime_repository.record_widget(id=uuid.uuid4(), execution_id=execution.id, dashboard_id=execution.dashboard_id, tenant_id=execution.tenant_id, widget_id=widget_plan.widget_id, binding_id=widget_plan.binding_id, plan_checksum=widget_plan.plan_checksum, status="COMPLETE", cache_indicator=result.cache_indicator.value, certification_reference=result.certification_reference, result_checksum=result.checksum, warning_count=len(result.warnings))
            except DashboardBackendError:
                failed += 1
                warnings.append(DashboardRuntimeWarningV2(code="WIDGET_UNAVAILABLE", message="Widget indisponível; nenhum valor foi sintetizado.", severity="CRITICAL", widget_id=widget_plan.widget_id))
                if not request.allow_partial:
                    break
        status = DashboardRuntimeStatusV2.COMPLETE if failed == 0 else (DashboardRuntimeStatusV2.PARTIAL if results and request.allow_partial else DashboardRuntimeStatusV2.UNAVAILABLE)
        completed = datetime.now(timezone.utc)
        cache_indicator = results[0].cache_indicator if results else DashboardCacheIndicatorV2.BYPASS
        provenance = DashboardRuntimeProvenanceV2(publication_id=str(publication.id), blueprint_version=revision.blueprint_version, revision_id=str(revision.id), effective_filters=plan.effective_filters, validation_status="CERTIFIED" if status is DashboardRuntimeStatusV2.COMPLETE else "PARTIAL", source_freshness="per-widget", cache_indicator=cache_indicator, warnings=tuple(warnings))
        basis = {"execution": str(execution.id), "status": status.value, "widgets": [item.checksum for item in results], "warnings": warnings}
        result_checksum = checksum(basis)
        if not replayed_execution:
            await self.runtime_repository.complete_execution(actor.tenant_id, str(execution.id), status=status.value, completed_widget_count=len(results), failed_widget_count=failed, warnings_count=len(warnings), result_checksum=result_checksum)
            event_type = {
                DashboardRuntimeStatusV2.COMPLETE: "DASHBOARD_RUNTIME_COMPLETED",
                DashboardRuntimeStatusV2.PARTIAL: "DASHBOARD_RUNTIME_PARTIAL",
                DashboardRuntimeStatusV2.UNAVAILABLE: "DASHBOARD_RUNTIME_FAILED",
                DashboardRuntimeStatusV2.BLOCKED: "DASHBOARD_RUNTIME_FAILED",
            }[status]
            await self.audit.append(
                actor=actor, dashboard_id=dashboard_id, event_type=event_type,
                resource_reference=str(execution.id),
                outcome="SUCCESS" if status is DashboardRuntimeStatusV2.COMPLETE else "FAILED",
                metadata={
                    "completed_widget_count": len(results),
                    "failed_widget_count": failed,
                    "warnings_count": len(warnings),
                },
            )
        return DashboardRuntimeResultV2(execution_id=str(execution.id), dashboard_id=dashboard_id, publication_id=str(publication.id), status=status, widgets=tuple(results), provenance=provenance, warnings=tuple(warnings), started_at=started, completed_at=completed, checksum=result_checksum)
