"""
LuminaAI — Intent Fingerprint Generator
-----------------------------------------
Gera o fingerprint semântico de uma intenção de consulta.

O fingerprint é o "DNA" de uma análise: representa sua intenção
em termos de conceitos normalizados (domínio, operação, entidade,
granularidade, métricas, agrupamentos).

REGRA FUNDAMENTAL: Nunca usa texto literal. Sempre normaliza para
conceitos semânticos antes de gerar o fingerprint. "Quanto vendemos
hoje" e "Qual foi o faturamento de ontem" devem gerar fingerprints
com o mesmo `domain` e `operation`, diferindo apenas no `time_scope`.

O `intent_key` é um hash SHA-256 dos campos semânticos estruturais
(sem período temporal), permitindo que consultas sobre o mesmo tema
em períodos diferentes sejam reconhecidas como compatíveis.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger("luminaai.data_platform.intent_fingerprint")


# ── Mapeamentos Semânticos Canônicos ─────────────────────────────────────────

_DOMAIN_MAP: dict[str, str] = {
    # Vendas e Faturamento
    "venda": "VENDAS", "vendas": "VENDAS", "faturamento": "VENDAS",
    "receita": "VENDAS", "faturou": "VENDAS", "vendeu": "VENDAS",
    "vw_vendas": "VENDAS", "vw_faturamento": "VENDAS",
    # Produtos
    "produto": "PRODUTOS", "produtos": "PRODUTOS", "item": "PRODUTOS",
    "itens": "PRODUTOS", "vw_produtos": "PRODUTOS", "sku": "PRODUTOS",
    # Clientes
    "cliente": "CLIENTES", "clientes": "CLIENTES", "comprador": "CLIENTES",
    "vw_clientes": "CLIENTES",
    # Estoque
    "estoque": "ESTOQUE", "inventario": "ESTOQUE", "vw_estoque": "ESTOQUE",
    "saldo": "ESTOQUE",
    # Financeiro
    "financeiro": "FINANCEIRO", "caixa": "FINANCEIRO", "pagamento": "FINANCEIRO",
    "vw_financeiro": "FINANCEIRO", "inadimplencia": "FINANCEIRO",
    # Compras
    "compra": "COMPRAS", "fornecedor": "COMPRAS", "vw_compras": "COMPRAS",
    # Vendedores
    "vendedor": "VENDEDORES", "representante": "VENDEDORES",
    "vw_vendedores": "VENDEDORES",
    # Regiões
    "regiao": "REGIOES", "cidade": "REGIOES", "uf": "REGIOES",
    "estado": "REGIOES", "filial": "REGIOES",
}

_OPERATION_MAP: dict[str, str] = {
    "soma": "AGGREGATION", "total": "AGGREGATION", "somatorio": "AGGREGATION",
    "media": "AGGREGATION", "media_movel": "AGGREGATION",
    "count": "COUNT", "quantidade": "COUNT", "contagem": "COUNT",
    "ranking": "RANKING", "top": "RANKING", "maior": "RANKING",
    "menor": "RANKING", "lider": "RANKING",
    "comparacao": "COMPARISON", "versus": "COMPARISON", "vs": "COMPARISON",
    "evolucao": "COMPARISON", "crescimento": "COMPARISON",
    "tendencia": "TREND", "projecao": "TREND", "previsao": "TREND",
    "historico": "TREND", "serie_temporal": "TREND",
    "detalhe": "SELECT", "lista": "SELECT", "listar": "SELECT",
    "mostrar": "SELECT", "ver": "SELECT",
    "margem": "MARGIN", "lucro": "MARGIN", "markup": "MARGIN",
}

_ENTITY_MAP: dict[str, str] = {
    "produto": "PRODUTO", "item": "PRODUTO",
    "cliente": "CLIENTE", "comprador": "CLIENTE",
    "vendedor": "VENDEDOR", "representante": "VENDEDOR",
    "regiao": "REGIAO", "cidade": "REGIAO", "estado": "REGIAO",
    "filial": "FILIAL",
    "categoria": "CATEGORIA", "grupo": "CATEGORIA",
    "periodo": "PERIODO", "mes": "PERIODO", "dia": "PERIODO",
    "geral": "GERAL",
}

_GRANULARITY_MAP: dict[str, str] = {
    "dia": "DIARIA", "diario": "DIARIA", "hoje": "DIARIA", "ontem": "DIARIA",
    "semana": "SEMANAL", "semanal": "SEMANAL",
    "mes": "MENSAL", "mensal": "MENSAL", "mes_passado": "MENSAL",
    "trimestre": "TRIMESTRAL", "trimestral": "TRIMESTRAL",
    "ano": "ANUAL", "anual": "ANUAL", "ytd": "ANUAL",
    "geral": "GERAL",
}

_ANALYSIS_TYPE_MAP: dict[str, str] = {
    "AGGREGATION": "AGGREGATION",
    "COUNT": "COUNT",
    "RANKING": "RANKING",
    "COMPARISON": "COMPARISON",
    "TREND": "TREND",
    "SELECT": "SELECT",
    "MARGIN": "AGGREGATION",  # Margem é um tipo de agregação
}


class IntentFingerprintGenerator:
    """
    Gera fingerprints semânticos de intenções de consulta.

    O fingerprint captura a INTENÇÃO da análise, não o texto da pergunta.
    Duas perguntas sobre o mesmo tema geram o mesmo fingerprint (ou compatível).
    """

    def generate(
        self,
        intention: Any,
        plan: Any | None = None,
        pergunta: str = "",
    ) -> dict[str, Any]:
        """
        Gera o fingerprint semântico de uma intenção.

        Parâmetros:
            intention — IntentionResponse do pipeline QIE
            plan      — QueryPlan gerado pelo Planner (opcional)
            pergunta  — Pergunta original (apenas para enriquecimento, nunca para hash)

        Retorno:
            dict com: intent_key, domain, operation, entity, granularity,
                     metrics, group_by, analysis_type, time_scope_type
        """
        # Extrai campos do plano estruturado (mais preciso) ou da intenção direta
        structured = getattr(intention, "plano_estruturado", None)

        domain = self._extract_domain(intention, plan)
        operation = self._extract_operation(intention, structured)
        entity = self._extract_entity(intention, structured, plan)
        granularity = self._extract_granularity(intention, structured)
        metrics = self._extract_metrics(structured)
        group_by = self._extract_group_by(structured, plan)
        analysis_type = self._extract_analysis_type(intention, structured)
        time_scope_type = self._extract_time_scope_type(intention, structured)

        # Campos estruturais (sem período E sem granularidade — ambos são temporais/variáveis)
        structural_fields = {
            "domain": domain,
            "operation": operation,
            "entity": entity,
            "metrics": sorted(metrics),
            "group_by": sorted(group_by),
            "analysis_type": analysis_type,
        }

        # intent_key: hash apenas dos campos estruturais (período e granularidade excluídos)
        canonical = json.dumps(structural_fields, sort_keys=True, ensure_ascii=False)
        intent_key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        fingerprint = {
            "intent_key": intent_key,
            **structural_fields,
            "granularity": granularity,       # Incluso no fingerprint, mas não no hash
            "time_scope_type": time_scope_type,  # Incluso no fingerprint, mas não no hash
        }

        logger.debug(
            "[IntentFingerprint] Gerado | domain=%s operation=%s entity=%s "
            "granularity=%s metrics=%s key=%s...",
            domain, operation, entity, granularity, metrics, intent_key[:12],
        )

        return fingerprint

    # ── Extratores Semânticos ──────────────────────────────────────────────

    def _extract_domain(self, intention: Any, plan: Any | None) -> str:
        """Extrai o domínio de negócio (VENDAS, PRODUTOS, CLIENTES, etc.)."""
        # Tenta via view_name do plano
        if plan:
            view_name = getattr(plan.consulta_principal, "view_name", "") or ""
            for key, domain in _DOMAIN_MAP.items():
                if key in view_name.lower():
                    return domain

        # Tenta via entidade_alvo da intenção
        entity_raw = (getattr(intention, "entidade_alvo", "") or "").lower()
        for key, domain in _DOMAIN_MAP.items():
            if key in entity_raw:
                return domain

        # Tenta via operação
        op_raw = (getattr(intention, "operacao", "") or "").lower()
        for key, domain in _DOMAIN_MAP.items():
            if key in op_raw:
                return domain

        return "GERAL"

    def _extract_operation(self, intention: Any, structured: Any | None) -> str:
        """Extrai a operação analítica (AGGREGATION, RANKING, COMPARISON, etc.)."""
        # Verifica comparação primeiro (tem precedência sobre plano estruturado)
        if getattr(intention, "is_comparacao", False):
            return "COMPARISON"

        if structured:
            qtype = (getattr(structured, "query_type", "") or "").upper()
            if qtype in _ANALYSIS_TYPE_MAP:
                return _ANALYSIS_TYPE_MAP[qtype]

        op_raw = (getattr(intention, "operacao", "") or "").lower()
        for key, op in _OPERATION_MAP.items():
            if key in op_raw:
                return op

        return "AGGREGATION"

    def _extract_entity(self, intention: Any, structured: Any | None, plan: Any | None) -> str:
        """Extrai a entidade-alvo principal (PRODUTO, CLIENTE, VENDEDOR, etc.)."""
        entity_raw = (getattr(intention, "entidade_alvo", "") or "").lower()
        for key, entity in _ENTITY_MAP.items():
            if key == entity_raw or key in entity_raw:
                return entity

        # Tenta via group_by do plano estruturado
        if structured:
            group_by = getattr(structured, "group_by", []) or []
            for gb in group_by:
                gb_lower = gb.lower()
                for key, entity in _ENTITY_MAP.items():
                    if key in gb_lower:
                        return entity

        return "GERAL"

    def _extract_granularity(self, intention: Any, structured: Any | None) -> str:
        """Extrai a granularidade temporal (DIARIA, MENSAL, ANUAL, etc.)."""
        # Tenta via periodo_referencia
        periodo = (getattr(intention, "periodo_referencia", "") or "").lower()
        for key, gran in _GRANULARITY_MAP.items():
            if key in periodo:
                return gran

        # Tenta via date_range do plano estruturado
        if structured:
            filters = getattr(structured, "filters", None)
            if filters:
                date_range = (getattr(filters, "date_range", "") or "").lower()
                if "hoje" in date_range or len(date_range) <= 12:
                    return "DIARIA"
                elif "mes" in date_range:
                    return "MENSAL"
                elif "ano" in date_range:
                    return "ANUAL"

        return "GERAL"

    def _extract_metrics(self, structured: Any | None) -> list[str]:
        """Extrai e normaliza as métricas do plano estruturado."""
        if not structured:
            return []

        raw_metrics = getattr(structured, "metrics", []) or []
        normalized = []
        for m in raw_metrics:
            m_lower = m.lower().strip()
            # Normaliza sinônimos de métricas
            if any(x in m_lower for x in ("receita", "faturamento", "venda")):
                normalized.append("receita_total")
            elif any(x in m_lower for x in ("quantidade", "qtd", "pedido")):
                normalized.append("quantidade")
            elif any(x in m_lower for x in ("ticket", "media", "avg")):
                normalized.append("ticket_medio")
            elif any(x in m_lower for x in ("margem", "lucro")):
                normalized.append("margem")
            elif any(x in m_lower for x in ("custo", "cmv")):
                normalized.append("custo")
            else:
                normalized.append(m_lower)

        return list(dict.fromkeys(normalized))  # Remove duplicatas mantendo ordem

    def _extract_group_by(self, structured: Any | None, plan: Any | None) -> list[str]:
        """Extrai e normaliza os agrupamentos."""
        if structured:
            raw = getattr(structured, "group_by", []) or []
            return [g.lower().strip() for g in raw if g]

        if plan:
            items = getattr(plan, "items_secundarios", []) or []
            groups = []
            for item in items:
                gb = getattr(item, "group_by", []) or []
                groups.extend([g.lower().strip() for g in gb if g])
            return groups

        return []

    def _extract_analysis_type(self, intention: Any, structured: Any | None) -> str:
        """Extrai o tipo de análise do plano estruturado."""
        if structured:
            qtype = (getattr(structured, "query_type", "") or "").upper()
            return _ANALYSIS_TYPE_MAP.get(qtype, "AGGREGATION")

        op = (getattr(intention, "operacao", "") or "").upper()
        return _ANALYSIS_TYPE_MAP.get(op, "AGGREGATION")

    def _extract_time_scope_type(self, intention: Any, structured: Any | None) -> str:
        """
        Extrai o tipo de escopo temporal (TODAY, YESTERDAY, MONTH, YEAR, CUSTOM).

        Nota: Este campo NÃO é incluído no hash do intent_key, pois períodos
        diferentes do mesmo tema devem ser reconhecidos como compatíveis.
        """
        periodo = (getattr(intention, "periodo_referencia", "") or "").lower()
        if "hoje" in periodo:
            return "TODAY"
        elif "ontem" in periodo:
            return "YESTERDAY"
        elif "semana" in periodo:
            return "WEEK"
        elif "mes" in periodo:
            return "MONTH"
        elif "trimestre" in periodo:
            return "QUARTER"
        elif "ano" in periodo:
            return "YEAR"

        if structured:
            filters = getattr(structured, "filters", None)
            if filters:
                date_range = getattr(filters, "date_range", "") or ""
                if date_range:
                    return "CUSTOM"

        return "UNSPECIFIED"

    def compute_compatibility_score(
        self,
        fingerprint_a: dict[str, Any],
        fingerprint_b: dict[str, Any],
    ) -> float:
        """
        Calcula o score de compatibilidade entre dois fingerprints (0.0-1.0).

        Score ≥ 0.85 → Compatível para reuso do Package.
        Score < 0.85 → Intenções distintas → Novo Package necessário.

        A compatibilidade considera:
        - domain: 30% (mesmo domínio de negócio)
        - operation: 25% (mesma operação analítica)
        - entity: 20% (mesma entidade-alvo)
        - metrics: 15% (overlap de métricas)
        - granularity: 10% (compatibilidade de granularidade)
        """
        if not isinstance(fingerprint_a, dict) or not isinstance(fingerprint_b, dict):
            return 0.0

        score = 0.0

        # Domain (30%)
        if fingerprint_a.get("domain") == fingerprint_b.get("domain"):
            score += 0.30

        # Operation (25%)
        if fingerprint_a.get("operation") == fingerprint_b.get("operation"):
            score += 0.25

        # Entity (20%)
        if fingerprint_a.get("entity") == fingerprint_b.get("entity"):
            score += 0.20

        # Metrics overlap (15%) — Jaccard sobre as métricas normalizadas
        metrics_a = set(fingerprint_a.get("metrics", []))
        metrics_b = set(fingerprint_b.get("metrics", []))
        if metrics_a or metrics_b:
            intersection = metrics_a & metrics_b
            union = metrics_a | metrics_b
            jaccard = len(intersection) / len(union) if union else 0.0
            score += jaccard * 0.15

        # Granularity (10%) — granularidades iguais ou compatíveis (ex: DIARIA e GERAL)
        gran_a = fingerprint_a.get("granularity", "GERAL")
        gran_b = fingerprint_b.get("granularity", "GERAL")
        if gran_a == gran_b:
            score += 0.10
        elif "GERAL" in (gran_a, gran_b):
            score += 0.05  # Bônus parcial por granularidade genérica

        return round(min(1.0, score), 4)


# ── Singleton ─────────────────────────────────────────────────────────────────
intent_fingerprint_generator = IntentFingerprintGenerator()
