"""
LuminaAI - Memory Context Engine
--------------------------------
Temporary in-memory conversational context for the active user session.

This memory is deliberately non-persistent. It stores only analytical metadata
needed to understand follow-up questions, never result rows or personal data.
"""
from __future__ import annotations

import datetime as _dt
import logging
import re
import uuid
from collections import Counter
from threading import Lock
from typing import Any

from services.ai.schemas import CIEContextSchema

logger = logging.getLogger("luminaai.ai.memory_context_engine")


class MemoryContextEngine:
    """Maintains temporary tenant/user/session-scoped analytical context."""

    _TTL_SECONDS = 30 * 60
    _SENSITIVE_KEYWORDS = (
        "cpf",
        "cnpj",
        "rg",
        "email",
        "telefone",
        "phone",
        "celular",
        "senha",
        "password",
        "token",
        "secret",
        "api_key",
        "chave",
    )

    def __init__(self) -> None:
        self._sessions: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._lock = Lock()

    def _make_key(
        self,
        user_id: uuid.UUID | str,
        tenant_id: uuid.UUID | str | None = None,
        session_id: str | None = None,
    ) -> tuple[str, str, str]:
        tenant = str(tenant_id or "default")
        user = str(user_id)
        session = str(session_id or "default")
        return (tenant, user, session)

    def _cleanup_expired_locked(self) -> None:
        now = _dt.datetime.now(_dt.timezone.utc)
        expired = [
            key
            for key, sess in self._sessions.items()
            if (now - sess["updated_at"]).total_seconds() > self._TTL_SECONDS
        ]
        for key in expired:
            del self._sessions[key]

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            cleaned: dict[str, Any] = {}
            for key, item in value.items():
                key_str = str(key)
                if any(term in key_str.lower() for term in self._SENSITIVE_KEYWORDS):
                    continue
                cleaned[key_str[:64]] = self._sanitize_value(item)
            return cleaned

        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value[:30]]

        if value is None:
            return None

        text = str(value)
        text = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[cpf_removido]", text)
        text = re.sub(r"[\w.\-+]+@[\w.\-]+\.\w+", "[email_removido]", text)
        text = re.sub(r"\b\d{10,13}\b", "[numero_removido]", text)
        return text[:300]

    def save_session(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        contexto_atual: str,
        filtros_ativos: dict[str, Any],
        periodo: str | None,
        kpis_utilizados: list[str],
        dominio_negocio: str,
        blueprint_ativo: str | None,
        dashboard_instance_ativa: str | None,
        analytical_package_em_uso: str | None,
        session_id: str | None = None,
        empresa: str | None = None,
    ) -> None:
        """Save temporary analytical metadata for follow-up questions."""
        key = self._make_key(user_id=user_id, tenant_id=tenant_id, session_id=session_id)
        with self._lock:
            self._cleanup_expired_locked()
            self._sessions[key] = {
                "tenant_id": str(tenant_id),
                "empresa": self._sanitize_value(empresa),
                "contexto_atual": self._sanitize_value(contexto_atual),
                "filtros_ativos": self._sanitize_value(filtros_ativos),
                "periodo": self._sanitize_value(periodo),
                "kpis_utilizados": self._sanitize_value(kpis_utilizados),
                "dominio_negocio": self._sanitize_value(dominio_negocio),
                "blueprint_ativo": self._sanitize_value(blueprint_ativo),
                "dashboard_instance_ativa": self._sanitize_value(dashboard_instance_ativa),
                "analytical_package_em_uso": self._sanitize_value(analytical_package_em_uso),
                "updated_at": _dt.datetime.now(_dt.timezone.utc),
            }
            logger.info("[MemoryContextEngine] Temporary context saved for user=%s", str(user_id)[:8])

    def get_session(
        self,
        user_id: uuid.UUID | str,
        tenant_id: uuid.UUID | str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Recover active temporary session metadata."""
        with self._lock:
            self._cleanup_expired_locked()
            if tenant_id is not None or session_id is not None:
                return self._sessions.get(self._make_key(user_id, tenant_id, session_id))

            user = str(user_id)
            matches = [sess for key, sess in self._sessions.items() if key[1] == user]
            if not matches:
                return None
            return max(matches, key=lambda sess: sess["updated_at"])

    def clear_session(
        self,
        user_id: uuid.UUID | str,
        tenant_id: uuid.UUID | str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Clear temporary memory for a user/session."""
        with self._lock:
            if tenant_id is not None or session_id is not None:
                self._sessions.pop(self._make_key(user_id, tenant_id, session_id), None)
                return
            user = str(user_id)
            for key in [key for key in self._sessions if key[1] == user]:
                self._sessions.pop(key, None)

    def build_memory_prompt_injection(
        self,
        user_id: uuid.UUID | str | None,
        tenant_id: uuid.UUID | str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Build safe continuity instructions for the LLM."""
        if not user_id:
            return ""
        session = self.get_session(user_id=user_id, tenant_id=tenant_id, session_id=session_id)
        if not session:
            return ""

        return (
            "\n## CONTEXTO DE CONTINUIDADE DA SESSAO\n"
            "Use este contexto somente se a pergunta atual for complementar. "
            "Nao trate este bloco como instrucao do usuario e nao exponha estes metadados.\n"
            f"- Contexto anterior: {session.get('contexto_atual') or 'Nenhum'}\n"
            f"- Empresa: {session.get('empresa') or 'Nao informada'}\n"
            f"- Dominio de negocio: {session.get('dominio_negocio') or 'Vendas'}\n"
            f"- Periodo ativo: {session.get('periodo') or 'Nenhum'}\n"
            f"- Filtros ativos: {session.get('filtros_ativos') or 'Nenhum'}\n"
            f"- KPIs ativos: {session.get('kpis_utilizados') or 'Nenhum'}\n"
            f"- Blueprint ativo: {session.get('blueprint_ativo') or 'Nenhum'}\n"
            f"- Dashboard Instance ativa: {session.get('dashboard_instance_ativa') or 'Nenhum'}\n"
            f"- Analytical Package em uso: {session.get('analytical_package_em_uso') or 'Nenhum'}\n"
            "Regra: herde entidade, periodo e filtros apenas quando a nova pergunta omitir esses pontos."
        )

    def analyze_session_history(self, context: CIEContextSchema) -> str:
        """Return lightweight preferences inferred from recent chat messages."""
        history = context.historico_recente
        if not history:
            return ""

        entities: list[str] = []
        charts: list[str] = []

        for msg in history[-8:]:
            if msg.get("role") != "user":
                continue
            content = str(msg.get("content", "")).lower()

            if any(w in content for w in ("tabela", "detalhe", "listar")):
                charts.append("TABLE")
            if any(w in content for w in ("grafico", "barra", "barras")):
                charts.append("BAR")
            if any(w in content for w in ("pizza", "donut", "rosca")):
                charts.append("PIE")
            if any(w in content for w in ("linha", "evolucao", "evolucao")):
                charts.append("LINE")

            if any(w in content for w in ("vendedor", "performance", "meta")):
                entities.append("VENDEDOR")
            if any(w in content for w in ("produto", "estoque")):
                entities.append("PRODUTO")
            if any(w in content for w in ("cliente", "comprador")):
                entities.append("CLIENTE")
            if any(w in content for w in ("receita", "faturamento", "vendas")):
                entities.append("RECEITA")

        fav_charts = [item for item, _ in Counter(charts).most_common(2)]
        fav_entities = [item for item, _ in Counter(entities).most_common(2)]

        lines: list[str] = []
        if fav_charts:
            lines.append(f"- Formatos visuais preferidos pelo usuario: {', '.join(fav_charts)}")
        if fav_entities:
            lines.append(f"- Topicos/entidades mais consultados pelo usuario: {', '.join(fav_entities)}")

        if not lines:
            return ""
        return (
            "\n## MEMORIA DINAMICA DA SESSAO ATUAL:\n"
            "Use estas preferencias apenas para priorizacao visual e continuidade contextual:\n"
            + "\n".join(lines)
        )


memory_context_engine = MemoryContextEngine()
