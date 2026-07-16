"""
LuminaAI — Business Context Engine Service
-------------------------------------------
Classifica todos os elementos da Business Layer pelos 11 contextos oficiais da empresa.
Permite que um KPI ou conceito pertença a múltiplos contextos simultaneamente.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.business_concept import BusinessConcept
from models.business_kpi import BusinessKPI

logger = logging.getLogger("luminaai.business.context_engine")

# 11 Contextos Corporativos Oficiais
OFFICIAL_CONTEXTS = [
    "Financeiro",
    "Comercial",
    "Compras",
    "Estoque",
    "Logística",
    "Produção",
    "CRM",
    "Fiscal",
    "RH",
    "Operacional",
    "Gerencial",
]


class BusinessContextEngine:
    """
    Classifica e organiza conceitos e KPIs corporativos por contextos.
    """

    def get_official_contexts(self) -> list[str]:
        """Retorna a lista dos 11 contextos oficiais da empresa."""
        return list(OFFICIAL_CONTEXTS)

    async def list_by_context(
        self,
        tenant_id: uuid.UUID,
        context: str,
        db: AsyncSession,
    ) -> dict[str, list[str]]:
        """
        Retorna todos os conceitos e KPIs associados ao contexto especificado.
        Procura o contexto nos campos categoria, area e tags.
        """
        context_clean = context.strip()

        # Busca conceitos no dicionário
        stmt_concept = select(BusinessConcept).where(
            and_(
                BusinessConcept.tenant_id == tenant_id,
                BusinessConcept.status == "ACTIVE",
                or_(
                    BusinessConcept.categoria.ilike(context_clean),
                    BusinessConcept.area.ilike(context_clean),
                    BusinessConcept.sinonimos.contains([context_clean]),
                ),
            )
        )
        res_concept = await db.execute(stmt_concept)
        concepts = res_concept.scalars().all()

        # Busca KPIs
        stmt_kpi = select(BusinessKPI).where(
            and_(
                BusinessKPI.tenant_id == tenant_id,
                BusinessKPI.status == "ACTIVE",
                or_(
                    BusinessKPI.categoria.ilike(context_clean),
                    BusinessKPI.area.ilike(context_clean),
                    BusinessKPI.tags.contains([context_clean]),
                ),
            )
        )
        res_kpi = await db.execute(stmt_kpi)
        kpis = res_kpi.scalars().all()

        return {
            "context": context_clean,
            "concepts": [c.nome for c in concepts],
            "kpis": [k.nome for k in kpis],
        }

    async def associate_to_context(
        self,
        tenant_id: uuid.UUID,
        element_tipo: str,
        element_nome: str,
        context: str,
        db: AsyncSession,
    ) -> bool:
        """
        Associa um conceito ou KPI a um contexto, inserindo-o nos campos categoria/tags.
        """
        if context not in OFFICIAL_CONTEXTS:
            raise ValueError(f"Contexto '{context}' não pertence aos contextos oficiais da empresa.")

        element_tipo = element_tipo.upper().strip()
        element_name_clean = element_nome.strip()

        if element_tipo == "CONCEPT":
            from services.business.business_dictionary import business_dictionary
            concept = await business_dictionary.get_concept(tenant_id, element_name_clean, db)
            if not concept:
                return False

            tags = list(concept.sinonimos or [])
            if context not in tags:
                tags.append(context)
                # Atualiza usando dicionário para registrar auditoria
                await business_dictionary.register_concept(
                    tenant_id=tenant_id,
                    concept_data={
                        "nome": concept.nome,
                        "sinonimos": tags,
                    },
                    autor="CONTEXT_ENGINE",
                    db=db,
                )
            return True

        elif element_tipo == "KPI":
            from services.business.business_kpi_registry import business_kpi_registry
            kpi = await business_kpi_registry.get_kpi(tenant_id, element_name_clean, db)
            if not kpi:
                return False

            tags = list(kpi.tags or [])
            if context not in tags:
                tags.append(context)
                await business_kpi_registry.register_kpi(
                    tenant_id=tenant_id,
                    kpi_data={
                        "nome": kpi.nome,
                        "tags": tags,
                    },
                    autor="CONTEXT_ENGINE",
                    db=db,
                )
            return True

        return False


# Singleton export
business_context_engine = BusinessContextEngine()
