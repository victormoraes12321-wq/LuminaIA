import logging
import re
import time
import unicodedata
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from models.view_catalog import ChartType
from schemas.view_catalog import ViewCatalogSummary
from services.query_planner import QueryPlan, QueryPlanItem
from services.ai_service import IntentionResponse
from services.ai_credential_manager import AICMError
from services.ai_invocation_manager import ai_invocation_manager
from services.cache_service import global_cache
from services.plan_validator import resolve_relative_date_range

logger = logging.getLogger("luminaai.services.iar")

# ── Dicionários Corporativos Estáticos (Resolução Local Rápida) ──
CORPORATE_DICTIONARY_METRICS = {
    "receita": "MET_001",
    "faturamento": "MET_001",
    "faturado": "MET_001",
    "venda": "MET_001",
    "vendas": "MET_001",
    "valor_venda": "MET_001",
    "valor_total": "MET_001",
    "total_venda": "MET_001",
    "retorno_financeiro": "MET_001",
    "lucro": "MET_003",
    "margem": "MET_004",
    "ticket_medio": "MET_005",
    "ticket": "MET_005",
    "ticket_medio_compra": "MET_005",
    "quantidade": "MET_006",
    "volume": "MET_006",
    "pedidos": "MET_006",
    "total_itens": "MET_006",
    "unidades_vendidas": "MET_006",
    "meta_mensal": "MET_009",
    "meta": "MET_010",
    "metas": "MET_010",
}

CORPORATE_DICTIONARY_DIMENSIONS = {
    "cliente": "DIM_001",
    "comprador": "DIM_001",
    "parceiro": "DIM_001",
    "vendedor": "DIM_002",
    "usuario": "DIM_002",
    "representante": "DIM_002",
    "consultor": "DIM_002",
    "responsavel_venda": "DIM_002",
    "produto": "DIM_003",
    "item": "DIM_003",
    "mercadoria": "DIM_003",
    "sku": "DIM_003",
    "categoria": "DIM_004",
    "grupo": "DIM_004",
    "regiao": "DIM_005",
    "filial": "DIM_005",
    "loja": "DIM_005",
    "unidade": "DIM_005",
    "cidade": "DIM_010",
    "municipio": "DIM_010",
    "estado": "DIM_011",
    "uf": "DIM_011",
}

CORPORATE_CALENDAR = {
    "hoje": "TODAY",
    "ontem": "YESTERDAY",
    "semana": "CURRENT_WEEK",
    "mes": "CURRENT_MONTH",
    "mês": "CURRENT_MONTH",
    "ano": "CURRENT_YEAR",
    "ultimos_30_dias": "LAST_30_DAYS",
    "competencia": "FISCAL_PERIOD",
    "safra": "HARVEST_PERIOD",
    "exercicio": "FISCAL_YEAR",
}

class IARAuditorItem(BaseModel):
    timestamp: str
    original_query: str
    steps_executed: List[str]
    corporate_ids_involved: List[str]
    views_evaluated: List[Dict[str, Any]]
    winning_strategy: str
    resolution_score: float
    justification: str
    elapsed_time_ms: int

