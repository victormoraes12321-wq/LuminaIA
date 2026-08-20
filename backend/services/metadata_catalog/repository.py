import logging
from typing import List, Dict, Optional, Set
from collections import deque
from services.metadata_catalog.models import (
    CorporateCatalog, ViewMetadata, BusinessEntityMetadata, MetricMetadata,
    DimensionMetadata, AliasMetadata, RelationshipMetadata
)
from services.metadata_catalog.catalog import get_corporate_catalog

logger = logging.getLogger("luminaai.services.metadata_catalog.repository")

class CorporateCatalogRepository:
    """
    Repositório de APIs somente leitura sobre o Corporate Knowledge Catalog.
    """
    
    @property
    def catalog(self) -> CorporateCatalog:
        return get_corporate_catalog()

    def get_view(self, name: str) -> Optional[ViewMetadata]:
        return self.catalog.views.get(name.upper())

    def get_entity(self, name: str) -> Optional[BusinessEntityMetadata]:
        # Busca case-insensitive
        for ent_name, ent in self.catalog.entities.items():
            if ent_name.lower() == name.lower():
                return ent
        return None

    def get_metric(self, canonical_name: str) -> Optional[MetricMetadata]:
        for met_name, met in self.catalog.metrics.items():
            if met_name.lower() == canonical_name.lower():
                return met
        return None

    def get_dimension(self, name: str) -> Optional[DimensionMetadata]:
        for dim_name, dim in self.catalog.dimensions.items():
            if dim_name.lower() == name.lower():
                return dim
        return None

    def resolve_alias(self, alias_term: str) -> Optional[AliasMetadata]:
        cleaned = alias_term.strip().lower()
        return self.catalog.aliases.get(cleaned)

    def find_shortest_join_path(self, start_view: str, target_view: str) -> List[RelationshipMetadata]:
        """
        Encontra o caminho de JOIN mais curto (menor número de saltos) entre duas views
        utilizando busca em largura (BFS). Retorna lista vazia se desconectado.
        """
        start = start_view.upper()
        target = target_view.upper()
        
        if start == target:
            return []
            
        if start not in self.catalog.views or target not in self.catalog.views:
            return []

        # Fila BFS: (current_view_name, path_taken_as_list_of_relationships)
        queue = deque([(start, [])])
        visited: Set[str] = {start}
        
        while queue:
            curr, path = queue.popleft()
            
            if curr == target:
                return path
                
            view_meta = self.catalog.views.get(curr)
            if not view_meta:
                continue
                
            for rel in view_meta.relationships:
                neighbor = rel.target_view
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = path + [rel]
                    queue.append((neighbor, new_path))
                    
        return []  # Sem caminho disponível

    def get_views_for_entity(self, entity_name: str) -> List[str]:
        entity = self.get_entity(entity_name)
        return entity.views if entity else []

    def get_metrics_for_view(self, view_name: str) -> List[MetricMetadata]:
        result = []
        for met in self.catalog.metrics.values():
            if met.physical_view.upper() == view_name.upper():
                result.append(met)
        return result

    def get_dimensions_for_view(self, view_name: str) -> List[DimensionMetadata]:
        result = []
        for dim in self.catalog.dimensions.values():
            if dim.physical_view.upper() == view_name.upper():
                result.append(dim)
        return result

catalog_repository = CorporateCatalogRepository()
