"""
LuminaAI — Query Planner Service (v4.4)
---------------------------------------
Elabora um plano estratégico de consulta (QueryPlan) baseado nas intenções NLU.
- Identifica a Consulta Principal.
- Decide e adiciona Consultas Complementares relevantes para enriquecer o contexto de BI.
- Planeja Comparações e KPIs automaticamente.
- Sugere os tipos de visualização corretos para o frontend.
- Define a prioridade, obrigatoriedade, dependências e a ordem de execução em paralelo.
- Otimiza e remove redundâncias (consultas duplicadas ou englobadas).
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Final
from pydantic import BaseModel, Field

from schemas.view_catalog import ViewCatalogSummary
from services.ai_service import IntentionResponse

logger = logging.getLogger("luminaai.services.query_planner")


# ── Classes de Modelo do Plano de Execução ────────────────────

class QueryPlanItem(BaseModel):
    """Representa um item individual planejado para execução."""
    id: str = Field(description="Identificador único da consulta no plano (ex: 'principal', 'meta_vendedor')")
    view_catalog_id: uuid.UUID | None = Field(default=None)
    view_name: str | None = Field(default=None)
    parametros: dict[str, str] = Field(default_factory=dict)
    prioridade: str = Field(default="ALTA", description="ALTA | MEDIA | BAIXA")
    sugestao_visualizacao: str = Field(default="TABLE", description="BAR | LINE | PIE | TABLE | KPI | AREA | SCATTER")
    visualizacoes_solicitadas: list[str] | None = Field(default=None, description="Tipos de visualização explícitos solicitados pelo usuário")
    depende_de: list[str] = Field(default_factory=list, description="IDs de consultas de que esta depende")
    objetivo: str = Field(description="Descrição da finalidade analítica desta consulta")
    obrigatoria: bool = Field(default=True, description="Se False, falhas nesta consulta serão toleradas")


class QueryPlan(BaseModel):
    """Representa o plano de execução analítico completo (Query Plan)."""
    consulta_principal: QueryPlanItem
    consultas_complementares: list[QueryPlanItem] = Field(default_factory=list)
    kpis_planejados: list[str] = Field(default_factory=list)
    comparacoes_planejadas: list[str] = Field(default_factory=list)
    master_blueprint: Any | None = Field(
        default=None,
        description="Blueprint mestre opcional gerado por decomposicao analitica."
    )
    ordem_execucao: list[list[str]] = Field(
        default_factory=list,
        description="Lista de grupos de IDs de consulta a serem executados em ordem. Itens no mesmo grupo rodam em paralelo."
    )
    contexto: dict[str, Any] = Field(default_factory=dict)


# ── Métodos Auxiliares do Planejador ─────────────────────────

def _suggest_visualizacao(operacao: str, entidade_alvo: str, default_type: str) -> str:
    """Heurística para sugerir o melhor componente visual do frontend."""
    op = operacao.upper() if operacao else "SOMA"
    ent = entidade_alvo.upper() if entidade_alvo else "VENDA"
    
    if op in ("RANKING", "TOP", "BOTTOM", "MAIOR", "MENOR"):
        return "BAR"
    elif op in ("TENDENCIA", "CRESCIMENTO", "QUEDA", "PROJECOES"):
        return "LINE"
    elif op in ("PARTICIPACAO", "DISTRIBUICAO"):
        return "PIE"
    elif op in ("TOTAL", "KPI", "SOMA", "MEDIA", "MAXIMO", "MINIMO", "RESUMO") and ent in ("RECEITA", "LUCRO", "MARGEM", "TICKET"):
        return "KPI"
    elif op in ("LISTAGEM", "DETALHAMENTO"):
        return "TABLE"
    return default_type


def _find_view_by_keyword(
    catalog: list[ViewCatalogSummary],
    keywords: list[str],
    exclude_id: uuid.UUID | None = None
) -> ViewCatalogSummary | None:
    """Busca no catálogo por view que corresponda semanticamente às palavras-chave."""
    for view in catalog:
        if exclude_id and view.id == exclude_id:
            continue
        name_upper = view.nome_view_oracle.upper()
        desc_upper = (view.descricao_para_ia or "").upper()
        if any(kw.upper() in name_upper or kw.upper() in desc_upper for kw in keywords):
            return view
    return None


# ── Função Central do Query Planner ──────────────────────────

def _intention_domain(intention: IntentionResponse) -> str | None:
    """Infer the business domain that the final plan must respect."""
    entity = (intention.entidade_alvo or "").upper()

    if entity in {"VENDEDOR", "VENDEDORES", "REPRESENTANTE", "REPRESENTANTES"}:
        return "VENDEDOR"
    if entity in {"PRODUTO", "PRODUTOS", "ITEM", "ITENS"}:
        return "PRODUTO"
    if entity in {"CLIENTE", "CLIENTES"}:
        return "CLIENTE"
    if entity in {"ESTOQUE", "INVENTARIO"}:
        return "ESTOQUE"

    plan = intention.plano_estruturado
    if not plan:
        return None

    signal_text = " ".join(
        [
            plan.intent or "",
            plan.query_type or "",
            " ".join(plan.group_by or []),
            " ".join(plan.metrics or []),
        ]
    ).upper()

    if "VENDEDOR" in signal_text or "REPRESENTANTE" in signal_text:
        return "VENDEDOR"
    if "PRODUTO" in signal_text or "ITEM" in signal_text:
        return "PRODUTO"
    if "CLIENTE" in signal_text:
        return "CLIENTE"
    if "ESTOQUE" in signal_text or "INVENTARIO" in signal_text:
        return "ESTOQUE"

    return None


def _domain_keywords(domain: str) -> tuple[list[str], list[str]]:
    """Return positive and negative hints used to score catalog views."""
    specs: dict[str, tuple[list[str], list[str]]] = {
        "VENDEDOR": (
            ["VW_VENDAS_LM", "PERFORMANCE_VENDEDORES", "VENDEDORES", "VENDEDOR", "REPRESENTANTE", "VENDEDOR_NOME"],
            ["PRODUTO", "CLIENTE", "ESTOQUE", "COMPRA", "FORNECEDOR"],
        ),
        "PRODUTO": (
            ["VW_VENDAS_LM", "PRODUTOS_MAIS_VENDIDOS", "RANKING_PRODUTOS", "PRODUTOS", "PRODUTO", "ITEM", "DETALHE_PEDIDOS"],
            ["VENDEDOR", "CLIENTE", "ESTOQUE", "COMPRA", "FORNECEDOR"],
        ),
        "CLIENTE": (
            ["VW_VENDAS_LM", "CLIENTES", "CLIENTE", "SEGMENTACAO_CLIENTES"],
            ["VENDEDOR", "PRODUTO", "ESTOQUE", "COMPRA", "FORNECEDOR"],
        ),
        "ESTOQUE": (
            ["ESTOQUE", "INVENTARIO", "SALDO", "COBERTURA"],
            ["VENDEDOR", "CLIENTE", "COMPRA"],
        ),
    }
    return specs.get(domain, ([], []))


def _is_registry_catalog_view(view: ViewCatalogSummary | None) -> bool:
    if not view:
        return False
    name_upper = (view.nome_view_oracle or "").upper()
    desc_upper = (view.descricao_para_ia or "").upper()
    return (
        "_CAD" in name_upper
        or "CADASTRO" in name_upper
        or "CADASTRO MESTRE" in desc_upper
        or "NAO REPRESENTA VENDAS" in desc_upper
        or "NÃO REPRESENTA VENDAS" in desc_upper
    )


def _is_registry_intention(intention: IntentionResponse) -> bool:
    op = (intention.operacao or "").upper()
    if op in {"LISTAGEM", "DETALHAMENTO", "SELECT"}:
        plan = intention.plano_estruturado
        metrics = list(getattr(plan, "metrics", []) or []) if plan else []
        return not metrics
    return False


def _score_view_for_domain(view: ViewCatalogSummary | None, domain: str) -> int:
    """Score how well a catalog view fits the requested business domain."""
    if not view:
        return -999

    positives, negatives = _domain_keywords(domain)
    if not positives:
        return 0

    name_upper = view.nome_view_oracle.upper()
    desc_upper = (view.descricao_para_ia or "").upper()
    score = 0

    for keyword in positives:
        keyword = keyword.upper()
        if keyword in name_upper:
            score += 5
        elif keyword in desc_upper:
            score += 1

    for keyword in negatives:
        keyword = keyword.upper()
        if keyword in name_upper:
            score -= 4

    return score


def _guard_primary_view_domain(
    primary_intention: IntentionResponse,
    primary_view: ViewCatalogSummary | None,
    catalog: list[ViewCatalogSummary],
) -> ViewCatalogSummary | None:
    """Prevent a structured intent from being executed against an incompatible view."""
    domain = _intention_domain(primary_intention)
    if not domain:
        return primary_view

    registry_intention = _is_registry_intention(primary_intention)

    def contextual_score(view: ViewCatalogSummary | None) -> int:
        score = _score_view_for_domain(view, domain)
        if view and not registry_intention and _is_registry_catalog_view(view):
            score -= 20
        if view and registry_intention and _is_registry_catalog_view(view):
            score += 8
        return score

    current_score = contextual_score(primary_view)
    if (
        primary_view
        and primary_intention.view_catalog_id
        and str(primary_view.id) == str(primary_intention.view_catalog_id)
        and current_score > 0
    ):
        return primary_view

    ranked_candidates = sorted(
        ((view, contextual_score(view)) for view in catalog),
        key=lambda item: item[1],
        reverse=True,
    )
    best_view, best_score = ranked_candidates[0] if ranked_candidates else (None, -999)

    if best_view and best_score > max(current_score, 0):
        logger.warning(
            "Query Planner corrigiu view incompatível | Dominio=%s | Original=%s | Corrigida=%s",
            domain,
            primary_view.nome_view_oracle if primary_view else None,
            best_view.nome_view_oracle,
        )
        primary_intention.view_catalog_id = best_view.id
        return best_view

    return primary_view


def _requires_daily_view(intention: IntentionResponse) -> bool:
    """Return True when the current intent asks for one explicit calendar day."""
    params = dict(intention.parametros or {})
    start = params.get("data_inicio")
    end = params.get("data_fim")
    if start and end and start == end:
        return True

    plan = intention.plano_estruturado
    date_range = ""
    if plan and plan.filters:
        date_range = plan.filters.date_range or ""

    match = re.search(r"(\d{4}-\d{2}-\d{2})\s*(?:to|ate|a|-)\s*(\d{4}-\d{2}-\d{2})", date_range)
    if match and match.group(1) == match.group(2):
        return True

    single_day = re.fullmatch(r"\s*\d{4}-\d{2}-\d{2}\s*", date_range or "")
    return bool(single_day)


def _attach_structured_execution_hints(params: dict[str, str], intention: IntentionResponse) -> dict[str, str]:
    """Carrega metadados internos para a Data Platform agregar sem expor ao usuário."""
    enriched = dict(params or {})
    plan = intention.plano_estruturado
    if not plan:
        return enriched
    metrics = [str(item) for item in (plan.metrics or []) if item]
    group_by = [str(item) for item in (plan.group_by or []) if item]
    if metrics:
        enriched["_metrics"] = ",".join(metrics)
    if group_by:
        enriched["_group_by"] = ",".join(group_by)
    return enriched


def _score_daily_view(view: ViewCatalogSummary | None) -> int:
    if not view:
        return -999

    name_upper = view.nome_view_oracle.upper()
    desc_upper = (view.descricao_para_ia or "").upper()
    score = 0
    if "VW_VENDAS_LM" in name_upper:
        score += 14
    if "VENDAS_CONTEXTO_GERAL" in name_upper:
        score += 12
    if "DETALHE_PEDIDOS" in name_upper:
        score += 10
    if "PEDIDO" in name_upper or "DIARIO" in name_upper or "DIA" in desc_upper:
        score += 4
    if "VENDAS" in name_upper:
        score += 2
    if "MENSAL" in name_upper or "MENSAIS" in name_upper or "FATURAMENTO_MENSAL" in name_upper:
        score -= 12
    return score


def _guard_temporal_granularity(
    primary_intention: IntentionResponse,
    primary_view: ViewCatalogSummary | None,
    catalog: list[ViewCatalogSummary],
) -> ViewCatalogSummary | None:
    """Route explicit daily sales questions away from monthly aggregate views."""
    if not _requires_daily_view(primary_intention):
        return primary_view

    current_score = _score_daily_view(primary_view)

    if (
        primary_view
        and primary_intention.view_catalog_id
        and str(primary_view.id) == str(primary_intention.view_catalog_id)
        and current_score > 0
    ):
        return primary_view

    ranked_candidates = sorted(
        ((view, _score_daily_view(view)) for view in catalog),
        key=lambda item: item[1],
        reverse=True,
    )
    best_view, best_score = ranked_candidates[0] if ranked_candidates else (None, -999)

    if best_view and best_score > max(current_score, 0):
        logger.warning(
            "Query Planner corrigiu granularidade temporal | Original=%s | Corrigida=%s",
            primary_view.nome_view_oracle if primary_view else None,
            best_view.nome_view_oracle,
        )
        primary_intention.view_catalog_id = best_view.id
        return best_view

    return primary_view

def create_query_plan(
    intentions: list[IntentionResponse],
    catalog: list[ViewCatalogSummary]
) -> QueryPlan:
    """
    Cria a estratégia de consulta otimizada (QueryPlan) para responder à pergunta do usuário.
    Garante enriquecimento analítico adicionando consultas complementares e aplicando
    regras de eliminação de redundância e paralelismo.
    """
    if not intentions:
        logger.warning("Query Planner recebeu lista vazia de intenções. Criando plano vazio.")
        dummy_item = QueryPlanItem(
            id="principal",
            objetivo="Nenhuma intenção identificada",
            prioridade="ALTA"
        )
        return QueryPlan(
            consulta_principal=dummy_item,
            ordem_execucao=[["principal"]]
        )

    # 1. Mapeia a Consulta Principal (Primeira intenção da NLU)
    primary_intention = intentions[0]
    primary_view = next((v for v in catalog if v.id == primary_intention.view_catalog_id), None)
    primary_view = _guard_primary_view_domain(primary_intention, primary_view, catalog)
    primary_view = _guard_temporal_granularity(primary_intention, primary_view, catalog)
    
    primary_chart_type = "TABLE"
    if primary_view:
        primary_chart_type = primary_view.tipo_grafico_padrao.value
    

        
    sugestao_vis = _suggest_visualizacao(
        primary_intention.operacao or "SOMA",
        primary_intention.entidade_alvo or "VENDA",
        primary_chart_type
    )

    if primary_intention.visualizacao_preferida:
        sugestao_vis = primary_intention.visualizacao_preferida.upper()

    # Sobrescreve visualização caso solicitado explicitamente pelo NLU
    if primary_intention.chart_type_sobrescrever:
        sugestao_vis = primary_intention.chart_type_sobrescrever

    primary_params = _attach_structured_execution_hints(primary_intention.parametros.copy(), primary_intention)
    if primary_intention.quantidade_limite:
        primary_params["limite"] = str(primary_intention.quantidade_limite)

    consulta_principal = QueryPlanItem(
        id="principal",
        view_catalog_id=primary_intention.view_catalog_id,
        view_name=primary_view.nome_view_oracle if primary_view else None,
        parametros=primary_params,
        prioridade="ALTA",
        sugestao_visualizacao=sugestao_vis,
        visualizacoes_solicitadas=primary_intention.chart_types_solicitados,
        objetivo=f"Consulta principal de {primary_intention.entidade_alvo or 'vendas'}",
        obrigatoria=True
    )

    # Listas de controle
    complementares: list[QueryPlanItem] = []
    kpis_planejados: list[str] = []
    comparacoes_planejadas: list[str] = []

    # 2. Mapeia Intenções Compostas (Se houverem mais de uma na NLU)
    for idx, intention in enumerate(intentions[1:], start=1):
        comp_view = next((v for v in catalog if v.id == intention.view_catalog_id), None)
        if not comp_view:
            continue
            
        comp_chart_type = comp_view.tipo_grafico_padrao.value
        comp_sugestao_vis = _suggest_visualizacao(
            intention.operacao or "SOMA",
            intention.entidade_alvo or "VENDA",
            comp_chart_type
        )
        if intention.visualizacao_preferida:
            comp_sugestao_vis = intention.visualizacao_preferida.upper()
        if intention.chart_type_sobrescrever:
            comp_sugestao_vis = intention.chart_type_sobrescrever

        comp_params = _attach_structured_execution_hints(intention.parametros.copy(), intention)
        if intention.quantidade_limite:
            comp_params["limite"] = str(intention.quantidade_limite)

        item_composto = QueryPlanItem(
            id=f"composto_{idx}",
            view_catalog_id=intention.view_catalog_id,
            view_name=comp_view.nome_view_oracle,
            parametros=comp_params,
            prioridade="ALTA",
            sugestao_visualizacao=comp_sugestao_vis,
            visualizacoes_solicitadas=intention.chart_types_solicitados,
            objetivo=f"Consulta composta solicitada do tópico {intention.entidade_alvo or 'geral'}",
            obrigatoria=True
        )
        complementares.append(item_composto)

    # 3. Heurísticas de Enriquecimento Analítico (BI Analyst Engine)
    entidade = (primary_intention.entidade_alvo or "VENDA").upper()
    operacao = (primary_intention.operacao or "SOMA").upper()
    
    # Heurística A: Consultas sobre Vendedor / Performance
    if entidade == "VENDEDOR":
        # Planeja KPI de atingimento de meta do vendedor
        meta_view = _find_view_by_keyword(catalog, ["meta", "atingimento"], exclude_id=primary_intention.view_catalog_id)
        if meta_view:
            item_meta = QueryPlanItem(
                id="complementar_meta_vendedor",
                view_catalog_id=meta_view.id,
                view_name=meta_view.nome_view_oracle,
                parametros=primary_intention.parametros.copy(),
                prioridade="MEDIA",
                sugestao_visualizacao="KPI",
                objetivo="Verificar meta e comissão do vendedor",
                obrigatoria=False
            )
            complementares.append(item_meta)
            kpis_planejados.append("meta_atingimento")
        comparacoes_planejadas.append("vs_equipe")

    # Heurística B: Consultas sobre Produto / Estoque
    elif entidade == "PRODUTO":
        # Planeja consulta sobre estoque crítico e custo
        estoque_view = _find_view_by_keyword(catalog, ["estoque", "status"], exclude_id=primary_intention.view_catalog_id)
        if estoque_view:
            item_estoque = QueryPlanItem(
                id="complementar_estoque_produto",
                view_catalog_id=estoque_view.id,
                view_name=estoque_view.nome_view_oracle,
                parametros={"produto_nome": primary_intention.parametros.get("produto_nome", "")},
                prioridade="MEDIA",
                sugestao_visualizacao="KPI",
                objetivo="Verificar níveis de estoque do produto consultado",
                obrigatoria=False
            )
            complementares.append(item_estoque)
            kpis_planejados.append("estoque_disponivel")
        comparacoes_planejadas.append("vs_segundo_colocado")

    # Heurística C: Consultas de Receita / Vendas Gerais
    elif entidade in ("RECEITA", "VENDA", "TOTAL", "QUANTIDADE"):
        # Planeja KPIs de Ticket Médio e NPS do catálogo executivo
        kpi_view = _find_view_by_keyword(catalog, ["kpi", "executivo"], exclude_id=primary_intention.view_catalog_id)
        if kpi_view:
            item_kpi = QueryPlanItem(
                id="complementar_kpi_executivo",
                view_catalog_id=kpi_view.id,
                view_name=kpi_view.nome_view_oracle,
                parametros=primary_intention.parametros.copy(),
                prioridade="MEDIA",
                sugestao_visualizacao="KPI",
                objetivo="KPIs executivos da empresa para o mesmo período",
                obrigatoria=False
            )
            complementares.append(item_kpi)
            kpis_planejados.extend(["ticket_medio", "pedidos_totais"])
        comparacoes_planejadas.append("vs_periodo_anterior")

    # 4. Otimização e Eliminação de Redundâncias
    unique_complementares: list[QueryPlanItem] = []
    seen_queries: set[str] = set()

    # Registra a principal para evitar que complementares façam a mesma query
    if consulta_principal.view_name:
        seen_queries.add(f"{consulta_principal.view_name}:{sorted(consulta_principal.parametros.items())}")

    for item in complementares:
        if not item.view_name:
            continue
        # Chave de unicidade baseada em view e parâmetros
        q_key = f"{item.view_name}:{sorted(item.parametros.items())}"
        
        # Elimina se já planejada
        if q_key in seen_queries:
            logger.info("Query Planner otimizou e removeu consulta redundante: %s", item.id)
            continue
            
        seen_queries.add(q_key)
        unique_complementares.append(item)

    # 5. Organização da Ordem de Execução (Grupo Concorrente)
    # Como as queries Oracle/Postgres são de leitura independentes, rodamos todas as não-dependentes em paralelo.
    grupo_paralelo_1 = ["principal"] + [c.id for c in unique_complementares if not c.depende_de]
    grupo_paralelo_2 = [c.id for c in unique_complementares if c.depende_de]
    
    ordem_execucao = [grupo_paralelo_1]
    if grupo_paralelo_2:
        ordem_execucao.append(grupo_paralelo_2)

    logger.info(
        "Plano de Consulta gerado | Principal=%s | Complementares_Otimizadas=%d | Ordem=%s",
        consulta_principal.view_name,
        len(unique_complementares),
        ordem_execucao,
    )

    return QueryPlan(
        consulta_principal=consulta_principal,
        consultas_complementares=unique_complementares,
        kpis_planejados=kpis_planejados,
        comparacoes_planejadas=comparacoes_planejadas,
        ordem_execucao=ordem_execucao,
        contexto={
            "entidade": entidade,
            "operacao": operacao,
            "total_filtros": len(primary_intention.parametros),
        }
    )
