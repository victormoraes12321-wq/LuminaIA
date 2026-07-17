import logging
import time
import unicodedata
from typing import List, Dict, Any, Optional
from models.new_pipeline_contracts import (
    SemanticPlan, CanonicalPlan, CanonicalFilter, SemanticFilter,
    ExecutionStatus, IntentType, VisualizationType, ComparisonOperator
)
from services.metadata_catalog.repository import catalog_repository

logger = logging.getLogger("luminaai.services.metadata_catalog.canonicalizer")

class SemanticCanonicalizer:
    """
    O Canonicalizer é responsável por transformar o SemanticPlan produzido pela IA
    em um CanonicalPlan, utilizando unicamente o Corporate Knowledge Catalog (CKC).
    Não conhece Views, SQL ou infraestrutura de banco de dados.
    """

    def canonicalize(self, semantic_plan: SemanticPlan) -> CanonicalPlan:
        start_time = time.perf_counter()
        trace_id = semantic_plan.trace_id
        
        # 1. Logs de início e controle
        aliases_resolved = []
        concepts_found = []
        concepts_not_found = []
        ambiguities_detected = []
        trace_list = []

        logger.info(f"[Canonicalizer] Iniciando canonicalização do plano. Trace ID: {trace_id}")

        # ── Pré-processamento e auto-correção analítica de planos incompletos/flutuantes ──
        query_lower = semantic_plan.goal.lower() if semantic_plan.goal else ""
        query_folded = unicodedata.normalize("NFKD", query_lower)
        query_folded = "".join(ch for ch in query_folded if not unicodedata.combining(ch))
        
        # Injeção para a Curva ABC
        if "curva abc" in query_lower:
            if not semantic_plan.entities:
                semantic_plan.entities = []
            if "Venda" not in semantic_plan.entities:
                semantic_plan.entities.append("Venda")
            if "Produto" not in semantic_plan.entities:
                semantic_plan.entities.append("Produto")
            if not semantic_plan.metrics:
                semantic_plan.metrics = []
            if "Receita" not in semantic_plan.metrics:
                semantic_plan.metrics.append("Receita")
                
        # Injeção para Ticket Médio
        if any(x in query_folded for x in ("ticket m", "ticket medio")):
            if not semantic_plan.entities:
                semantic_plan.entities = []
            if "Venda" not in semantic_plan.entities:
                semantic_plan.entities.append("Venda")
            semantic_plan.metrics = ["Ticket Médio"]

        # Auto-deduz entidades de acordo com as métricas ou palavras-chave na pergunta
        if "desconto" in query_folded:
            if not semantic_plan.entities:
                semantic_plan.entities = []
            if "Venda" not in semantic_plan.entities:
                semantic_plan.entities.append("Venda")
            if "medio" in query_folded or "media" in query_folded:
                semantic_plan.metrics = ["Desconto Medio"]
            elif not semantic_plan.metrics:
                semantic_plan.metrics = ["Desconto"]

        temp_entities = list(semantic_plan.entities or [])
        if not temp_entities:
            for met in (semantic_plan.metrics or []):
                met_lower = met.lower()
                if any(x in met_lower for x in ("receita", "faturamento", "venda", "ticket", "comissao", "comissão")):
                    if "Venda" not in temp_entities:
                        temp_entities.append("Venda")
                elif "estoque" in met_lower:
                    if "Produto" not in temp_entities:
                        temp_entities.append("Produto")
                elif "parcela" in met_lower:
                    if "Financeiro" not in temp_entities:
                        temp_entities.append("Financeiro")
            
            if "cliente" in query_lower:
                if "Cliente" not in temp_entities:
                    temp_entities.append("Cliente")
            if "produto" in query_lower:
                if "Produto" not in temp_entities:
                    temp_entities.append("Produto")
            if any(x in query_lower for x in ("vendedor", "comissão", "comissao")):
                if "Vendedor" not in temp_entities:
                    temp_entities.append("Vendedor")
            if any(x in query_lower for x in ("venda", "faturamento", "receita", "ticket")):
                if "Venda" not in temp_entities:
                    temp_entities.append("Venda")
            
            semantic_plan.entities = temp_entities

        # ── Validação A: Campos Obrigatórios Ausentes (MISSING_INFORMATION) ──
        if not semantic_plan.goal or not semantic_plan.goal.strip():
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.warning(f"[Canonicalizer] Falha: Objetivo (goal) ausente. Tempo: {elapsed:.2f}ms")
            return self._build_error_plan(
                semantic_plan, ExecutionStatus.MISSING_INFORMATION,
                missing_info=["O objetivo analítico da consulta não foi especificado."]
            )

        if not semantic_plan.entities:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.warning(f"[Canonicalizer] Falha: Nenhuma entidade especificada. Tempo: {elapsed:.2f}ms")
            return self._build_error_plan(
                semantic_plan, ExecutionStatus.MISSING_INFORMATION,
                missing_info=["Nenhuma entidade de negócio (ex: Cliente, Venda) foi identificada no plano."]
            )

        # ── Validação B: Resolução de Intenção ──
        canonical_intent = self._resolve_intent(semantic_plan.intent)
        concepts_found.append(f"Intent.{canonical_intent.value}")
        trace_list.append({
            "semantic_term": str(semantic_plan.intent),
            "matched_alias": None,
            "canonical_name": canonical_intent.value,
            "type": "Intent",
            "source": "Intent Enum mapping",
            "confidence": "DIRECT_MATCH"
        })

        # ── Validação C: Resolução de Entidades ──
        canonical_entities = []
        for ent in semantic_plan.entities:
            # Resolve alias da entidade
            resolved_alias = catalog_repository.resolve_alias(ent)
            resolved_name = resolved_alias.canonical_name if resolved_alias else ent
            
            # Normaliza e pesquisa no catálogo
            canonical_ent_meta = catalog_repository.get_entity(resolved_name)
            if not canonical_ent_meta:
                concepts_not_found.append(f"Entity.{ent}")
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.warning(f"[Canonicalizer] Falha: Entidade '{ent}' não suportada. Tempo: {elapsed:.2f}ms")
                return self._build_error_plan(semantic_plan, ExecutionStatus.UNSUPPORTED)
            
            trace_list.append({
                "semantic_term": ent,
                "matched_alias": resolved_alias.alias if resolved_alias else None,
                "canonical_name": resolved_name,
                "type": "Entity",
                "source": "Corporate Knowledge Catalog",
                "confidence": "EXACT_ALIAS" if resolved_alias else "CATALOG_DIRECT"
            })
            
            if resolved_alias:
                aliases_resolved.append(f"{ent} -> {resolved_name}")
            concepts_found.append(f"Entity.{resolved_name}")
            
            if resolved_name not in canonical_entities:
                canonical_entities.append(resolved_name)

        # ── Validação D: Resolução de Métricas ──
        canonical_metrics = []
        for metric in semantic_plan.metrics:
            # Tenta resolver alias
            resolved_alias = catalog_repository.resolve_alias(metric)
            resolved_name = resolved_alias.canonical_name if resolved_alias else metric
            
            # Mapeamento estático específico de métricas qualificadas conceituais
            metric_mapping = {
                "Receita": "Venda.Receita",
                "Faturamento": "Venda.Receita",
                "receita_total": "Venda.Receita",
                "Quantidade": "Venda.Quantidade",
                "quantidade": "Venda.Quantidade",
                "Estoque": "Produto.Estoque",
                "estoque": "Produto.Estoque",
                "Valor Parcela": "Financeiro.Valor Parcela",
                "valor_parcela": "Financeiro.Valor Parcela",
                "Ticket Médio": "Venda.Ticket Médio",
                "Ticket Medio": "Venda.Ticket Médio",
                "ticket_medio": "Venda.Ticket Médio"
            }
            
            metric_mapping.update({
                "Desconto": "Venda.Desconto",
                "desconto": "Venda.Desconto",
                "Desconto Medio": "Venda.Desconto Medio",
                "desconto_medio": "Venda.Desconto Medio",
            })

            if resolved_name in metric_mapping:
                canonical_metric = metric_mapping[resolved_name]
                concepts_found.append(f"Metric.{canonical_metric}")
                trace_list.append({
                    "semantic_term": metric,
                    "matched_alias": resolved_alias.alias if resolved_alias else None,
                    "canonical_name": canonical_metric,
                    "type": "Metric",
                    "source": "Metric mapping dictionary",
                    "confidence": "EXACT_ALIAS" if resolved_alias else "MAPPED_METRIC"
                })
                if resolved_alias:
                    aliases_resolved.append(f"{metric} -> {resolved_name}")
                if canonical_metric not in canonical_metrics:
                    canonical_metrics.append(canonical_metric)
            else:
                concepts_not_found.append(f"Metric.{metric}")
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.warning(f"[Canonicalizer] Falha: Métrica '{metric}' não suportada. Tempo: {elapsed:.2f}ms")
                return self._build_error_plan(semantic_plan, ExecutionStatus.UNSUPPORTED)

        # ── Validação E: Resolução de Dimensões ──
        canonical_dimensions = []
        for dim in semantic_plan.dimensions:
            # Resolve aliases
            resolved_alias = catalog_repository.resolve_alias(dim)
            resolved_name = resolved_alias.canonical_name if resolved_alias else dim
            
            resolved_dim = self._resolve_dimension_field(resolved_name, canonical_entities, ambiguities_detected)
            if resolved_dim == "AMBIGUOUS":
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.warning(f"[Canonicalizer] Falha: Ambiguidade na dimensão '{dim}'. Tempo: {elapsed:.2f}ms")
                return self._build_error_plan(
                    semantic_plan, ExecutionStatus.AMBIGUOUS,
                    ambiguities=ambiguities_detected
                )
            elif not resolved_dim:
                concepts_not_found.append(f"Dimension.{dim}")
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.warning(f"[Canonicalizer] Falha: Dimensão '{dim}' não suportada. Tempo: {elapsed:.2f}ms")
                return self._build_error_plan(semantic_plan, ExecutionStatus.UNSUPPORTED)
            
            trace_list.append({
                "semantic_term": dim,
                "matched_alias": resolved_alias.alias if resolved_alias else None,
                "canonical_name": resolved_dim,
                "type": "Dimension",
                "source": "Dimension resolver heuristics",
                "confidence": "EXACT_ALIAS" if resolved_alias else "CATALOG_DIRECT"
            })
            
            if resolved_alias:
                aliases_resolved.append(f"{dim} -> {resolved_name}")
            concepts_found.append(f"Dimension.{resolved_dim}")
            
            if resolved_dim not in canonical_dimensions:
                canonical_dimensions.append(resolved_dim)

        # ── Validação F: Resolução de Filtros ──
        canonical_filters = []
        for f in semantic_plan.filters:
            resolved_alias = catalog_repository.resolve_alias(f.field)
            resolved_field = resolved_alias.canonical_name if resolved_alias else f.field
            
            resolved_filter_field = self._resolve_dimension_field(resolved_field, canonical_entities, ambiguities_detected)
            if resolved_filter_field == "AMBIGUOUS":
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.warning(f"[Canonicalizer] Falha: Ambiguidade no filtro '{f.field}'. Tempo: {elapsed:.2f}ms")
                return self._build_error_plan(
                    semantic_plan, ExecutionStatus.AMBIGUOUS,
                    ambiguities=ambiguities_detected
                )
            elif not resolved_filter_field:
                concepts_not_found.append(f"FilterField.{f.field}")
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.warning(f"[Canonicalizer] Falha: Campo de filtro '{f.field}' não suportado. Tempo: {elapsed:.2f}ms")
                return self._build_error_plan(semantic_plan, ExecutionStatus.UNSUPPORTED)
                
            trace_list.append({
                "semantic_term": f.field,
                "matched_alias": resolved_alias.alias if resolved_alias else None,
                "canonical_name": resolved_filter_field,
                "type": "FilterField",
                "source": "Dimension filter resolver",
                "confidence": "EXACT_ALIAS" if resolved_alias else "CATALOG_DIRECT"
            })
            
            if resolved_alias:
                aliases_resolved.append(f"{f.field} -> {resolved_field}")
            concepts_found.append(f"FilterField.{resolved_filter_field}")
            
            # Normalização de valor do filtro para campos específicos (ex: Produto.nome = milho)
            normalized_value = f.value
            
            canonical_filters.append(
                CanonicalFilter(
                    field=resolved_filter_field,
                    operator=f.operator,
                    value=normalized_value
                )
            )

        # Fallback de projeção de colunas se métricas e dimensões vierem vazias
        if not canonical_metrics and not canonical_dimensions:
            logger.info("[Canonicalizer] Métricas e Dimensões vazias detectadas. Aplicando fallbacks de colunas descritivas principais do CKG.")
            for ent_name in canonical_entities:
                if ent_name == "Cliente":
                    canonical_dimensions.append("Cliente.nome")
                elif ent_name == "Produto":
                    canonical_dimensions.append("Produto.nome_produto")
                elif ent_name == "Vendedor":
                    canonical_dimensions.append("Vendedor.nome_ved")
                elif ent_name == "Venda":
                    canonical_metrics.append("Venda.Receita")

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"[Canonicalizer] Sucesso! Status: READY. Tempo: {elapsed:.2f}ms. "
            f"Aliases resolvidos: {len(aliases_resolved)}. Conceitos encontrados: {len(concepts_found)}."
        )

        return CanonicalPlan(
            trace_id=trace_id,
            status=ExecutionStatus.READY,
            intent=canonical_intent,
            goal=semantic_plan.goal,
            entities=canonical_entities,
            metrics=canonical_metrics,
            dimensions=canonical_dimensions,
            filters=canonical_filters,
            limit=semantic_plan.limit,
            suggested_visualization=semantic_plan.suggested_visualization,
            canonicalization_trace=trace_list
        )

    def _resolve_intent(self, intent: IntentType) -> IntentType:
        # Garante normalização de intenções
        mapping = {
            "listar": IntentType.LIST,
            "ranking": IntentType.RANKING,
            "comparar": IntentType.COMPARISON,
            "tendencia": IntentType.TREND,
            "kpi": IntentType.KPI
        }
        val = intent.value.lower() if hasattr(intent, 'value') else str(intent).lower()
        return mapping.get(val, intent)

    def _resolve_dimension_field(self, field: str, active_entities: List[str], ambiguities: List[str]) -> Optional[str]:
        """
        Resolve uma dimensão simples ou qualificada para o formato conceitual canônico `{Entidade}.{Campo}`.
        Mapeia ambiguidades se houver conflitos entre as entidades selecionadas no plano.
        """
        # Se for qualificado (ex: "Cliente.cidade")
        parts = field.split(".")
        if len(parts) == 2:
            ent = catalog_repository.get_entity(parts[0])
            if ent:
                return f"{ent.name}.{parts[1]}"
            return None

        # Mapeamento estático e heurístico de dimensões comuns para o CKG
        field_lower = field.lower().strip()
        
        # Se for o próprio nome descritivo de uma entidade, resolve para seu campo principal
        if field_lower == "cliente":
            return "Cliente.nome"
        elif field_lower == "produto":
            return "Produto.nome_produto"
        elif field_lower == "vendedor":
            return "Vendedor.nome_ved"
        
        # Detecção de Ambiguidade: Se for "nome", pode ser de Cliente, Produto ou Vendedor
        if field_lower == "nome":
            candidates = []
            if "Cliente" in active_entities:
                candidates.append("Cliente.nome")
            if "Produto" in active_entities:
                candidates.append("Produto.nome_produto")
            if "Vendedor" in active_entities:
                candidates.append("Vendedor.nome_ved")
                
            if len(candidates) > 1:
                ambiguities.append(f"Você deseja ver o nome do Cliente ou o nome do Vendedor?")
                return "AMBIGUOUS"
            elif len(candidates) == 1:
                return candidates[0]
            else:
                # Fallback padrão seguro
                return "Cliente.nome"

        # Cidade
        if field_lower in ("cidade", "nome_cidade", "municipio"):
            if "Vendedor" in active_entities and "Cliente" not in active_entities:
                return "Vendedor.muni_ved"
            return "Cliente.cidade" if "Cliente.cidade" else "Cliente.nome_cidade"

        # Estado
        if field_lower in ("estado", "uf"):
            return "Cliente.uf"

        # Categoria / Família
        if field_lower in ("categoria", "familia", "categoria_produto"):
            return "Produto.familia"

        # Vendedor
        if field_lower in ("vendedor", "nome_vendedor", "vendedor_nome", "vendedor"):
            return "Vendedor.nome_ved"

        # Produto
        if field_lower in ("produto", "nome_produto", "produto_nome"):
            return "Produto.nome_produto"

        # Data
        if field_lower in ("data", "ano", "mes", "dtemissao", "dtemissao_"):
            return "Venda.dtemissao_"

        # Status
        if field_lower in ("status", "status_cliente", "tpcli"):
            return "Cliente.tpcli"

        # Documento
        if field_lower in ("cnpj", "cpf", "cnpj_cpf"):
            return "Cliente.cnpj_cpf"

        # Se não cair em nenhum mapeamento
        return None

    def _build_error_plan(
        self, semantic_plan: SemanticPlan, status: ExecutionStatus,
        ambiguities: List[str] = None, missing_info: List[str] = None
    ) -> CanonicalPlan:
        return CanonicalPlan(
            trace_id=semantic_plan.trace_id,
            status=status,
            intent=self._resolve_intent(semantic_plan.intent),
            goal=semantic_plan.goal or "Falha de Processamento",
            entities=[],
            metrics=[],
            dimensions=[],
            filters=[],
            limit=semantic_plan.limit,
            suggested_visualization=semantic_plan.suggested_visualization
        )
