from __future__ import annotations

import logging
import uuid
import time
import re
from typing import Any, Final
from pydantic import BaseModel, Field

from schemas.view_catalog import ViewCatalogSummary
from services.ai.csie import STABLE_METRICS, STABLE_DIMENSIONS, STABLE_PERIODS

logger = logging.getLogger("luminaai.services.aqd")


_VISUAL_FRAGMENT_TERMS: Final[set[str]] = {
    "area", "areas", "barra", "barras", "card", "cards", "grafico", "graficos",
    "heatmap", "kpi", "kpis", "linha", "linhas", "pizza", "ranking", "rosca",
    "tabela", "tabelas", "treemap",
}


def _is_visual_only_fragment(fragment: str) -> bool:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", fragment.lower())
    tokens = {token for token in cleaned.split() if token}
    if not tokens:
        return False

    allowed_terms = _VISUAL_FRAGMENT_TERMS | {"com", "de", "do", "da", "em", "e", "por", "visualizacao"}
    return bool(tokens & _VISUAL_FRAGMENT_TERMS) and tokens <= allowed_terms


class AnalyticalTask(BaseModel):
    """
    Representa uma tarefa analÃƒÂ­tica individual gerada pelo AQD.
    Mapeia uma subconsulta otimizada e independente.
    """
    task_id: str = Field(description="ID ÃƒÂºnico da tarefa analÃƒÂ­tica (ex: task_vendedores)")
    objetivo: str = Field(description="Objetivo de negÃƒÂ³cio da tarefa")
    descricao: str = Field(description="DescriÃƒÂ§ÃƒÂ£o detalhada do resultado esperado")
    corporate_ids: list[str] = Field(default_factory=list, description="Lista de IDs corporativos de mÃƒÂ©tricas e dimensÃƒÂµes envolvidas")
    dependencias: list[str] = Field(default_factory=list, description="Lista de task_ids das quais esta tarefa depende")
    prioridade: str = Field(default="ALTA", description="ALTA | MEDIA | BAIXA")
    fonte_sugerida: str = Field(description="Nome fÃƒÂ­sico da View analÃƒÂ­tica recomendada")
    estrategia_visual: str = Field(default="TABLE", description="BAR | LINE | PIE | TABLE | KPI")
    resultado_esperado: str = Field(description="Formato descritivo do retorno esperado")


class MasterBlueprint(BaseModel):
    """
    Blueprint Mestre gerado pelo AQD.
    Organiza a orquestraÃƒÂ§ÃƒÂ£o do Dashboard composto e de seus blueprints filhos.
    """
    master_id: str = Field(description="ID ÃƒÂºnico do blueprint mestre")
    nome: str = Field(description="Nome amigÃƒÂ¡vel do dashboard composto")
    blueprints_filhos: list[dict[str, Any]] = Field(default_factory=list, description="DefiniÃƒÂ§ÃƒÂµes completas dos blueprints de cada subconsulta")
    relacionamentos: list[dict[str, Any]] = Field(default_factory=list, description="DefiniÃƒÂ§ÃƒÂ£o de dependÃƒÂªncias e ordem de carregamento")
    layout: dict[str, Any] = Field(default_factory=dict, description="ConfiguraÃƒÂ§ÃƒÂ£o de posicionamento e grid dos widgets no frontend")


# RepositÃ³rio de HistÃ³rico de ExecuÃ§Ã£o do AQD (para Aprendizado Controlado)
# Formato: { strategy_id: { "utilizacoes": int, "sucessos": int, "falhas": int, "tempo_total_ms": int } }
AQD_STRATEGY_HISTORY: dict[str, dict[str, Any]] = {}

