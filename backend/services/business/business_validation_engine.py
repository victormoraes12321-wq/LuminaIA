"""
LuminaAI — Business Validation Engine Service
----------------------------------------------
Validador ativo de consistência de regras de negócio.
Analisa e valida fórmulas, KPIs, dependências, agrupamentos e filtros antes de executar dados.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("luminaai.business.validation_engine")


class BusinessValidationError(Exception):
    """Exceção levantada em caso de violação de consistência de regras de negócio."""
    def __init__(self, message: str, errors: list[str] = None):
        super().__init__(message)
        self.errors = errors or [message]


class BusinessValidationEngine:
    """
    Executa validações lógicas e matemáticas no plano de consulta antes da execução no banco.
    """

    async def validate_query_plan(
        self,
        tenant_id: uuid.UUID,
        plan: Any,
        db: AsyncSession,
    ) -> tuple[bool, list[str]]:
        """
        Valida a consistência de um Query Plan.
        Retorna (is_valid, list_of_errors).
        """
        errors: list[str] = []

        if not plan:
            return True, []

        from services.business.business_dictionary import business_dictionary
        from services.business.business_kpi_registry import business_kpi_registry

        principal = getattr(plan, "consulta_principal", None)
        if not principal:
            return True, []

        # Coleta as métricas solicitadas
        metrics = getattr(principal, "metrics", []) or []
        group_bys = getattr(principal, "group_by", []) or []
        filters = getattr(principal, "filters", {}) or {}
        operation = getattr(principal, "operacao", "") or "SOMA"

        # 1. Validação de existência de métricas no dicionário ou registro de KPIs
        for metric in metrics:
            concept = await business_dictionary.get_concept(tenant_id, metric, db)
            kpi = await business_kpi_registry.get_kpi(tenant_id, metric, db)

            if not concept and not kpi:
                # Caso a métrica seja genérica, tenta verificar se existe no fallback estático
                from services.semantic_layer import get_metric_info
                if not get_metric_info(metric):
                    errors.append(f"Métrica/KPI '{metric}' não registrada no dicionário de negócios oficial.")
                    continue
                else:
                    # Métrica está no catálogo estático, válido para compatibilidade
                    continue

            # 2. Validação matemática de agregação (SUM em taxas/porcentagens)
            tipo_unidade = ""
            if concept:
                tipo_unidade = concept.unidade or ""
            elif kpi:
                tipo_unidade = kpi.unidade or ""

            if "%" in tipo_unidade or "taxa" in metric.lower() or "margem" in metric.lower():
                if operation.upper() in ["SOMA", "SUM"]:
                    errors.append(
                        f"Operação SOMA inválida para a métrica proporcional/percentual '{metric}'. "
                        "Taxas e percentuais exigem médias ponderadas ou cálculos compostos."
                    )

            # 3. Validação de dependências do KPI
            if kpi and kpi.formula_oficial:
                # Se o KPI tem dependências explícitas, elas precisam estar mapeadas ou disponíveis
                # (no futuro, o dependency engine pode enriquecer essa validação)
                pass

        # 4. Validação de filtros e períodos
        # Exemplo: impedir filtros inválidos (ex: filtrar produto por região sem junção)
        # E garantir que as datas de referência façam sentido
        date_range = filters.get("date_range") if isinstance(filters, dict) else getattr(filters, "date_range", None)
        if date_range:
            # Validação simples de formato de range temporal
            if len(str(date_range)) > 100:
                errors.append("Período temporal (date_range) muito longo ou em formato inválido.")

        # 5. Validação de tipos de agrupamento (group_by)
        # Impede agrupamento por valores métricos (ex: agrupar por 'receita')
        for gb in group_bys:
            gb_kpi = await business_kpi_registry.get_kpi(tenant_id, gb, db)
            if gb_kpi:
                errors.append(
                    f"Agrupamento (group_by) inválido: '{gb}' é um KPI e não uma dimensão catalogada."
                )

        is_valid = len(errors) == 0
        return is_valid, errors

    async def validate_formula_inputs(
        self,
        formula_nome: str,
        inputs: dict[str, Any],
    ) -> list[str]:
        """Valida se os inputs informados satisfazem as regras e tipos de dados da fórmula."""
        from services.business.business_formula_engine import business_formula_engine
        meta_list = business_formula_engine.get_default_formulas_metadata()
        meta = next((m for m in meta_list if m["nome"].lower() == formula_nome.lower()), None)

        if not meta:
            return [f"Fórmula '{formula_nome}' não localizada no catálogo."]

        errors = []
        for entrada in meta["entradas"]:
            nome = entrada["nome"]
            tipo = entrada["tipo"]

            if nome not in inputs:
                errors.append(f"Parâmetro de entrada '{nome}' obrigatório ausente.")
                continue

            val = inputs[nome]
            # Validação de tipo de dado
            if tipo == "float" and not isinstance(val, (int, float)):
                errors.append(f"Tipo incorreto para '{nome}': esperado float, obtido {type(val).__name__}.")
            elif tipo == "int" and not isinstance(val, int):
                errors.append(f"Tipo incorreto para '{nome}': esperado int, obtido {type(val).__name__}.")
            elif tipo == "list[float]" and not isinstance(val, list):
                errors.append(f"Tipo incorreto para '{nome}': esperado list, obtido {type(val).__name__}.")

        return errors


# Singleton export
business_validation_engine = BusinessValidationEngine()
