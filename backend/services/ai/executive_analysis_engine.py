"""
LuminaAI - Executive Analysis Engine
------------------------------------
Generates response text only from backend-provided analytical evidence.

The engine never queries databases, never executes SQL and never recalculates
metrics. Its role is to explain KPIs, comparisons, rankings and anomalies that
were already prepared by the backend/data platform.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from services.ai.response_builder import response_builder

logger = logging.getLogger("luminaai.ai.executive_analysis_engine")


class ExecutiveAnalysisEngine:
    """
    Motor do CIE encarregado da interpretação de relatórios e resumos em markdown.
    """

    _MAX_ROWS = 12
    _MAX_JSON_CHARS = 4500
    _SENSITIVE_KEYS = {
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
    }

    def build_analysis_prompt(self, mode: str, custom_instructions: str | None = None) -> str:
        """Return the system prompt for the official response mode."""
        resolved_mode = response_builder.normalize_mode(mode)

        if resolved_mode == "quick":
            system_prompt = (
                "Voce e o Assistente Operacional de Business Intelligence do LuminaAI.\n\n"
                "Modo oficial: Resposta Rapida.\n"
                "Objetivo: maxima velocidade, objetividade e baixo consumo de tokens.\n\n"
                "Regras:\n"
                "1. Retorne apenas uma resposta curta e operacional.\n"
                "2. Nao produza analises, insights, recomendacoes, correlacoes ou diagnosticos.\n"
                "3. Use exclusivamente numeros e metadados enviados pelo backend.\n"
                "4. Nunca invente dados, percentuais, tendencias ou comparacoes."
            )
        elif resolved_mode == "executive":
            system_prompt = (
                "Voce e o Diretor Executivo de Business Intelligence do LuminaAI.\n\n"
                "Modo oficial: Consultor Executivo.\n"
                "Sua responsabilidade e transformar evidencias fornecidas pelo backend em uma leitura "
                "executiva, madura e objetiva para decisores.\n\n"
                "Limites obrigatorios:\n"
                "1. Nunca consulte banco, nunca gere SQL e nunca recalcule metricas.\n"
                "2. Nunca invente informacoes, percentuais, tendencias, metas ou comparacoes.\n"
                "3. Se uma evidencia nao estiver no JSON, declare que ela nao esta disponivel.\n"
                "4. Nao exponha nomes tecnicos como query, view, tabela, coluna ou mock.\n\n"
                "Formato obrigatorio em Markdown:\n"
                "## 1. RESUMO EXECUTIVO\n"
                "## 2. PRINCIPAIS INDICADORES\n"
                "## 3. ANALISE COMPARATIVA\n"
                "## 4. INSIGHTS ESTRATEGICOS\n"
                "## 5. RISCOS IDENTIFICADOS\n"
                "## 6. OPORTUNIDADES IDENTIFICADAS\n"
                "## 7. RECOMENDACOES DE INVESTIGACAO\n"
                "## 8. OBSERVACOES FINAIS"
            )
        else:
            system_prompt = (
                "Voce e o Analista de Business Intelligence do LuminaAI.\n\n"
                "Modo oficial: Resposta Inteligente.\n"
                "Sua responsabilidade e explicar de forma curta os resultados ja calculados pelo backend, "
                "destacando apenas insights, alertas e comparacoes que estejam explicitamente disponiveis.\n\n"
                "Regras:\n"
                "1. Nunca consulte banco, nunca gere SQL e nunca recalcule metricas.\n"
                "2. Nunca invente informacoes, percentuais, tendencias ou comparacoes.\n"
                "3. Seja objetivo e evite exageros: 2 a 4 insights no maximo.\n"
                "4. Nao use jargoes tecnicos de implementacao.\n\n"
                "Formato obrigatorio em Markdown:\n"
                "## 1. RESUMO ANALITICO\n"
                "## 2. COMPARACOES DISPONIVEIS\n"
                "## 3. INSIGHTS RELEVANTES\n"
                "## 4. ALERTAS"
            )

        if custom_instructions:
            system_prompt += (
                "\n\n## CONTEXTO EMPRESARIAL AUTORIZADO DO TENANT\n"
                f"{self._strip_prompt_control_text(custom_instructions)}"
            )

        return system_prompt

    def _strip_prompt_control_text(self, text: str) -> str:
        """Remove common prompt-control fragments from tenant/user-provided text."""
        cleaned = str(text or "")
        blocked_fragments = [
            r"ignore (as )?(instrucoes|instructions).*",
            r"revele? (o )?(prompt|system prompt).*",
            r"jailbreak.*",
            r"developer message.*",
            r"system message.*",
        ]
        for pattern in blocked_fragments:
            cleaned = re.sub(pattern, "[trecho removido por seguranca]", cleaned, flags=re.IGNORECASE)
        return cleaned[:1200]

    def _mask_sensitive(self, value: Any, key: str | None = None) -> Any:
        key_norm = (key or "").lower()
        if any(s in key_norm for s in self._SENSITIVE_KEYS):
            return "[removido]"

        if isinstance(value, dict):
            return {str(k): self._mask_sensitive(v, str(k)) for k, v in value.items()}

        if isinstance(value, list):
            return [self._mask_sensitive(item, key) for item in value]

        if isinstance(value, str):
            text = value
            text = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[cpf_removido]", text)
            text = re.sub(r"[\w.\-+]+@[\w.\-]+\.\w+", "[email_removido]", text)
            return text[:300]

        return value

    def _summarize_data_for_tokens(self, data: Any) -> Any:
        """Compact large payloads before sending them to the LLM."""
        data = self._mask_sensitive(data)

        if isinstance(data, dict):
            return {str(k): self._summarize_data_for_tokens(v) for k, v in data.items()}

        if isinstance(data, list):
            total = len(data)
            if total > self._MAX_ROWS:
                return {
                    "total_linhas": total,
                    "nota": "Dataset resumido para reduzir tokens; dados completos ficam no backend.",
                    "primeiras_linhas_amostra": data[:5],
                    "ultimas_linhas_amostra": data[-3:],
                }
            return [self._summarize_data_for_tokens(item) for item in data]

        return data

    async def generate_analysis(
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
        """Generate the final natural-language response for the selected mode."""
        resolved_mode = response_builder.normalize_mode(mode)
        if resolved_mode == "quick":
            return response_builder.build_quick_response()

        system_prompt = self.build_analysis_prompt(resolved_mode, custom_instructions)

        from services.ai.memory_context_engine import memory_context_engine
        from services.ai.schemas import CIEContextSchema
        import uuid as _uuid

        ctx = CIEContextSchema(tenant_id=_uuid.uuid4(), historico_recente=history or [])
        session_profile = memory_context_engine.analyze_session_history(ctx)
        if session_profile:
            system_prompt += f"\n\n{session_profile}"

        optimized_data = self._summarize_data_for_tokens(dados)
        data_json = json.dumps(optimized_data, default=str, ensure_ascii=False)[: self._MAX_JSON_CHARS]

        user_prompt = (
            f"Pergunta do usuario: {pergunta[:1000]}\n"
            f"Contexto de negocio: {view_name[:200]}\n"
            "Dados preparados pelo backend em JSON:\n"
            f"{data_json}\n"
        )

        try:
            response = await client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=900 if resolved_mode == "analytical" else 1500,
                temperature=0.2,
            )
            insight = response.choices[0].message.content
            return insight.strip() if insight else "Nenhuma analise gerada."
        except Exception as exc:
            logger.error("Erro ao gerar analise de dados com IA: %s", exc)
            return "Dados processados com sucesso. Consulte os indicadores e graficos para detalhes."


executive_analysis_engine = ExecutiveAnalysisEngine()
