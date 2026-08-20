"""
LuminaAI — KPI Discovery Engine
--------------------------------
Identifica métricas e KPIs oficiais com base no dicionário do BKE,
garantindo que a IA nunca invente indicadores analíticos.
"""
from __future__ import annotations

import uuid
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.business.business_knowledge_engine import business_knowledge_engine
from services.semantic_layer import canonicalize_metric_name, get_metric_info

logger = logging.getLogger("luminaai.ai.kpi_discovery_engine")


class KPIDiscoveryEngine:
    """
    Motor de descoberta de KPIs oficiais no repositório de metadados do BKE.
    """

    async def discover_metrics(
        self,
        tenant_id: uuid.UUID,
        raw_indicators: list[str],
        db: AsyncSession,
    ) -> list[str]:
        """
        Mapeia os termos de indicadores em linguagem natural informados para os nomes oficiais no BKE.
        """
        logger.info("[CIE] Descobrindo KPIs oficiais para as métricas solicitadas: %s", raw_indicators)
        discovered = []
        
        for indicator in raw_indicators:
            # 1. Tenta buscar sinônimos e conceitos no Dicionário Corporativo do BKE
            concept = await business_knowledge_engine.dictionary.get_concept(tenant_id, indicator, db)
            if concept:
                discovered.append(concept.nome)
                continue
                
            # 2. Tenta buscar no Registro de KPIs do BKE
            kpi = await business_knowledge_engine.kpi_registry.get_kpi(tenant_id, indicator, db)
            if kpi:
                discovered.append(kpi.nome)
                continue
                
            # 3. Fallback: Mantém o indicador original
            canonical_indicator = canonicalize_metric_name(indicator)
            if get_metric_info(canonical_indicator):
                discovered.append(canonical_indicator)
            else:
                discovered.append(indicator)
            
        return list(dict.fromkeys(discovered))  # Remove duplicados preservando a ordem


# Singleton export
kpi_discovery_engine = KPIDiscoveryEngine()
