import pytest
import uuid
import time
from unittest.mock import AsyncMock, MagicMock, patch
from models.new_pipeline_contracts import (
    ExecutionPlan, ResolvedEntities, ResolvedEntity, ExecutionStatus, EmptyDatasetPolicy,
    IntentType, QueryCost, CanonicalFilter, ComparisonOperator
)
from services.metadata_catalog.executor import (
    QueryPlanner, QueryOptimizer, SQLGenerator, SecurityValidator, DatabaseExecutor
)
from services.metadata_catalog.loader import load_corporate_catalog

@pytest.fixture(autouse=True)
def setup_catalog():
    load_corporate_catalog()

def test_query_planner_validation():
    planner = QueryPlanner()
    
    # Plano válido
    valid_plan = ExecutionPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        resolved_entities=ResolvedEntities(
            entities={"Cliente": ResolvedEntity(
                logical_name="Cliente", physical_view="VW_CLIENTES_CAD_LM", primary_key="codigo",
                available_columns=["codigo", "nome"], foreign_keys={}, supported_metrics=[], supported_dimensions=[]
            )},
            joins=[]
        ),
        selected_views=["VW_CLIENTES_CAD_LM"],
        columns=["VW_CLIENTES_CAD_LM.nome"],
        filters=[],
        group_by=[],
        order_by=[],
        having=[],
        cte=[],
        parameters={},
        estimated_cost=QueryCost.LOW,
        estimated_rows=10,
        execution_priority=1,
        cacheable=True,
        cache_key="key_1",
        required_permissions=[],
        timeout=30,
        empty_dataset_policy=EmptyDatasetPolicy.EMPTY_EXPECTED
    )
    assert planner.validate_plan(valid_plan) is True

    # Plano inválido (sem views)
    invalid_plan = valid_plan.model_copy(update={"selected_views": []})
    with pytest.raises(ValueError, match="não contém nenhuma view física"):
        planner.validate_plan(invalid_plan)

def test_query_optimizer_reduces_redundant_views():
    optimizer = QueryOptimizer()
    
    plan = ExecutionPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        resolved_entities=ResolvedEntities(
            entities={
                "Cliente": ResolvedEntity(logical_name="Cliente", physical_view="VW_CLIENTES_CAD_LM", primary_key="codigo", available_columns=[], foreign_keys={}, supported_metrics=[], supported_dimensions=[]),
                "Venda": ResolvedEntity(logical_name="Venda", physical_view="VW_VENDAS_LM", primary_key="nota_", available_columns=[], foreign_keys={}, supported_metrics=[], supported_dimensions=[])
            },
            joins=[]
        ),
        # VW_CLIENTES_CAD_LM está selecionada, mas não é usada em nenhuma coluna ou filtro!
        selected_views=["VW_VENDAS_LM", "VW_CLIENTES_CAD_LM"],
        columns=["VW_VENDAS_LM.ptotal_"],
        filters=[],
        group_by=[],
        order_by=[],
        having=[],
        cte=[],
        parameters={},
        estimated_cost=QueryCost.MEDIUM,
        estimated_rows=10,
        execution_priority=1,
        cacheable=True,
        cache_key="key_2",
        required_permissions=[],
        timeout=30,
        empty_dataset_policy=EmptyDatasetPolicy.EMPTY_EXPECTED
    )
    
    opt_plan = optimizer.optimize_plan(plan)
    # A view não utilizada deve ser eliminada da lista física
    assert "VW_CLIENTES_CAD_LM" not in opt_plan.selected_views
    assert opt_plan.selected_views == ["VW_VENDAS_LM"]