class IntelligentAnalyticalResolver:
    """
    Intelligent Analytical Resolver (IAR) — Módulo Enterprise LuminaAI
    ------------------------------------------------------------------
    Responsável por interceptar, adaptar e resolver incompatibilidades
    semânticas e físicas de planos analíticos em runtime através de 14 etapas.
    """

    def __init__(self):
        self.auditor_logs: List[IARAuditorItem] = []

    def _normalize_text(self, value: Any) -> str:
        text = str(value or "").lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9_]+", " ", text)

    def _infer_requested_domain(
        self,
        original_query: str,
        intentions: List[IntentionResponse],
    ) -> Optional[str]:
        """
        Identifica o domínio forte solicitado pelo usuário.

        O IAR pode corrigir uma view, mas não pode trocar o domínio da pergunta
        (ex.: produto -> vendas mensais). Domínios genéricos de venda não
        bloqueiam redirecionamento porque muitas análises corporativas passam
        por vendas.
        """
        query = self._normalize_text(original_query)
        strong_terms = {
            "PRODUTOS": ("produto", "produtos", "item", "itens", "sku", "mercadoria"),
            "VENDEDORES": ("vendedor", "vendedores", "representante", "representantes", "consultor", "consultores"),
            "CLIENTES": ("cliente", "clientes", "comprador", "compradores", "parceiro", "parceiros"),
            "ESTOQUE": ("estoque", "estoques", "saldo", "cobertura", "giro"),
            "FORNECEDORES": ("fornecedor", "fornecedores", "supplier", "suppliers"),
        }

        for domain, terms in strong_terms.items():
            if any(re.search(rf"\b{re.escape(term)}\b", query) for term in terms):
                return domain

        for intention in intentions:
            fields = [
                getattr(intention, "entidade_alvo", ""),
                getattr(intention, "operacao", ""),
            ]
            if intention.plano_estruturado:
                fields.extend(intention.plano_estruturado.group_by or [])
                fields.extend(intention.plano_estruturado.metrics or [])

            haystack = self._normalize_text(" ".join(str(field) for field in fields))
            if "dim_002" in haystack:
                return "PRODUTOS"
            if "dim_001" in haystack:
                return "VENDEDORES"
            if "dim_003" in haystack:
                return "CLIENTES"
            for domain, terms in strong_terms.items():
                if any(re.search(rf"\b{re.escape(term)}\b", haystack) for term in terms):
                    return domain

        return None

    def _view_matches_requested_domain(
        self,
        view_name: str,
        requested_domain: Optional[str],
        catalog: List[ViewCatalogSummary],
    ) -> bool:
        if not requested_domain:
            return True

        view_schema = next((v for v in catalog if v.nome_view_oracle == view_name), None)
        schema_text = ""
        if view_schema:
            schema_text = " ".join(
                [
                    view_schema.nome_view_oracle,
                    getattr(view_schema, "descricao_para_ia", "") or "",
                    " ".join(view_schema.parametros_schema.keys()),
                ]
            )
        else:
            schema_text = view_name

        haystack = self._normalize_text(schema_text)
        domain_terms = {
            "PRODUTOS": ("produto", "produtos", "item", "itens", "sku", "mercadoria"),
            "VENDEDORES": ("vendedor", "vendedores", "representante", "representantes", "consultor", "consultores"),
            "CLIENTES": ("cliente", "clientes", "comprador", "compradores", "parceiro", "parceiros"),
            "ESTOQUE": ("estoque", "estoques", "saldo", "cobertura", "giro"),
            "FORNECEDORES": ("fornecedor", "fornecedores", "supplier", "suppliers"),
        }
        return any(term in haystack for term in domain_terms.get(requested_domain, ()))

    def _requires_daily_granularity(
        self,
        original_query: str,
        intentions: List[IntentionResponse],
    ) -> bool:
        query = self._normalize_text(original_query)
        if any(term in query for term in ("dia", "diario", "diaria", "hoje", "ontem")):
            return True
        if re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", original_query or ""):
            return True
        resolved = resolve_relative_date_range(original_query or "")
        if resolved and resolved[0] == resolved[1]:
            return True

        for intention in intentions:
            params = dict(getattr(intention, "parametros", {}) or {})
            if params.get("data_inicio") and params.get("data_inicio") == params.get("data_fim"):
                return True
            if intention.plano_estruturado and intention.plano_estruturado.filters:
                date_range = intention.plano_estruturado.filters.date_range or ""
                resolved_range = resolve_relative_date_range(date_range)
                if resolved_range and resolved_range[0] == resolved_range[1]:
                    return True
        return False

    def _is_monthly_view(self, view_name: str | None) -> bool:
        normalized = self._normalize_text(view_name or "")
        return "mensal" in normalized or "mensais" in normalized or "faturamento_mensal" in normalized

    def _find_daily_view(self, catalog: List[ViewCatalogSummary]) -> Optional[ViewCatalogSummary]:
        scored: list[tuple[int, ViewCatalogSummary]] = []
        for view in catalog:
            name = self._normalize_text(view.nome_view_oracle)
            desc = self._normalize_text(getattr(view, "descricao_para_ia", "") or "")
            score = 0
            if "vendas_contexto_geral" in name:
                score += 12
            if "detalhe_pedidos" in name:
                score += 10
            if "diario" in name or "diaria" in name or "data_ref" in desc or "dia" in desc:
                score += 4
            if "vendas" in name:
                score += 2
            if self._is_monthly_view(view.nome_view_oracle):
                score -= 12
            scored.append((score, view))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1] if scored and scored[0][0] > 0 else None

    def _has_locked_explicit_source(
        self,
        query_plan: QueryPlan,
        intentions: List[IntentionResponse],
        catalog: List[ViewCatalogSummary],
    ) -> bool:
        """
        Preserve explicit high-confidence sources selected by the intent layer.

        The IAR may correct incompatible plans, but it must not replace a
        concrete source that the NLU/planner already selected with high
        confidence just because a generic ARP strategy scores better.
        """
        principal = query_plan.consulta_principal
        if not principal.view_catalog_id or not principal.view_name:
            return False

        principal_id = str(principal.view_catalog_id)
        principal_name = str(principal.view_name or "").upper()
        catalog_view = next((v for v in catalog if str(v.id) == principal_id), None)
        if catalog_view and catalog_view.nome_view_oracle.upper() != principal_name:
            return False

        for intention in intentions:
            if str(getattr(intention, "view_catalog_id", "") or "") != principal_id:
                continue
            if float(getattr(intention, "confianca", 0.0) or 0.0) < 0.90:
                continue
            plan = getattr(intention, "plano_estruturado", None)
            plan_intent = str(getattr(plan, "intent", "") or "").upper()
            if principal_name.startswith("VW_TEST") or principal_name in plan_intent:
                return True
        return False

    async def resolve_incompatibilities(
        self,
        query_plan: QueryPlan,
        intentions: List[IntentionResponse],
        catalog: List[ViewCatalogSummary],
        tenant_id: Any,
        db: AsyncSession,
        original_query: str = "",
        arp: Optional[Any] = None
    ) -> QueryPlan:
        """
        Ponto de entrada do IAR. Executa o pipeline sequencial de 14 etapas
        para resolver incompatibilidades do plano analítico.
        """
        inicio = time.perf_counter()
        primary_view = query_plan.consulta_principal.view_name
        requested_domain = self._infer_requested_domain(original_query, intentions)
        requires_daily_granularity = self._requires_daily_granularity(original_query, intentions)
        explicit_source_locked = self._has_locked_explicit_source(query_plan, intentions, catalog)
        steps = []
        corporate_ids = []
        views_scores = []
        winning_strategy = "Default Execution"
        score = 100.0
        justification = "Plano original 100% compatível, nenhuma correção necessária."

        logger.info("[IAR] Iniciando Intelligent Analytical Resolver para consulta...")

        # ── ETAPA 1: Alias Resolution ──
        steps.append("1. Alias Resolution")
        for intention in intentions:
            if intention.plano_estruturado:
                # Resolve aliases de métricas
                resolved_metrics = []
                for m in intention.plano_estruturado.metrics:
                    canon = self._resolve_alias_metric(m)
                    resolved_metrics.append(canon)
                intention.plano_estruturado.metrics = resolved_metrics

                # Resolve aliases de dimensões
                resolved_group = []
                for d in intention.plano_estruturado.group_by:
                    canon = self._resolve_alias_dimension(d)
                    resolved_group.append(canon)
                intention.plano_estruturado.group_by = resolved_group

        # ── ETAPA 2: Corporate ID Resolution ──
        steps.append("2. Corporate ID Resolution")
        for intention in intentions:
            if intention.plano_estruturado:
                # Converte métricas e dimensões para Corporate IDs exatos
                c_metrics = []
                for m in intention.plano_estruturado.metrics:
                    c_id = self._to_corporate_id(m, CORPORATE_DICTIONARY_METRICS)
                    c_metrics.append(c_id)
                    corporate_ids.append(c_id)
                intention.plano_estruturado.metrics = c_metrics

                c_dims = []
                for d in intention.plano_estruturado.group_by:
                    c_id = self._to_corporate_id(d, CORPORATE_DICTIONARY_DIMENSIONS)
                    c_dims.append(c_id)
                    corporate_ids.append(c_id)
                intention.plano_estruturado.group_by = c_dims

        # A conversão física de colunas foi postergada para rodar após a seleção definitiva da View.

        # ── ETAPA 4: Metric Resolution & Fallback de IA Enxuto ──
        steps.append("4. Metric Resolution")
        metric_fail = False
        for intention in intentions:
            if intention.plano_estruturado:
                for m in intention.plano_estruturado.metrics:
                    if m == "unknown_metric" or not m:
                        metric_fail = True
                        break
        
        if metric_fail:
            # Caso não achou métrica compatível localmente, tenta fallback de IA enxuto
            logger.info("[IAR] Métricas indefinidas detectadas. Acionando IA Fallback de baixo custo...")
            steps.append("IA Semantic Fallback (Etapa 4)")
            fallback_metric = await self._ai_semantic_fallback(original_query, list(CORPORATE_DICTIONARY_METRICS.keys()))
            if fallback_metric:
                canon_metric = CORPORATE_DICTIONARY_METRICS.get(fallback_metric)
                if canon_metric:
                    if primary_view:
                        view_schema = next((v for v in catalog if v.nome_view_oracle == primary_view), None)
                        if view_schema:
                            canon_metric = self._to_physical_name(canon_metric, view_schema, "MET")
                    logger.info("[IAR] [IA MATCH] Métrica mapeada para: %s (%s)", fallback_metric, canon_metric)
                    for intention in intentions:
                        if intention.plano_estruturado:
                            intention.plano_estruturado.metrics = [
                                canon_metric if (mx == "unknown_metric" or not mx) else mx
                                for mx in intention.plano_estruturado.metrics
                            ]
                            corporate_ids.append(canon_metric)

        # ── ETAPA 5: Dimension Resolution ──
        steps.append("5. Dimension Resolution")
        dim_fail = False
        for intention in intentions:
            if intention.plano_estruturado:
                for d in intention.plano_estruturado.group_by:
                    if d == "unknown_dimension" or not d:
                        dim_fail = True
                        break
                        
        if dim_fail:
            logger.info("[IAR] Dimensões indefinidas detectadas. Acionando IA Fallback de baixo custo...")
            steps.append("IA Semantic Fallback (Etapa 5)")
            fallback_dim = await self._ai_semantic_fallback(original_query, list(CORPORATE_DICTIONARY_DIMENSIONS.keys()))
            if fallback_dim:
                canon_dim = CORPORATE_DICTIONARY_DIMENSIONS.get(fallback_dim)
                if canon_dim:
                    if primary_view:
                        view_schema = next((v for v in catalog if v.nome_view_oracle == primary_view), None)
                        if view_schema:
                            canon_dim = self._to_physical_name(canon_dim, view_schema, "DIM")
                    logger.info("[IAR] [IA MATCH] Dimensão mapeada para: %s (%s)", fallback_dim, canon_dim)
                    for intention in intentions:
                        if intention.plano_estruturado:
                            intention.plano_estruturado.group_by = [
                                canon_dim if (dx == "unknown_dimension" or not dx) else dx
                                for dx in intention.plano_estruturado.group_by
                            ]
                            corporate_ids.append(canon_dim)

        # ── ETAPA 6: Time Resolution ──
        steps.append("6. Time Resolution")
        for intention in intentions:
            if intention.plano_estruturado and intention.plano_estruturado.filters:
                dr = intention.plano_estruturado.filters.date_range
                if dr:
                    canon_time = self._resolve_time_range(dr)
                    intention.plano_estruturado.filters.date_range = canon_time

        # ── ETAPA 7: Granularity Resolution ──
        steps.append("7. Granularity Resolution")
        # Se a pergunta pede uma data di?ria, uma view mensal n?o pode ser a fonte final.
        if requires_daily_granularity and primary_view:
            view_schema = next((v for v in catalog if v.nome_view_oracle == primary_view), None)
            if view_schema and self._is_monthly_view(view_schema.nome_view_oracle):
                daily_view = self._find_daily_view(catalog)
                if daily_view:
                    logger.warning(
                        "[IAR] Conflito de granularidade: di?rio solicitado mas a view '%s' ? mensal. Redirecionando para '%s'.",
                        primary_view,
                        daily_view.nome_view_oracle,
                    )
                    steps.append("Granularity Redirected to Daily View")
                    query_plan.consulta_principal.view_name = daily_view.nome_view_oracle
                    query_plan.consulta_principal.view_catalog_id = str(daily_view.id)
                    primary_view = daily_view.nome_view_oracle

        # ── ETAPA 8: View Resolution (Pontuação e Classificação) ──
        steps.append("8. View Resolution")
        candidate_views = []
        for v in catalog:
            score_v = self._calculate_resolution_score(v, intentions)
            candidate_views.append({"view_name": v.nome_view_oracle, "score": score_v, "id": v.id})
            views_scores.append({"view_name": v.nome_view_oracle, "score": score_v})

        candidate_views.sort(key=lambda x: x["score"], reverse=True)

        # Se um plano ARP com múltiplas estratégias estiver disponível, prioriza o seu redirecionamento
        if arp and arp.intencoes and not explicit_source_locked:
            arp_intent = next(
                (i for i in arp.intencoes if i.objetivo.lower() in original_query.lower() or i.objetivo.lower() in query_plan.consulta_principal.objetivo.lower()),
                arp.intencoes[0]
            )
            if arp_intent and arp_intent.estrategias_candidatas:
                best_arp_strat = arp_intent.estrategias_candidatas[0]
                if best_arp_strat.views_utilizadas and best_arp_strat.views_utilizadas[0] != primary_view:
                    target_view = best_arp_strat.views_utilizadas[0]
                    if requires_daily_granularity and self._is_monthly_view(target_view):
                        logger.warning(
                            "[IAR] [ARP REDIRECT BLOCKED] Granularidade diaria impede troca de '%s' para view mensal '%s'",
                            primary_view,
                            target_view,
                        )
                        steps.append("ARP Redirect Blocked by Temporal Granularity Guard")
                    elif not self._view_matches_requested_domain(target_view, requested_domain, catalog):
                        logger.warning(
                            "[IAR] [ARP REDIRECT BLOCKED] Domínio solicitado '%s' impede troca de '%s' para '%s'",
                            requested_domain,
                            primary_view,
                            target_view,
                        )
                        steps.append("ARP Redirect Blocked by Domain Guard")
                    elif best_arp_strat.overall_resolution_score >= 60.0:
                        logger.info(
                            "[IAR] [ARP REDIRECT] Substituindo view '%s' pela estratégia vencedora do ARP '%s' (Score %.1f)",
                            primary_view, target_view, best_arp_strat.overall_resolution_score
                        )
                        winning_strategy = f"ARP Redirect: {best_arp_strat.id}"
                        score = best_arp_strat.overall_resolution_score
                        justification = best_arp_strat.descricao
                        query_plan.consulta_principal.view_name = target_view
                        matched_meta = next((v for v in catalog if v.nome_view_oracle == target_view), None)
                        if matched_meta:
                            query_plan.consulta_principal.view_catalog_id = str(matched_meta.id)
        
        # Se a View principal do plano original tiver pontuação muito baixa (< 50) e houver alternativa melhor (Fallback local)
        elif candidate_views and primary_view and not explicit_source_locked:
            current_score_entry = next((cv for cv in candidate_views if cv["view_name"] == primary_view), None)
            current_score = current_score_entry["score"] if current_score_entry else 0.0
            compatible_candidates = [
                cv for cv in candidate_views
                if self._view_matches_requested_domain(cv["view_name"], requested_domain, catalog)
                and not (requires_daily_granularity and self._is_monthly_view(cv["view_name"]))
            ]
            best_cand = (compatible_candidates or candidate_views)[0]

            if best_cand["score"] > current_score + 20 and best_cand["score"] >= 60.0:
                logger.info(
                    "[IAR] View original '%s' (Score %.1f) substituída pela melhor alternativa '%s' (Score %.1f)",
                    primary_view, current_score, best_cand["view_name"], best_cand["score"]
                )
                winning_strategy = f"Redirecionamento de View: {best_cand['view_name']}"
                score = best_cand["score"]
                justification = f"View '{best_cand['view_name']}' possui maior compatibilidade com as métricas e dimensões solicitadas."
                query_plan.consulta_principal.view_name = best_cand["view_name"]
                query_plan.consulta_principal.view_catalog_id = str(best_cand["id"])
        elif explicit_source_locked:
            steps.append("View Redirect Blocked by Explicit Source Lock")

        # ── ETAPA 9: Multi-View Resolution ──
        steps.append("9. Multi-View Resolution")
        # (Futuro: Se nenhuma View isolada der score >= 60%, avalia JOIN entre Views do mesmo upstream)

        # ── ETAPA 10: Join Resolution ──
        steps.append("10. Join Resolution")

        # ── ETAPA 3: Physical Column Resolution (Diferida) ──
        steps.append("3. Physical Column Resolution")
        final_view = query_plan.consulta_principal.view_name
        if final_view:
            view_schema = next((v for v in catalog if v.nome_view_oracle == final_view), None)
            if view_schema:
                for intention in intentions:
                    if intention.plano_estruturado:
                        intention.plano_estruturado.metrics = [
                            self._to_physical_name(m, view_schema, "MET") for m in intention.plano_estruturado.metrics
                        ]
                        intention.plano_estruturado.group_by = [
                            self._to_physical_name(d, view_schema, "DIM") for d in intention.plano_estruturado.group_by
                        ]

        # ── ETAPA 11: Blueprint Adaptation ──
        steps.append("11. Blueprint Adaptation")
        # Garante que adaptamos o Blueprint de execução em runtime para as colunas físicas corretas
        adapted_metrics = []
        adapted_group = []
        for intention in intentions:
            if intention.plano_estruturado:
                adapted_metrics.extend(intention.plano_estruturado.metrics)
                adapted_group.extend(intention.plano_estruturado.group_by)
        # As colunas físicas adaptadas já residem no plano estruturado das intenções correspondentes.

        # ── ETAPA 12: Cache Resolution ──
        steps.append("12. Cache Resolution")
        # Tenta reuso do cache
        cache_key = f"iar_cache:{tenant_id}:{original_query.strip().lower()}"
        cached_result = global_cache.get(tenant_id, "iar", cache_key)
        if cached_result:
            logger.info("[IAR] [CACHE HIT] Cache de plano do IAR reutilizado com sucesso.")
            steps.append("Cache Reused")
            winning_strategy = "Cache Resolution"

        # ── ETAPA 13: Version Resolution ──
        steps.append("13. Version Resolution")

        # ── ETAPA 14: Final Validation ──
        steps.append("14. Final Validation")
        # Higieniza nulos e valores de refino vazios para execução segura nas intenções
        for intention in intentions:
            if intention.plano_estruturado:
                if not intention.plano_estruturado.metrics:
                    intention.plano_estruturado.metrics = ["receita_total"]
                    corporate_ids.append("MET_001")

        # Grava auditoria final para fins de rastreabilidade
        fim_ms = int((time.perf_counter() - inicio) * 1000)
        auditor_item = IARAuditorItem(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            original_query=original_query,
            steps_executed=steps,
            corporate_ids_involved=list(set(corporate_ids)),
            views_evaluated=views_scores,
            winning_strategy=winning_strategy,
            resolution_score=score,
            justification=justification,
            elapsed_time_ms=fim_ms
        )
        self.auditor_logs.append(auditor_item)
        logger.info("[IAR] Resolução do IAR concluída em %d ms! Estratégia: %s", fim_ms, winning_strategy)

        # Salva o plano resolvido no cache
        global_cache.set(tenant_id, "iar", cache_key, query_plan, ttl_seconds=300)

        return query_plan

    def _resolve_alias_metric(self, metric: str) -> str:
        clean = metric.lower().replace(" ", "_").strip()
        if clean in CORPORATE_DICTIONARY_METRICS:
            return clean
        # Busca parcial simples
        for alias in CORPORATE_DICTIONARY_METRICS.keys():
            if alias in clean or clean in alias:
                return alias
        return metric

    def _resolve_alias_dimension(self, dimension: str) -> str:
        clean = dimension.lower().replace(" ", "_").strip()
        if clean in CORPORATE_DICTIONARY_DIMENSIONS:
            return clean
        for alias in CORPORATE_DICTIONARY_DIMENSIONS.keys():
            if alias in clean or clean in alias:
                return alias
        return dimension

    def _to_corporate_id(self, key: str, dictionary: Dict[str, str]) -> str:
        clean = key.lower().replace(" ", "_").strip()
        if clean in dictionary:
            return dictionary[clean]
        # Se já for um Corporate ID válido (ex: MET_001), mantém
        if key.startswith("MET_") or key.startswith("DIM_"):
            return key
        return key

    def _to_physical_name(self, corporate_id: str, view_schema: ViewCatalogSummary, layer_type: str) -> str:
        # Tenta mapear o Corporate ID de volta para o nome físico de coluna suportado no schema
        cols = list(view_schema.parametros_schema.keys())
        
        # Obtém todos os aliases que mapeiam para o Corporate ID fornecido
        dictionary = CORPORATE_DICTIONARY_METRICS if layer_type == "MET" else CORPORATE_DICTIONARY_DIMENSIONS
        aliases = [k for k, v in dictionary.items() if v == corporate_id]

        if not aliases:
            # Se o próprio ID já for uma coluna da view, mantém
            for col in cols:
                if col.lower() == corporate_id.lower():
                    return col
            return corporate_id

        # Busca um alias que bata com alguma coluna da view
        for alias in aliases:
            for col in cols:
                if col.lower() == alias.lower() or alias.lower() in col.lower() or col.lower() in alias.lower():
                    return col

        # Se não deu match por alias, verifica se o próprio ID de metadados está entre as colunas da view
        for col in cols:
            if col.lower() == corporate_id.lower():
                return col

        # Retorna a primeira coluna condizente do schema
        return cols[0] if cols else corporate_id

    def _resolve_time_range(self, date_range: str) -> str:
        clean = date_range.lower().replace(" ", "_").strip()
        if clean in CORPORATE_CALENDAR:
            return CORPORATE_CALENDAR[clean]
        return date_range

    def _calculate_resolution_score(self, view: ViewCatalogSummary, intentions: List[IntentionResponse]) -> float:
        """
        Cálculo do Resolution Score (0-100) da View baseado em compatibilidade de métricas e dimensões.
        """
        score = 50.0 # Pontuação base
        cols = [c.lower() for c in view.parametros_schema.keys()]

        # Mapeia colunas da view para Corporate IDs
        view_corp_ids = []
        for col in cols:
            # Tenta métricas
            if col in CORPORATE_DICTIONARY_METRICS:
                view_corp_ids.append(CORPORATE_DICTIONARY_METRICS[col])
            # Tenta dimensões
            if col in CORPORATE_DICTIONARY_DIMENSIONS:
                view_corp_ids.append(CORPORATE_DICTIONARY_DIMENSIONS[col])
            # Se for ID exato
            if col.startswith("MET_") or col.startswith("DIM_"):
                view_corp_ids.append(col)

        matched_metrics = 0
        total_metrics = 0
        matched_dims = 0
        total_dims = 0

        for intention in intentions:
            if intention.plano_estruturado:
                # Métricas
                for m in intention.plano_estruturado.metrics:
                    total_metrics += 1
                    c_m = self._to_corporate_id(m, CORPORATE_DICTIONARY_METRICS)
                    if c_m in view_corp_ids:
                        matched_metrics += 1
                # Dimensões
                for d in intention.plano_estruturado.group_by:
                    total_dims += 1
                    c_d = self._to_corporate_id(d, CORPORATE_DICTIONARY_DIMENSIONS)
                    if c_d in view_corp_ids:
                        matched_dims += 1

        # Adiciona bônus por métricas compatíveis
        if total_metrics > 0:
            score += (matched_metrics / total_metrics) * 30
        else:
            score += 15

        # Adiciona bônus por dimensões compatíveis
        if total_dims > 0:
            score += (matched_dims / total_dims) * 20
        else:
            score += 10

        return min(max(score, 0.0), 100.0)

    async def _ai_semantic_fallback(self, query: str, opcoes: List[str]) -> Optional[str]:
        """
        Fallback enxuto utilizando IA via AICM para associar semanticamente
        um termo desconhecido a uma das opcoes do dicionario corporativo.
        """
        import json

        try:
            prompt = (
                f"Analise a pergunta do usuario: '{query}'\n"
                f"Identifique qual dessas opcoes se adequa semanticamente ao objetivo da pergunta:\n"
                f"{json.dumps(opcoes)}\n"
                f"Responda APENAS a string exata correspondente da opcao escolhida. Nao adicione pontuacao ou explicacao."
            )

            async def _request_completion(client: Any, model: str, _lease: Any) -> Any:
                return await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=15,
                    temperature=0.0,
                )

            response = await ai_invocation_manager.invoke(
                tenant_id=None,
                requested_model="gpt-4o-mini",
                purpose="iar_semantic_fallback",
                context={
                    "query": query,
                    "fresh_data_required": False,
                    "expected_confidence": 85,
                    "estimated_tokens": 220,
                },
                force_ai=False,
                allow_response_reuse=True,
                operation=_request_completion,
            )
            result = response.choices[0].message.content.strip().lower()
            for op in opcoes:
                if op.lower() in result or result in op.lower():
                    return op
        except AICMError as exc:
            logger.info("[IAR] Fallback IA indisponivel via AICM: %s", exc)
        except Exception as exc:
            logger.warning("[IAR] Falha ao executar fallback de IA do IAR: %s", exc)
        return None
# Instância singleton global do IAR
iar = IntelligentAnalyticalResolver()
