"""
LuminaAI - Response Builder Engine
----------------------------------
Builds final response fragments and normalizes official response modes.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("luminaai.ai.response_builder")


class ResponseBuilder:
    """Formats natural-language messages and response metadata."""

    _MODE_ALIASES = {
        "quick": "quick",
        "fast": "quick",
        "rapido": "quick",
        "rapida": "quick",
        "operational": "quick",
        "operacional": "quick",
        "mode_1": "quick",
        "analytical": "analytical",
        "analytic": "analytical",
        "intelligent": "analytical",
        "inteligente": "analytical",
        "smart": "analytical",
        "padrao": "analytical",
        "default": "analytical",
        "mode_2": "analytical",
        "executive": "executive",
        "executivo": "executive",
        "advisor": "executive",
        "consultor": "executive",
        "premium": "executive",
        "mode_3": "executive",
    }

    def normalize_mode(self, mode: str | None) -> str:
        """Return one of the official modes: quick, analytical or executive."""
        if not mode:
            return "analytical"
        clean = (
            str(mode)
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )
        return self._MODE_ALIASES.get(clean, "analytical")

    def build_direct_response(self, text: str) -> str:
        """Return direct conceptual answers with basic formatting cleanup."""
        return text.strip()

    def build_block_message(self, message: str | None) -> str:
        """Format user-friendly block messages for unauthorized queries."""
        if message:
            return message.strip()
        return "Esta consulta esta fora do escopo analitico autorizado."

    def build_quick_response(self) -> str:
        """Official Mode 1 response: no analysis, only operational confirmation."""
        return "Dashboard, KPIs e componentes foram preparados com os dados atualizados do backend."

    def build_confirmation_request(self, confidence_message: str, details: str | None = None) -> str:
        """Build a concise confirmation message for ambiguous interpretations."""
        suffix = f" Detalhe: {details.strip()}" if details else ""
        return (
            "Antes de executar, preciso confirmar a interpretacao da consulta. "
            f"{confidence_message.strip()}{suffix}"
        )

    def build_response_metadata(
        self,
        *,
        mode: str,
        confidence_score: float | None = None,
        confidence_status: str | None = None,
        package_reused: bool = False,
        package_id: str | None = None,
        dashboard_instance_id: str | None = None,
        tokens_consumed: int = 0,
        timings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build observability metadata returned to the frontend."""
        return {
            "mode": self.normalize_mode(mode),
            "confidence_score": confidence_score,
            "confidence_status": confidence_status,
            "tokens_consumed": int(tokens_consumed or 0),
            "package_reused": package_reused,
            "package_id": package_id,
            "dashboard_instance_id": dashboard_instance_id,
            "timings_ms": timings or {},
        }


response_builder = ResponseBuilder()