class CandidateStrategy(BaseModel):
    """Representa uma estratÃ©gia alternativa de resoluÃ§Ã£o analÃ­tica."""
    id: str = Field(description="ID Ãºnico da estratÃ©gia (ex: strat_1_vw_vendas)")
    descricao: str = Field(description="DescriÃ§Ã£o da abordagem desta estratÃ©gia")
    corporate_ids_envolvidos: list[str] = Field(default_factory=list, description="Corporate IDs que esta estratÃ©gia atende")
    views_utilizadas: list[str] = Field(default_factory=list, description="Views candidatas a serem consultadas")
    dimensoes: list[str] = Field(default_factory=list, description="DimensÃµes fÃ­sicas mapeadas")
    metricas: list[str] = Field(default_factory=list, description="MÃ©tricas fÃ­sicas mapeadas")
    granularidade: str = Field(default="mensal", description="diaria | mensal | anual")
    relacionamentos: list[dict[str, Any]] = Field(default_factory=list, description="Relacionamentos de JOIN")
    necessidade_join: bool = Field(default=False)
    necessidade_agregacao: bool = Field(default=True)
    compatibilidade: str = Field(default="ALTA", description="ALTA | MEDIA | BAIXA")
    performance_estimada: str = Field(default="RAPIDA", description="RAPIDA | MODERADA | LENTA")
    cobertura: float = Field(default=100.0, description="Percentual de cobertura de termos solicitados")
    freshness: str = Field(default="D-1", description="Tempo de atualizaÃ§Ã£o dos dados")
    complexidade: str = Field(default="BAIXA", description="BAIXA | MEDIA | ALTA")
    prioridade: str = Field(default="ALTA", description="ALTA | MEDIA | BAIXA")
    
    # Scores individuais (0 a 100)
    semantic_score: float = Field(default=100.0)
    metadata_score: float = Field(default=100.0)
    coverage_score: float = Field(default=100.0)
    performance_score: float = Field(default=100.0)
    freshness_score: float = Field(default=100.0)
    integrity_score: float = Field(default=100.0)
    compatibility_score: float = Field(default=100.0)
    historical_success_score: float = Field(default=100.0)
    overall_resolution_score: float = Field(default=100.0)

class IntencaoAnalitica(BaseModel):
    """Representa a intenÃ§Ã£o analÃ­tica detalhada mapeada para o ARP."""
    objetivo: str
    corporate_ids: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    periodo: str | None = None
    filtros: dict[str, str] = Field(default_factory=dict)
    granularidade: str = Field(default="mensal")
    dependencias: list[str] = Field(default_factory=list)
    regras_negocio: list[str] = Field(default_factory=list)
    estrategias_candidatas: list[CandidateStrategy] = Field(default_factory=list)

class AnalyticalResolutionPlan(BaseModel):
    """Analytical Resolution Plan (ARP) contendo mÃºltiplas estratÃ©gias candidatas priorizadas."""
    arp_id: str = Field(description="ID Ãºnico do plano ARP")
    original_query: str = Field(description="Pergunta original do usuÃ¡rio")
    intencoes: list[IntencaoAnalitica] = Field(default_factory=list)
    timestamp: str = Field(description="Data e hora de geraÃ§Ã£o do plano")

class AQDDecompositionResult(BaseModel):
    """
    Retorno final do processamento do Analytical Query Decomposer (AQD).
    """
    decomposed: bool = Field(default=False)
    quantidade_consultas: int = Field(default=1)
    tempo_decomposicao_ms: int = Field(default=0)
    tempo_planejamento_ms: int = Field(default=0)
    tasks: list[AnalyticalTask] = Field(default_factory=list)
    master_blueprint: MasterBlueprint | None = Field(default=None)
    arp: AnalyticalResolutionPlan | None = Field(default=None)


