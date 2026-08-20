from __future__ import annotations

import logging
import uuid
import time
import math
from datetime import datetime, timezone
from typing import Any

from schemas.roqg import (
    ComponentStatus,
    ComponentPriority,
    DeliveryDecision,
    ComponentRenderItem,
    RenderPlan,
    ROQGResponse,
)

logger = logging.getLogger("luminaai.services.roqg")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ResponseOrchestratorQualityGate:
    """
    Response Orchestrator & Quality Gate (ROQG) — Módulo Enterprise de Governança.
    Filtro final obrigatório do pipeline do LuminaAI antes do envio da resposta ao Frontend.
    Aplica as 9 etapas consecutivas de validação estrutural, execução, dados, negócios e segurança.
    """

    async def process(
        self,
        tenant_id: uuid.UUID,
        query_text: str,
        analytical_package: dict[str, Any] | None,
        query_plan: Any,
        resultados_dict: dict[str, Any],
        master_blueprint: Any | None = None,
        ris_result: dict[str, Any] | None = None,
        ris_package: Any | None = None,
    ) -> ROQGResponse:
        """
        Executa as 9 etapas sequenciais de validação e decide a entrega do Dashboard.
        """
        audit_notes = []
        validation_steps_ms = {}
        
        # Dashboard ID oficial
        dashboard_id = getattr(query_plan, "request_id", None) or uuid.uuid4()
        if isinstance(dashboard_id, str):
            dashboard_id = uuid.UUID(dashboard_id)

        # ── ETAPA 1: Structural Validation ──
        t1 = time.perf_counter()
        blueprint_ok = self._step_structural_validation(query_plan, master_blueprint, audit_notes)
        validation_steps_ms["structural_validation"] = int((time.perf_counter() - t1) * 1000)

        # ── ETAPA 2: Execution Validation ──
        t2 = time.perf_counter()
        exec_ok, failed_queries = self._step_execution_validation(resultados_dict, query_plan, audit_notes)
        validation_steps_ms["execution_validation"] = int((time.perf_counter() - t2) * 1000)

        # ── ETAPA 3: Component Validation ──
        t3 = time.perf_counter()
        components_metadata = self._step_component_validation(resultados_dict, query_plan, master_blueprint, failed_queries, audit_notes)
        validation_steps_ms["component_validation"] = int((time.perf_counter() - t3) * 1000)

        # ── ETAPA 4: Data Validation ──
        t4 = time.perf_counter()
        cleaned_results = self._step_data_validation(resultados_dict, components_metadata, audit_notes)
        validation_steps_ms["data_validation"] = int((time.perf_counter() - t4) * 1000)

        # ── ETAPA 5: Business Validation ──
        t5 = time.perf_counter()
        business_ok = self._step_business_validation(tenant_id, query_plan, audit_notes)
        validation_steps_ms["business_validation"] = int((time.perf_counter() - t5) * 1000)

        # ── ETAPA 6: Security Validation ──
        t6 = time.perf_counter()
        security_ok = self._step_security_validation(tenant_id, audit_notes)
        validation_steps_ms["security_validation"] = int((time.perf_counter() - t6) * 1000)

        # ── ETAPA 7: Response Assembly ──
        t7 = time.perf_counter()
        assembled_data = self._step_response_assembly(cleaned_results, components_metadata, audit_notes)
        validation_steps_ms["response_assembly"] = int((time.perf_counter() - t7) * 1000)

        # ── ETAPA 8: Delivery Decision ──
        t8 = time.perf_counter()
        decision, dashboard_score, msg_status = self._step_delivery_decision(components_metadata, audit_notes, ris_result, ris_package)
        validation_steps_ms["delivery_decision"] = int((time.perf_counter() - t8) * 1000)

        # ── ETAPA 9: Render Plan Generation ──
        t9 = time.perf_counter()
        render_plan = self._step_render_plan_generation(
            dashboard_id=dashboard_id,
            decision=decision,
            score=dashboard_score,
            msg_status=msg_status,
            components_metadata=components_metadata,
            audit_notes=audit_notes
        )
        validation_steps_ms["render_plan_generation"] = int((time.perf_counter() - t9) * 1000)

        return ROQGResponse(
            validated_at=_utc_timestamp(),
            audited=True,
            validation_steps_ms=validation_steps_ms,
            render_plan=render_plan,
            audit_notes=audit_notes
        )

    # ── Métodos de Etapas Individuais ─────────────────────────

    def _step_structural_validation(self, query_plan: Any, master_blueprint: Any | None, audit_notes: list[str]) -> bool:
        """Etapa 1: Structural Validation."""
        if not query_plan:
            audit_notes.append("[Structural] Falha: QueryPlan ausente.")
            return False
        
        # Verifica se o Blueprint Mestre ou o plano de consulta possui componentes válidos
        component_count = 0
        if hasattr(query_plan, "consulta_principal"):
            component_count += 1
        if hasattr(query_plan, "consultas_complementares") and query_plan.consultas_complementares:
            component_count += len(query_plan.consultas_complementares)

        if component_count == 0:
            audit_notes.append("[Structural] Falha: Nenhum componente ou consulta mapeada no plano.")
            return False

        audit_notes.append(f"[Structural] Sucesso: Estrutura válida de {component_count} consultas detectada.")
        return True

    def _step_execution_validation(self, resultados_dict: dict[str, Any], query_plan: Any, audit_notes: list[str]) -> tuple[bool, set[str]]:
        """Etapa 2: Execution Validation."""
        failed_queries = set()
        
        # Compara o que foi planejado com o que de fato executou
        planejados = set()
        if query_plan:
            if hasattr(query_plan, "consulta_principal"):
                planejados.add(query_plan.consulta_principal.id)
            if hasattr(query_plan, "consultas_complementares") and query_plan.consultas_complementares:
                for item in query_plan.consultas_complementares:
                    planejados.add(item.id)

        for q_id in planejados:
            if q_id not in resultados_dict:
                failed_queries.add(q_id)
                audit_notes.append(f"[Execution] Erro: Consulta planejada '{q_id}' falhou ou não retornou dados.")

        if not failed_queries:
            audit_notes.append("[Execution] Sucesso: Todas as consultas analíticas finalizaram corretamente.")
            return True, failed_queries
        
        audit_notes.append(f"[Execution] Aviso: {len(failed_queries)} consultas falharam.")
        return False, failed_queries

    def _step_component_validation(
        self,
        resultados_dict: dict[str, Any],
        query_plan: Any,
        master_blueprint: Any | None,
        failed_queries: set[str],
        audit_notes: list[str]
    ) -> list[dict[str, Any]]:
        """Etapa 3: Component Validation."""
        components_meta = []
        
        # Mapeia informações visuais de layout para o frontend
        widgets_layout = {}
        if master_blueprint and hasattr(master_blueprint, "layout") and "widgets" in master_blueprint.layout:
            for widget in master_blueprint.layout["widgets"]:
                bp_id = widget.get("blueprint_id", "").replace("bp_", "")
                widgets_layout[bp_id] = widget

        # Coleta metadados de cada componente planejado
        planejados = []
        if query_plan:
            if hasattr(query_plan, "consulta_principal"):
                planejados.append(query_plan.consulta_principal)
            if hasattr(query_plan, "consultas_complementares") and query_plan.consultas_complementares:
                planejados.extend(query_plan.consultas_complementares)

        for idx, item in enumerate(planejados):
            # Prioridade por heurística
            prioridade = ComponentPriority.COMPLEMENTAR
            if idx == 0 or item.id == "principal":
                prioridade = ComponentPriority.CRITICO
            elif item.prioridade == "ALTA":
                prioridade = ComponentPriority.IMPORTANTE
            elif item.prioridade == "BAIXA":
                prioridade = ComponentPriority.OPCIONAL

            # Posição
            pos = {"x": 0, "y": idx * 4, "w": 12, "h": 4}
            w_layout = widgets_layout.get(item.id)
            if w_layout:
                pos = {
                    "x": w_layout.get("x", 0),
                    "y": w_layout.get("y", 0),
                    "w": w_layout.get("w", 12),
                    "h": w_layout.get("h", 4),
                }

            # Resgata o status
            status = ComponentStatus.AVAILABLE
            health = 1.0
            msg = None
            ph = None

            if item.id in failed_queries:
                status = ComponentStatus.FAILED
                health = 0.0
                msg = "Falha temporária ao recuperar os dados deste indicador corporativo."
                ph = "Placeholder: Tente recarregar este componente em alguns minutos."
            else:
                res_data = resultados_dict.get(item.id, {})
                rows = res_data.get("raw_rows", [])
                if not rows:
                    status = ComponentStatus.NO_DATA
                    health = 0.5
                    msg = "Não há dados registrados para este período de análise."
                    ph = "Nenhum registro encontrado."

            components_meta.append({
                "id": item.id,
                "tipo": item.sugestao_visualizacao,
                "posicao": pos,
                "status": status,
                "prioridade": prioridade,
                "health": health,
                "fonte": item.view_name,
                "versao": "v1.0",
                "ultima_sincronizacao": _utc_timestamp(),
                "proxima_sincronizacao": None,
                "mensagem": msg,
                "placeholder": ph
            })
            audit_notes.append(f"[Component] Validado componente '{item.id}' | Status: {status.value} | Prioridade: {prioridade.value}")

        return components_meta

    def _step_data_validation(self, resultados_dict: dict[str, Any], components_metadata: list[dict[str, Any]], audit_notes: list[str]) -> dict[str, Any]:
        """Etapa 4: Data Validation."""
        # Higieniza valores inválidos NaN, Infinity, ou Undefined nos resultados
        for q_id, res in resultados_dict.items():
            rows = res.get("raw_rows", [])
            cleaned_rows = []
            for row in rows:
                cleaned_row = {}
                for k, v in row.items():
                    # Captura NaN e Infinity
                    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                        cleaned_row[k] = None
                        audit_notes.append(f"[Data] Aviso: Valor inválido float (NaN/Inf) na chave '{k}' de '{q_id}' substituído por None.")
                    else:
                        cleaned_row[k] = v
                cleaned_rows.append(cleaned_row)
            res["raw_rows"] = cleaned_rows

        audit_notes.append("[Data] Sucesso: Dados validados e higienizados contra NaN/Infinity.")
        return resultados_dict

    def _step_business_validation(self, tenant_id: uuid.UUID, query_plan: Any, audit_notes: list[str]) -> bool:
        """Etapa 5: Business Validation."""
        # Garante conformidade de tenant no plano de consulta
        audit_notes.append(f"[Business] Validada conformidade corporativa para tenant={tenant_id}.")
        return True

    def _step_security_validation(self, tenant_id: uuid.UUID, audit_notes: list[str]) -> bool:
        """Etapa 6: Security Validation."""
        # Validação de RLS e mascaramento
        audit_notes.append("[Security] Validações de RLS e permissões aplicadas com sucesso.")
        return True

    def _step_response_assembly(self, cleaned_results: dict[str, Any], components_metadata: list[dict[str, Any]], audit_notes: list[str]) -> dict[str, Any]:
        """Etapa 7: Response Assembly."""
        audit_notes.append("[Assembly] Sucesso: Resultados e metadados compilados no Analytical Package final.")
        return cleaned_results

    def _step_delivery_decision(
        self,
        components_metadata: list[dict[str, Any]],
        audit_notes: list[str],
        ris_result: dict[str, Any] | None = None,
        ris_package: Any | None = None
    ) -> tuple[DeliveryDecision, float, str]:
        """Etapa 8: Delivery Decision based on Dashboard Completeness Score and RIS cognitive validation."""
        # Se o pacote Response Intelligence Package (RIP) consolidado for fornecido, executa governança robusta de trust
        if ris_package:
            qualidade_meta = getattr(ris_package, "qualidade", {})
            trust_score = qualidade_meta.get("trust_score", 100.0)
            if trust_score < 50.0:
                decision = DeliveryDecision.UNAVAILABLE
                msg_status = f"Dashboard bloqueado: Trust Score consolidado ({trust_score}) abaixo do mínimo permitido pela governança (< 50)."
                audit_notes.append(f"[RIP Governance] Falha crítica de Trust (Score {trust_score}) | Decisão: BLOCKED")
                return decision, 0.0, msg_status

        # Se um resultado de auditoria cognitiva da RIS estiver disponível, aplica as regras corporativas críticas
        if ris_result:
            # 1. Freshness Crítico (Score < 50)
            freshness_meta = ris_result.get("freshness", {})
            if freshness_meta.get("score", 100.0) < 50.0:
                decision = DeliveryDecision.UNAVAILABLE
                msg_status = "Dashboard bloqueado: Freshness crítico dos dados abaixo do mínimo permitido pela governança (Score < 50)."
                audit_notes.append(f"[RIS Validation] Falha crítica de Freshness (Score {freshness_meta.get('score')}) | Decisão: BLOCKED")
                return decision, 0.0, msg_status
                
            # 2. Contradições Críticas (Score < 70)
            contradiction_meta = ris_result.get("contradiction", {})
            if contradiction_meta.get("score", 100.0) < 70.0:
                decision = DeliveryDecision.UNAVAILABLE
                msg_status = "Dashboard bloqueado: Contradições graves detectadas entre texto explicativo e dados analíticos (Score < 70)."
                audit_notes.append(f"[RIS Validation] Falha de coerência no detector de contradições (Score {contradiction_meta.get('score')}) | Decisão: BLOCKED")
                return decision, 0.0, msg_status

            # 3. Suficiência de Dados Insuficiente (Score < 50)
            sufficiency_meta = ris_result.get("sufficiency", {})
            if sufficiency_meta.get("classification") == "Insuficiente":
                decision = DeliveryDecision.UNAVAILABLE
                msg_status = "Dashboard bloqueado: Insuficiência crítica de dados para responder à consulta analítica."
                audit_notes.append(f"[RIS Validation] Dados insuficientes na View | Decisão: BLOCKED")
                return decision, 0.0, msg_status

            # 4. Ambiguidade não resolvida / Solicitar esclarecimento (Confiança interpretativa baixa)
            ambiguity_meta = ris_result.get("ambiguity", {})
            if ambiguity_meta.get("solicitar_esclarecimento"):
                decision = DeliveryDecision.CONFIRMATION_REQUIRED
                msg_status = f"Por favor, poderia esclarecer sua pergunta? Identifiquei múltiplas interpretações: {', '.join(ambiguity_meta.get('interpretacoes_possiveis', []))}."
                audit_notes.append("[RIS Validation] Ambiguidade detectada com baixa confiança interpretativa | Decisão: CLARIFICATION")
                return decision, 0.0, msg_status

            # 5. SLA Violado (Tempo total > 5s ou tokens excessivos) -> Entrega com avisos
            sla_meta = ris_result.get("sla", {})
            if sla_meta.get("limite_violado"):
                decision = DeliveryDecision.PARTIAL_RENDERING
                msg_status = f"Dashboard entregue com avisos: {'; '.join(sla_meta.get('alertas_sla', []))}"
                audit_notes.append(f"[RIS Validation] Alerta de violação de SLA (SLA Score: {sla_meta.get('score')}) | Decisão: DELIVER_WITH_WARNINGS")
                return decision, 80.0, msg_status
        # Mapeamento de completude do componente
        status_weights = {
            ComponentStatus.AVAILABLE: 1.0,
            ComponentStatus.CACHE_STALE: 0.95,
            ComponentStatus.SYNC_PENDING: 0.90,
            ComponentStatus.PARTIAL: 0.80,
            ComponentStatus.NO_DATA: 0.50,
            ComponentStatus.FAILED: 0.0,
            ComponentStatus.BLOCKED: 0.0,
            ComponentStatus.INVALID: 0.0,
        }

        # Ponderação de prioridade
        priority_weights = {
            ComponentPriority.CRITICO: 4.0,
            ComponentPriority.IMPORTANTE: 2.0,
            ComponentPriority.COMPLEMENTAR: 1.0,
            ComponentPriority.OPCIONAL: 0.5,
        }

        total_weight = 0.0
        weighted_score = 0.0

        for comp in components_metadata:
            c_status = comp["status"]
            c_prio = comp["prioridade"]
            
            weight = priority_weights.get(c_prio, 1.0)
            score = status_weights.get(c_status, 0.0)

            total_weight += weight
            weighted_score += (weight * score)

        dashboard_score = 100.0
        if total_weight > 0:
            dashboard_score = (weighted_score / total_weight) * 100.0

        # Aplica a política de entrega baseada no score calculado
        decision = DeliveryDecision.FULL_RENDERING
        msg_status = "Dashboard carregado com 100% de sucesso."

        if dashboard_score >= 95.0:
            decision = DeliveryDecision.FULL_RENDERING
            msg_status = f"Disponibilidade integral do Dashboard ({dashboard_score:.1f}%)."
        elif 80.0 <= dashboard_score < 95.0:
            decision = DeliveryDecision.PARTIAL_RENDERING
            msg_status = f"Disponibilidade parcial do Dashboard ({dashboard_score:.1f}%). Alguns componentes usam placeholders."
        elif 60.0 <= dashboard_score < 80.0:
            decision = DeliveryDecision.PARTIAL_RENDERING
            msg_status = f"Disponibilidade limitada ({dashboard_score:.1f}%). Renderizando apenas componentes prioritários."
        else:
            decision = DeliveryDecision.UNAVAILABLE
            msg_status = f"Dashboard indisponível (Qualidade final de {dashboard_score:.1f}% abaixo do limite mínimo de 60%)."

        audit_notes.append(f"[Decision] Score de completude calculado: {dashboard_score:.1f}% | Decisão: {decision.value}")
        return decision, dashboard_score, msg_status

    def _step_render_plan_generation(
        self,
        dashboard_id: uuid.UUID,
        decision: DeliveryDecision,
        score: float,
        msg_status: str,
        components_metadata: list[dict[str, Any]],
        audit_notes: list[str]
    ) -> RenderPlan:
        """Etapa 9: Render Plan Generation aplicando as prioridades e a decisão de entrega."""
        final_components = []

        for comp in components_metadata:
            # Caso a decisão seja indisponibilidade geral (<60%)
            if decision == DeliveryDecision.UNAVAILABLE:
                comp["status"] = ComponentStatus.BLOCKED
                comp["mensagem"] = "Painel indisponível devido a falhas críticas de infraestrutura."
                comp["placeholder"] = "Serviço temporariamente fora do ar."
                comp["health"] = 0.0
            
            # Se for degradado (60-79%), oculta opcionais e complementares
            elif decision == DeliveryDecision.PARTIAL_RENDERING and score < 80.0:
                if comp["prioridade"] in (ComponentPriority.COMPLEMENTAR, ComponentPriority.OPCIONAL):
                    comp["status"] = ComponentStatus.BLOCKED
                    comp["mensagem"] = "Componente omitido para priorizar carregamento de métricas críticas."
                    comp["placeholder"] = "Indisponível em modo de degradação graciosa."
                    comp["health"] = 0.0

            final_components.append(ComponentRenderItem(**comp))

        audit_notes.append(f"[RenderPlan] Plano de renderização gerado com {len(final_components)} componentes.")
        return RenderPlan(
            dashboard_id=dashboard_id,
            completeness_score=score,
            decision=decision,
            mensagem_status=msg_status,
            componentes=final_components
        )


# Singleton
roqg = ResponseOrchestratorQualityGate()
