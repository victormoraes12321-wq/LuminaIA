from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ColumnDataType(str, Enum):
    NUMERIC = "NUMERIC"
    TEXT = "TEXT"
    TIMESTAMP = "TIMESTAMP"
    BOOLEAN = "BOOLEAN"
    UNKNOWN = "UNKNOWN"

class ViewType(str, Enum):
    CADASTRAL = "CADASTRAL"
    TRANSACTONAL = "TRANSACTIONAL"
    AGGREGATED = "AGGREGATED"
    ANALYTICAL = "ANALYTICAL"

class AggregationType(str, Enum):
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    COUNT = "COUNT"
    COUNT_DISTINCT = "COUNT DISTINCT"
    NONE = "NONE"

class ColumnMetadata(BaseModel):
    physical_name: str
    friendly_name: str
    description: str
    data_type: ColumnDataType
    business_entity: str
    is_dimension: bool = False
    is_metric: bool = False
    filterable: bool = True
    groupable: bool = True
    sortable: bool = True
    chartable: bool = True
    supported_aggregations: List[AggregationType] = Field(default_factory=list)

class RelationshipMetadata(BaseModel):
    source_view: str
    source_column: str
    target_view: str
    target_column: str
    cardinality: str = "N:1"  # 1:1, N:1, 1:N
    is_forbidden: bool = False
    is_indirect: bool = False
    distance: int = 1
    description: str = ""

class ViewMetadata(BaseModel):
    name: str
    functional_description: str
    business_description: str
    purpose: str
    granularity: str
    view_type: ViewType
    columns: Dict[str, ColumnMetadata] = Field(default_factory=dict)
    primary_key: str
    foreign_keys: Dict[str, str] = Field(default_factory=dict)  # Target Entity -> Local Column
    related_views: List[str] = Field(default_factory=list)
    relationships: List[RelationshipMetadata] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)

class BusinessEntityMetadata(BaseModel):
    name: str
    views: List[str] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)  # Format: "View.Column"
    relationships: List[str] = Field(default_factory=list)  # Target Entity names
    metrics: List[str] = Field(default_factory=list)
    dimensions: List[str] = Field(default_factory=list)

class MetricMetadata(BaseModel):
    canonical_name: str
    description: str
    metric_type: str  # e.g., "Currency", "Quantity", "Ratio"
    supported_aggregations: List[AggregationType] = Field(default_factory=list)
    physical_column: str
    physical_view: str
    unit: str

class DimensionMetadata(BaseModel):
    name: str
    dimension_type: str  # e.g., "Geography", "Time", "Entity"
    physical_column: str
    physical_view: str
    hierarchy: List[str] = Field(default_factory=list)

class AliasMetadata(BaseModel):
    alias: str
    canonical_name: str
    category: str  # "Metric", "Dimension", "Entity"

class CorporateCatalog(BaseModel):
    views: Dict[str, ViewMetadata] = Field(default_factory=dict)
    entities: Dict[str, BusinessEntityMetadata] = Field(default_factory=dict)
    metrics: Dict[str, MetricMetadata] = Field(default_factory=dict)
    dimensions: Dict[str, DimensionMetadata] = Field(default_factory=dict)
    aliases: Dict[str, AliasMetadata] = Field(default_factory=dict)
    relationships: List[RelationshipMetadata] = Field(default_factory=list)
