import logging
from typing import Optional
from services.metadata_catalog.models import CorporateCatalog

logger = logging.getLogger("luminaai.services.metadata_catalog.catalog")

# Instância única global do catálogo em memória
_global_corporate_catalog: Optional[CorporateCatalog] = None

def get_corporate_catalog() -> CorporateCatalog:
    """
    Retorna a instância global do Corporate Knowledge Catalog.
    Caso não esteja inicializada, retorna um catálogo vazio para evitar falhas estruturais.
    """
    global _global_corporate_catalog
    if _global_corporate_catalog is None:
        logger.warning("Solicitada leitura do catálogo corporativo, mas ele ainda não foi inicializado.")
        _global_corporate_catalog = CorporateCatalog()
    return _global_corporate_catalog

def set_corporate_catalog(catalog: CorporateCatalog) -> None:
    """
    Define a instância global do catálogo corporativo.
    """
    global _global_corporate_catalog
    _global_corporate_catalog = catalog
    logger.info("Instância global do Corporate Knowledge Catalog atualizada com sucesso.")
