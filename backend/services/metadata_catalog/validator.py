import logging
from typing import List, Dict, Any
from services.metadata_catalog.models import CorporateCatalog, ViewMetadata, AggregationType
from services.metadata_catalog.catalog import get_corporate_catalog

logger = logging.getLogger("luminaai.services.metadata_catalog.validator")

class CatalogValidationError:
    def __init__(self, error_type: str, element: str, message: str, severity: str = "ERROR"):
        self.error_type = error_type
        self.element = element
        self.message = message
        self.severity = severity  # WARNING, ERROR, CRITICAL

    def to_dict(self) -> Dict[str, str]:
        return {
            "type": self.error_type,
            "element": self.element,
            "message": self.message,
            "severity": self.severity
        }

def validate_catalog(catalog: CorporateCatalog) -> List[CatalogValidationError]:
    """
    Executa testes de integridade semântica e física no Corporate Knowledge Catalog.
    Identifica: views sem PK, FKs inexistentes, relacionamentos quebrados,
    aliases conflitantes, tipos incompatíveis no JOIN.
    """
    errors: List[CatalogValidationError] = []
    
    # 1. Validação de Views
    for view_name, view in catalog.views.items():
        # 1.1 View sem PK
        if not view.primary_key:
            errors.append(CatalogValidationError(
                "MISSING_PK", view_name, f"A view {view_name} não possui Chave Primária declarada.", "CRITICAL"
            ))
        elif view.primary_key not in view.columns:
            errors.append(CatalogValidationError(
                "INVALID_PK", view_name, f"A PK '{view.primary_key}' da view {view_name} não existe nas colunas declaradas.", "CRITICAL"
            ))

        # 1.2 Validação de FKs e Views relacionadas
        for target_entity, local_col in view.foreign_keys.items():
            if local_col not in view.columns:
                errors.append(CatalogValidationError(
                    "INVALID_FK", view_name, f"A FK local '{local_col}' referenciando a entidade '{target_entity}' não existe nas colunas.", "ERROR"
                ))
            if target_entity not in catalog.entities:
                errors.append(CatalogValidationError(
                    "ORPHAN_FK_TARGET", view_name, f"A FK '{local_col}' aponta para a entidade inexistente '{target_entity}'.", "ERROR"
                ))

        # 1.3 Relacionamentos quebrados
        for rel in view.relationships:
            # Verifica existência da view de destino
            if rel.target_view not in catalog.views:
                errors.append(CatalogValidationError(
                    "BROKEN_RELATIONSHIP", view_name, f"O relacionamento aponta para a view inexistente '{rel.target_view}'.", "CRITICAL"
                ))
            else:
                target_view = catalog.views[rel.target_view]
                # Verifica existência de colunas locais e remotas
                if rel.source_column not in view.columns:
                    errors.append(CatalogValidationError(
                        "BROKEN_RELATIONSHIP_SOURCE_COL", view_name, f"A coluna de origem '{rel.source_column}' no JOIN com '{rel.target_view}' não existe.", "ERROR"
                    ))
                if rel.target_column not in target_view.columns:
                    errors.append(CatalogValidationError(
                        "BROKEN_RELATIONSHIP_TARGET_COL", view_name, f"A coluna de destino '{rel.target_column}' na view '{rel.target_view}' não existe.", "ERROR"
                    ))
                    
                # Tipo de dados incompatível (Warning de performance/tipo)
                source_col = view.columns.get(rel.source_column)
                target_col = target_view.columns.get(rel.target_column)
                if source_col and target_col and source_col.data_type != target_col.data_type:
                    errors.append(CatalogValidationError(
                        "TYPE_MISMATCH_JOIN", f"{view_name} <-> {rel.target_view}",
                        f"Tipo incompatível no JOIN: {rel.source_column} ({source_col.data_type}) vs {rel.target_column} ({target_col.data_type}). Requer cast explícito.",
                        "WARNING"
                    ))

    # 2. Validação de Aliases Conflitantes
    alias_map: Dict[str, str] = {}
    for alias_name, alias_meta in catalog.aliases.items():
        if alias_name in alias_map:
            # Conflito de nomes
            if alias_map[alias_name] != alias_meta.canonical_name:
                errors.append(CatalogValidationError(
                    "CONFLICTING_ALIAS", alias_name, f"Alias '{alias_name}' mapeia para múltiplos conceitos: '{alias_map[alias_name]}' e '{alias_meta.canonical_name}'.", "ERROR"
                ))
        else:
            alias_map[alias_name] = alias_meta.canonical_name

    # 3. Validação de Métricas Órfãs
    for metric_name, metric in catalog.metrics.items():
        if metric.physical_view not in catalog.views:
            errors.append(CatalogValidationError(
                "ORPHAN_METRIC_VIEW", metric_name, f"A métrica '{metric_name}' aponta para a view inexistente '{metric.physical_view}'.", "ERROR"
            ))
        else:
            view = catalog.views[metric.physical_view]
            if metric.physical_column not in view.columns:
                errors.append(CatalogValidationError(
                    "ORPHAN_METRIC_COLUMN", metric_name, f"A métrica '{metric_name}' aponta para a coluna inexistente '{metric.physical_column}' da view '{metric.physical_view}'.", "ERROR"
                ))

    # 4. Validação de Dimensões Órfãs
    for dim_name, dim in catalog.dimensions.items():
        if dim.physical_view not in catalog.views:
            errors.append(CatalogValidationError(
                "ORPHAN_DIMENSION_VIEW", dim_name, f"A dimensão '{dim_name}' aponta para a view inexistente '{dim.physical_view}'.", "ERROR"
            ))
        else:
            view = catalog.views[dim.physical_view]
            if dim.physical_column not in view.columns:
                errors.append(CatalogValidationError(
                    "ORPHAN_DIMENSION_COLUMN", dim_name, f"A dimensão '{dim_name}' aponta para a coluna inexistente '{dim.physical_column}' da view '{dim.physical_view}'.", "ERROR"
                ))

    return errors
