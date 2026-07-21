"""
LuminaAI — Business Formula Engine Service
-------------------------------------------
Centraliza as fórmulas analíticas corporativas oficiais de BI.
Implementa definições e metadados para as 23 fórmulas de gestão exigidas.
Garante que não haja conflitos e valida parâmetros de entrada/saída.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.business_formula import BusinessFormula
from services.business.business_governance import business_governance

logger = logging.getLogger("luminaai.business.formula_engine")


class BusinessFormulaEngine:
    """
    Gerencia e executa validações/definições de fórmulas de BI corporativas.
    """

    async def get_formula(
        self,
        tenant_id: uuid.UUID,
        nome: str,
        db: AsyncSession,
    ) -> BusinessFormula | None:
        """Busca uma fórmula pelo nome e tenant."""
        stmt = select(BusinessFormula).where(
            and_(
                BusinessFormula.tenant_id == tenant_id,
                BusinessFormula.nome.ilike(nome.strip()),
                BusinessFormula.status == "ACTIVE",
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_formulas(
        self,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[BusinessFormula]:
        """Lista todas as fórmulas ativas do tenant."""
        stmt = select(BusinessFormula).where(
            and_(
                BusinessFormula.tenant_id == tenant_id,
                BusinessFormula.status == "ACTIVE",
            )
        ).order_by(BusinessFormula.nome.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def register_formula(
        self,
        tenant_id: uuid.UUID,
        formula_data: dict[str, Any],
        autor: str,
        db: AsyncSession,
    ) -> BusinessFormula:
        """Registra ou atualiza uma fórmula de negócio sob controle de governança."""
        nome = formula_data["nome"].strip()
        existing = await self.get_formula(tenant_id, nome, db)

        if existing:
            has_changes = False
            alteracoes = {}
            for field in ["formula", "entradas", "saidas", "pre_requisitos", "dependencias", "validacoes"]:
                if field in formula_data:
                    val_new = formula_data[field]
                    val_old = getattr(existing, field)
                    if val_new != val_old:
                        has_changes = True
                        alteracoes[field] = {"old": val_old, "new": val_new}

            if not has_changes:
                return existing

            old_snapshot = self._to_snapshot(existing)
            existing.formula = formula_data.get("formula", existing.formula)
            existing.entradas = list(formula_data.get("entradas", existing.entradas))
            existing.saidas = list(formula_data.get("saidas", existing.saidas))
            existing.pre_requisitos = list(formula_data.get("pre_requisitos", existing.pre_requisitos))
            existing.dependencias = list(formula_data.get("dependencias", existing.dependencias))
            existing.validacoes = list(formula_data.get("validacoes", existing.validacoes))
            existing.versao += 1

            db.add(existing)

            await business_governance.log_action(
                tenant_id=tenant_id,
                estrutura_tipo="FORMULA",
                estrutura_nome=nome,
                versao=existing.versao,
                autor=autor,
                acao="UPDATE",
                alteracoes=alteracoes,
                snapshot=old_snapshot,
                db=db,
            )
            return existing

        else:
            formula = BusinessFormula(
                tenant_id=tenant_id,
                nome=nome,
                formula=formula_data["formula"],
                entradas=list(formula_data.get("entradas", [])),
                saidas=list(formula_data.get("saidas", [])),
                pre_requisitos=list(formula_data.get("pre_requisitos", [])),
                dependencias=list(formula_data.get("dependencias", [])),
                validacoes=list(formula_data.get("validacoes", [])),
                status="ACTIVE",
                versao=1,
            )
            db.add(formula)
            await db.flush()

            await business_governance.log_action(
                tenant_id=tenant_id,
                estrutura_tipo="FORMULA",
                estrutura_nome=nome,
                versao=1,
                autor=autor,
                acao="CREATE",
                alteracoes={"criado": True},
                snapshot=self._to_snapshot(formula),
                db=db,
            )
            return formula

    def evaluate_formula(
        self,
        formula_nome: str,
        inputs: dict[str, Any],
    ) -> Any:
        """
        Avalia (executa) uma fórmula localmente com propósitos de validação matemática.
        Previne inconsistências ou erros de divisão por zero.
        """
        # Obtenção da definição matemática estática associada
        definitions = self.get_default_formulas_metadata()
        meta = next((m for m in definitions if m["nome"].lower() == formula_nome.lower()), None)

        if not meta:
            raise ValueError(f"Fórmula '{formula_nome}' não catalogada.")

        # Valida pré-requisitos lógicos
        for req in meta["pre_requisitos"]:
            if "investimento > 0" in req and inputs.get("investimento", 0) <= 0:
                raise ValueError("Erro: Investimento deve ser maior que zero.")
            if "preco_custo > 0" in req and inputs.get("preco_custo", 0) <= 0:
                raise ValueError("Erro: Preço de custo deve ser maior que zero.")
            if "receita_total > 0" in req and inputs.get("receita_total", 0) <= 0:
                raise ValueError("Erro: Receita total deve ser maior que zero.")
            if "total_pedidos > 0" in req and inputs.get("total_pedidos", 0) <= 0:
                raise ValueError("Erro: Total de pedidos deve ser maior que zero.")
            if "valor_anterior != 0" in req and inputs.get("valor_anterior", 0) == 0:
                raise ValueError("Erro: Valor anterior não pode ser zero.")

        # Avaliação de fórmula (cálculos matemáticos)
        try:
            name_lower = formula_nome.lower()
            if name_lower == "receita":
                return sum(inputs["vendas_aprovadas"])
            elif name_lower == "lucro":
                return inputs["receita_total"] - inputs["custo_total"]
            elif name_lower == "margem":
                return (inputs["lucro_bruto"] / inputs["receita_total"]) * 100
            elif name_lower == "markup":
                return (inputs["preco_venda"] - inputs["preco_custo"]) / inputs["preco_custo"]
            elif name_lower == "roi":
                return (inputs["retorno"] - inputs["investimento"]) / inputs["investimento"]
            elif name_lower == "roas":
                return inputs["receita_campanha"] / inputs["custo_campanha"]
            elif name_lower == "cac":
                return inputs["custos_aquisicao"] / inputs["novos_clientes"]
            elif name_lower == "ltv":
                return inputs["ticket_medio"] * inputs["frequencia_compras"] * inputs["tempo_vida_medio"]
            elif name_lower == "cmv":
                return inputs["estoque_inicial"] + inputs["compras"] - inputs["estoque_final"]
            elif name_lower == "ticket médio" or name_lower == "ticket_medio":
                return inputs["receita_total"] / inputs["total_pedidos"]
            elif name_lower == "preço médio" or name_lower == "preco_medio":
                return inputs["receita_total"] / inputs["total_unidades"]
            elif name_lower == "conversão" or name_lower == "conversao":
                return (inputs["oportunidades_ganhas"] / inputs["total_oportunidades"]) * 100
            elif name_lower == "giro":
                return inputs["custo_vendas"] / inputs["estoque_medio"]
            elif name_lower == "cobertura":
                return inputs["estoque_atual"] / inputs["media_vendas_periodo"]
            elif name_lower == "capital de giro" or name_lower == "capital_de_giro":
                return inputs["ativo_circulante"] - inputs["passivo_circulante"]
            elif name_lower == "fluxo de caixa" or name_lower == "fluxo_de_caixa":
                return inputs["entradas_caixa"] - inputs["saidas_caixa"]
            elif name_lower == "rentabilidade":
                return (inputs["lucro_liquido"] / inputs["investimento_total"]) * 100
            elif name_lower == "curva abc" or name_lower == "curva_abc":
                # Ordena decrescente por valor
                sorted_items = sorted(inputs["valores_itens"], key=lambda x: x["valor"], reverse=True)
                total = sum(item["valor"] for item in sorted_items)
                accum = 0.0
                result = []
                for item in sorted_items:
                    accum += item["valor"]
                    part = accum / total
                    if part <= 0.80:
                        classe = "A"
                    elif part <= 0.95:
                        classe = "B"
                    else:
                        classe = "C"
                    result.append({"nome": item["nome"], "classe": classe, "acumulado": part})
                return result
            elif name_lower == "participação" or name_lower == "participacao":
                return (inputs["valor_item"] / inputs["valor_total"]) * 100
            elif name_lower == "diferença absoluta" or name_lower == "diferenca_absoluta":
                return inputs["valor_atual"] - inputs["valor_anterior"]
            elif name_lower == "diferença percentual" or name_lower == "diferenca_percentual":
                return ((inputs["valor_actual"] - inputs["valor_anterior"]) / inputs["valor_anterior"]) * 100
            elif name_lower == "crescimento":
                return (inputs["valor_fim"] / inputs["valor_inicio"] - 1) * 100
            elif name_lower == "média móvel" or name_lower == "media_movel":
                serie = inputs["valores_serie"]
                w = inputs["janela"]
                return [sum(serie[i:i+w])/w for i in range(len(serie)-w+1)]
        except Exception as e:
            raise ValueError(f"Falha na execução da fórmula '{formula_nome}': {e}")

    async def seed_formulas(self, tenant_id: uuid.UUID, db: AsyncSession) -> int:
        """Popula as 23 fórmulas de BI padrão no banco do tenant no primeiro acesso."""
        defaults = self.get_default_formulas_metadata()
        count = 0
        for data in defaults:
            existing = await self.get_formula(tenant_id, data["nome"], db)
            if not existing:
                await self.register_formula(tenant_id, data, "SYSTEM_SEED", db)
                count += 1
        return count

    def get_default_formulas_metadata(self) -> list[dict[str, Any]]:
        """Retorna o dicionário padrão com as especificações das 23 fórmulas de BI."""
        return [
            {
                "nome": "Faturamento Bruto",
                "formula": "sum(ptotal_)",
                "entradas": [{"nome": "vendas_brutas", "tipo": "list[float]"}],
                "saidas": [{"nome": "faturamento_bruto", "tipo": "float"}],
                "pre_requisitos": [],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Faturamento Líquido",
                "formula": "faturamento_bruto - devolucoes - descontos",
                "entradas": [
                    {"nome": "faturamento_bruto", "tipo": "float"},
                    {"nome": "devolucoes", "tipo": "float"},
                    {"nome": "descontos", "tipo": "float"},
                ],
                "saidas": [{"nome": "faturamento_liquido", "tipo": "float"}],
                "pre_requisitos": [],
                "dependencias": ["faturamento_bruto"],
                "validacoes": [],
            },
            {
                "nome": "Receita",
                "formula": "sum(vendas_aprovadas)",
                "entradas": [{"nome": "vendas_aprovadas", "tipo": "list[float]"}],
                "saidas": [{"nome": "receita_total", "tipo": "float"}],
                "pre_requisitos": [],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Lucro",
                "formula": "receita_total - custo_total",
                "entradas": [{"nome": "receita_total", "tipo": "float"}, {"nome": "custo_total", "tipo": "float"}],
                "saidas": [{"nome": "lucro_bruto", "tipo": "float"}],
                "pre_requisitos": [],
                "dependencias": ["receita_total", "custo_total"],
                "validacoes": [],
            },
            {
                "nome": "Margem",
                "formula": "(lucro_bruto / receita_total) * 100",
                "entradas": [{"nome": "lucro_bruto", "tipo": "float"}, {"nome": "receita_total", "tipo": "float"}],
                "saidas": [{"nome": "margem_lucro", "tipo": "float"}],
                "pre_requisitos": ["receita_total > 0"],
                "dependencias": ["lucro_bruto", "receita_total"],
                "validacoes": [],
            },
            {
                "nome": "Markup",
                "formula": "(preco_venda - preco_custo) / preco_custo",
                "entradas": [{"nome": "preco_venda", "tipo": "float"}, {"nome": "preco_custo", "tipo": "float"}],
                "saidas": [{"nome": "markup", "tipo": "float"}],
                "pre_requisitos": ["preco_custo > 0"],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "ROI",
                "formula": "(retorno - investimento) / investimento",
                "entradas": [{"nome": "retorno", "tipo": "float"}, {"nome": "investimento", "tipo": "float"}],
                "saidas": [{"nome": "roi", "tipo": "float"}],
                "pre_requisitos": ["investimento > 0"],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "ROAS",
                "formula": "receita_campanha / custo_campanha",
                "entradas": [{"nome": "receita_campanha", "tipo": "float"}, {"nome": "custo_campanha", "tipo": "float"}],
                "saidas": [{"nome": "roas", "tipo": "float"}],
                "pre_requisitos": ["custo_campanha > 0"],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "CAC",
                "formula": "custos_aquisicao / novos_clientes",
                "entradas": [{"nome": "custos_aquisicao", "tipo": "float"}, {"nome": "novos_clientes", "tipo": "int"}],
                "saidas": [{"nome": "cac", "tipo": "float"}],
                "pre_requisitos": ["novos_clientes > 0"],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "LTV",
                "formula": "ticket_medio * frequencia_compras * tempo_vida_medio",
                "entradas": [
                    {"nome": "ticket_medio", "tipo": "float"},
                    {"nome": "frequencia_compras", "tipo": "float"},
                    {"nome": "tempo_vida_medio", "tipo": "float"},
                ],
                "saidas": [{"nome": "ltv", "tipo": "float"}],
                "pre_requisitos": [],
                "dependencias": ["ticket_medio"],
                "validacoes": [],
            },
            {
                "nome": "CMV",
                "formula": "estoque_inicial + compras - estoque_final",
                "entradas": [
                    {"nome": "estoque_inicial", "tipo": "float"},
                    {"nome": "compras", "tipo": "float"},
                    {"nome": "estoque_final", "tipo": "float"},
                ],
                "saidas": [{"nome": "cmv", "tipo": "float"}],
                "pre_requisitos": [],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Ticket Médio",
                "formula": "receita_total / total_pedidos",
                "entradas": [{"nome": "receita_total", "tipo": "float"}, {"nome": "total_pedidos", "tipo": "int"}],
                "saidas": [{"nome": "ticket_medio", "tipo": "float"}],
                "pre_requisitos": ["total_pedidos > 0"],
                "dependencias": ["receita_total"],
                "validacoes": [],
            },
            {
                "nome": "Preço Médio",
                "formula": "receita_total / total_unidades",
                "entradas": [{"nome": "receita_total", "tipo": "float"}, {"nome": "total_unidades", "tipo": "int"}],
                "saidas": [{"nome": "preco_medio", "tipo": "float"}],
                "pre_requisitos": ["total_unidades > 0"],
                "dependencias": ["receita_total"],
                "validacoes": [],
            },
            {
                "nome": "Conversão",
                "formula": "(oportunidades_ganhas / total_oportunidades) * 100",
                "entradas": [
                    {"nome": "oportunidades_ganhas", "tipo": "int"},
                    {"nome": "total_oportunidades", "tipo": "int"},
                ],
                "saidas": [{"nome": "taxa_conversao", "tipo": "float"}],
                "pre_requisitos": ["total_oportunidades > 0"],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Giro",
                "formula": "custo_vendas / estoque_medio",
                "entradas": [{"nome": "custo_vendas", "tipo": "float"}, {"nome": "estoque_medio", "tipo": "float"}],
                "saidas": [{"nome": "giro_estoque", "tipo": "float"}],
                "pre_requisitos": ["estoque_medio > 0"],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Cobertura",
                "formula": "estoque_atual / media_vendas_periodo",
                "entradas": [
                    {"nome": "estoque_atual", "tipo": "float"},
                    {"nome": "media_vendas_periodo", "tipo": "float"},
                ],
                "saidas": [{"nome": "cobertura_estoque", "tipo": "float"}],
                "pre_requisitos": ["media_vendas_periodo > 0"],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Capital de Giro",
                "formula": "ativo_circulante - passivo_circulante",
                "entradas": [
                    {"nome": "ativo_circulante", "tipo": "float"},
                    {"nome": "passivo_circulante", "tipo": "float"},
                ],
                "saidas": [{"nome": "capital_de_giro", "tipo": "float"}],
                "pre_requisitos": [],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Fluxo de Caixa",
                "formula": "entradas_caixa - saidas_caixa",
                "entradas": [{"nome": "entradas_caixa", "tipo": "float"}, {"nome": "saidas_caixa", "tipo": "float"}],
                "saidas": [{"nome": "fluxo_de_caixa", "tipo": "float"}],
                "pre_requisitos": [],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Rentabilidade",
                "formula": "(lucro_liquido / investimento_total) * 100",
                "entradas": [
                    {"nome": "lucro_liquido", "tipo": "float"},
                    {"nome": "investimento_total", "tipo": "float"},
                ],
                "saidas": [{"nome": "rentabilidade", "tipo": "float"}],
                "pre_requisitos": ["investimento_total > 0"],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Curva ABC",
                "formula": "Ordena decrescente e categoriza classes A(80%), B(15%) e C(5%)",
                "entradas": [{"nome": "valores_itens", "tipo": "list[dict]"}],
                "saidas": [{"nome": "classificacao_abc", "tipo": "list[dict]"}],
                "pre_requisitos": [],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Participação",
                "formula": "(valor_item / valor_total) * 100",
                "entradas": [{"nome": "valor_item", "tipo": "float"}, {"nome": "valor_total", "tipo": "float"}],
                "saidas": [{"nome": "participacao", "tipo": "float"}],
                "pre_requisitos": ["valor_total > 0"],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Diferença Absoluta",
                "formula": "valor_atual - valor_anterior",
                "entradas": [{"nome": "valor_atual", "tipo": "float"}, {"nome": "valor_anterior", "tipo": "float"}],
                "saidas": [{"nome": "diferenca_absoluta", "tipo": "float"}],
                "pre_requisitos": [],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Diferença Percentual",
                "formula": "((valor_atual - valor_anterior) / valor_anterior) * 100",
                "entradas": [{"nome": "valor_atual", "tipo": "float"}, {"nome": "valor_anterior", "tipo": "float"}],
                "saidas": [{"nome": "diferenca_percentual", "tipo": "float"}],
                "pre_requisitos": ["valor_anterior != 0"],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Crescimento",
                "formula": "(valor_fim / valor_inicio - 1) * 100",
                "entradas": [{"nome": "valor_fim", "tipo": "float"}, {"nome": "valor_inicio", "tipo": "float"}],
                "saidas": [{"nome": "crescimento", "tipo": "float"}],
                "pre_requisitos": ["valor_inicio > 0"],
                "dependencias": [],
                "validacoes": [],
            },
            {
                "nome": "Média Móvel",
                "formula": "Média dos valores em janela deslizante",
                "entradas": [{"nome": "valores_serie", "tipo": "list[float]"}, {"nome": "janela", "tipo": "int"}],
                "saidas": [{"nome": "media_movel", "tipo": "list[float]"}],
                "pre_requisitos": [],
                "dependencias": [],
                "validacoes": [],
            },
        ]

    def _to_snapshot(self, formula: BusinessFormula) -> dict[str, Any]:
        return {
            "nome": formula.nome,
            "formula": formula.formula,
            "entradas": list(formula.entradas or []),
            "saidas": list(formula.saidas or []),
            "pre_requisitos": list(formula.pre_requisitos or []),
            "dependencias": list(formula.dependencias or []),
            "validacoes": list(formula.validacoes or []),
            "status": formula.status,
            "versao": formula.versao,
        }


# Singleton export
business_formula_engine = BusinessFormulaEngine()
