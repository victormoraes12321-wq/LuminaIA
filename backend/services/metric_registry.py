from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    label: str
    source: str
    formula: str
    default_filters: tuple[str, ...]
    grain: str
    confidence: str
    supported: bool = True
    notes: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["default_filters"] = list(self.default_filters)
        payload["notes"] = list(self.notes)
        return payload


METRIC_DEFINITIONS: dict[str, MetricDefinition] = {
    "faturamento_comercial": MetricDefinition(
        key="faturamento_comercial",
        label="Faturamento comercial/liquido",
        source="VW_VENDAS_LM",
        formula="SUM(ptotal_) WHERE tp_ IN (2, 61)",
        default_filters=(
            "dtemissao_ dentro do periodo solicitado",
            "filial_ quando o usuario informar filial",
            "tipos comerciais 2 e 61",
        ),
        grain="Periodo, filial e movimento de venda",
        confidence="alta",
        notes=(
            "E a metrica padrao de faturamento para bater com o relatorio comercial do ERP.",
            "Nao soma RB, bonificacao, transferencia, remessa ou outros movimentos.",
        ),
    ),
    "total_bruto": MetricDefinition(
        key="total_bruto",
        label="Total bruto sem transferencias",
        source="VW_VENDAS_LM",
        formula=(
            "SUM(ptotal_) das categorias classificadas, excluindo transferencias: comercial, RB, "
            "devolucao, bonificacao, outras vendas, remessa/uso e demais movimentos"
        ),
        default_filters=("dtemissao_ dentro do periodo solicitado", "filial_ quando informada"),
        grain="Periodo, filial e movimento de venda",
        confidence="media",
        notes=("Transferencias ficam em coluna propria e nunca entram em faturamento ou lucro total.",),
    ),
    "total_movimentos_view": MetricDefinition(
        key="total_movimentos_view",
        label="Total geral de movimentos",
        source="VW_VENDAS_LM",
        formula="SUM(ptotal_) de todas as categorias classificadas, incluindo transferencias",
        default_filters=("dtemissao_ dentro do periodo solicitado", "filial_ quando informada"),
        grain="Periodo, filial e movimento de venda",
        confidence="media",
        notes=("Usado apenas para auditoria operacional; nao e faturamento/lucro total.",),
    ),
    "saida_rb": MetricDefinition(
        key="saida_rb",
        label="Saida RB",
        source="VW_VENDAS_LM",
        formula="SUM(ptotal_) WHERE tp_ = 9 OR tpdescricao_ contem SAIDA RB",
        default_filters=("dtemissao_ dentro do periodo solicitado", "filial_ quando informada"),
        grain="Periodo, filial, vendedor/cliente quando solicitado",
        confidence="alta",
        notes=("Fica separado de devolucao, faturamento comercial e transferencias.",),
    ),
    "devolucao": MetricDefinition(
        key="devolucao",
        label="Devolucao",
        source="VW_VENDAS_LM",
        formula="SUM(ptotal_) WHERE tpdescricao_ contem DEVOL",
        default_filters=("dtemissao_ dentro do periodo solicitado", "filial_ quando informada"),
        grain="Periodo, filial, vendedor/cliente quando solicitado",
        confidence="media",
        notes=("Na auditoria de 06/2026 e 07/2026 a view atual nao trouxe linhas com DEVOL.",),
    ),
    "venda_bonificada": MetricDefinition(
        key="venda_bonificada",
        label="Venda bonificada",
        source="VW_VENDAS_LM",
        formula="SUM(ptotal_) WHERE tp_ = 22 OR tpdescricao_ contem BONIFIC",
        default_filters=("dtemissao_ dentro do periodo solicitado", "filial_ quando informada"),
        grain="Periodo, filial e movimento",
        confidence="alta",
    ),
    "transferencias": MetricDefinition(
        key="transferencias",
        label="Transferencias",
        source="VW_VENDAS_LM",
        formula="SUM(ptotal_) WHERE tp_ IN (3, 31, 96) OR tpdescricao_ contem TRANSFERENCIA",
        default_filters=("dtemissao_ dentro do periodo solicitado", "filial_ quando informada"),
        grain="Periodo, filial e movimento",
        confidence="media",
    ),
    "desconto_total": MetricDefinition(
        key="desconto_total",
        label="Total de desconto",
        source="VW_VENDAS_LM",
        formula="Coluna explicita de desconto quando existir; senao GREATEST(qtde_ * p_unit_ - ptotal_, 0)",
        default_filters=("dtemissao_ dentro do periodo solicitado", "faturamento comercial para desconto comercial"),
        grain="Periodo, filial e movimento",
        confidence="baixa",
        notes=(
            "A confianca sobe para alta automaticamente quando a view possuir coluna explicita de desconto.",
            "Sem coluna explicita, o valor derivado nao prova ausencia de desconto no ERP.",
        ),
    ),
    "desconto_medio": MetricDefinition(
        key="desconto_medio",
        label="Desconto medio",
        source="VW_VENDAS_LM",
        formula="desconto_total / COUNT(DISTINCT pedido_)",
        default_filters=("Mesmo filtro do desconto total",),
        grain="Periodo e filial",
        confidence="baixa",
        notes=("Depende da mesma fonte de desconto total.",),
    ),
    "ticket_medio": MetricDefinition(
        key="ticket_medio",
        label="Ticket medio",
        source="VW_VENDAS_LM",
        formula="faturamento_comercial / COUNT(DISTINCT pedido_) dos tipos 2 e 61",
        default_filters=("dtemissao_ dentro do periodo solicitado", "filial_ quando informada"),
        grain="Periodo e filial",
        confidence="alta",
    ),
    "ranking_vendedores": MetricDefinition(
        key="ranking_vendedores",
        label="Ranking de vendedores",
        source="VW_VENDAS_LM + VW_VENDEDOR_CAD_LM",
        formula="Agrupa a metrica solicitada por vendedor e abre colunas por filial",
        default_filters=("Exclui cadastro tecnico PADRAO apenas no ranking de vendedores",),
        grain="Vendedor por periodo/filial",
        confidence="alta",
    ),
    "ranking_clientes": MetricDefinition(
        key="ranking_clientes",
        label="Ranking de clientes",
        source="VW_VENDAS_LM + VW_CLIENTES_CAD_LM",
        formula="Agrupa a metrica solicitada por cliente e abre colunas por filial",
        default_filters=("Exclui cliente interno LAGES E LOPES LTDA apenas no ranking de clientes",),
        grain="Cliente por periodo/filial",
        confidence="alta",
    ),
    "lucro": MetricDefinition(
        key="lucro",
        label="Lucro bruto/liquido",
        source="Nao disponivel na VW_VENDAS_LM",
        formula="Necessita custo, impostos, despesas e/ou margem em fonte propria",
        default_filters=(),
        grain="Nao aplicavel",
        confidence="indisponivel",
        supported=False,
        notes=("O sistema nao deve inventar lucro sem uma view/coluna contabil validada.",),
    ),
    "vendas_nao_faturadas": MetricDefinition(
        key="vendas_nao_faturadas",
        label="Vendas ainda nao faturadas",
        source="Nao disponivel na VW_VENDAS_LM",
        formula="Necessita status de pedido pendente/nao faturado em fonte propria",
        default_filters=(),
        grain="Nao aplicavel",
        confidence="indisponivel",
        supported=False,
        notes=("A view atual contem vendas emitidas/faturadas, nao carteira pendente.",),
    ),
}