def test_sql_generator_parametrized_compilation():
    generator = SQLGenerator()
    
    plan = ExecutionPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        resolved_entities=ResolvedEntities(
            entities={},
            joins=[{
                "source_view": "VW_VENDAS_LM",
                "source_column": "codcliente_",
                "target_view": "VW_CLIENTES_CAD_LM",
                "target_column": "codigo"
            }]
        ),
        selected_views=["VW_VENDAS_LM", "VW_CLIENTES_CAD_LM"],
        columns=["SUM(VW_VENDAS_LM.ptotal_)", "VW_CLIENTES_CAD_LM.nome_cidade"],
        filters=[
            CanonicalFilter(field="VW_CLIENTES_CAD_LM.uf", operator=ComparisonOperator.EQUALS, value="MG")
        ],
        group_by=["VW_CLIENTES_CAD_LM.nome_cidade"],
        order_by=["VW_CLIENTES_CAD_LM.nome_cidade DESC"],
        cte=[],
        parameters={},
        limit=10,
        estimated_cost=QueryCost.MEDIUM,
        estimated_rows=10,
        execution_priority=1,
        cacheable=True,
        cache_key="key_3",
        required_permissions=[],
        timeout=30,
        empty_dataset_policy=EmptyDatasetPolicy.EMPTY_EXPECTED
    )
    
    sql, binds = generator.generate_sql(plan)
    
    assert "SELECT SUM(VW_VENDAS_LM.ptotal_), VW_CLIENTES_CAD_LM.nome_cidade" in sql
    assert "FROM VW_VENDAS_LM" in sql
    assert "INNER JOIN VW_CLIENTES_CAD_LM ON coalesce(nullif(ltrim(VW_VENDAS_LM.codcliente_::text, '0'), ''), '0') = coalesce(nullif(ltrim(VW_CLIENTES_CAD_LM.codigo::text, '0'), ''), '0')" in sql
    assert "WHERE VW_CLIENTES_CAD_LM.uf = :param_0" in sql
    assert "GROUP BY VW_CLIENTES_CAD_LM.nome_cidade" in sql
    assert "ORDER BY VW_CLIENTES_CAD_LM.nome_cidade DESC" in sql
    assert "LIMIT 10" in sql
    assert binds["param_0"] == "MG"

def test_security_validator_blocks_malicious_sql():
    validator = SecurityValidator()
    tenant_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    
    # SQL Seguro
    safe_sql = "SELECT nome FROM VW_CLIENTES_CAD_LM WHERE tenant_id = :tenant_id"
    assert validator.validate_sql_safety(safe_sql, tenant_id) is True
    
    # Bloqueio de DDL
    with pytest.raises(ValueError, match="comando proibido"):
        validator.validate_sql_safety("DROP TABLE VW_CLIENTES_CAD_LM", tenant_id)
        
    # Bloqueio de injeção por ponto e vírgula
    with pytest.raises(ValueError, match="comando proibido"):
        validator.validate_sql_safety("SELECT * FROM VW_VENDAS_LM; DELETE FROM VW_VENDAS_LM", tenant_id)

@pytest.mark.asyncio
@patch("services.metadata_catalog.executor.get_db_context")
@patch("services.metadata_catalog.executor.create_async_engine")
async def test_database_executor_cache_and_empty_dataset_policy(mock_create_engine, mock_db_context):
    executor = DatabaseExecutor()
    tenant_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    
    plan = ExecutionPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        resolved_entities=ResolvedEntities(entities={}, joins=[]),
        selected_views=["VW_VENDAS_LM"],
        columns=["VW_VENDAS_LM.ptotal_"],
        filters=[],
        group_by=[],
        order_by=[],
        having=[],
        cte=[],
        parameters={},
        estimated_cost=QueryCost.LOW,
        estimated_rows=10,
        execution_priority=1,
        cacheable=True,
        cache_key="unique_cache_key_123",
        required_permissions=[],
        timeout=30,
        empty_dataset_policy=EmptyDatasetPolicy.EMPTY_UNEXPECTED
    )
    
    # Mock do banco clone retornando registros vazios
    mock_session = AsyncMock()
    mock_db_result = MagicMock()
    mock_db_result.fetchall.return_value = []
    mock_session.execute.return_value = mock_db_result
    
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine
    
    mock_sessionmaker = MagicMock()
    mock_sessionmaker.return_value.__aenter__.return_value = mock_session
    
    # Mock do tenant no get_db_context
    tenant_mock = MagicMock()
    tenant_mock.clone_db_conn = "encrypted_details"
    mock_corp_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = tenant_mock
    mock_corp_session.execute.return_value = mock_result
    mock_db_context.return_value.__aenter__.return_value = mock_corp_session
    
    with patch("services.metadata_catalog.executor.sessionmaker", return_value=mock_sessionmaker), \
         patch("services.metadata_catalog.executor.decrypt_connection_details", return_value={"database": "test_db"}):
        
        # Executa query (Vazia + EMPTY_UNEXPECTED)
        res = await executor.execute_query(plan, "SELECT ptotal_ FROM VW_VENDAS_LM", {}, tenant_id)
        
        # Deve marcar NEEDS_REPLANNING
        assert res["status"] == "NEEDS_REPLANNING"
        assert len(res["warnings"]) > 0
