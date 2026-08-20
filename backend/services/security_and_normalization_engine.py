import logging
from typing import Any, List, Dict
from models.new_pipeline_contracts import ExecutionPlan
from services.metadata_catalog.executor import SecurityValidator as NewSecurityValidator

logger = logging.getLogger("luminaai.services.security_and_normalization_engine")

class SecurityValidationError(Exception):
    pass

class EmptyDatasetAnomalyError(Exception):
    pass

class SecurityValidator(NewSecurityValidator):
    """
    Wrapper da nova implementação do SecurityValidator baseado no CKC dinâmico.
    """
    pass

class ResultNormalizer:
    """
    Normalizador de resultado que mantém compatibilidade com o formato legado
    caso o orquestrador o chame diretamente, utilizando a nova normalização de tipo.
    """
    def normalize_dataset(self, raw_rows: List[Dict[str, Any]], plan: ExecutionPlan) -> List[Dict[str, Any]]:
        from services.metadata_catalog.executor import database_executor
        normalized = []
        for r in raw_rows:
            normalized.append(database_executor._normalize_row(r))
            
        # Política de Dataset Vazio para retrocompatibilidade com loops de auto-cura baseados em exceção
        from models.new_pipeline_contracts import EmptyDatasetPolicy
        if not normalized:
            if plan.empty_dataset_policy == EmptyDatasetPolicy.EMPTY_UNEXPECTED:
                raise EmptyDatasetAnomalyError("Dataset vazio inesperado detectado durante a normalização analítica.")
        return normalized
