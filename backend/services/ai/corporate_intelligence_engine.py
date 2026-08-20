"""
LuminaAI - Corporate Intelligence Engine Facade
-----------------------------------------------
Coordinates the internal AI engines without executing queries or calculations.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from services.ai.blueprint_builder import blueprint_builder
from services.ai.business_understanding_engine import business_understanding_engine
from services.ai.confidence_engine import confidence_engine
from services.ai.context_engine import context_engine
from services.ai.executive_analysis_engine import executive_analysis_engine
from services.ai.intent_engine import intent_engine
from services.ai.kpi_discovery_engine import kpi_discovery_engine
from services.ai.package_matcher import package_matcher
from services.ai.response_builder import response_builder
from services.ai.schemas import BusinessIntentSchema
from services.ai.semantic_engine import semantic_engine
from services.ai.visualization_strategy_engine import visualization_strategy_engine

logger = logging.getLogger("luminaai.ai.corporate_intelligence_engine")


class CorporateIntelligenceEngine:
    """Facade for the Corporate Intelligence Engine."""

    def _params_to_dict(self, params: Any) -> dict[str, Any]:
        if isinstance(params, dict):
            return dict(params)
        result: dict[str, Any] = {}
        for item in params or []:
            key = getattr(item, "chave", None)
            value = getattr(item, "valor", None)
            if key:
                result[str(key)] = value
        return result

    def _as_list(self, value: Any) -> list[Any]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple | set):
            return list(value)
        return [value]

    def _plan_metrics(self, raw: Any) -> list[str]:
        plan = getattr(raw, "plano_estruturado", None)
        return list(getattr(plan, "metrics", []) or [])

    def _plan_group_by(self, raw: Any) -> list[str]:
        plan = getattr(raw, "plano_estruturado", None)
        return list(getattr(plan, "group_by", []) or [])

    def _has_executable_structure(self, raw: Any) -> bool:
        """Detect intents that are safe to execute even with medium confidence."""
        if getattr(raw, "view_catalog_id", None) is None:
            return False

        operation = str(getattr(raw, "operacao", "") or "").strip().upper()
        entity = str(getattr(raw, "entidade_alvo", "") or "").strip().upper()
        metrics = self._plan_metrics(raw)
        group_by = self._plan_group_by(raw)
        plan = getattr(raw, "plano_estruturado", None)

        if operation in {"LISTAGEM", "DETALHAMENTO", "SELECT"} and entity:
            return True

        return bool(operation and entity and (plan or metrics or group_by))

    async def identify_intention(
        self,
        pergunta: str,
        catalog: list[Any],
        client: AsyncOpenAI,
        target_model: str,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        history: list[dict[str, str]] | None = None,
        custom_instructions: str | None = None,
        request_id: str | None = None,
        user_id: uuid.UUID | None = None,
        session_id: str | None = None,
    ) -> list[Any]:
        """
        Build structured analytical intention and Blueprint metadata.

        The CIE does not execute data access. It only interprets, validates and
        coordinates semantic strategy for the backend pipeline.
        """
        total_start = time.perf_counter()
        logger.info("[CIE] Starting semantic processing: %r", pergunta[:80])

        context_start = time.perf_counter()
        context = await context_engine.build_context(
            tenant_id=tenant_id,
            db=db,
            history=history,
            custom_instructions=custom_instructions,
            user_id=user_id,
            session_id=session_id,
        )
        context_ms = int((time.perf_counter() - context_start) * 1000)

        nlu_start = time.perf_counter()
        raw_result = await intent_engine.extract_intent(
            pergunta=pergunta,
            catalog=catalog,
            context=context,
            client=client,
            target_model=target_model,
            request_id=request_id,
        )
        if isinstance(raw_result, tuple):
            raw_intentions, tokens_consumed = raw_result
        else:
            raw_intentions, tokens_consumed = raw_result, 0
        nlu_ms = int((time.perf_counter() - nlu_start) * 1000)

        from services.ai.legacy_contracts import (
            IntentionResponse,
            PlanFiltersSchema,
            PlanVisualizationSchema,
            StructuredPlanSchema,
        )

        if not raw_intentions:
            return [
                IntentionResponse(
                    view_catalog_id=None,
                    confianca=0.0,
                    parametros={},
                    justificativa="Nao foi possivel identificar uma intencao analitica valida.",
                    resposta_direta="Nao consegui interpretar a consulta. Pode reformular com o indicador, periodo ou entidade desejada?",
                    telemetry=response_builder.build_response_metadata(
                        mode="analytical",
                        confidence_score=0.0,
                        confidence_status="REJECTED",
                        tokens_consumed=tokens_consumed,
                        timings={"context_engine": context_ms, "intent_engine": nlu_ms},
                    ),
                )
            ]

        results: list[Any] = []
        for raw in raw_intentions:
            raw_confidence = float(getattr(raw, "confianca", 0.0) or 0.0)
            conf_res = confidence_engine.process_confidence(raw_confidence)
            if (
                conf_res["status"] != "APPROVED"
                and raw_confidence >= 0.55
                and self._has_executable_structure(raw)
            ):
                logger.info(
                    "[CIE] Auto-aprovando intencao estruturada de confianca media | score=%.2f | op=%s | entidade=%s",
                    raw_confidence,
                    getattr(raw, "operacao", None),
                    getattr(raw, "entidade_alvo", None),
                )
                conf_res = {
                    **conf_res,
                    "status": "APPROVED",
                    "executar": True,
                    "nivel": "MEDIA",
                    "mensagem": "Intencao estruturada suficiente para execucao.",
                    "auto_approved": True,
                }

            if getattr(raw, "fora_de_escopo", False):
                results.append(
                    IntentionResponse(
                        view_catalog_id=None,
                        confianca=0.0,
                        parametros={},
                        justificativa=getattr(raw, "justificativa", ""),
                        fora_de_escopo=True,
                        mensagem_bloqueio=response_builder.build_block_message(getattr(raw, "mensagem_bloqueio", None)),
                        telemetry=response_builder.build_response_metadata(
                            mode="analytical",
                            confidence_score=0.0,
                            confidence_status="REJECTED",
                            tokens_consumed=tokens_consumed,
                            timings={"context_engine": context_ms, "intent_engine": nlu_ms},
                        ),
                    )
                )
                continue

            if getattr(raw, "resposta_direta", None):
                results.append(
                    IntentionResponse(
                        view_catalog_id=None,
                        confianca=raw_confidence,
                        parametros={},
                        justificativa=getattr(raw, "justificativa", ""),
                        resposta_direta=response_builder.build_direct_response(raw.resposta_direta),
                        telemetry=response_builder.build_response_metadata(
                            mode="analytical",
                            confidence_score=raw_confidence,
                            confidence_status=conf_res["status"],
                            tokens_consumed=tokens_consumed,
                            timings={"context_engine": context_ms, "intent_engine": nlu_ms},
                        ),
                    )
                )
                continue

            if conf_res["status"] != "APPROVED":
                results.append(
                    IntentionResponse(
                        view_catalog_id=None,
                        confianca=raw_confidence,
                        parametros=self._params_to_dict(getattr(raw, "parametros", None)),
                        justificativa=getattr(raw, "justificativa", ""),
                        resposta_direta=response_builder.build_confirmation_request(
                            conf_res["mensagem"],
                            getattr(raw, "justificativa", None),
                        ),
                        operacao=getattr(raw, "operacao", None),
                        entidade_alvo=getattr(raw, "entidade_alvo", None),
                        periodo_referencia=getattr(raw, "periodo_referencia", None),
                        nivel_confianca=conf_res["nivel"],
                        telemetry=response_builder.build_response_metadata(
                            mode="analytical",
                            confidence_score=raw_confidence,
                            confidence_status=conf_res["status"],
                            tokens_consumed=tokens_consumed,
                            timings={"context_engine": context_ms, "intent_engine": nlu_ms},
                        ),
                    )
                )
                continue

            semantic_start = time.perf_counter()
            standardized_metrics = [
                semantic_engine.resolve_synonyms(metric)
                for metric in self._plan_metrics(raw)
            ]
            semantic_ms = int((time.perf_counter() - semantic_start) * 1000)

            business_start = time.perf_counter()
            for metric in standardized_metrics[:5]:
                try:
                    await business_understanding_engine.get_concept_meaning(tenant_id, metric, db=db)
                except Exception as exc:
                    logger.debug("[CIE] Business meaning lookup skipped for %s: %s", metric, exc)
            business_ms = int((time.perf_counter() - business_start) * 1000)

            kpi_start = time.perf_counter()
            official_kpis = await kpi_discovery_engine.discover_metrics(
                tenant_id=tenant_id,
                raw_indicators=standardized_metrics,
                db=db,
            )
            if not official_kpis:
                official_kpis = standardized_metrics
            kpi_ms = int((time.perf_counter() - kpi_start) * 1000)

            visual_start = time.perf_counter()
            visual_strategy = visualization_strategy_engine.determine_strategy(
                operacao=getattr(raw, "operacao", None),
                entidade=getattr(raw, "entidade_alvo", None),
                explicit_chart=getattr(raw, "chart_type_sobrescrever", None),
                explicit_charts=getattr(raw, "chart_types_solicitados", None),
            )
            visual_ms = int((time.perf_counter() - visual_start) * 1000)

            filters_dict = self._params_to_dict(getattr(raw, "parametros", None))
            business_intent = BusinessIntentSchema(
                objetivo=getattr(raw, "operacao", None) or "SOMA",
                entidade=getattr(raw, "entidade_alvo", None) or "VENDA",
                indicadores=standardized_metrics,
                kpis=official_kpis,
                filtros=filters_dict,
                periodo=getattr(raw, "periodo_referencia", None),
                comparacoes=[
                    getattr(raw, "comparativo_detalhe")
                ]
                if getattr(raw, "is_comparacao", False) and getattr(raw, "comparativo_detalhe", None)
                else [],
                agrupamentos=self._plan_group_by(raw),
                prioridade="ALTA" if getattr(raw, "nivel_confianca", "") == "ALTA" else "MEDIA",
                complexidade="ALTA" if getattr(raw, "is_comparacao", False) else "BAIXA",
                visual_sugerido=visual_strategy.componente_principal,
                nivel_confianca=getattr(raw, "nivel_confianca", None) or conf_res["nivel"],
                score_confianca=raw_confidence,
            )

            blueprint_start = time.perf_counter()
            blueprint = blueprint_builder.compile_blueprint(business_intent, visual_strategy)
            blueprint_ms = int((time.perf_counter() - blueprint_start) * 1000)

            package_start = time.perf_counter()
            matched_package, match_score = await package_matcher.match_package(
                tenant_id=tenant_id,
                business_intent=business_intent,
                db=db,
            )
            package_ms = int((time.perf_counter() - package_start) * 1000)

            legacy_plan = StructuredPlanSchema(
                request_id=request_id or str(uuid.uuid4()),
                intent=getattr(raw, "justificativa", "") or business_intent.objetivo,
                query_type="AGGREGATION" if business_intent.agrupamentos else "SELECT",
                metrics=business_intent.kpis,
                group_by=business_intent.agrupamentos,
                filters=PlanFiltersSchema(
                    date_range=business_intent.periodo or "",
                    products=self._as_list(filters_dict.get("produtos", filters_dict.get("produto_nome"))),
                    customers=self._as_list(filters_dict.get("clientes", filters_dict.get("cliente_nome"))),
                    regions=self._as_list(filters_dict.get("regioes", filters_dict.get("filial_nome", filters_dict.get("regiao")))),
                ),
                comparisons=business_intent.comparacoes,
                visualization=PlanVisualizationSchema(
                    type=visual_strategy.componente_principal,
                    layout_priority=business_intent.prioridade,
                ),
                requires_insight=True,
                confidence_score=business_intent.score_confianca,
            )

            timings = {
                "context_engine": context_ms,
                "intent_engine": nlu_ms,
                "semantic_engine": semantic_ms,
                "business_understanding_engine": business_ms,
                "kpi_discovery_engine": kpi_ms,
                "visualization_strategy_engine": visual_ms,
                "blueprint_builder": blueprint_ms,
                "package_matcher": package_ms,
            }
            telemetry = response_builder.build_response_metadata(
                mode="analytical",
                confidence_score=business_intent.score_confianca,
                confidence_status=conf_res["status"],
                package_reused=matched_package is not None,
                package_id=str(matched_package.id) if matched_package else None,
                tokens_consumed=tokens_consumed,
                timings={**timings, "total_ai": int((time.perf_counter() - total_start) * 1000)},
            )
            telemetry.update(
                {
                    "blueprint_id": str(blueprint.id),
                    "dashboard_template": blueprint.dashboard_sugerida,
                    "package_compatibility_score": match_score,
                }
            )

            results.append(
                IntentionResponse(
                    view_catalog_id=getattr(raw, "view_catalog_id", None),
                    confianca=business_intent.score_confianca,
                    parametros=filters_dict,
                    justificativa=getattr(raw, "justificativa", ""),
                    fora_de_escopo=False,
                    chart_type_sobrescrever=getattr(raw, "chart_type_sobrescrever", None),
                    chart_types_solicitados=getattr(raw, "chart_types_solicitados", None),
                    plano_estruturado=legacy_plan,
                    operacao=getattr(raw, "operacao", None),
                    entidade_alvo=getattr(raw, "entidade_alvo", None),
                    quantidade_limite=getattr(raw, "quantidade_limite", None),
                    periodo_referencia=getattr(raw, "periodo_referencia", None),
                    is_comparacao=getattr(raw, "is_comparacao", False),
                    comparativo_detalhe=getattr(raw, "comparativo_detalhe", None),
                    visualizacao_preferida=getattr(raw, "visualizacao_preferida", None),
                    nivel_confianca=business_intent.nivel_confianca,
                    telemetry=telemetry,
                )
            )

        return results

    async def generate_data_insights(
        self,
        pergunta: str,
        dados: list[dict[str, Any]] | dict[str, Any],
        view_name: str,
        client: AsyncOpenAI,
        target_model: str,
        history: list[dict[str, str]] | None = None,
        custom_instructions: str | None = None,
        mode: str = "analytical",
    ) -> str:
        """Delegate final explanation to the Executive Analysis Engine."""
        return await executive_analysis_engine.generate_analysis(
            pergunta=pergunta,
            dados=dados,
            view_name=view_name,
            client=client,
            target_model=target_model,
            history=history,
            custom_instructions=custom_instructions,
            mode=mode,
        )


corporate_intelligence_engine = CorporateIntelligenceEngine()

