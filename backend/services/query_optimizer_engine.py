import re
from typing import List, Dict, Any, Optional
from models.new_pipeline_contracts import ExecutionPlan, ComparisonOperator

from services.metadata_catalog.executor import QueryOptimizer as NewQueryOptimizer
from services.metadata_catalog.executor import SQLGenerator as NewSQLGenerator

def translate_expression(expr: str) -> str:
    """
    Mantido para retrocompatibilidade caso outros módulos importem esta função auxiliar.
    """
    return expr

class QueryOptimizer(NewQueryOptimizer):
    """
    Wrapper da nova implementação do QueryOptimizer baseada no CKC dinâmico.
    """
    pass

class SQLGenerator(NewSQLGenerator):
    """
    Wrapper da nova implementação do SQLGenerator baseada no CKC dinâmico.
    """
    pass
