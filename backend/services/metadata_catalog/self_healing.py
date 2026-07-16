import logging
import time
from typing import Dict, Any, Optional, List
from models.new_pipeline_contracts import SemanticPlan, CanonicalPlan, ExecutionPlan, ExecutionStatus

logger = logging.getLogger("luminaai.services.metadata_catalog.self_healing")

class SelfHealingEngine:
    """
    O SelfHealingEngine analisa falhas recuperáveis do pipeline analítico
    (ex: dataset vazio inesperado, caminhos físicos inválidos, aliases desatualizados)
    e tenta corrigi-los gerando feedbacks refinados para replanejamento de uma única tentativa.
    """
    
    def __init__(self):
        # Cache para rastrear tentativas de self-healing por trace_id e evitar loops infinitos
        self._healed_traces: List[str] = []

    def should_heal(self, trace_id: str, status: ExecutionStatus, dataset_rows: List[Dict[str, Any]], plan: ExecutionPlan) -> bool:
        # Se o trace_id já passou por healing, bloqueia para garantir tentativa única
        if trace_id in self._healed_traces:
            logger.warning(f"[SelfHealing] Tentativa de re-healing abortada. Limite único atingido. Trace: {trace_id}")
            return False

        # 1. Dataset vazio inesperado
        from models.new_pipeline_contracts import EmptyDatasetPolicy
        if not dataset_rows and plan.empty_dataset_policy == EmptyDatasetPolicy.EMPTY_UNEXPECTED:
            logger.info(f"[SelfHealing] Detectado dataset vazio inesperado. Iniciando auto-cura. Trace: {trace_id}")
            return True

        # 2. Caminho de JOIN impossível ou view inválida
        if status in (ExecutionStatus.NEEDS_REPLANNING, ExecutionStatus.INVALID):
            logger.info(f"[SelfHealing] Falha física ou lógica no plano (Status: {status}). Iniciando auto-cura. Trace: {trace_id}")
            return True

        return False

    def generate_healing_feedback(self, reason: str, plan: ExecutionPlan) -> str:
        # Reconstrói um prompt explicativo contendo a falha técnica para guiar o replanejamento conceitual da IA
        entities_str = ", ".join(plan.resolved_entities.entities.keys()) if plan.resolved_entities else "Nenhuma"
        feedback = (
            f"O plano logico gerou um dataset vazio ou erro de conexao: {reason}. "
            f"Tabelas/Views envolvidas: [{entities_str}]. "
            "Por favor, reformule as restricoes, aliases corporativos ou datas do filtro temporal para "
            "abranger periodos historicos válidos ou tente utilizar entidades analíticas equivalentes."
        )
        return feedback

    def mark_healed(self, trace_id: str):
        self._healed_traces.append(trace_id)
        # Limita o histórico na RAM para evitar vazamentos de memória
        if len(self._healed_traces) > 1000:
            self._healed_traces.pop(0)

self_healing_engine = SelfHealingEngine()
