import logging
import time
import json
import hashlib
from typing import List, Dict, Any, Optional, Set
from models.new_pipeline_contracts import (
    CanonicalPlan, ExecutionPlan, ResolvedEntities, ResolvedEntity,
    ExecutionStatus, EmptyDatasetPolicy, IntentType, QueryCost, CanonicalFilter,
    ComparisonOperator
)
from services.metadata_catalog.repository import catalog_repository
from services.metadata_catalog.models import AggregationType

logger = logging.getLogger("luminaai.services.metadata_catalog.resolver")

class MetadataResolver:
    """
    O MetadataResolver é o componente responsável por converter um CanonicalPlan
    em um ExecutionPlan físico determinístico utilizando o Corporate Knowledge Catalog (CKC).
    Nenhuma inteligência cognitiva (IA) participa deste componente.
    """

    def __init__(self):
        self._plan_cache: Dict[str, ExecutionPlan] = {}

    def _generate_cache_key(self, plan: CanonicalPlan) -> str:
        # Serializa elementos lógicos do plano canônico ordenadamente para consistência de hash
        plan_dict = {
            "intent": plan.intent.value if hasattr(plan.intent, 'value') else str(plan.intent),
            "goal": plan.goal,
            "entities": sorted(plan.entities),
            "metrics": sorted(plan.metrics),
            "dimensions": sorted(plan.dimensions),
            "filters": sorted([f.model_dump_json() for f in plan.filters]),
            "limit": plan.limit
        }
        serialized = json.dumps(plan_dict, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def resolve(self, canonical_plan: CanonicalPlan) -> ExecutionPlan:
        start_time = time.perf_counter()
        trace_id = canonical_plan.trace_id

        # 1. Verificação de Cache
        cache_key = self._generate_cache_key(canonical_plan)
        if cache_key in self._plan_cache:
            cached_plan = self._plan_cache[cache_key]
            # Atualiza o trace_id para rastreabilidade
            cached_plan.trace_id = trace_id
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info(f"[MetadataResolver] Cache HIT para o plano. Trace ID: {trace_id}. Tempo: {elapsed:.2f}ms")
            return cached_plan

        logger.info(f"[MetadataResolver] Iniciando resolução física. Trace ID: {trace_id}")

        # ── Passo A: Identificação de Views Físicas ──
        selected_views: List[str] = []
        resolved_entities_dict: Dict[str, ResolvedEntity] = {}
        resolution_justification = {}

        for ent_name in canonical_plan.entities:
            entity_meta = catalog_repository.get_entity(ent_name)
            if not entity_meta:
                logger.error(f"[MetadataResolver] Entidade inexistente: {ent_name}")
                return self._build_error_plan(canonical_plan, "Entidade inexistente no CKG.")

            if not entity_meta.views:
                return self._build_error_plan(canonical_plan, f"Entidade '{ent_name}' não possui Views cadastradas.")

            req_metrics = canonical_plan.metrics
            req_dimensions = canonical_plan.dimensions
            req_filters = [f.field for f in canonical_plan.filters]
            total_reqs = list(set(req_metrics + req_dimensions + req_filters))

            best_view = None
            best_score = -1.0
            best_view_reasons = []
            candidates_scores = {}

            for v_name in entity_meta.views:
                v_meta = catalog_repository.get_view(v_name)
                if not v_meta:
                    continue

                supported_metrics = [m.canonical_name for m in catalog_repository.get_metrics_for_view(v_name)]
                supported_dimensions = [d.name for d in catalog_repository.get_dimensions_for_view(v_name)]

                matched_items = []
                missing_items = []

                for req in total_reqs:
                    if req in supported_metrics or req in supported_dimensions:
                        matched_items.append(req)
                    else:
                        short_req = req.split(".")[-1]
                        if any(short_req == col.split(".")[-1] for col in list(v_meta.columns.keys()) + supported_metrics + supported_dimensions):
                            matched_items.append(req)
                        else:
                            missing_items.append(req)

                if total_reqs:
                    score = round((len(matched_items) / len(total_reqs)) * 100, 2)
                else:
                    score = 100.0 if v_meta.view_type.value == "CADASTRAL" else 50.0

                candidates_scores[v_name] = {
                    "score": score,
                    "matched": matched_items,
                    "missing": missing_items,
                    "view_type": v_meta.view_type.value
                }

                if score > best_score:
                    best_score = score
                    best_view = v_name
                    best_view_reasons = matched_items

            if not best_view:
                best_view = entity_meta.views[0]
                best_score = 0.0
                best_view_reasons = []

            if best_view not in selected_views:
                selected_views.append(best_view)

            view_meta = catalog_repository.get_view(best_view)
            if not view_meta:
                return self._build_error_plan(canonical_plan, f"View física '{best_view}' não localizada.")

            resolved_entities_dict[ent_name] = ResolvedEntity(
                logical_name=ent_name,
                physical_view=best_view,
                primary_key=view_meta.primary_key,
                available_columns=list(view_meta.columns.keys()),
                foreign_keys=view_meta.foreign_keys,
                supported_metrics=[m.physical_column for m in catalog_repository.get_metrics_for_view(best_view)],
                supported_dimensions=[d.physical_column for d in catalog_repository.get_dimensions_for_view(best_view)]
            )

            resolution_justification[ent_name] = {
                "chosen_view": best_view,
                "score": best_score,
                "matched_elements": best_view_reasons,
                "candidates": candidates_scores,
                "reason": f"View {best_view} selecionada para a entidade '{ent_name}' por possuir maior compatibilidade ({best_score}% cobertura: {best_view_reasons})."
            }

            logger.info(f"[MetadataResolver] Entidade '{ent_name}' resolvida para a view '{best_view}' (Score: {best_score}%)")

        # ── Passo B: Resolução de Colunas Físicas, Filtros e Agregações ──
        columns_physical: List[str] = []
        group_by_physical: List[str] = []
        metric_aliases: List[str] = []
        having_clauses: List[str] = []
        parameters = {}
        filters_physical = []

        # Helper para encontrar view e coluna física a partir de termo qualificado ou não
        def find_physical_mapping(term: str) -> Optional[tuple[str, str, Any]]:
            # 1. Tenta buscar no catálogo global de dimensões (ex: "Cliente", "Cidade", "Estado", "Vendedor")
            short_term = term.split(".")[-1].strip().lower()

            # Busca nas dimensões do catálogo
            for dim_name, dim_meta in catalog_repository.catalog.dimensions.items():
                if dim_name.lower() == short_term or dim_meta.physical_column.lower() == short_term:
                    v_name = dim_meta.physical_view
                    v_meta = catalog_repository.get_view(v_name)
                    if v_meta and dim_meta.physical_column in v_meta.columns:
                        return v_name, dim_meta.physical_column, v_meta.columns[dim_meta.physical_column]

            # Busca nas métricas do catálogo
            for met_name, met_meta in catalog_repository.catalog.metrics.items():
                if met_name.lower() == short_term or met_meta.physical_column.lower() == short_term:
                    v_name = met_meta.physical_view
                    v_meta = catalog_repository.get_view(v_name)
                    if v_meta and met_meta.physical_column in v_meta.columns:
                        return v_name, met_meta.physical_column, v_meta.columns[met_meta.physical_column]

            # 2. Caso de Fallback qualificado clássico
            parts = term.split(".")
            if len(parts) == 2:
                ent_name = parts[0]
                col_name = parts[1]
                if ent_name in resolved_entities_dict:
                    v_name = resolved_entities_dict[ent_name].physical_view
                    v_meta = catalog_repository.get_view(v_name)
                    if v_meta and col_name in v_meta.columns:
                        return v_name, v_meta.columns[col_name].physical_name, v_meta.columns[col_name]
                # Fallback se a entidade não estiver em resolved_entities_dict mas existir no CKG
                ent_meta = catalog_repository.get_entity(ent_name)
                if ent_meta and ent_meta.views:
                    v_name = ent_meta.views[0]
                    v_meta = catalog_repository.get_view(v_name)
                    if v_meta and col_name in v_meta.columns:
                        return v_name, v_meta.columns[col_name].physical_name, v_meta.columns[col_name]
            else:
                # Caso não qualificado (Campo simples) - busca recursiva nas views resolvidas no Passo A
                col_name = parts[0]
                for ent_name, res_ent in resolved_entities_dict.items():
                    v_name = res_ent.physical_view
                    v_meta = catalog_repository.get_view(v_name)
                    if v_meta and col_name in v_meta.columns:
                        return v_name, v_meta.columns[col_name].physical_name, v_meta.columns[col_name]
            return None

        # B.1 Mapeamento de Dimensões para o SELECT e GROUP BY
        for dim in canonical_plan.dimensions:
            mapping = find_physical_mapping(dim)
            if mapping:
                v_name, physical_col, col_meta = mapping

                # Se for Ranking, Agregação ou KPI, e a dimensão for de data, pula a projeção e o group by.
                # A data deve ser usada apenas como filtro na cláusula WHERE.
                is_time_dim = any(term in physical_col.lower() or term in dim.lower() for term in ("dtemissao", "data", "periodo", "mes", "ano"))
                if is_time_dim and canonical_plan.intent in (IntentType.RANKING, IntentType.KPI, IntentType.AGGREGATION):
                    logger.info(f"[Resolver] Poupando dimensão de data {dim} no agrupamento de RANKING/AGGREGATION/KPI.")
                    continue

                col_expr = f"{v_name}.{physical_col}"
                columns_physical.append(col_expr)
                group_by_physical.append(col_expr)
                if v_name not in selected_views:
                    selected_views.append(v_name)

        # B.2 Mapeamento de Métricas para SELECT e Agregações
        for metric in canonical_plan.metrics:
            mapping = find_physical_mapping(metric)
            if mapping:
                v_name, physical_col, col_meta = mapping
                # Tenta recuperar os metadados da métrica conceitual no catálogo para usar sua agregação correta
                short_term = metric.split(".")[-1].strip().lower()
                metric_meta = None
                for met_name, m_meta in catalog_repository.catalog.metrics.items():
                    if met_name.lower() == short_term:
                        metric_meta = m_meta
                        break

                # Prioriza as agregações declaradas na métrica de negócio sobre as genéricas da coluna física
                supported_aggs = metric_meta.supported_aggregations if metric_meta else col_meta.supported_aggregations

                metric_label_lower = metric.lower()
                if "ticket" in metric_label_lower:
                    metric_alias = "ticket_medio"
                    col_expr = f"(SUM({v_name}.ptotal_) / NULLIF(COUNT(DISTINCT {v_name}.pedido_), 0)) as {metric_alias}"
                    columns_physical.append(col_expr)
                    metric_aliases.append(metric_alias)
                    if v_name not in selected_views:
                        selected_views.append(v_name)
                    continue

                if "desconto" in metric_label_lower:
                    discount_expr = f"GREATEST(ROUND((({v_name}.qtde_ * {v_name}.p_unit_) - {v_name}.ptotal_)::numeric, 2), 0::numeric)"
                    if "medio" in metric_label_lower or "mÃ©dio" in metric_label_lower:
                        metric_alias = "desconto_medio"
                        col_expr = f"(SUM({discount_expr}) / NULLIF(COUNT(DISTINCT {v_name}.pedido_), 0)) as {metric_alias}"
                    else:
                        metric_alias = "desconto_total"
                        col_expr = f"SUM({discount_expr}) as {metric_alias}"
                    columns_physical.append(col_expr)
                    metric_aliases.append(metric_alias)
                    if v_name not in selected_views:
                        selected_views.append(v_name)
                    continue

                if AggregationType.SUM in supported_aggs and not (metric_meta and metric_meta.canonical_name == "Ticket Médio"):
                    agg_type = "SUM"
                elif AggregationType.AVG in supported_aggs:
                    agg_type = "AVG"
                else:
                    agg_type = "COUNT"

                metric_alias = col_meta.friendly_name.lower().replace(' ', '_')
                col_expr = f"{agg_type}({v_name}.{physical_col}) as {metric_alias}"
                columns_physical.append(col_expr)
                metric_aliases.append(metric_alias)
                if v_name not in selected_views:
                    selected_views.append(v_name)

        # B.3 Resolução de Filtros Físicos
        for idx, f in enumerate(canonical_plan.filters):
            mapping = find_physical_mapping(f.field)
            if mapping:
                v_name, physical_col, col_meta = mapping

                # Tradução inteligente de filiais e estados para a base de testes analítica
                filter_val = f.value
                field_lower = f.field.lower()
                physical_col_lower = physical_col.lower()

                if any(term in field_lower for term in ("filial", "loja", "cidade", "estado", "uf")):
                    val_clean = str(f.value).lower().replace("%", "").strip()
                    translated = None

                    if val_clean in ("1", "filial 1", "filial1", "loja 1", "loja1", "sp", "sao paulo", "são paulo"):
                        translated = "SP" if physical_col_lower == "uf" else "Sao Paulo"
                    elif val_clean in ("2", "filial 2", "filial2", "loja 2", "loja2", "mg", "belo horizonte", "bh"):
                        translated = "MG" if physical_col_lower == "uf" else "Belo Horizonte"
                    elif val_clean in ("3", "filial 3", "filial3", "loja 3", "loja3", "pr", "curitiba"):
                        translated = "PR" if physical_col_lower == "uf" else "Curitiba"
                    elif val_clean in ("rj", "rio de janeiro", "rio"):
                        translated = "RJ" if physical_col_lower == "uf" else "Rio de Janeiro"
                    elif val_clean in ("rs", "porto alegre", "poa"):
                        translated = "RS" if physical_col_lower == "uf" else "Porto Alegre"

                    if translated:
                        has_leading_percent = str(f.value).startswith("%")
                        has_trailing_percent = str(f.value).endswith("%")
                        filter_val = f"{'%' if has_leading_percent else ''}{translated}{'%' if has_trailing_percent else ''}"

                param_name = f"param_{idx}"
                parameters[param_name] = filter_val

                filters_physical.append(CanonicalFilter(
                    field=f"{v_name}.{physical_col}",
                    operator=f.operator,
                    value=filter_val
                ))
                if v_name not in selected_views:
                    selected_views.append(v_name)

        # ── Passo C: Resolução de Caminhos de JOIN (BFS Dijkstra) ──
        plan_terms = " ".join(
            [
                canonical_plan.goal,
                " ".join(canonical_plan.entities),
                " ".join(canonical_plan.dimensions),
                " ".join(canonical_plan.metrics),
            ]
        ).lower()
        is_client_ranking = canonical_plan.intent == IntentType.RANKING and "cliente" in plan_terms
        if is_client_ranking and "VW_CLIENTES_CAD_LM" in selected_views:
            internal_client_filter = CanonicalFilter(
                field="VW_CLIENTES_CAD_LM.nome",
                operator=ComparisonOperator.NOT_EQUALS,
                value="LAGES E LOPES LTDA",
            )
            if not any(
                f.field == internal_client_filter.field
                and f.operator == internal_client_filter.operator
                and f.value == internal_client_filter.value
                for f in filters_physical
            ):
                filters_physical.append(internal_client_filter)
                parameters[f"param_{len(parameters)}"] = internal_client_filter.value
                resolution_justification.setdefault("business_rules", {})[
                    "exclude_internal_store_from_client_ranking"
                ] = "Cliente interno LAGES E LOPES LTDA excluido apenas de rankings/top clientes."

        is_vendor_ranking = canonical_plan.intent == IntentType.RANKING and "vendedor" in plan_terms
        if is_vendor_ranking and "VW_VENDEDOR_CAD_LM" in selected_views:
            default_vendor_filter = CanonicalFilter(
                field="VW_VENDEDOR_CAD_LM.nome_ved",
                operator=ComparisonOperator.NOT_EQUALS,
                value="PADRAO",
            )
            if not any(
                f.field == default_vendor_filter.field
                and f.operator == default_vendor_filter.operator
                and f.value == default_vendor_filter.value
                for f in filters_physical
            ):
                filters_physical.append(default_vendor_filter)
                parameters[f"param_{len(parameters)}"] = default_vendor_filter.value
                resolution_justification.setdefault("business_rules", {})[
                    "exclude_default_vendor_from_ranking"
                ] = "Vendedor tecnico PADRAO excluido apenas de rankings/top vendedores."

        joins_list: List[Dict[str, str]] = []
        evaluated_paths = 0

        if len(selected_views) > 1:
            connected_views: Set[str] = {selected_views[0]}
            target_views = set(selected_views[1:])

            while target_views:
                best_path: List[Any] = []
                best_source = ""
                best_target = ""

                for src in connected_views:
                    for tgt in target_views:
                        path = catalog_repository.find_shortest_join_path(src, tgt)
                        evaluated_paths += 1
                        if path:
                            if not best_path or len(path) < len(best_path):
                                best_path = path
                                best_source = src
                                best_target = tgt

                if not best_path:
                    elapsed = (time.perf_counter() - start_time) * 1000
                    logger.warning(f"[MetadataResolver] NEEDS_REPLANNING: Views desconectadas no CKG: {selected_views}")
                    return self._build_error_plan(
                        canonical_plan,
                        f"Não foi possível conectar as views analíticas do negócio: {selected_views}.",
                        ExecutionStatus.NEEDS_REPLANNING
                    )

                for rel in best_path:
                    join_item = {
                        "source_view": rel.source_view,
                        "source_column": rel.source_column,
                        "target_view": rel.target_view,
                        "target_column": rel.target_column
                    }
                    if join_item not in joins_list:
                        joins_list.append(join_item)
                    connected_views.add(rel.target_view)

                    for view_name in (rel.source_view, rel.target_view):
                        if view_name not in selected_views:
                            selected_views.append(view_name)
                            view_meta = catalog_repository.get_view(view_name)
                            if view_meta:
                                ent_name = view_name.replace("VW_", "").replace("_CAD_LM", "").replace("_LM", "").title()
                                if ent_name not in resolved_entities_dict:
                                    resolved_entities_dict[ent_name] = ResolvedEntity(
                                        logical_name=ent_name,
                                        physical_view=view_name,
                                        primary_key=view_meta.primary_key,
                                        available_columns=list(view_meta.columns.keys()),
                                        foreign_keys=view_meta.foreign_keys,
                                        supported_metrics=[m.physical_column for m in catalog_repository.get_metrics_for_view(view_name)],
                                        supported_dimensions=[d.physical_column for d in catalog_repository.get_dimensions_for_view(view_name)]
                                    )

                target_views.remove(best_target)

        # ── Passo D: Montagem do Plano de Execução ──
        resolved_entities = ResolvedEntities(
            entities=resolved_entities_dict,
            joins=joins_list
        )
        order_by_physical = []
        if canonical_plan.intent == IntentType.RANKING and metric_aliases:
            order_by_physical.append(f"{metric_aliases[0]} DESC")

        exec_plan = ExecutionPlan(
            trace_id=trace_id,
            status=ExecutionStatus.READY,
            resolved_entities=resolved_entities,
            selected_views=selected_views,
            columns=columns_physical,
            filters=filters_physical,
            group_by=group_by_physical,
            order_by=order_by_physical,
            having=having_clauses,
            cte=[],
            parameters=parameters,
            limit=canonical_plan.limit,
            estimated_cost=QueryCost.LOW if len(selected_views) <= 1 else (QueryCost.MEDIUM if len(selected_views) == 2 else QueryCost.HIGH),
            estimated_rows=1000,
            execution_priority=1,
            cacheable=True,
            cache_key=cache_key,
            required_permissions=[],
            timeout=30,
            empty_dataset_policy=EmptyDatasetPolicy.EMPTY_UNEXPECTED if canonical_plan.intent == IntentType.KPI else EmptyDatasetPolicy.EMPTY_EXPECTED,
            resolution_justification=resolution_justification
        )

        self._plan_cache[cache_key] = exec_plan

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"[MetadataResolver] Sucesso! Resolvido em {elapsed:.2f}ms. "
            f"Views: {len(selected_views)}, JOINs: {len(joins_list)}, Caminhos avaliados: {evaluated_paths}."
        )
        return exec_plan

    def _build_error_plan(
        self, plan: CanonicalPlan, reason: str, status: ExecutionStatus = ExecutionStatus.INVALID
    ) -> ExecutionPlan:
        return ExecutionPlan(
            trace_id=plan.trace_id,
            status=status,
            resolved_entities=ResolvedEntities(entities={}, joins=[]),
            selected_views=[],
            columns=[],
            filters=[],
            group_by=[],
            order_by=[],
            having=[],
            cte=[],
            parameters={},
            estimated_cost=QueryCost.VERY_HIGH,
            estimated_rows=0,
            execution_priority=99,
            cacheable=False,
            cache_key="",
            required_permissions=[],
            timeout=30,
            empty_dataset_policy=EmptyDatasetPolicy.EMPTY_EXPECTED
        )

metadata_resolver = MetadataResolver()
