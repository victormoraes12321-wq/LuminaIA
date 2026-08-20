from __future__ import annotations

import logging
import uuid
from typing import Any, Final

from sqlalchemy.ext.asyncio import AsyncSession

from services.svr_service import svr_service

logger = logging.getLogger("luminaai.services.corporate_abstraction_layer")


_DEFAULT_METRIC_MAPPINGS: Final[dict[str, str]] = {
    "MET_001": "receita_total",
    "MET_002": "faturamento_realizado",
    "MET_003": "lucro_bruto",
    "MET_004": "margem_lucro",
    "MET_005": "ticket_medio",
    "MET_006": "quantidade_pedidos",
    "MET_007": "custo_total",
    "MET_008": "atingimento_meta",
    "MET_009": "meta_mensal",
    "MET_010": "meta_valor",
    "MET_011": "atingimento",
    "MET_012": "comissao",
    "MET_013": "ranking",
    "MET_014": "taxa_conversao",
    "MET_015": "churn_rate",
    "MET_016": "ltv_estimado",
    "MET_017": "cac_estimado",
    "MET_018": "cliente_ativo",
}

_DEFAULT_DIMENSION_MAPPINGS: Final[dict[str, str]] = {
    "DIM_001": "cliente",
    "DIM_002": "vendedor",
    "DIM_003": "produto",
    "DIM_004": "categoria",
    "DIM_005": "regiao",
    "DIM_006": "mes",
    "DIM_007": "ano",
    "DIM_008": "forma_pagamento",
    "DIM_009": "status",
    "DIM_010": "cidade",
    "DIM_011": "estado",
}

_DEFAULT_PERIOD_LABELS: Final[dict[str, str]] = {
    "PER_TODAY": "hoje",
    "PER_YESTERDAY": "ontem",
    "PER_LAST_7_DAYS": "ultimos 7 dias",
    "PER_LAST_30_DAYS": "ultimos 30 dias",
    "PER_LAST_90_DAYS": "ultimos 90 dias",
    "PER_CURRENT_MONTH": "este mes",
    "PER_CURRENT_YEAR": "este ano",
    "PER_LAST_YEAR": "ano passado",
}


class CorporateAbstractionLayer:
    """
    Compatibility boundary that maps corporate concept IDs to execution-ready
    semantic keys. Physical storage details remain outside CSIE.
    """

    async def translate_plan_to_execution(
        self,
        stable_plan: dict[str, Any],
        tenant_id: uuid.UUID,
        db: AsyncSession | None = None,
        semantic_version: str | None = None,
        mapping_version: str | None = None,
        blueprint_version: str | None = None,
    ) -> dict[str, Any]:
        metrics = []
        for concept_id in stable_plan.get("metrics", []) or []:
            metrics.append(
                await self._resolve_concept_key(
                    concept_id=concept_id,
                    tenant_id=tenant_id,
                    db=db,
                    fallback_map=_DEFAULT_METRIC_MAPPINGS,
                    semantic_version=semantic_version,
                    mapping_version=mapping_version,
                    blueprint_version=blueprint_version,
                )
            )

        group_by = []
        for concept_id in stable_plan.get("dimensions", []) or []:
            group_by.append(
                await self._resolve_concept_key(
                    concept_id=concept_id,
                    tenant_id=tenant_id,
                    db=db,
                    fallback_map=_DEFAULT_DIMENSION_MAPPINGS,
                    semantic_version=semantic_version,
                    mapping_version=mapping_version,
                    blueprint_version=blueprint_version,
                )
            )

        filters = {}
        for concept_id, value in (stable_plan.get("filters", {}) or {}).items():
            key = await self._resolve_concept_key(
                concept_id=concept_id,
                tenant_id=tenant_id,
                db=db,
                fallback_map=_DEFAULT_DIMENSION_MAPPINGS,
                semantic_version=semantic_version,
                mapping_version=mapping_version,
                blueprint_version=blueprint_version,
            )
            filters[key] = value

        period_id = stable_plan.get("period")
        period_label = await self._resolve_period_label(
            period_id=period_id,
            tenant_id=tenant_id,
            db=db,
            semantic_version=semantic_version,
            mapping_version=mapping_version,
            blueprint_version=blueprint_version,
        )
        if period_label:
            from services.plan_validator import resolve_relative_date_range

            resolved_dates = resolve_relative_date_range(period_label)
            if resolved_dates:
                filters["date_range"] = f"{resolved_dates[0]} to {resolved_dates[1]}"

        return {
            "metrics": list(dict.fromkeys(item for item in metrics if item)),
            "group_by": list(dict.fromkeys(item for item in group_by if item)),
            "filters": filters,
        }

    async def _resolve_concept_key(
        self,
        concept_id: str,
        tenant_id: uuid.UUID,
        db: AsyncSession | None,
        fallback_map: dict[str, str],
        semantic_version: str | None = None,
        mapping_version: str | None = None,
        blueprint_version: str | None = None,
    ) -> str:
        if db:
            resolved = await svr_service.resolve_concept(
                db=db,
                tenant_id=tenant_id,
                concept_id=concept_id,
                semantic_version=semantic_version,
                mapping_version=mapping_version,
                blueprint_version=blueprint_version,
            )
            if resolved:
                return str(
                    resolved.get("name")
                    or resolved.get("semantic_key")
                    or resolved.get("physical_col")
                    or fallback_map.get(concept_id)
                    or concept_id
                )
        return fallback_map.get(concept_id, concept_id)

    async def _resolve_period_label(
        self,
        period_id: str | None,
        tenant_id: uuid.UUID,
        db: AsyncSession | None,
        semantic_version: str | None = None,
        mapping_version: str | None = None,
        blueprint_version: str | None = None,
    ) -> str | None:
        if not period_id:
            return None
        if db:
            resolved = await svr_service.resolve_concept(
                db=db,
                tenant_id=tenant_id,
                concept_id=period_id,
                semantic_version=semantic_version,
                mapping_version=mapping_version,
                blueprint_version=blueprint_version,
            )
            if resolved:
                return str(resolved.get("label") or resolved.get("name") or _DEFAULT_PERIOD_LABELS.get(period_id))
        return _DEFAULT_PERIOD_LABELS.get(period_id)


corporate_abstraction_layer = CorporateAbstractionLayer()
