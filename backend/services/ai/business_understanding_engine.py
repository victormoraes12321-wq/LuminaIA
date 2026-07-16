"""
LuminaAI — Business Understanding Engine
----------------------------------------
Fornece compreensão profunda sobre conceitos de gestão e KPIs cadastrados na Business Layer,
permitindo à IA entender o significado sem fazer cálculos ou acessar o banco.
"""
from __future__ import annotations

import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from services.business.business_knowledge_engine import business_knowledge_engine

logger = logging.getLogger("luminaai.ai.business_understanding_engine")


class BusinessUnderstandingEngine:
    """
    Motor de compreensão do domínio de negócios.
    Conecta a IA ao conhecimento corporativo registrado no BKE.
    """

    async def get_concept_meaning(
        self,
        tenant_id: uuid.UUID,
        concept_name: str,
        db: AsyncSession,
    ) -> dict[str, str]:
        """
        Retorna a definição de negócio e a área associada a um termo a partir do BKE.
        """
        concept = await business_knowledge_engine.dictionary.get_concept(tenant_id, concept_name, db)
        if concept:
            return {
                "nome": concept.nome,
                "descricao": concept.descricao,
                "definicao_oficial": concept.definicao_oficial or "Conceito corporativo básico.",
                "area": concept.area,
            }
            
        kpi = await business_knowledge_engine.kpi_registry.get_kpi(tenant_id, concept_name, db)
        if kpi:
            return {
                "nome": kpi.nome,
                "descricao": kpi.descricao,
                "definicao_oficial": kpi.formula_oficial,
                "area": kpi.area,
            }
            
        return {
            "nome": concept_name,
            "descricao": "Termo de negócio customizado.",
            "definicao_oficial": "Sem fórmula cadastrada.",
            "area": "Geral",
        }


# Singleton export
business_understanding_engine = BusinessUnderstandingEngine()