class AnalyticalQueryDecomposer:
    """
    Analytical Query Decomposer (AQD) Ã¢â‚¬â€ MÃƒÂ³dulo Enterprise de DecomposiÃƒÂ§ÃƒÂ£o AnalÃƒÂ­tica.
    Interpreta perguntas complexas, divide-as em subconsultas compatÃƒÂ­veis com as fontes fÃƒÂ­sicas,
    planeja paralelismo e orquestra a composiÃƒÂ§ÃƒÂ£o de dashboards unificados.
    """

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if isinstance(value, dict):
            return value
        return {}

    def _extract_corporate_ids_from_context(
        self,
        corporate_intent_plan: Any | None = None,
        semantic_hypotheses: list[Any] | None = None,
    ) -> list[str]:
        ids: list[str] = []
        cip_dict = self._as_dict(corporate_intent_plan)

        for key in ("corporate_metrics", "corporate_dimensions"):
            for item in cip_dict.get(key, []) or []:
                item_dict = self._as_dict(item)
                concept_id = item_dict.get("id")
                if concept_id:
                    ids.append(str(concept_id))

        for hypothesis in semantic_hypotheses or cip_dict.get("hypotheses", []) or []:
            hypothesis_dict = self._as_dict(hypothesis)
            ids.extend(str(item) for item in hypothesis_dict.get("metrics", []) or [] if item)
            ids.extend(str(item) for item in hypothesis_dict.get("dimensions", []) or [] if item)

        return list(dict.fromkeys(ids))

    def decompose(
        self,
        query_text: str,
        catalog: list[ViewCatalogSummary],
        tenant_id: uuid.UUID,
        corporate_intent_plan: Any | None = None,
        semantic_hypotheses: list[Any] | None = None,
    ) -> AQDDecompositionResult:
        """
        Analisa a solicitaÃƒÂ§ÃƒÂ£o do usuÃƒÂ¡rio e a divide em mÃƒÂºltiplas consultas independentes (Tasks)
        caso envolva mÃƒÂºltiplos domÃƒÂ­nios, perÃƒÂ­odos, mÃƒÂ©tricas incompatÃƒÂ­veis ou rankings.
        """
        inicio = time.perf_counter()
        query_lower = query_text.lower().strip()
        simple_entity_ranking = (
            any(term in query_lower for term in ("top", "ranking", "mais vende", "mais vendido", "lider"))
            and (
                ("vendedor" in query_lower and "produto" not in query_lower)
                or ("produto" in query_lower and "vendedor" not in query_lower)
            )
            and not any(term in query_lower for term in ("fornecedor", "fornecedores", "compra", "compras", "transportadora"))
        )

        # 1. IdentificaÃƒÂ§ÃƒÂ£o de mÃƒÂºltiplas intenÃƒÂ§ÃƒÂµes e necessidade de decomposiÃƒÂ§ÃƒÂ£o
        # HeurÃƒÂ­sticas: presenÃƒÂ§a de conectores ("e", "alÃƒÂ©m de"), mÃƒÂºltiplos termos corporativos,
        # ou mÃƒÂ©tricas de fontes fÃƒÂ­sicas distintas.
        needs_decomposition = False
        sub_requests = []

        # Caso A: Pergunta explÃƒÂ­cita com mÃƒÂºltiplas anÃƒÂ¡lises separadas por conectores ou quebra de linha
        if simple_entity_ranking:
            needs_decomposition = False
            sub_requests = []
        elif " e " in query_lower or "\n" in query_lower or " alem de " in query_lower:
            parts = re.split(r'\be\b|\balem de\b|\n', query_lower)
            sub_requests = [p.strip() for p in parts if len(p.strip()) > 5]
            visual_only_tail = len(sub_requests) > 1 and all(
                _is_visual_only_fragment(part) for part in sub_requests[1:]
            )
            if visual_only_tail:
                needs_decomposition = False
                sub_requests = []
            else:
                needs_decomposition = True
        
        # Caso B: MÃƒÂºltiplos domÃƒÂ­nios na mesma string (ex: "vendedores" + "produtos")
        elif "vendedor" in query_lower and "produto" in query_lower:
            needs_decomposition = True
            sub_requests = [
                "ranking de performance de vendedores",
                "top produtos mais vendidos"
            ]

        # Caso C: MÃƒÂºltiplas perguntas diretas consecutivas
        elif query_lower.count("?") > 1:
            needs_decomposition = True
            parts = query_lower.split("?")
            sub_requests = [p.strip() for p in parts if len(p.strip()) > 5]

        # Se nÃ£o identificou mÃºltiplos tÃ³picos, gera uma Ãºnica consulta padrÃ£o
        if not needs_decomposition or len(sub_requests) <= 1:
            tempo_ms = int((time.perf_counter() - inicio) * 1000)
            single_task = self._create_single_task(
                query_text,
                catalog,
                tenant_id,
                corporate_intent_plan=corporate_intent_plan,
                semantic_hypotheses=semantic_hypotheses,
            )
            master_bp = self._compose_master_blueprint([single_task], query_text)
            arp = self._build_arp(query_text, [single_task], catalog)
            return AQDDecompositionResult(
                decomposed=False,
                quantidade_consultas=1,
                tempo_decomposicao_ms=tempo_ms,
                tempo_planejamento_ms=2,
                tasks=[single_task],
                master_blueprint=master_bp,
                arp=arp
            )

        # 2. DecomposiÃ§Ã£o em MÃºltiplas Tasks AnalÃ­ticas
        tasks = []
        for idx, sub_req in enumerate(sub_requests, start=1):
            task = self._create_sub_task(sub_req, catalog, idx)
            tasks.append(task)

        # Elimina redundÃ¢ncias de tarefas iguais
        unique_tasks = []
        seen_targets = set()
        for t in tasks:
            t_key = f"{t.fonte_sugerida}:{sorted(t.corporate_ids)}"
            if t_key not in seen_targets:
                seen_targets.add(t_key)
                unique_tasks.append(t)

        # Atualiza IDs de tarefas para consistÃªncia
        for idx, t in enumerate(unique_tasks, start=1):
            t.task_id = f"task_{idx}_{t.fonte_sugerida.lower().replace('vw_', '')}"

        # 3. Planejamento de ExecuÃ§Ã£o Paralela / Sequencial
        # Por padrÃ£o, tarefas analÃ­ticas de leitura de views Oracle/PG diferentes sÃ£o independentes
        # e podem rodar em paralelo.
        for t in unique_tasks:
            t.dependencias = [] # Se dependÃªncia nÃ£o-bloqueante

        tempo_decompor = int((time.perf_counter() - inicio) * 1000)
        
        # 4. ComposiÃ§Ã£o do Dashboard Mestre (Dashboard Composer)
        master_bp = self._compose_master_blueprint(unique_tasks, query_text)
        arp = self._build_arp(query_text, unique_tasks, catalog)

        return AQDDecompositionResult(
            decomposed=True,
            quantidade_consultas=len(unique_tasks),
            tempo_decomposicao_ms=tempo_decompor,
            tempo_planejamento_ms=int(tempo_decompor * 0.15) + 1,
            tasks=unique_tasks,
            master_blueprint=master_bp,
            arp=arp
        )

    def _create_single_task(
        self,
        query_text: str,
        catalog: list[ViewCatalogSummary],
        tenant_id: uuid.UUID,
        corporate_intent_plan: Any | None = None,
        semantic_hypotheses: list[Any] | None = None,
    ) -> AnalyticalTask:
        """Cria uma tarefa analÃ­tica Ãºnica padrÃ£o (fallback)."""
        view_name = "VW_VENDAS_MENSAIS"
        view_obj = next((v for v in catalog if "vendas" in v.nome_view_oracle.lower()), None)
        if view_obj:
            view_name = view_obj.nome_view_oracle

        # ExtraÃ§Ã£o dinÃ¢mica baseada em palavras-chave para metas e vendas
        c_ids = self._extract_corporate_ids_from_context(corporate_intent_plan, semantic_hypotheses)
        q_lower = query_text.lower()
        if "DIM_002" in c_ids:
            seller_view = next(
                (v for v in catalog if "vendedor" in v.nome_view_oracle.lower() or "performance" in v.nome_view_oracle.lower()),
                None,
            )
            if seller_view:
                view_name = seller_view.nome_view_oracle
        elif "DIM_003" in c_ids:
            product_view = next(
                (v for v in catalog if "produto" in v.nome_view_oracle.lower() or "ranking_produtos" in v.nome_view_oracle.lower()),
                None,
            )
            if product_view:
                view_name = product_view.nome_view_oracle

        if "vendedor" in q_lower:
            seller_view = next(
                (v for v in catalog if "vendedor" in v.nome_view_oracle.lower() or "performance" in v.nome_view_oracle.lower()),
                None,
            )
            if seller_view:
                view_name = seller_view.nome_view_oracle
            c_ids.extend(["MET_001", "DIM_002"])
        elif "produto" in q_lower:
            product_view = next(
                (v for v in catalog if "produto" in v.nome_view_oracle.lower() or "ranking_produtos" in v.nome_view_oracle.lower()),
                None,
            )
            if product_view:
                view_name = product_view.nome_view_oracle
            c_ids.extend(["MET_006", "MET_001", "DIM_003"])

        if "meta" in q_lower:
            c_ids.extend(["MET_010", "MET_009"])
            meta_view = next((v for v in catalog if "meta" in v.nome_view_oracle.lower()), None)
            if meta_view and "vendedor" not in q_lower:
                view_name = meta_view.nome_view_oracle
        if "venda" in q_lower or "faturamento" in q_lower or not c_ids:
            c_ids.append("MET_001")

        c_ids = list(dict.fromkeys(c_ids))

        return AnalyticalTask(
            task_id="task_principal",
            objetivo="AnÃ¡lise Geral",
            descricao=f"Executa a consulta analÃ­tica para responder: {query_text}",
            corporate_ids=c_ids,
            dependencias=[],
            prioridade="ALTA",
            fonte_sugerida=view_name,
            estrategia_visual="TABLE",
            resultado_esperado="Resultados consolidados em tabela"
        )

    def _create_sub_task(self, sub_query: str, catalog: list[ViewCatalogSummary], index: int) -> AnalyticalTask:
        """Cria uma subtask analÃƒÂ­tica especÃƒÂ­fica inferida do texto decomposto."""
        # Data Source Resolver simplificado integrado
        # Escolhe a melhor view baseado em termos chave do sub_query
        view_name = "VW_VENDAS_MENSAIS"
        corporate_ids = ["MET_001"]
        objetivo = "AnÃƒÂ¡lise complementar"
        vis = "TABLE"

        if "vendedor" in sub_query or "ranking" in sub_query:
            view_obj = next((v for v in catalog if "venda" in v.nome_view_oracle.lower() or "perf" in v.nome_view_oracle.lower()), None)
            if view_obj:
                view_name = view_obj.nome_view_oracle
            corporate_ids = ["MET_001", "DIM_002"]
            objetivo = "Ranking de Performance de Vendedores"
            vis = "BAR"
        elif "produto" in sub_query or "top 10" in sub_query:
            view_obj = next((v for v in catalog if "venda" in v.nome_view_oracle.lower() or "prod" in v.nome_view_oracle.lower()), None)
            if view_obj:
                view_name = view_obj.nome_view_oracle
            corporate_ids = ["MET_006", "MET_001", "DIM_003"]
            objetivo = "Top Produtos Vendidos"
            vis = "BAR"
        elif "fornecedor" in sub_query or "compra" in sub_query:
            view_obj = next((v for v in catalog if "compra" in v.nome_view_oracle.lower() or "forn" in v.nome_view_oracle.lower()), None)
            if view_obj:
                view_name = view_obj.nome_view_oracle
            else:
                # Se nÃƒÂ£o houver view de compras, usa a de KPIs
                view_obj = next((v for v in catalog if "kpi" in v.nome_view_oracle.lower()), None)
                if view_obj:
                    view_name = view_obj.nome_view_oracle
            corporate_ids = ["MET_002", "DIM_003"]
            objetivo = "Entrega e Performance de Fornecedores"
            vis = "TABLE"
        elif "atraso" in sub_query or "transportadora" in sub_query:
            view_obj = next((v for v in catalog if "logis" in v.nome_view_oracle.lower() or "transp" in v.nome_view_oracle.lower() or "kpi" in v.nome_view_oracle.lower()), None)
            if view_obj:
                view_name = view_obj.nome_view_oracle
            corporate_ids = ["MET_003", "DIM_004"]
            objetivo = "Atrasos e EficiÃƒÂªncia LogÃƒÂ­stica"
            vis = "LINE"
        elif "faturamento" in sub_query or "receita" in sub_query or "kpi" in sub_query:
            view_obj = next((v for v in catalog if "kpi" in v.nome_view_oracle.lower() or "venda" in v.nome_view_oracle.lower()), None)
            if view_obj:
                view_name = view_obj.nome_view_oracle
            corporate_ids = ["MET_001"]
            objetivo = "Acompanhamento de KPIs Executivos"
            vis = "KPI"

        return AnalyticalTask(
            task_id=f"task_{index}",
            objetivo=objetivo,
            descricao=f"Subconsulta para analisar: {sub_query}",
            corporate_ids=corporate_ids,
            dependencias=[],
            prioridade="ALTA" if index == 1 else "MEDIA",
            fonte_sugerida=view_name,
            estrategia_visual=vis,
            resultado_esperado=f"Dashboard component {vis}"
        )

    def _compose_master_blueprint(self, tasks: list[AnalyticalTask], query_text: str) -> MasterBlueprint:
        """Monta o Blueprint Mestre estruturando o layout final e blueprints filhos."""
        blueprints_filhos = []
        relacionamentos = []
        widgets = []

        # Determina posicionamento dos componentes do Grid layout
        # e.g. Se forem 2 tarefas, divide horizontalmente (50% cada)
        # Se for 1, 100% de largura
        for idx, t in enumerate(tasks):
            # Cria o blueprint filho simplificado
            bp_filho = {
                "id": f"bp_{t.task_id}",
                "nome_consulta": t.objetivo,
                "view_name": t.fonte_sugerida,
                "metrics": [m for m in t.corporate_ids if "MET" in m],
                "group_by": [d for d in t.corporate_ids if "DIM" in d],
                "filters": {},
                "visualization_type": t.estrategia_visual,
                "version": 1
            }
            blueprints_filhos.append(bp_filho)

            # Adiciona ao layout do dashboard mestre
            w_width = 12 if len(tasks) == 1 else (6 if len(tasks) == 2 else 4)
            w_height = 4
            x_pos = (idx * w_width) % 12
            y_pos = (idx * w_width) // 12 * w_height

            widgets.append({
                "id": f"widget_{t.task_id}",
                "title": t.objetivo,
                "type": t.estrategia_visual if t.estrategia_visual != "KPI" else "KPI_CARD",
                "blueprint_id": f"bp_{t.task_id}",
                "blueprintId": f"bp_{t.task_id}",
                "x": x_pos,
                "y": y_pos,
                "w": w_width,
                "h": w_height
            })

            if t.dependencias:
                for dep in t.dependencias:
                    relacionamentos.append({"from": dep, "to": t.task_id, "type": "SEQUENTIAL"})

        return MasterBlueprint(
            master_id=f"master_{uuid.uuid4().hex[:8]}",
            nome=f"Dashboard Composto: {query_text[:40]}...",
            blueprints_filhos=blueprints_filhos,
            relacionamentos=relacionamentos,
            layout={"widgets": widgets}
        )

    def _build_arp(
        self,
        query_text: str,
        tasks: list[AnalyticalTask],
        catalog: list[ViewCatalogSummary]
    ) -> AnalyticalResolutionPlan:
        """ConstrÃ³i o Analytical Resolution Plan contendo mÃºltiplas estratÃ©gias candidatos priorizados."""
        intencoes = []
        
        for task in tasks:
            group_by_ids = [cid for cid in task.corporate_ids if "DIM" in cid]
            metrics_ids = [cid for cid in task.corporate_ids if "MET" in cid]
            
            intent = IntencaoAnalitica(
                objetivo=task.objetivo,
                corporate_ids=task.corporate_ids,
                metrics=metrics_ids,
                group_by=group_by_ids,
                periodo="este mÃªs",
                filtros={},
                granularidade="mensal",
                dependencias=task.dependencias
            )
            
            estrategias = []
            
            # Caso A: DetecÃ§Ã£o de MÃ©tricas Compostas (mÃºltiplas Views com JOINs)
            composite_matches = self._detect_composite_metrics(task.corporate_ids, catalog)
            if composite_matches:
                for idx, (v1, v2, rel_join) in enumerate(composite_matches, start=1):
                    strat = CandidateStrategy(
                        id=f"strat_composite_{idx}_{task.task_id}",
                        descricao=f"EstratÃ©gia Composta via JOIN entre {v1} e {v2}",
                        corporate_ids_envolvidos=task.corporate_ids,
                        views_utilizadas=[v1, v2],
                        relacionamentos=[rel_join],
                        necessidade_join=True,
                        necessidade_agregacao=True,
                        performance_estimada="MODERADA",
                        cobertura=100.0,
                        freshness="D-1",
                        complexidade="MEDIA"
                    )
                    # Mapeia colunas fÃ­sicas estimadas temporÃ¡rias
                    strat.dimensoes = group_by_ids
                    strat.metricas = metrics_ids
                    strat = self._calculate_strategy_scores(strat, intent, catalog[0] if catalog else None)
                    estrategias.append(strat)
            
            # Caso B: Consulta direta em View compatÃ­vel
            for view in catalog:
                view_cols = [col.lower() for col in view.parametros_schema.keys()]
                view_corp_ids = []
                for col in view_cols:
                    # DicionÃ¡rio local estÃ¡tico integrado para matching
                    from services.iar_service import CORPORATE_DICTIONARY_METRICS, CORPORATE_DICTIONARY_DIMENSIONS
                    if col in CORPORATE_DICTIONARY_METRICS:
                        view_corp_ids.append(CORPORATE_DICTIONARY_METRICS[col])
                    if col in CORPORATE_DICTIONARY_DIMENSIONS:
                        view_corp_ids.append(CORPORATE_DICTIONARY_DIMENSIONS[col])
                    if col.startswith("MET_") or col.startswith("DIM_"):
                        view_corp_ids.append(col)
                        
                intersection = set(task.corporate_ids) & set(view_corp_ids)
                if intersection:
                    cobertura_percent = (len(intersection) / len(task.corporate_ids) * 100.0) if task.corporate_ids else 100.0
                    
                    strat = CandidateStrategy(
                        id=f"strat_single_{view.nome_view_oracle.lower()}_{task.task_id}",
                        descricao=f"Consulta direta na View {view.nome_view_oracle}",
                        corporate_ids_envolvidos=list(intersection),
                        views_utilizadas=[view.nome_view_oracle],
                        relacionamentos=[],
                        necessidade_join=False,
                        necessidade_agregacao=True,
                        performance_estimada="RAPIDA" if "mensal" in view.nome_view_oracle.lower() else "MODERADA",
                        cobertura=cobertura_percent,
                        freshness="D-1",
                        complexidade="BAIXA"
                    )
                    # Mapeia colunas fÃ­sicas estimadas temporÃ¡rias
                    strat.dimensoes = group_by_ids
                    strat.metricas = metrics_ids
                    strat = self._calculate_strategy_scores(strat, intent, view)
                    estrategias.append(strat)
                    
                    # Caso C: DimensÃµes equivalentes
                    equivalent_dims = []
                    for dim in group_by_ids:
                        eqs = self._get_equivalent_dimensions(dim)
                        if eqs:
                            equivalent_dims.extend(eqs)
                    if equivalent_dims:
                        strat_eq = strat.model_copy(update={
                            "id": f"strat_eq_{view.nome_view_oracle.lower()}_{task.task_id}",
                            "descricao": f"Consulta com dimensÃ£o equivalente em {view.nome_view_oracle}",
                            "dimensoes": equivalent_dims
                        })
                        strat_eq = self._calculate_strategy_scores(strat_eq, intent, view)
                        estrategias.append(strat_eq)
                        
                    # Caso D: Granularidade alternativa (ex: diÃ¡rio se solicitado na pergunta)
                    is_daily = any(t in query_text.lower() for t in ["dia", "diario", "diÃ¡ria", "diÃ¡rio"])
                    if is_daily and "mes" in view.nome_view_oracle.lower():
                        strat_daily = strat.model_copy(update={
                            "id": f"strat_daily_{view.nome_view_oracle.lower()}_{task.task_id}",
                            "descricao": f"Consulta adaptada para granularidade diÃ¡ria em {view.nome_view_oracle}",
                            "granularidade": "diaria"
                        })
                        strat_daily = self._calculate_strategy_scores(strat_daily, intent, view)
                        estrategias.append(strat_daily)

            # Ordena e aplica aprendizado controlado baseado nas estatÃ­sticas histÃ³ricas
            estrategias = self._apply_controlled_learning(estrategias)
            intent.estrategias_candidatas = estrategias
            intencoes.append(intent)
            
        return AnalyticalResolutionPlan(
            arp_id=f"arp_{uuid.uuid4().hex[:8]}",
            original_query=query_text,
            intencoes=intencoes,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )

    def _calculate_strategy_scores(
        self,
        strategy: CandidateStrategy,
        intent: IntencaoAnalitica,
        view_meta: ViewCatalogSummary | None
    ) -> CandidateStrategy:
        """Calcula os scores parciais e ponderados da estratÃ©gia candidata."""
        # 1. Coverage Score
        coverage = strategy.cobertura
        
        # 2. Semantic Score
        semantic = 90.0
        
        # 3. Metadata Score
        metadata = 95.0 if (view_meta and view_meta.descricao_para_ia) else 75.0
        
        # 4. Performance Score
        perf = 95.0 if strategy.performance_estimada == "RAPIDA" else (80.0 if strategy.performance_estimada == "MODERADA" else 60.0)
        
        # 5. Freshness Score
        fresh = 90.0 if strategy.freshness == "D-1" else 100.0
        
        # 6. Integrity Score
        integrity = 95.0 if not strategy.necessidade_join else 80.0
        
        # 7. Compatibility Score
        compat = 100.0
        if view_meta and intent.estrategias_candidatas:
            # Verifica se o tipo grÃ¡fico Ã© condizente
            if view_meta.tipo_grafico_padrao.value == strategy.prioridade:
                compat = 90.0
                
        # 8. Historical Success Score (Aprendizado Controlado)
        hist = AQD_STRATEGY_HISTORY.get(strategy.id)
        if hist and hist.get("utilizacoes", 0) > 0:
            hist_success = (hist["sucessos"] / hist["utilizacoes"]) * 100
        else:
            hist_success = 85.0 # PadrÃ£o neutro para novas estratÃ©gias
            
        # 9. Overall Resolution Score (MÃ©dia ponderada)
        overall = (
            (coverage * 0.25) +
            (semantic * 0.15) +
            (metadata * 0.10) +
            (perf * 0.10) +
            (fresh * 0.10) +
            (integrity * 0.10) +
            (compat * 0.10) +
            (hist_success * 0.10)
        )
        
        strategy.coverage_score = coverage
        strategy.semantic_score = semantic
        strategy.metadata_score = metadata
        strategy.performance_score = perf
        strategy.freshness_score = fresh
        strategy.integrity_score = integrity
        strategy.compatibility_score = compat
        strategy.historical_success_score = hist_success
        strategy.overall_resolution_score = min(max(overall, 0.0), 100.0)
        
        return strategy

    def _apply_controlled_learning(self, estrategias: list[CandidateStrategy]) -> list[CandidateStrategy]:
        """Aplica aprendizado controlado re-calculando e ordenando o ranking de estratÃ©gias pelo sucesso histÃ³rico."""
        for strat in estrategias:
            hist = AQD_STRATEGY_HISTORY.get(strat.id)
            if hist and hist.get("utilizacoes", 0) > 0:
                hist_success = (hist["sucessos"] / hist["utilizacoes"]) * 100
                strat.historical_success_score = hist_success
                # Recalcula o overall com a nova nota de sucesso histÃ³rico
                overall = (
                    (strat.coverage_score * 0.25) +
                    (strat.semantic_score * 0.15) +
                    (strat.metadata_score * 0.10) +
                    (strat.performance_score * 0.10) +
                    (strat.freshness_score * 0.10) +
                    (strat.integrity_score * 0.10) +
                    (strat.compatibility_score * 0.10) +
                    (strat.historical_success_score * 0.10)
                )
                strat.overall_resolution_score = min(max(overall, 0.0), 100.0)
                
        # Ordena por score final decrescente
        estrategias.sort(key=lambda x: x.overall_resolution_score, reverse=True)
        return estrategias

    def _get_equivalent_dimensions(self, dim: str) -> list[str]:
        if dim == "DIM_002": # vendedor
            return ["representante", "consultor", "usuario", "responsavel"]
        elif dim == "DIM_001": # cliente
            return ["comprador", "parceiro"]
        elif dim == "DIM_003": # produto
            return ["produto_nome", "item", "sku", "mercadoria"]
        return []

    def _get_equivalent_filters(self, filter_name: str) -> list[str]:
        if filter_name == "filial_id":
            return ["empresa_id", "unidade_id", "loja_id"]
        return []

    def _detect_composite_metrics(self, corporate_ids: list[str], catalog: list[ViewCatalogSummary]) -> list[tuple[str, str, dict[str, Any]]]:
        has_vendas = any(cid == "MET_001" for cid in corporate_ids)
        has_metas = any("meta" in cid.lower() or cid in {"MET_008", "MET_009", "MET_010", "MET_011"} for cid in corporate_ids)
        
        if has_vendas or has_metas:
            vw_vendas = next((v.nome_view_oracle for v in catalog if "venda" in v.nome_view_oracle.lower()), None)
            vw_metas = next((v.nome_view_oracle for v in catalog if "meta" in v.nome_view_oracle.lower()), None)
            if vw_vendas and vw_metas:
                rel_join = {"from_view": vw_vendas, "to_view": vw_metas, "on_columns": ["vendedor", "vendedor"]}
                return [(vw_vendas, vw_metas, rel_join)]
        return []

def record_strategy_success(strategy_id: str, success: bool, elapsed_time_ms: int):
    """Atualiza o repositÃ³rio de histÃ³rico para aprendizado controlado das estratÃ©gias analÃ­ticas."""
    if strategy_id not in AQD_STRATEGY_HISTORY:
        AQD_STRATEGY_HISTORY[strategy_id] = {"utilizacoes": 0, "sucessos": 0, "falhas": 0, "tempo_total_ms": 0}
    
    AQD_STRATEGY_HISTORY[strategy_id]["utilizacoes"] += 1
    if success:
        AQD_STRATEGY_HISTORY[strategy_id]["sucessos"] += 1
    else:
        AQD_STRATEGY_HISTORY[strategy_id]["falhas"] += 1
    AQD_STRATEGY_HISTORY[strategy_id]["tempo_total_ms"] += elapsed_time_ms

# InstÃ¢ncia Singleton do AQD
aqd = AnalyticalQueryDecomposer()
