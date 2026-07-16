"""
LuminaAI — Business Knowledge Engine Facade
--------------------------------------------
Ponto central de acesso e coordenação de todo o conhecimento corporativo de gestão.
Integra dicionário, KPIs, fórmulas, contextos, validações, dependências e governança.
"""
from __future__ import annotations

import logging
import uuid
import time
from typing import Any

from sqlalchemy import select, func as sql_func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from services.business.business_dictionary import business_dictionary
from services.business.business_kpi_registry import business_kpi_registry
from services.business.business_formula_engine import business_formula_engine
from services.business.business_relationship_engine import business_relationship_engine
from services.business.business_context_engine import business_context_engine
from services.business.business_validation_engine import business_validation_engine, BusinessValidationError
from services.business.business_dependency_engine import business_dependency_engine
from services.business.business_governance import business_governance


logger = logging.getLogger("luminaai.business.knowledge_engine")


class BusinessKnowledgeEngine:
    """
    Fachada corporativa para a Business Layer de alto desempenho do LuminaAI.
    """

    async def apply_business_rules(
        self,
        plan: Any,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> Any:
        """
        Substitui/refatora a lógica original da Business Layer.
        Aplica padronização de conceitos de BI, valida ativamente regras de negócio
        e enriquece o plano com dependências e relações de causa/efeito.
        """
        logger.info("[BKE] Aplicando regras e validações corporativas...")
        start_time = time.perf_counter()

        # 1. Executa validação de plano ativa
        is_valid, errors = await business_validation_engine.validate_query_plan(tenant_id, plan, db)
        validation_time_ms = (time.perf_counter() - start_time) * 1000

        if not is_valid:
            # Em conformidade com o validator, levantamos erro descritivo em caso de violações
            logger.error("[BKE] Validação falhou: %s", errors)
            raise BusinessValidationError("Violação de consistência na Business Layer.", errors)

        # 2. Padronização de nomes de métricas (sinônimos oficiais)
        metrics = []
        if hasattr(plan, "metrics"):
            metrics = plan.metrics or []
        elif hasattr(plan, "kpis_planejados"):
            metrics = plan.kpis_planejados or []

        standardized = []
        for metric in metrics:
            concept = await business_dictionary.get_concept(tenant_id, metric, db)
            if concept:
                resolved_metric = concept.nome
            else:
                kpi = await business_kpi_registry.get_kpi(tenant_id, metric, db)
                if kpi:
                    resolved_metric = kpi.nome
                else:
                    resolved_metric = metric

            from services.semantic_layer import canonicalize_metric_name, get_metric_info
            canonical_metric = canonicalize_metric_name(resolved_metric)
            if get_metric_info(canonical_metric):
                standardized.append(canonical_metric)
            else:
                standardized.append(resolved_metric)

        # Atualiza no plano
        if hasattr(plan, "metrics"):
            plan.metrics = standardized
        if hasattr(plan, "kpis_planejados"):
            plan.kpis_planejados = standardized

        # 3. Enriquecimento de contexto (Fórmulas, Dependências, Relacionamentos)
        formulas = {}
        rules = {}
        dependencies = set()
        relations = []

        for metric in standardized:
            kpi = await business_kpi_registry.get_kpi(tenant_id, metric, db)
            formula = await business_formula_engine.get_formula(tenant_id, metric, db)

            # Busca fórmulas
            if kpi and kpi.formula_oficial:
                formulas[metric] = kpi.formula_oficial
            elif formula and formula.formula:
                formulas[metric] = formula.formula

            # Busca validações e restrições
            if kpi:
                rules[metric] = kpi.faixas or {}
                # Busca relações de causa e efeito associadas
                rel_list = await business_relationship_engine.get_relationships(tenant_id, metric, db)
                for r in rel_list:
                    relations.append({
                        "origem": r.origem_nome,
                        "destino": r.destino_nome,
                        "tipo": r.tipo_relacao,
                        "descricao": r.descricao,
                    })

        # Enriquece o contexto do plano de consulta
        if not hasattr(plan, "contexto") or plan.contexto is None:
            plan.contexto = {}

        plan.contexto["formulas_oficiais"] = formulas
        plan.contexto["regras_validacao"] = rules
        plan.contexto["relacionamentos_causa_efeito"] = relations
        plan.contexto["validation_time_ms"] = round(validation_time_ms, 2)
        plan.contexto["standardized_metrics"] = standardized

        logger.info(
            "[BKE] Regras aplicadas com sucesso (tempo=%s ms). Métricas oficiais: %s",
            round(validation_time_ms, 2),
            standardized,
        )

        return plan

    async def get_observability_metrics(
        self,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Retorna métricas de saúde e observabilidade da camada Business Layer.
        """
        # Contagem de conceitos
        from models.business_concept import BusinessConcept
        stmt_concepts = select(sql_func.count(BusinessConcept.id)).where(
            and_(BusinessConcept.tenant_id == tenant_id, BusinessConcept.status == "ACTIVE")
        )
        concepts_count = (await db.execute(stmt_concepts)).scalar() or 0

        # Contagem de KPIs
        from models.business_kpi import BusinessKPI
        stmt_kpis = select(sql_func.count(BusinessKPI.id)).where(
            and_(BusinessKPI.tenant_id == tenant_id, BusinessKPI.status == "ACTIVE")
        )
        kpis_count = (await db.execute(stmt_kpis)).scalar() or 0

        # Contagem de Fórmulas
        from models.business_formula import BusinessFormula
        stmt_formulas = select(sql_func.count(BusinessFormula.id)).where(
            and_(BusinessFormula.tenant_id == tenant_id, BusinessFormula.status == "ACTIVE")
        )
        formulas_count = (await db.execute(stmt_formulas)).scalar() or 0

        # Contagem de Relacionamentos
        from models.business_relationship import BusinessRelationship
        stmt_rels = select(sql_func.count(BusinessRelationship.id)).where(
            BusinessRelationship.tenant_id == tenant_id
        )
        rels_count = (await db.execute(stmt_rels)).scalar() or 0

        # Contagem de Logs de Governança
        from models.business_governance_log import BusinessGovernanceLog
        stmt_logs = select(sql_func.count(BusinessGovernanceLog.id)).where(
            BusinessGovernanceLog.tenant_id == tenant_id
        )
        logs_count = (await db.execute(stmt_logs)).scalar() or 0

        return {
            "concepts_active_count": concepts_count,
            "kpis_active_count": kpis_count,
            "formulas_active_count": formulas_count,
            "relationships_count": rels_count,
            "governance_logs_count": logs_count,
            "contexts_available": len(business_context_engine.get_official_contexts()),
        }

    # Exposição de submotores delegados
    @property
    def dictionary(self):
        return business_dictionary

    @property
    def kpi_registry(self):
        return business_kpi_registry

    @property
    def formula_engine(self):
        return business_formula_engine

    @property
    def relationship_engine(self):
        return business_relationship_engine

    @property
    def context_engine(self):
        return business_context_engine

    @property
    def validation_engine(self):
        return business_validation_engine

    @property
    def dependency_engine(self):
        return business_dependency_engine

    @property
    def governance(self):
        return business_governance


# Singleton export
business_knowledge_engine = BusinessKnowledgeEngine()
