from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from contracts.safe_analytical_postgresql_v2.identity import (
    SAFE_ANALYTICAL_POSTGRESQL_VERSION,
    AnalyticalCatalogLifecycleV2,
    AnalyticalColumnTypeV2,
    AnalyticalDataClassificationV2,
    AnalyticalJoinTypeV2,
    AnalyticalTenantStrategyV2,
)


class StrictAnalyticalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AnalyticalColumnDefinitionV2(StrictAnalyticalModel):
    canonical_column_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    physical_name: str = Field(pattern=r"^[a-zA-Z0-9_]+$")
    logical_type: AnalyticalColumnTypeV2
    nullable: bool = True
    classification: AnalyticalDataClassificationV2 = AnalyticalDataClassificationV2.TENANT_BUSINESS_DATA
    filterable: bool = True
    groupable: bool = True
    sortable: bool = True
    exposable: bool = True
    canonical_dimension_ref: Optional[str] = None
    checksum: str = Field(min_length=16, max_length=64)


class AnalyticalRelationDefinitionV2(StrictAnalyticalModel):
    canonical_relation_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    physical_name: str = Field(pattern=r"^[a-zA-Z0-9_]+$")
    relation_type: str = Field(default="VIEW", pattern=r"^(TABLE|VIEW|MATERIALIZED_VIEW)$")
    primary_key_column: Optional[str] = None
    tenant_column: Optional[str] = None
    columns: Dict[str, AnalyticalColumnDefinitionV2]
    checksum: str = Field(min_length=16, max_length=64)


class AnalyticalJoinDefinitionV2(StrictAnalyticalModel):
    join_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    left_relation_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    right_relation_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    join_type: AnalyticalJoinTypeV2 = AnalyticalJoinTypeV2.INNER
    left_column: str = Field(pattern=r"^[a-zA-Z0-9_]+$")
    right_column: str = Field(pattern=r"^[a-zA-Z0-9_]+$")
    cardinality: str = Field(default="MANY_TO_ONE", pattern=r"^(ONE_TO_ONE|MANY_TO_ONE|ONE_TO_MANY)$")
    checksum: str = Field(min_length=16, max_length=64)


class AnalyticalMetricBindingV2(StrictAnalyticalModel):
    canonical_metric_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    relation_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    formula_expression: str = Field(min_length=1, max_length=512)
    unit: str = "BRL"
    aggregation: str = Field(default="SUM", pattern=r"^(SUM|AVG|COUNT|COUNT_DISTINCT|MIN|MAX)$")
    formula_fingerprint: str = Field(min_length=16, max_length=64)
    checksum: str = Field(min_length=16, max_length=64)


class AnalyticalDimensionBindingV2(StrictAnalyticalModel):
    canonical_dimension_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    relation_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    column_name: str = Field(pattern=r"^[a-zA-Z0-9_]+$")
    dimension_type: AnalyticalColumnTypeV2
    checksum: str = Field(min_length=16, max_length=64)


class AnalyticalDatasetDefinitionV2(StrictAnalyticalModel):
    canonical_dataset_id: str = Field(pattern=r"^[a-z0-9_.]+$")
    domain: str = "sales"
    tenant_strategy: AnalyticalTenantStrategyV2
    relations: Dict[str, AnalyticalRelationDefinitionV2]
    joins: List[AnalyticalJoinDefinitionV2] = Field(default_factory=list)
    metric_bindings: Dict[str, AnalyticalMetricBindingV2] = Field(default_factory=dict)
    dimension_bindings: Dict[str, AnalyticalDimensionBindingV2] = Field(default_factory=dict)
    version: str = "1.0.0"
    checksum: str = Field(min_length=16, max_length=64)


class AnalyticalCatalogSnapshotV2(StrictAnalyticalModel):
    snapshot_id: str = Field(min_length=1, max_length=128)
    contract_version: str = SAFE_ANALYTICAL_POSTGRESQL_VERSION
    catalog_version: str = "1.0.0"
    lifecycle: AnalyticalCatalogLifecycleV2 = AnalyticalCatalogLifecycleV2.PUBLISHED
    datasets: Dict[str, AnalyticalDatasetDefinitionV2]
    published_at: datetime
    published_by: str
    checksum: str = Field(min_length=16, max_length=64)


class AnalyticalCatalogV2(StrictAnalyticalModel):
    catalog_id: str = Field(min_length=1, max_length=128)
    snapshot: AnalyticalCatalogSnapshotV2
    is_active: bool = True
