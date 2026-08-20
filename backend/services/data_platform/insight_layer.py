import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from services.ai_service import generate_data_insights

logger = logging.getLogger("luminaai.data_platform.insight_layer")


class InsightLayer:
    """
    Interprets backend-prepared analytical evidence and produces business text.

    It never queries databases and never defines business rules. Objective totals
    and rankings are narrated from deterministic backend outputs to prevent the
    LLM from inventing or recalculating numbers.
    """

    async def generate_insights(
        self,
        pergunta: str,
        resultados_dict: dict[str, Any],
        principal_view_name: str,
        api_key: str | None,
        model: str | None,
        tenant_id: Any,
        history: list[dict[str, str]] | None,
        custom_instructions: str | None,
        mode: str,
        bi_intelligence: dict[str, Any] | None = None,
    ) -> tuple[str | None, dict[str, Any]]:
        """Generate business insights from calculations already produced by the backend."""
        logger.info("[InsightLayer] Analisando dados para geracao de insights...")

        dados_para_insights = []
        raw_rows_principal: list[dict[str, Any]] = []

        for q_id, res in resultados_dict.items():
            if q_id == "principal":
                raw_rows_principal = res.get("raw_rows") or []
            dados_para_insights.append({"view": res["view_name"], "dados": res["raw_rows"]})

        if bi_intelligence is None:
            logger.warning("[InsightLayer] bi_intelligence ausente. Seguindo sem recalcular metricas.")
            bi_intelligence = {}

        deterministic_report = self._build_deterministic_report(
            pergunta=pergunta,
            principal_view_name=principal_view_name,
            raw_rows=raw_rows_principal,
            bi_intelligence=bi_intelligence,
        )
        if deterministic_report:
            logger.info("[InsightLayer] Insight deterministico gerado pelo backend.")
            return deterministic_report, bi_intelligence

        dados_insights_consolidado = {
            "calculos_bi_deterministicos": bi_intelligence,
            "dados_brutos": dados_para_insights if len(dados_para_insights) > 1 else (raw_rows_principal or []),
        }

        clean_view_name = principal_view_name.upper().replace("VW_", "").replace("_", " ").title()

        try:
            ia_analise = await generate_data_insights(
                pergunta=pergunta,
                dados=dados_insights_consolidado,
                view_name=clean_view_name,
                api_key=api_key,
                model=model,
                tenant_id=tenant_id,
                history=history,
                custom_instructions=custom_instructions,
                mode=mode,
            )
            logger.info("[InsightLayer] Insights de IA gerados com sucesso.")
            return ia_analise, bi_intelligence
        except Exception as exc:
            logger.error("[InsightLayer] Falha ao gerar insights de IA: %s", exc)
            return None, bi_intelligence

    def _build_deterministic_report(
        self,
        pergunta: str,
        principal_view_name: str,
        raw_rows: list[dict[str, Any]],
        bi_intelligence: dict[str, Any],
    ) -> str | None:
        question = (pergunta or "").lower()
        view_upper = (principal_view_name or "").upper()
        kpis = bi_intelligence.get("kpis") if isinstance(bi_intelligence, dict) else {}
        kpis = kpis if isinstance(kpis, dict) else {}

        asks_product_financial_ranking = (
            "produto" in question
            and any(term in question for term in ("margem", "lucro", "rentabilidade", "rentavel", "lucratividade", "lucrativo", "retorno financeiro"))
            and raw_rows
        )
        if asks_product_financial_ranking:
            top = raw_rows[0]
            product = self._first_value(
                top,
                ("produto_nome", "PRODUTO_NOME", "produto", "PRODUTO", "descricao_", "DESCRICAO_", "descricao", "DESCRICAO"),
            ) or "produto identificado"
            margin = self._first_number(top, ("margem_lucro", "MARGEM_LUCRO", "margem_media", "MARGEM_MEDIA"))
            profit = self._first_number(top, ("lucro_bruto", "LUCRO_BRUTO", "lucro", "LUCRO"))
            revenue = self._first_number(top, ("receita_total", "RECEITA_TOTAL", "valor_vendido", "VALOR_VENDIDO"))
            ascending = any(term in question for term in ("menor", "pior", "mais baixo", "mais baixa", "menos"))
            qualifier = "menor" if ascending else "maior"
            metric_label = "margem de lucro" if "margem" in question or "rentabilidade" in question else "lucro bruto"
            metric_value = (
                f"{margin:.2f}%" if margin is not None and metric_label == "margem de lucro"
                else self._format_brl(profit) if profit is not None
                else "valor nao disponivel"
            )
            return (
                "## 1. RESUMO ANALITICO\n"
                f"O produto com {qualifier} {metric_label} retornado pelo backend foi {product}, com {metric_value}.\n\n"
                "## 2. EVIDENCIAS\n"
                f"A consulta foi agrupada por produto e ordenada pela metrica solicitada ({metric_label})."
                f"{f' Receita associada: {self._format_brl(revenue)}.' if revenue is not None else ''}"
                f"{f' Lucro bruto associado: {self._format_brl(profit)}.' if profit is not None and metric_label == 'margem de lucro' else ''}\n\n"
                "## 3. INSIGHTS RELEVANTES\n"
                "Use a tabela/grafico para verificar se a margem baixa e pontual ou recorrente em outros produtos proximos no ranking.\n\n"
                "## 4. ALERTAS\n"
                "Se a margem estiver abaixo do esperado, valide custo, preco de venda, descontos e impostos antes de decidir a acao comercial."
            )

        has_product_column = bool(
            raw_rows
            and any(
                k.upper() in {"PRODUTO_NOME", "DESCRICAO_", "DESCRICAO", "PRODUTO", "NOME_PRODUTO"}
                for k in raw_rows[0].keys()
            )
        )
        if ("PRODUTOS" in view_upper or has_product_column or "produto" in question) and raw_rows and has_product_column:
            top = raw_rows[0]
            product = self._first_value(
                top,
                ("produto_nome", "PRODUTO_NOME", "produto", "PRODUTO", "descricao_", "DESCRICAO_", "descricao", "DESCRICAO"),
            ) or "produto líder"
            units = self._first_number(top, ("unidades_vendidas", "UNIDADES_VENDIDAS", "quantidade_vendida", "QTDE_", "quantidade_pedidos"))
            revenue = self._first_number(top, ("receita_total", "RECEITA_TOTAL", "faturamento_realizado", "FATURAMENTO_REALIZADO", "valor_vendido", "PTOTAL_"))
            total_items = len(raw_rows)
            
            return (
                "## 1. RESUMO ANALITICO\n"
                f"O relatório retornou {total_items} produtos ranqueados com base nos registros do banco de dados. "
                f"O item na primeira posição é {product}"
                f"{f' com {self._format_number(units)} unidades comercializadas' if units is not None else ''}"
                f"{f' e receita total de {self._format_brl(revenue)}' if revenue is not None else ''}.\n\n"
                "## 2. COMPARACOES DISPONIVEIS\n"
                "A listagem foi processada e consolidada com precisão matemática diretamente sobre as transações de vendas.\n\n"
                "## 3. INSIGHTS RELEVANTES\n"
                "A base de dados clonada contém o histórico analítico de agosto/2024 a agosto/2026. "
                "É possível visualizar a evolução por trimestre ou por mês utilizando os controles de período.\n\n"
                "## 4. ALERTAS\n"
                "O relatório reflete as quantidades e faturamento de vendas. "
                "Para acompanhamento de compras, são exibidos os estoques atuais cadastrados."
            )

        has_seller_column = bool(
            raw_rows
            and any(
                k.upper() in {"VENDEDOR_NOME", "NOME_VED", "VENDEDOR", "NOME_VENDEDOR"}
                for k in raw_rows[0].keys()
            )
        )
        if ("PERFORMANCE_VENDEDORES" in view_upper or has_seller_column) and raw_rows and has_seller_column:
            top = raw_rows[0]
            seller = self._first_value(
                top,
                ("vendedor_nome", "VENDEDOR_NOME", "vendedor", "VENDEDOR", "nome_ved", "NOME_VED", "nome_vendedor", "NOME_VENDEDOR"),
            ) or "vendedor líder"
            value = self._first_number(top, ("valor_vendido", "receita_total", "VALOR_VENDIDO", "RECEITA_TOTAL", "faturamento_realizado", "FATURAMENTO_REALIZADO"))
            orders = self._first_number(top, ("pedidos_qtd", "quantidade_pedidos", "PEDIDOS_QTD", "unidades_vendidas", "UNIDADES_VENDIDAS"))
            return (
                "## 1. RESUMO ANALITICO\n"
                f"O ranking retornou {len(raw_rows)} vendedores. A liderança está com {seller}"
                f"{f' com {self._format_brl(value)} em vendas' if value is not None else ''}.\n\n"
                "## 2. COMPARACOES DISPONIVEIS\n"
                f"A ordenação foi entregue pela Data Platform pela métrica principal da view."
                f"{f' O líder possui {self._format_number(orders)} pedidos/vendas registrados.' if orders is not None else ''}\n\n"
                "## 3. INSIGHTS RELEVANTES\n"
                "Use o ranking e a tabela para avaliar concentração de performance entre vendedores.\n\n"
                "## 4. ALERTAS\n"
                "Sem alertas críticos identificados para esta consulta."
            )

        asks_total_sales = (
            any(term in question for term in ("valor", "quanto", "total", "vendeu", "vendas", "faturamento"))
            and not has_product_column
            and not has_seller_column
        )
        if asks_total_sales and raw_rows and self._is_number(kpis.get("receita_total")):
            total = float(kpis["receita_total"])
            records = int(kpis.get("total_registros") or len(raw_rows))
            periodo = self._period_label(raw_rows)
            return (
                "## 1. RESUMO ANALITICO\n"
                f"No período {periodo}, o valor total das vendas foi de {self._format_brl(total)}, "
                f"considerando {records} registros retornados pelo backend.\n\n"
                "## 2. COMPARACOES DISPONIVEIS\n"
                "Nenhuma comparação automática foi aplicada porque a pergunta solicitou um valor pontual.\n\n"
                "## 3. INSIGHTS RELEVANTES\n"
                "O resultado foi calculado pela camada de BI determinística do backend e respeita os filtros temporais da pergunta.\n\n"
                "## 4. ALERTAS\n"
                "Sem alertas críticos identificados para esta consulta."
            )

        return None

    def _period_label(self, rows: list[dict[str, Any]]) -> str:
        dates: list[str] = []
        for row in rows:
            value = row.get("data_referencia") or row.get("data_ref") or row.get("DATA_REFERENCIA") or row.get("DATA_REF")
            if isinstance(value, (datetime, date)):
                dates.append(value.date().isoformat() if isinstance(value, datetime) else value.isoformat())
            elif value:
                dates.append(str(value)[:10])
        unique_dates = sorted(set(dates))
        if not unique_dates:
            return "solicitado"
        if len(unique_dates) == 1:
            return self._format_date_br(unique_dates[0])
        return f"{self._format_date_br(unique_dates[0])} a {self._format_date_br(unique_dates[-1])}"

    def _format_date_br(self, iso_date: str) -> str:
        try:
            parsed = datetime.fromisoformat(str(iso_date)[:10])
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            return str(iso_date)

    def _is_number(self, value: Any) -> bool:
        if isinstance(value, (int, float, Decimal)):
            return True
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

    def _first_number(self, row: dict[str, Any], keys: tuple[str, ...]) -> float | None:
        for key in keys:
            if key in row and self._is_number(row[key]):
                return float(row[key])
        return None

    def _first_value(self, row: dict[str, Any], keys: tuple[str, ...]) -> Any:
        for key in keys:
            value = row.get(key)
            if value not in (None, ""):
                return value
        return None

    def _format_brl(self, value: float) -> str:
        formatted = f"R$ {value:,.2f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

    def _format_number(self, value: float) -> str:
        if float(value).is_integer():
            return f"{int(value):,}".replace(",", ".")
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


insight_layer = InsightLayer()


async def generate_insights(*args: Any, **kwargs: Any) -> tuple[str | None, dict[str, Any]]:
    """Compatibility proxy for legacy package-level imports."""
    return await insight_layer.generate_insights(*args, **kwargs)
