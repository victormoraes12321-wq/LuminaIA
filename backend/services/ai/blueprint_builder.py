"""
LuminaAI — Blueprint Builder
----------------------------
Compila o Blueprint estruturado completo a partir do Business Intent e da Visual Strategy.
Importante: O Blueprint nunca contém SQL, tabelas de banco ou views físicas.
"""
from __future__ import annotations

import datetime
import uuid
import logging
from services.ai.schemas import BlueprintSchema, BusinessIntentSchema, VisualStrategySchema

logger = logging.getLogger("luminaai.ai.blueprint_builder")


class BlueprintBuilder:
    """
    Motor que compila e gera os Blueprints de execução de BI.
    """

    def compile_blueprint(
        self,
        business_intent: BusinessIntentSchema,
        visual_strategy: VisualStrategySchema,
    ) -> BlueprintSchema:
        """
        Compila e serializa o Blueprint estruturado pronto para a camada do Analytics Engine.
        """
        logger.info("[CIE] Compilando Blueprint analítico para a consulta...")
        
        # Determina o template de painel sugerido
        dashboard_template = "TEMPLATE_PADRAO"
        if visual_strategy.componente_principal == "KPI":
            dashboard_template = "TEMPLATE_KPI_CARDS"
        elif visual_strategy.componente_principal == "BAR":
            dashboard_template = "TEMPLATE_DASHBOARD_BARRAS"
            
        # Dependências de indicadores
        dependencies = list(business_intent.kpis or [])
        
        blueprint = BlueprintSchema(
            id=uuid.uuid4(),
            business_intent=business_intent,
            kpis=business_intent.kpis,
            filtros=business_intent.filtros,
            agrupamentos=business_intent.agrupamentos,
            periodo=business_intent.periodo,
            comparacoes=business_intent.comparacoes,
            visual_strategy=visual_strategy,
            dependencias=dependencies,
            dashboard_sugerida=dashboard_template,
            criado_em=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        return blueprint


# Singleton export
blueprint_builder = BlueprintBuilder()
