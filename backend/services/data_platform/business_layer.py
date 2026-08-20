"""
LuminaAI — Business Layer Bridge
---------------------------------
Refatorado para atuar como ponte de compatibilidade retroativa para a Business Layer.
Encaminha as solicitações de validação e padronização para o Business Knowledge Engine (BKE).
"""
from __future__ import annotations

import importlib
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.business.synonym_cache import _SYNONYM_CACHE, _SYNONYM_CACHE_TENANT

logger = logging.getLogger("luminaai.data_platform.business_layer")
def _get_metric_info(metric: str) -> dict[str, Any] | None:
    semantic_layer = importlib.import_module("services.semantic_layer")
    return semantic_layer.get_metric_info(metric)

# Cache em memória de sinônimos → nome oficial, populado dinamicamente pelo SemanticCatalog




class BusinessLayer:
    """
    Camada de Regras Corporativas de Negócio (Business Layer).
    Ponte para o Business Knowledge Engine (BKE).
    """

    def _resolve_synonym_local(self, metric: str) -> str:
        """
        Resolve metric synonyms through the centralized Semantic Layer.
        """
        semantic_layer = importlib.import_module("services.semantic_layer")
        return semantic_layer.canonicalize_metric_name(metric)

    async def apply_business_rules(
        self,
        plan: Any,
        tenant_id: uuid.UUID | str | None = None,
        db: AsyncSession | None = None,
    ) -> Any:
        """
        Aplica regras de negócio analíticas e validações do BKE corporativo.
        Caso db esteja ausente (modo offline/testes), utiliza o fallback legado em memória.
        """
        if db is not None and tenant_id is not None:
            # Integração com o novo Business Knowledge Engine
            business_knowledge_engine = importlib.import_module("services.business.business_knowledge_engine").business_knowledge_engine
            tenant_uuid = uuid.UUID(str(tenant_id))
            return await business_knowledge_engine.apply_business_rules(plan, tenant_uuid, db)

        # Fallback legado em memória para compatibilidade com testes offline
        logger.info("[BusinessLayer] Modo offline: aplicando regras legadas em memória...")
        metrics = getattr(plan, "metrics", []) or []
        standardized_metrics = []
        for metric in metrics:
            resolved = self._resolve_synonym_local(metric)
            if _get_metric_info(resolved):
                standardized_metrics.append(resolved)
            else:
                standardized_metrics.append(metric)

        if hasattr(plan, "metrics"):
            plan.metrics = standardized_metrics
        else:
            if not hasattr(plan, "contexto") or plan.contexto is None:
                plan.contexto = {}
            plan.contexto["standardized_metrics"] = standardized_metrics

        dependencies = set()
        formulas = {}
        rules = {}
        for metric in standardized_metrics:
            info = _get_metric_info(metric)
            if info:
                formulas[metric] = info.get("formula", "")
                rules[metric] = info.get("validation_rules", [])
                for dep in info.get("dependencies", []):
                    dependencies.add(dep)

        if not hasattr(plan, "contexto") or plan.contexto is None:
            plan.contexto = {}

        plan.contexto["formulas_oficiais"] = formulas
        plan.contexto["regras_validacao"] = rules
        plan.contexto["dependencias_negocio"] = list(dependencies)

        return plan


business_layer = BusinessLayer()


async def apply_business_rules(*args: Any, **kwargs: Any) -> Any:
    """Compatibility proxy for legacy package-level imports."""
    return await business_layer.apply_business_rules(*args, **kwargs)