def _financial_runtime_source(
    key: str,
    financial_source_discovery: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not financial_source_discovery:
        return None
    if key == "lucro":
        return {
            "active_mapping": False,
            "lucro_bruto": financial_source_discovery.get("profit", {}).get("lucro_bruto"),
            "lucro_liquido": financial_source_discovery.get("profit", {}).get("lucro_liquido"),
            "candidates": financial_source_discovery.get("profit", {}).get("candidates", [])[:5],
        }
    if key == "vendas_nao_faturadas":
        return {
            "active_mapping": False,
            "vendas_nao_faturadas": financial_source_discovery.get("unbilled_sales", {}).get("vendas_nao_faturadas"),
            "candidates": financial_source_discovery.get("unbilled_sales", {}).get("candidates", [])[:5],
        }
    return None


def _definition(
    key: str,
    *,
    discount_source: dict[str, Any] | None = None,
    financial_source_discovery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    definition = METRIC_DEFINITIONS[key].to_payload()
    if key in {"desconto_total", "desconto_medio"} and discount_source:
        source_type = str(discount_source.get("desconto_fonte_tipo") or "derivado_sem_coluna_explicita")
        definition["confidence"] = "alta" if source_type == "coluna_explicita" else "baixa"
        definition["runtime_source"] = {
            "type": source_type,
            "column": discount_source.get("desconto_fonte_coluna"),
            "confidence": discount_source.get("desconto_fonte_confianca") or definition["confidence"],
            "observation": discount_source.get("desconto_fonte_observacao"),
        }
    if key in {"lucro", "vendas_nao_faturadas"}:
        runtime_source = _financial_runtime_source(key, financial_source_discovery)
        if runtime_source:
            definition["runtime_source"] = runtime_source
    return definition


def _add(keys: list[str], *values: str) -> None:
    for value in values:
        if value in METRIC_DEFINITIONS and value not in keys:
            keys.append(value)


def core_sales_metric_audit(
    *,
    topics: Iterable[str],
    value_basis: str,
    ranking_kind: str | None,
    primary_metric: str,
    period_label: str,
    filial: str | None,
    discount_source: dict[str, Any] | None = None,
    financial_source_discovery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    topic_set = set(topics)
    keys: list[str] = []

    if "faturamento" in topic_set:
        if value_basis == "ambos":
            _add(keys, "faturamento_comercial", "total_bruto")
        elif value_basis == "bruto":
            _add(keys, "total_bruto")
        else:
            _add(keys, "faturamento_comercial")

    if "rb" in topic_set or "ranking_vendedores_rb" in topic_set or "top_vendedor_rb" in topic_set:
        _add(keys, "saida_rb")
    if "devolucao" in topic_set or "ranking_vendedores_devolucao" in topic_set or "top_vendedor_devolucao" in topic_set:
        _add(keys, "devolucao")
    if "ticket" in topic_set:
        _add(keys, "ticket_medio")
    if any("desconto" in topic for topic in topic_set):
        _add(keys, "desconto_total", "desconto_medio")
    if "lucro" in topic_set:
        _add(keys, "lucro")
    if "vendas_nao_faturadas" in topic_set:
        _add(keys, "vendas_nao_faturadas")
    if ranking_kind and "vendedores" in ranking_kind:
        _add(keys, "ranking_vendedores", primary_metric)
    if ranking_kind == "clientes":
        _add(keys, "ranking_clientes", primary_metric)
    if not keys and primary_metric:
        _add(keys, primary_metric)

    definitions = [
        _definition(
            key,
            discount_source=discount_source,
            financial_source_discovery=financial_source_discovery,
        )
        for key in keys
    ]
    unsupported = [item for item in definitions if not item.get("supported", True)]

    return {
        "registry_version": "2026-07-20-rb-devolucao-transferencias",
        "period": period_label,
        "filial": filial or "todas",
        "value_basis": value_basis,
        "ranking_kind": ranking_kind,
        "primary_metric": primary_metric,
        "metric_definitions": definitions,
        "unsupported_metrics": unsupported,
        "calculation_steps": [
            {
                "step": 1,
                "name": "Periodo",
                "detail": f"Filtra dtemissao_ no intervalo {period_label}.",
            },
            {
                "step": 2,
                "name": "Escopo de filial",
                "detail": f"Aplica filial {filial}." if filial else "Mantem todas as filiais e mostra abertura por filial quando aplicavel.",
            },
            {
                "step": 3,
                "name": "Classificacao de movimento",
                "detail": "Classifica cada linha em comercial, RB, devolucao, bonificacao, transferencias, remessa ou outros movimentos.",
            },
            {
                "step": 4,
                "name": "Agregacao",
                "detail": "Soma valores e conta pedidos distintos conforme a metrica solicitada.",
            },
        ],
    }
