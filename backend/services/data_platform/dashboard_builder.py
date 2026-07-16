import logging
from typing import Any
from services.data_transformer import transform_data
from schemas.query import VisualizationItem
from models.view_catalog import ChartType

logger = logging.getLogger("luminaai.data_platform.dashboard_builder")

# Formatação semântica padrão por formato de tipo de dado (fallback estático)
_FORMAT_DEFAULTS: dict[str, dict[str, Any]] = {
    "currency": {"unit": "R$", "decimals": 2, "prefix": "R$ "},
    "percentage": {"unit": "%", "decimals": 1, "suffix": "%"},
    "integer": {"unit": "un", "decimals": 0},
    "number": {"unit": "", "decimals": 2},
}

# Cores semânticas padrão por categoria de conceito
_CATEGORY_COLORS: dict[str, str] = {
    "Financeiro": "#4F46E5",
    "Comercial": "#059669",
    "Operacional": "#D97706",
    "Cliente": "#7C3AED",
    "Geral": "#64748B",
}

class DashboardBuilder:
    """
    Dashboard Builder (Dashboard Builder).
    Responsável por organizar as visualizações (gráficos, tabelas, KPIs)
    e montar a estrutura/layout final (Dashboard Schema) para o frontend.
    Nunca cria dados ou interpreta regras de negócio.
    """

    def build_dashboard_schema(
        self,
        resultados_dict: dict[str, Any],
        primary_intention: Any,
        query_plan: Any
    ) -> dict[str, Any]:
        """
        Gera a estrutura visual do dashboard contendo todas as visualizações planejadas.
        """
        logger.info("[DashboardBuilder] Montando a estrutura visual (Dashboard Schema)...")
        visualizations_list = []
        
        # Mapeia a consulta principal e gera suas visualizações
        principal = resultados_dict.get("principal")
        if principal:
            view_name = principal["view_name"]
            raw_rows = principal["raw_rows"]
            sugestao_vis = principal["sugestao_visualizacao"]
            
            # Resolve os tipos visuais para a consulta principal.
            # A sugestao do Planner ja passou pelo Validator e governa a ordem primaria.
            types_to_generate = [sugestao_vis]

            if primary_intention.chart_type_sobrescrever and primary_intention.chart_type_sobrescrever not in types_to_generate:
                types_to_generate.append(primary_intention.chart_type_sobrescrever)
            if primary_intention.chart_types_solicitados:
                for ct in primary_intention.chart_types_solicitados:
                    if ct not in types_to_generate:
                        types_to_generate.append(ct)
                
            for t in types_to_generate:
                chart_type = self._normalize_chart_type(t)
                t_data = transform_data(raw_rows, chart_type)
                visualizations_list.append(
                    VisualizationItem(
                        chart_type=chart_type,
                        chart_data=t_data,
                        view_name=view_name
                    )
                )

        # Adiciona visualizações complementares/auxiliares
        for q_id, res in resultados_dict.items():
            if q_id == "principal":
                continue
            view_name = res["view_name"]
            raw_rows = res["raw_rows"]
            sugestao_vis = res["sugestao_visualizacao"]
            
            chart_type = self._normalize_chart_type(sugestao_vis)
            t_data = transform_data(raw_rows, chart_type)
            visualizations_list.append(
                VisualizationItem(
                    chart_type=chart_type,
                    chart_data=t_data,
                    view_name=view_name
                )
            )

        # Determina a visualização primária
        primary_vis = visualizations_list[0] if visualizations_list else None
        
        # Enriquece com contexto semântico corporativo (formatação, unidades, cores)
        semantic_context = self._build_semantic_context(
            primary_intention=primary_intention,
            query_plan=query_plan
        )
        
        # Define disposição de componentes e ordem do layout
        layout_schema = {
            "component_count": len(visualizations_list),
            "primary_chart_type": primary_vis.chart_type.value if primary_vis else "TABLE",
            "layout_structure": "split" if len(visualizations_list) > 1 else "full",
            "components_order": [vis.chart_type.value for vis in visualizations_list],
            "semantic_context": semantic_context
        }
        
        # Injeta o master blueprint do AQD para orquestração visual no frontend
        if query_plan and hasattr(query_plan, "master_blueprint") and query_plan.master_blueprint:
            layout_schema["master_blueprint"] = query_plan.master_blueprint.model_dump() if hasattr(query_plan.master_blueprint, "model_dump") else query_plan.master_blueprint

        logger.info(
            "[DashboardBuilder] Dashboard Schema gerado | Componentes: %d | Layout: %s | Semântica: %s",
            len(visualizations_list),
            layout_schema["layout_structure"],
            list(semantic_context.keys())
        )
        
        return {
            "visualizations": visualizations_list,
            "layout_schema": layout_schema
        }

    def _normalize_chart_type(self, value: Any) -> ChartType:
        """Normaliza sugestoes visuais vindas da IA/planner para o enum oficial."""
        if isinstance(value, ChartType):
            return value
        try:
            return ChartType(str(value).upper())
        except Exception:
            logger.warning("[DashboardBuilder] Tipo visual invalido '%s'. Usando TABLE.", value)
            return ChartType.TABLE

    def _build_semantic_context(self, primary_intention: Any, query_plan: Any) -> dict[str, Any]:
        """
        Constrói o contexto semântico do dashboard consultando as definições do SemanticCatalog.
        Define automaticamente unidades, formatação, casas decimais, ícones e cores semânticas.
        """
        context: dict[str, Any] = {}
        
        try:
            # Recupera as métricas do plano
            metrics = []
            if query_plan and hasattr(query_plan, "consulta_principal"):
                item = query_plan.consulta_principal
                if hasattr(item, "objective") or hasattr(item, "objetivo"):
                    # Usa as métricas do plano estruturado (se disponível)
                    pass
                    
            # Mapeamento estático de formatação por conceito (resolve via _FORMAT_DEFAULTS)
            if hasattr(primary_intention, "operacao") and primary_intention.operacao:
                op = primary_intention.operacao.upper()
                if op in ("SOMA", "TOTAL"):
                    context["metodo_agregacao"] = "Soma"
                    context["formato_padrao"] = _FORMAT_DEFAULTS.get("currency", {})
                    context["cor_semantica"] = _CATEGORY_COLORS.get("Financeiro", "#4F46E5")
                elif op == "MEDIA":
                    context["metodo_agregacao"] = "Média"
                    context["formato_padrao"] = _FORMAT_DEFAULTS.get("currency", {})
                    context["cor_semantica"] = _CATEGORY_COLORS.get("Financeiro", "#4F46E5")
                elif op == "PERCENTUAL":
                    context["metodo_agregacao"] = "Percentual"
                    context["formato_padrao"] = _FORMAT_DEFAULTS.get("percentage", {})
                    context["cor_semantica"] = _CATEGORY_COLORS.get("Financeiro", "#4F46E5")
                elif op == "CONTAGEM":
                    context["metodo_agregacao"] = "Contagem"
                    context["formato_padrao"] = _FORMAT_DEFAULTS.get("integer", {})
                    context["cor_semantica"] = _CATEGORY_COLORS.get("Comercial", "#059669")
            
            context["icone_padrao"] = self._resolve_icon(getattr(primary_intention, "entidade_alvo", None))
            
        except Exception as e:
            logger.debug("[DashboardBuilder] Contexto semântico não resolvido: %s", e)
            
        return context

    def _resolve_icon(self, entidade_alvo: str | None) -> str:
        """Resolve o ícone correto com base na entidade alvo da consulta."""
        if not entidade_alvo:
            return "chart"
        entidade = entidade_alvo.upper()
        icons = {
            "VENDA": "currency",
            "CLIENTE": "users",
            "VENDEDOR": "star",
            "PRODUTO": "ticket",
            "FINANCEIRO": "currency",
        }
        for key, icon in icons.items():
            if key in entidade:
                return icon
        return "chart"


dashboard_builder = DashboardBuilder()


def build_dashboard_schema(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Compatibility proxy for legacy package-level imports."""
    return dashboard_builder.build_dashboard_schema(*args, **kwargs)
