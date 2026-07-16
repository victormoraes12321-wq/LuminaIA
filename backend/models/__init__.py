"""
LuminaAI — ORM Models Package

Importa e expõe todos os modelos ORM para uso centralizado.
Garante que todos os models são registrados na metadata do SQLAlchemy
antes de qualquer operação de banco (ex: create_all, Alembic migrations).

Uso:
    from models import Tenant, User, ViewCatalog, SearchHistory, Favorite
"""
from models.tenant import Tenant
from models.user import User, UserRole
from models.view_catalog import ViewCatalog, ChartType
from models.search_history import SearchHistory
from models.favorite import Favorite
from models.blueprint import Blueprint
from models.metadata_catalog import MetadataCatalog
from models.dataset import Dataset
from models.data_platform_history import DataPlatformHistory
from models.semantic_catalog import SemanticCatalog
from models.metadata_catalog_version import MetadataCatalogVersion
from models.sync_queue import SyncQueue
from models.analytical_package import AnalyticalPackage, PackageStatus
from models.package_dashboard_instance import PackageDashboardInstance
from models.dashboard_template import DashboardTemplate
from models.dashboard_instance import DashboardInstance
from models.dashboard_studio_version import DashboardStudioVersion
from models.business_concept import BusinessConcept
from models.business_kpi import BusinessKPI
from models.business_formula import BusinessFormula
from models.business_relationship import BusinessRelationship
from models.business_governance_log import BusinessGovernanceLog
from models.semantic_memory import SemanticMemory
from models.svr import SVRConcept, SVRVersion, SVRCompatibilityMatrix, SVRAuditLog

__all__: list[str] = [
    "Tenant",
    "User",
    "UserRole",
    "ViewCatalog",
    "ChartType",
    "SearchHistory",
    "Favorite",
    "Blueprint",
    "MetadataCatalog",
    "MetadataCatalogVersion",
    "Dataset",
    "DataPlatformHistory",
    "SemanticCatalog",
    "SyncQueue",
    "AnalyticalPackage",
    "PackageStatus",
    "PackageDashboardInstance",
    "DashboardTemplate",
    "DashboardInstance",
    "DashboardStudioVersion",
    "BusinessConcept",
    "BusinessKPI",
    "BusinessFormula",
    "BusinessRelationship",
    "BusinessGovernanceLog",
    "SemanticMemory",
    "SVRConcept",
    "SVRVersion",
    "SVRCompatibilityMatrix",
    "SVRAuditLog",
]
