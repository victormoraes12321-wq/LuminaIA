"""
LuminaAI - Confidence Engine
----------------------------
Classifies semantic confidence and decides whether execution is safe.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("luminaai.ai.confidence_engine")


class ConfidenceEngine:
    """Decision guard for interpreted analytical intentions."""

    def process_confidence(self, score: float) -> dict[str, Any]:
        """
        Return an operational decision for a score between 0 and 1.

        - >= 0.80: approved for execution.
        - >= 0.40 and < 0.80: ask the user for confirmation.
        - < 0.40: reject and request clarification.
        """
        safe_score = max(0.0, min(float(score or 0.0), 1.0))
        logger.info("[CIE] Confidence score evaluated: %.2f", safe_score)

        if safe_score >= 0.80:
            return {
                "status": "APPROVED",
                "executar": True,
                "nivel": "ALTA",
                "mensagem": "Consulta segura para execucao imediata.",
            }

        if safe_score >= 0.40:
            return {
                "status": "WARNING",
                "executar": False,
                "nivel": "MEDIA",
                "mensagem": "A interpretacao ficou parcialmente ambigua.",
            }

        return {
            "status": "REJECTED",
            "executar": False,
            "nivel": "BAIXA",
            "mensagem": "Entendimento insuficiente. Reescreva a pergunta com mais contexto.",
        }


confidence_engine = ConfidenceEngine()
