from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select

from config import settings
from contracts.analytical_v2 import PipelineKind, attach_v2_sidecar
from models.metadata_catalog import MetadataCatalog
from models.sync_queue import SyncQueue
from models.user import UserRole

logger = logging.getLogger(__name__)


class QueryResponseGovernance:
    """Adds truthful freshness, validation and role-scoped diagnostics to query results."""

    tolerance = Decimal("0.02")

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("0")

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    async def _data_status(self, db: Any, *, tenant: Any, view_name: str | None) -> dict[str, Any]:
        sync_config = tenant.sync_config if isinstance(tenant.sync_config, dict) else {}
        catalog_stmt = select(MetadataCatalog).where(MetadataCatalog.tenant_id == tenant.id)
        if view_name:
            catalog_stmt = catalog_stmt.where(func.upper(MetadataCatalog.nome_view) == view_name.upper())
        catalog_stmt = catalog_stmt.order_by(MetadataCatalog.ultima_sincronizacao.desc().nullslast()).limit(1)
        metadata = (await db.execute(catalog_stmt)).scalar_one_or_none()

        job_stmt = (
            select(SyncQueue)
            .where(SyncQueue.tenant_id == tenant.id)
            .order_by(SyncQueue.criado_em.desc())
            .limit(1)
        )
        latest_job = (await db.execute(job_stmt)).scalar_one_or_none()

        synced_at = getattr(metadata, "ultima_sincronizacao", None)
        if synced_at is None and sync_config.get("last_sync"):
            try:
                synced_at = datetime.fromisoformat(str(sync_config["last_sync"]).replace("Z", "+00:00"))
            except ValueError:
                synced_at = None
        if synced_at is not None and synced_at.tzinfo is None:
            synced_at = synced_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_minutes = None
        if synced_at is not None:
            age_minutes = max(0, int((now - synced_at.astimezone(timezone.utc)).total_seconds() // 60))

        max_age_minutes = int(sync_config.get("freshness_warning_minutes") or 180)
        sync_status = str(
            getattr(latest_job, "status", None) or sync_config.get("last_sync_status") or "UNKNOWN"
        ).upper()
        if sync_status in {"RUNNING", "PENDING"}:
            freshness = "SYNCING"
        elif synced_at is None:
            freshness = "UNKNOWN"
        elif sync_status in {"FAILED", "ERROR"}:
            freshness = "DEGRADED"
        elif age_minutes is not None and age_minutes > max_age_minutes:
            freshness = "STALE"
        else:
            freshness = "CURRENT"

        return {
            "query_source": "POSTGRESQL_ANALYTICAL_CLONE",
            "source_label": "PostgreSQL analítico sincronizado",
            "view_name": view_name,
            "synced_at": synced_at.isoformat() if synced_at else None,
            "checked_at": now.isoformat(),
            "age_minutes": age_minutes,
            "freshness": freshness,
            "sync_status": sync_status,
            "records_last_sync": int(getattr(latest_job, "quantidade_registros", 0) or 0),
            "freshness_warning_minutes": max_age_minutes,
        }

    def validate_math(self, payload: dict[str, Any]) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        chart_data = self._as_dict(payload.get("chart_data"))
        resumo = self._as_dict(chart_data.get("resumo"))

        def add_check(code: str, actual: Any, expected: Any) -> None:
            actual_decimal = self._decimal(actual)
            expected_decimal = self._decimal(expected)
            difference = abs(actual_decimal - expected_decimal)
            checks.append({
                "code": code,
                "status": "PASS" if difference <= self.tolerance else "FAIL",
                "actual": float(actual_decimal),
                "expected": float(expected_decimal),
                "difference": float(difference),
                "required": True,
            })

        category_keys = (
            "faturamento_comercial", "saida_rb", "devolucao", "venda_bonificada",
            "outras_vendas", "remessa_uso_consumo", "outros_movimentos",
        )
        if "total_bruto" in resumo and any(key in resumo for key in category_keys):
            add_check(
                "TOTAL_BRUTO_EXCLUI_TRANSFERENCIAS",
                resumo.get("total_bruto"),
                sum((self._decimal(resumo.get(key)) for key in category_keys), Decimal("0")),
            )
        if "total_movimentos_view" in resumo and "total_bruto" in resumo:
            add_check(
                "TOTAL_MOVIMENTOS_INCLUI_TRANSFERENCIAS",
                resumo.get("total_movimentos_view"),
                self._decimal(resumo.get("total_bruto")) + self._decimal(resumo.get("transferencias")),
            )

        filiais = resumo.get("filiais")
        if isinstance(filiais, list) and len(filiais) > 1 and "faturamento_total" in resumo:
            filial_total = sum(
                (self._decimal(row.get("faturamento_comercial")) for row in filiais if isinstance(row, dict)),
                Decimal("0"),
            )
            add_check("SOMA_FILIAIS_IGUAL_TOTAL", resumo.get("faturamento_total"), filial_total)

        rows = chart_data.get("rows")
        if isinstance(rows, list):
            identities: list[str] = []
            ranking_mismatches = 0
            ranking_rows = 0
            for row in rows:
                if not isinstance(row, dict):
                    continue
                identity = row.get("vendedor") or row.get("cliente")
                if identity:
                    identities.append(str(identity).strip().upper())
                primary_metric = str(resumo.get("primary_metric") or "faturamento_comercial")
                filial_values = [
                    self._decimal(value)
                    for key, value in row.items()
                    if key.startswith("filial_") and key.endswith(f"_{primary_metric}")
                ]
                if filial_values and "valor_total" in row:
                    ranking_rows += 1
                    if abs(sum(filial_values, Decimal("0")) - self._decimal(row.get("valor_total"))) > self.tolerance:
                        ranking_mismatches += 1
            duplicate_count = max(0, len(identities) - len(set(identities)))
            checks.append({
                "code": "DIMENSAO_SEM_DUPLICIDADE",
                "status": "PASS" if duplicate_count == 0 else "FAIL",
                "actual": duplicate_count,
                "expected": 0,
                "difference": duplicate_count,
                "required": True,
            })
            if ranking_rows:
                checks.append({
                    "code": "TOTAL_RANKING_IGUAL_SOMA_FILIAIS",
                    "status": "PASS" if ranking_mismatches == 0 else "FAIL",
                    "actual": ranking_mismatches,
                    "expected": 0,
                    "difference": ranking_mismatches,
                    "required": True,
                })

        failures = [check for check in checks if check["status"] == "FAIL"]
        return {
            "status": "PASSED" if not failures else "FAILED",
            "checks_total": len(checks),
            "checks_passed": len(checks) - len(failures),
            "checks_failed": len(failures),
            "checks": checks,
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _interaction_options(payload: dict[str, Any]) -> list[dict[str, Any]]:
        question = str(payload.get("pergunta_original") or "esta analise")
        return [
            {"id": "documents", "label": "Ver documentos", "prompt": f"Detalhe os pedidos e notas que compõem a resposta para: {question}"},
            {"id": "by_branch", "label": "Separar por filial", "prompt": f"Separe por filial, mantendo os mesmos filtros de: {question}"},
            {"id": "more_detail", "label": "Mais detalhes", "prompt": f"Mostre mais detalhes importantes, mantendo o contexto de: {question}"},
        ]

    @staticmethod
    def _safe_admin_trace(payload: dict[str, Any]) -> dict[str, Any] | None:
        trace = payload.get("debug_info")
        if not isinstance(trace, dict):
            return None
        allowed = (
            "trace_id", "pergunta", "pergunta_contextualizada", "timeline",
            "semantic_plan", "canonical_plan", "sql", "rows", "sample_rows",
            "chart", "llm_response", "error_traceback", "business_rule",
        )
        return {key: trace.get(key) for key in allowed if key in trace}

    async def enrich(
        self,
        payload: dict[str, Any],
        *,
        db: Any,
        tenant: Any,
        current_user: Any,
        pipeline: PipelineKind = PipelineKind.LEGACY,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        result = dict(payload)
        data_status = await self._data_status(db, tenant=tenant, view_name=result.get("view_name"))
        validation = self.validate_math(result)
        result["data_status"] = data_status
        result["validation_summary"] = validation
        result["roqg_validated"] = validation["status"] == "PASSED"
        result["interaction_options"] = self._interaction_options(result) if result.get("chart_data") else []

        original_trust = self._as_dict(result.get("trust_center"))
        result["trust_center"] = {
            **original_trust,
            "source": "PostgreSQL analytical clone",
            "data_status": data_status,
            "validation_summary": validation,
            "data_lineage": [
                {"etapa": "SYNC", "nome": "ERP para PostgreSQL", "detalhes": "Processo técnico de sincronização; não acessado pela IA durante a consulta.", "status": data_status["sync_status"]},
                {"etapa": "QUERY", "nome": result.get("view_name") or "Fonte analítica", "detalhes": "Consulta executada exclusivamente no PostgreSQL analítico.", "status": "COMPLETED"},
            ],
        }

        if getattr(current_user, "role", None) == UserRole.ADMIN:
            intelligence = self._as_dict(result.get("bi_intelligence"))
            result["admin_diagnostics"] = {
                "request_id": result.get("request_id") or result.get("query_id"),
                "source": data_status,
                "filters": result.get("parametros_extraidos") or {},
                "execution_plan": result.get("plano_execucao"),
                "nlu_plan": result.get("plano_nlu"),
                "metric_definitions": intelligence.get("metric_definitions"),
                "calculation_steps": intelligence.get("calculation_steps"),
                "validation": validation,
                "telemetry": result.get("telemetry"),
                "context_resolution": result.get("context_resolution_metadata"),
                "trace": self._safe_admin_trace(result),
            }
            result.pop("debug_info", None)
        else:
            result.pop("debug_info", None)
            result["admin_diagnostics"] = None
            result["plano_execucao"] = None
            result["plano_nlu"] = None
            result["telemetry"] = None

        if settings.ANALYTICAL_CONTRACTS_V2_ENABLED:
            role = getattr(getattr(current_user, "role", None), "value", None) or "CONSULTA"
            try:
                with_sidecar = attach_v2_sidecar(
                    result,
                    tenant_id=tenant.id,
                    user_id=getattr(current_user, "id", None),
                    user_role=str(role).upper(),
                    session_id=session_id,
                    pipeline=pipeline,
                    comparison_planner_enabled=settings.COMPARISON_PLANNER_V2_ENABLED,
                    comparison_planner_shadow_mode=settings.COMPARISON_PLANNER_V2_SHADOW_MODE,
                )
                if settings.ANALYTICAL_CONTRACTS_V2_SHADOW_MODE:
                    contract = with_sidecar.get("analytical_contract")
                    metadata = contract.get("contract", {}) if isinstance(contract, dict) else {}
                    logger.info(
                        "Analytical contract V2 validated in shadow mode | schema=%s/%s | pipeline=%s",
                        metadata.get("schema_name"),
                        metadata.get("schema_version"),
                        pipeline.value,
                    )
                else:
                    result["analytical_contract"] = with_sidecar["analytical_contract"]
            except (TypeError, ValueError) as exc:
                logger.warning(
                    "Analytical contract V2 sidecar was not emitted | pipeline=%s | error=%s",
                    pipeline.value,
                    type(exc).__name__,
                )
        return result


query_response_governance = QueryResponseGovernance()
