from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from contracts.safe_analytical_postgresql_v2.catalog import (
    AnalyticalCatalogSnapshotV2,
    AnalyticalCatalogV2,
    AnalyticalColumnDefinitionV2,
    AnalyticalDatasetDefinitionV2,
    AnalyticalDimensionBindingV2,
    AnalyticalMetricBindingV2,
    AnalyticalRelationDefinitionV2,
)
from contracts.safe_analytical_postgresql_v2.identity import (
    SAFE_ANALYTICAL_POSTGRESQL_VERSION,
    AnalyticalCatalogLifecycleV2,
    AnalyticalColumnTypeV2,
    AnalyticalDataClassificationV2,
    AnalyticalTenantStrategyV2,
)
from services.safe_analytical_postgresql.exceptions import AnalyticalCatalogError


def _calc_hash(data: Any) -> str:
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class AnalyticalCatalogService:
    """
    Manages Analytical Catalog definitions, snapshots, datasets, relations, and metric bindings.
    """

    def __init__(self):
        self._seed_snapshot: Optional[AnalyticalCatalogSnapshotV2] = None

    def get_default_catalog_snapshot(self) -> AnalyticalCatalogSnapshotV2:
        if self._seed_snapshot is not None:
            return self._seed_snapshot

        # Define columns for vw_vendas_lm
        cols = {
            "venda_id": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.venda_id",
                physical_name="venda_id",
                logical_type=AnalyticalColumnTypeV2.IDENTIFIER,
                nullable=False,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                checksum=_calc_hash("venda_id"),
            ),
            "data_venda": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.data_venda",
                physical_name="data_venda",
                logical_type=AnalyticalColumnTypeV2.DATE,
                nullable=False,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                canonical_dimension_ref="date",
                checksum=_calc_hash("data_venda"),
            ),
            "filial_id": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.filial_id",
                physical_name="filial_id",
                logical_type=AnalyticalColumnTypeV2.IDENTIFIER,
                nullable=False,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                checksum=_calc_hash("filial_id"),
            ),
            "filial_nome": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.filial_nome",
                physical_name="filial_nome",
                logical_type=AnalyticalColumnTypeV2.STRING,
                nullable=False,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                canonical_dimension_ref="branch",
                checksum=_calc_hash("filial_nome"),
            ),
            "cliente_id": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.cliente_id",
                physical_name="cliente_id",
                logical_type=AnalyticalColumnTypeV2.IDENTIFIER,
                nullable=True,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                checksum=_calc_hash("cliente_id"),
            ),
            "cliente_nome": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.cliente_nome",
                physical_name="cliente_nome",
                logical_type=AnalyticalColumnTypeV2.STRING,
                nullable=True,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                canonical_dimension_ref="customer",
                checksum=_calc_hash("cliente_nome"),
            ),
            "produto_id": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.produto_id",
                physical_name="produto_id",
                logical_type=AnalyticalColumnTypeV2.IDENTIFIER,
                nullable=False,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                checksum=_calc_hash("produto_id"),
            ),
            "produto_nome": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.produto_nome",
                physical_name="produto_nome",
                logical_type=AnalyticalColumnTypeV2.STRING,
                nullable=False,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                canonical_dimension_ref="product",
                checksum=_calc_hash("produto_nome"),
            ),
            "categoria_nome": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.categoria_nome",
                physical_name="categoria_nome",
                logical_type=AnalyticalColumnTypeV2.STRING,
                nullable=True,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                canonical_dimension_ref="category",
                checksum=_calc_hash("categoria_nome"),
            ),
            "quantidade": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.quantidade",
                physical_name="quantidade",
                logical_type=AnalyticalColumnTypeV2.QUANTITY,
                nullable=False,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                checksum=_calc_hash("quantidade"),
            ),
            "valor_unitario": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.valor_unitario",
                physical_name="valor_unitario",
                logical_type=AnalyticalColumnTypeV2.CURRENCY,
                nullable=False,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                checksum=_calc_hash("valor_unitario"),
            ),
            "valor_total": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.valor_total",
                physical_name="valor_total",
                logical_type=AnalyticalColumnTypeV2.CURRENCY,
                nullable=False,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                checksum=_calc_hash("valor_total"),
            ),
            "lucro_bruto": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.lucro_bruto",
                physical_name="lucro_bruto",
                logical_type=AnalyticalColumnTypeV2.CURRENCY,
                nullable=False,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                checksum=_calc_hash("lucro_bruto"),
            ),
            "desconto": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.desconto",
                physical_name="desconto",
                logical_type=AnalyticalColumnTypeV2.CURRENCY,
                nullable=True,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                checksum=_calc_hash("desconto"),
            ),
            "canal_venda": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.canal_venda",
                physical_name="canal_venda",
                logical_type=AnalyticalColumnTypeV2.STRING,
                nullable=True,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                canonical_dimension_ref="channel",
                checksum=_calc_hash("canal_venda"),
            ),
            "uf": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.uf",
                physical_name="uf",
                logical_type=AnalyticalColumnTypeV2.STRING,
                nullable=True,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                canonical_dimension_ref="state",
                checksum=_calc_hash("uf"),
            ),
            "cidade": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.cidade",
                physical_name="cidade",
                logical_type=AnalyticalColumnTypeV2.STRING,
                nullable=True,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                canonical_dimension_ref="city",
                checksum=_calc_hash("cidade"),
            ),
            "status_venda": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.status_venda",
                physical_name="status_venda",
                logical_type=AnalyticalColumnTypeV2.STRING,
                nullable=True,
                classification=AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA,
                canonical_dimension_ref="status",
                checksum=_calc_hash("status_venda"),
            ),
            "tenant_id": AnalyticalColumnDefinitionV2(
                canonical_column_id="sales.tenant_id",
                physical_name="tenant_id",
                logical_type=AnalyticalColumnTypeV2.IDENTIFIER,
                nullable=False,
                classification=AnalyticalDataClassificationV2.TENANT_METADATA,
                checksum=_calc_hash("tenant_id"),
            ),
        }

        relation = AnalyticalRelationDefinitionV2(
            canonical_relation_id="sales.vw_vendas_lm",
            physical_name="vw_vendas_lm",
            relation_type="VIEW",
            primary_key_column="venda_id",
            tenant_column="tenant_id",
            columns=cols,
            checksum=_calc_hash({"name": "vw_vendas_lm", "cols": list(cols.keys())}),
        )

        metrics = {
            "total_sales": AnalyticalMetricBindingV2(
                canonical_metric_id="total_sales",
                relation_id="sales.vw_vendas_lm",
                formula_expression="SUM(valor_total)",
                unit="BRL",
                aggregation="SUM",
                formula_fingerprint=_calc_hash("SUM(valor_total)"),
                checksum=_calc_hash("total_sales"),
            ),
            "gross_profit": AnalyticalMetricBindingV2(
                canonical_metric_id="gross_profit",
                relation_id="sales.vw_vendas_lm",
                formula_expression="SUM(lucro_bruto)",
                unit="BRL",
                aggregation="SUM",
                formula_fingerprint=_calc_hash("SUM(lucro_bruto)"),
                checksum=_calc_hash("gross_profit"),
            ),
            "total_quantity": AnalyticalMetricBindingV2(
                canonical_metric_id="total_quantity",
                relation_id="sales.vw_vendas_lm",
                formula_expression="SUM(quantidade)",
                unit="UN",
                aggregation="SUM",
                formula_fingerprint=_calc_hash("SUM(quantidade)"),
                checksum=_calc_hash("total_quantity"),
            ),
            "order_count": AnalyticalMetricBindingV2(
                canonical_metric_id="order_count",
                relation_id="sales.vw_vendas_lm",
                formula_expression="COUNT(DISTINCT venda_id)",
                unit="ORDER",
                aggregation="COUNT_DISTINCT",
                formula_fingerprint=_calc_hash("COUNT(DISTINCT venda_id)"),
                checksum=_calc_hash("order_count"),
            ),
            "average_ticket": AnalyticalMetricBindingV2(
                canonical_metric_id="average_ticket",
                relation_id="sales.vw_vendas_lm",
                formula_expression="AVG(valor_total)",
                unit="BRL",
                aggregation="AVG",
                formula_fingerprint=_calc_hash("AVG(valor_total)"),
                checksum=_calc_hash("average_ticket"),
            ),
        }

        dimensions = {
            "date": AnalyticalDimensionBindingV2(
                canonical_dimension_id="date",
                relation_id="sales.vw_vendas_lm",
                column_name="data_venda",
                dimension_type=AnalyticalColumnTypeV2.DATE,
                checksum=_calc_hash("date"),
            ),
            "branch": AnalyticalDimensionBindingV2(
                canonical_dimension_id="branch",
                relation_id="sales.vw_vendas_lm",
                column_name="filial_nome",
                dimension_type=AnalyticalColumnTypeV2.STRING,
                checksum=_calc_hash("branch"),
            ),
            "product": AnalyticalDimensionBindingV2(
                canonical_dimension_id="product",
                relation_id="sales.vw_vendas_lm",
                column_name="produto_nome",
                dimension_type=AnalyticalColumnTypeV2.STRING,
                checksum=_calc_hash("product"),
            ),
            "category": AnalyticalDimensionBindingV2(
                canonical_dimension_id="category",
                relation_id="sales.vw_vendas_lm",
                column_name="categoria_nome",
                dimension_type=AnalyticalColumnTypeV2.STRING,
                checksum=_calc_hash("category"),
            ),
            "customer": AnalyticalDimensionBindingV2(
                canonical_dimension_id="customer",
                relation_id="sales.vw_vendas_lm",
                column_name="cliente_nome",
                dimension_type=AnalyticalColumnTypeV2.STRING,
                checksum=_calc_hash("customer"),
            ),
            "channel": AnalyticalDimensionBindingV2(
                canonical_dimension_id="channel",
                relation_id="sales.vw_vendas_lm",
                column_name="canal_venda",
                dimension_type=AnalyticalColumnTypeV2.STRING,
                checksum=_calc_hash("channel"),
            ),
            "state": AnalyticalDimensionBindingV2(
                canonical_dimension_id="state",
                relation_id="sales.vw_vendas_lm",
                column_name="uf",
                dimension_type=AnalyticalColumnTypeV2.STRING,
                checksum=_calc_hash("state"),
            ),
            "city": AnalyticalDimensionBindingV2(
                canonical_dimension_id="city",
                relation_id="sales.vw_vendas_lm",
                column_name="cidade",
                dimension_type=AnalyticalColumnTypeV2.STRING,
                checksum=_calc_hash("city"),
            ),
        }

        dataset = AnalyticalDatasetDefinitionV2(
            canonical_dataset_id="sales_analytics",
            domain="sales",
            tenant_strategy=AnalyticalTenantStrategyV2.TENANT_COLUMN_REQUIRED,
            relations={"vw_vendas_lm": relation},
            metric_bindings=metrics,
            dimension_bindings=dimensions,
            version="1.0.0",
            checksum=_calc_hash("sales_analytics"),
        )

        snapshot = AnalyticalCatalogSnapshotV2(
            snapshot_id="snap_default_v1",
            contract_version=SAFE_ANALYTICAL_POSTGRESQL_VERSION,
            catalog_version="1.0.0",
            lifecycle=AnalyticalCatalogLifecycleV2.PUBLISHED,
            datasets={"sales_analytics": dataset},
            published_at=datetime.now(timezone.utc),
            published_by="system",
            checksum=_calc_hash("snap_default_v1"),
        )

        self._seed_snapshot = snapshot
        return snapshot

    def get_dataset(self, snapshot: AnalyticalCatalogSnapshotV2, dataset_id: str) -> AnalyticalDatasetDefinitionV2:
        if dataset_id not in snapshot.datasets:
            # Fallback if alias matches
            for ds in snapshot.datasets.values():
                if ds.canonical_dataset_id == dataset_id or ds.domain == dataset_id:
                    return ds
            raise AnalyticalCatalogError(f"Dataset '{dataset_id}' not found in catalog snapshot.")
        return snapshot.datasets[dataset_id]
