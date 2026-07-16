"""
LuminaAI — Context Guard: Guardião de Escopo e Segurança do Contexto Vendas

Este módulo implementa a segunda camada de segurança após o Motor de Intenções.
Sua responsabilidade é:
1. Bloquear acesso a informações fora do escopo de vendas (salários, dados médicos, etc.)
2. Sanitizar e validar os parâmetros extraídos pela IA
3. Limitar o volume de dados retornados (proteção contra data dumps)
4. Detectar e bloquear tentativas de prompt injection nos parâmetros
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("luminaai.services.context_guard")

# ── Termos absolutamente proibidos nos parâmetros (dados fora de escopo) ──
_BLOCKED_PARAM_PATTERNS = [
    r"salario", r"salary", r"folha", r"payroll", r"cpf", r"rg", r"senha",
    r"password", r"hash", r"secret", r"medic", r"saude", r"health",
    r"ponto_eletronico", r"biometric", r"drop", r"delete", r"truncat",
    r"insert", r"update", r"create", r"alter", r"grant", r"revoke",
    r"exec", r"execute", r"xp_", r"sp_", r"union", r"--", r";",
    r"\bor\b.*=.*\b", r"\band\b.*=.*\b",
]

_COMPILED_BLOCKED = [re.compile(p, re.IGNORECASE) for p in _BLOCKED_PARAM_PATTERNS]

_BLOCKED_QUERY_PATTERNS = [
    r"ignore\s+.*(instrucoes|instructions|regras|rules)",
    r"desconsidere (as )?(instrucoes|regras)",
    r"reveal (the )?(system|developer|hidden) prompt",
    r"reveal\s+.*(token|secret|key|credential|api)",
    r"(revele|mostre|exponha)\s+.*(token|chave|senha|segredo|credencial|api)",
    r"mostre (o )?(prompt|system prompt|developer message)",
    r"jailbreak",
    r"prompt injection",
    r"developer message",
    r"system message",
    r"modo desenvolvedor",
    r"dan mode",
    r"bypass",
    r"sem autorizacao",
    r"exfiltr",
    r"<\s*script\b",
    r"javascript\s*:",
    r"document\.cookie",
    r"onerror\s*=",
    r"\bunion\s+select\b",
    r"\bor\s+1\s*=\s*1\b",
    r"--",
    r"\b(drop|truncate|alter|grant|revoke|delete)\s+(table|database|schema|from)\b",
]

_COMPILED_QUERY_BLOCKED = [re.compile(p, re.IGNORECASE) for p in _BLOCKED_QUERY_PATTERNS]

# Comprimento máximo permitido para um valor de parâmetro
_MAX_PARAM_VALUE_LEN = 200
_NULL_LIKE_VALUES = {"", "none", "null", "undefined", "nan"}

# Número máximo de linhas retornadas por consulta (proteção anti-dump)
MAX_ROWS_PER_QUERY = 500


class ScopeViolationError(Exception):
    """Raised when a query or parameter violates the authorized scope."""
    pass


def validate_user_query(query: str) -> str:
    """
    Validate the raw user query before it reaches the LLM or cache layers.

    This blocks prompt injection, jailbreak attempts and direct destructive SQL
    instructions. The returned text is trimmed but otherwise preserved so the
    user's analytical intent is not changed.
    """
    text = str(query or "").strip()
    if not text:
        raise ScopeViolationError("A pergunta nao pode estar vazia.")

    for pattern in _COMPILED_QUERY_BLOCKED:
        if pattern.search(text):
            logger.warning("Pergunta bloqueada por politica anti prompt-injection: %r", text[:120])
            raise ScopeViolationError(
                "A consulta contem instrucoes de manipulacao de contexto ou fora do escopo autorizado."
            )

    return text[:1000]


def sanitize_history(
    history: list[dict[str, str]] | None,
    *,
    max_messages: int = 8,
    max_chars: int = 600,
) -> list[dict[str, str]]:
    """
    Return a compact and safe chat history for prompt context.

    Suspicious history messages are omitted instead of raising, because old
    messages should not block a legitimate new query.
    """
    cleaned: list[dict[str, str]] = []
    for item in list(history or [])[-max_messages:]:
        role = item.get("role")
        content = str(item.get("content", "") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        if any(pattern.search(content) for pattern in _COMPILED_QUERY_BLOCKED):
            logger.warning("Mensagem de historico omitida por seguranca: %r", content[:120])
            continue
        cleaned.append({"role": role, "content": content[:max_chars]})
    return cleaned


def validate_params(params: dict[str, str]) -> dict[str, str]:
    """
    Validates and sanitizes parameters extracted by the AI.

    Raises ScopeViolationError if any parameter violates the security policy.
    Returns a cleaned copy of the parameters dict with safe keys and values.

    Security checks applied:
    - Key must be a valid identifier (alphanumeric + underscore, max 64 chars)
    - Value is truncated to _MAX_PARAM_VALUE_LEN characters
    - Both key and value are scanned against _COMPILED_BLOCKED patterns
    """
    cleaned: dict[str, str] = {}

    for key, value in params.items():
        # ── Validate key format ──
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]{0,63}$', str(key)):
            logger.warning("Parâmetro com chave inválida bloqueado: %r", key)
            continue

        str_value = str(value).strip() if value is not None else ""
        if str_value.lower() in _NULL_LIKE_VALUES:
            continue

        # ── Length guard on value ──
        if len(str_value) > _MAX_PARAM_VALUE_LEN:
            logger.warning(
                "Parâmetro '%s' truncado (comprimento %d > máximo %d)",
                key, len(str_value), _MAX_PARAM_VALUE_LEN,
            )
            str_value = str_value[:_MAX_PARAM_VALUE_LEN]

        # ── Pattern check on VALUE ──
        for pattern in _COMPILED_BLOCKED:
            if pattern.search(str_value):
                logger.error(
                    "BLOQUEIO DE SEGURANÇA: parâmetro '%s' contém padrão proibido. "
                    "Value: %r",
                    key, str_value[:50],
                )
                raise ScopeViolationError(
                    "A consulta contém informações fora do escopo autorizado. "
                    "O sistema só pode acessar dados de vendas, clientes e produtos."
                )

        # ── Pattern check on KEY name ──
        for pattern in _COMPILED_BLOCKED:
            if pattern.search(key):
                logger.warning(
                    "Chave de parâmetro bloqueada por segurança: %r", key
                )
                raise ScopeViolationError(
                    f"Parâmetro '{key}' não é permitido neste contexto."
                )

        cleaned[key] = str_value

    return cleaned


def validate_query_intent(justificativa: str) -> None:
    """
    Analyzes the AI's justification text for signs that the query
    is attempting to access out-of-scope data.

    This is a soft-warning check only — it does NOT raise an exception.
    Hard blocks occur at the parameter level in :func:`validate_params`.
    Out-of-scope queries flagged by the AI's own ``fora_de_escopo`` field
    are handled upstream in the router before this function is ever called.
    """
    blocked_intent_terms = [
        "salário", "salary", "folha de pagamento", "payroll",
        "dados médicos", "prontuário", "senha", "credencial",
        "dado pessoal sensível",
    ]
    j_lower = justificativa.lower()
    for term in blocked_intent_terms:
        if term in j_lower:
            logger.warning(
                "Intenção possivelmente fora de escopo detectada na justificativa: %r",
                justificativa[:100],
            )
            # Soft warning — the AI's fora_de_escopo field is the authoritative gate.
            break


def apply_row_limit(params: dict[str, str]) -> dict[str, str]:
    """
    Ensures the 'limite' parameter does not exceed MAX_ROWS_PER_QUERY.

    If the AI extracted a row limit higher than the allowed maximum, it is
    silently capped. If no ``limite`` key is present, the maximum is injected
    as a default so the oracle_service always has a safe ROWNUM bound.

    Args:
        params: Cleaned parameter dictionary (output of :func:`validate_params`).

    Returns:
        A copy of the parameters dict with ``limite`` set to a safe integer string.
    """
    p = dict(params)
    if "limite" in p:
        try:
            requested = int(p["limite"])
            if requested > MAX_ROWS_PER_QUERY:
                logger.warning(
                    "Limite de linhas reduzido: %d -> %d",
                    requested, MAX_ROWS_PER_QUERY,
                )
                p["limite"] = str(MAX_ROWS_PER_QUERY)
        except ValueError:
            # Non-numeric value — replace with the safe maximum
            logger.warning(
                "Valor de 'limite' não numérico '%s' substituído por %d",
                p["limite"], MAX_ROWS_PER_QUERY,
            )
            p["limite"] = str(MAX_ROWS_PER_QUERY)
    else:
        p["limite"] = str(MAX_ROWS_PER_QUERY)
    return p
