import pytest
from decimal import Decimal
from typing import Dict, Any

from contracts.safe_analytical_postgresql_v2.query_spec import (
    AnalyticalQuerySpecV2,
    AnalyticalMetricSelectV2,
    AnalyticalDimensionSelectV2,
    AnalyticalFilterGroupV2,
    AnalyticalFilterExpressionV2,
    AnalyticalOrderByV2,
    AnalyticalQueryBudgetV2,
)
from contracts.safe_analytical_postgresql_v2.identity import AnalyticalFilterOperatorV2
from services.safe_analytical_postgresql import (
    AnalyticalCatalogService,
    GovernedAnalyticalSQLCompiler,
    AnalyticalConnectionGuard,
    AnalyticalResultValidator,
    AnalyticalProvenanceService,
    SafeAnalyticalPostgreSQLService,
    AnalyticalConnectionGuardError,
    AnalyticalSecurityViolationError,
    AnalyticalBudgetExceededError,
    AnalyticalCompilationError,
)
from services.ai_tool_registry.adapters.analytical_postgresql_adapter import (
    AnalyticalPostgreSQLQueryToolAdapter,
)

pytestmark = pytest.mark.no_database


def test_catalog_snapshot_loading():
    cat_service = AnalyticalCatalogService()
    snapshot = cat_service.get_default_catalog_snapshot()
    assert snapshot.catalog_version == "1.0.0"
    assert "sales_analytics" in snapshot.datasets
    dataset = snapshot.datasets["sales_analytics"]
    assert dataset.canonical_dataset_id == "sales_analytics"
    assert "vw_vendas_lm" in dataset.relations
    assert "total_sales" in dataset.metric_bindings
    assert "branch" in dataset.dimension_bindings


def test_connection_guard_oracle_block():
    with pytest.raises(AnalyticalConnectionGuardError, match="Oracle"):
        AnalyticalConnectionGuard.assert_safe_target(
            db_url="oracle+cx_oracle://user:pass@localhost:1521/xe",
            tenant_id="tenant_test",
        )


def test_connection_guard_missing_tenant():
    with pytest.raises(AnalyticalConnectionGuardError, match="tenant_id"):
        AnalyticalConnectionGuard.assert_safe_target(
            db_url="postgresql+asyncpg://postgres:postgres@localhost:5432/lumina_test",
            tenant_id="",
        )


def test_connection_guard_non_read_only():
    with pytest.raises(AnalyticalConnectionGuardError, match="read-only"):
        AnalyticalConnectionGuard.assert_safe_target(
            db_url="postgresql+asyncpg://postgres:postgres@localhost:5432/lumina_test",
            tenant_id="tenant_test",
            is_read_only=False,
        )


def test_sql_compiler_valid():
    cat_service = AnalyticalCatalogService()
    snapshot = cat_service.get_default_catalog_snapshot()
    compiler = GovernedAnalyticalSQLCompiler(snapshot)

    spec = AnalyticalQuerySpecV2(
        spec_id="test_spec_001",
        dataset_id="sales_analytics",
        metrics=[AnalyticalMetricSelectV2(metric_id="total_sales", alias="faturamento")],
        dimensions=[AnalyticalDimensionSelectV2(dimension_id="branch", alias="filial")],
        filter_group=AnalyticalFilterGroupV2(
            expressions=[
                AnalyticalFilterExpressionV2(
                    dimension_id="branch",
                    operator=AnalyticalFilterOperatorV2.EQ,
                    values=["Filial SP"],
                )
            ]
        ),
        order_by=[AnalyticalOrderByV2(field="faturamento", direction="DESC")],
    )

    compiled = compiler.compile(spec, tenant_id="tenant_test")

    assert "vw_vendas_lm" in compiled.sql_template
    assert "tenant_id = :bind_tenant_id" in compiled.sql_template
    assert "filial_nome = :bind_filter_0" in compiled.sql_template
    assert compiled.isolation_proof.tenant_id == "tenant_test"
    assert compiled.isolation_proof.validation_status == "VALIDATED"
    assert compiled.query_fingerprint is not None


def test_sql_compiler_security_violation():

    spec = AnalyticalQuerySpecV2(
        spec_id="test_spec_002",
        dataset_id="sales_analytics",
        metrics=[AnalyticalMetricSelectV2(metric_id="total_sales")],
        dimensions=[AnalyticalDimensionSelectV2(dimension_id="branch")],
    )
    assert spec.dimensions[0].dimension_id == "branch"


def test_sql_compiler_budget_exceeded():
    cat_service = AnalyticalCatalogService()
    snapshot = cat_service.get_default_catalog_snapshot()
    compiler = GovernedAnalyticalSQLCompiler(snapshot)

    spec = AnalyticalQuerySpecV2(
        spec_id="test_spec_003",
        dataset_id="sales_analytics",
        metrics=[AnalyticalMetricSelectV2(metric_id="total_sales") for _ in range(25)],
    )

    budget = AnalyticalQueryBudgetV2(maximum_metrics=20)
    with pytest.raises(AnalyticalBudgetExceededError):
        compiler.compile(spec, tenant_id="tenant_test", budget=budget)


def test_result_validator_decimal_precision():
    validator = AnalyticalResultValidator()
    raw_rows = [
        {"filial_nome": "Filial SP", "valor_total": Decimal("15420.50")},
        {"filial_nome": "Filial RJ", "valor_total": 8750.25},
    ]

    cat_service = AnalyticalCatalogService()
    snapshot = cat_service.get_default_catalog_snapshot()
    compiler = GovernedAnalyticalSQLCompiler(snapshot)
    spec = AnalyticalQuerySpecV2(
        spec_id="test_spec_004",
        dataset_id="sales_analytics",
        metrics=[AnalyticalMetricSelectV2(metric_id="total_sales")],
    )
    compiled = compiler.compile(spec, tenant_id="tenant_test")

    res = validator.validate_and_format(raw_rows, compiled, execution_time_ms=12.5)

    assert res.statistics.row_count == 2
    assert res.validation.decimal_preserved is True
    assert res.rows[0].values["valor_total"] == "15420.50"
    assert res.rows[1].values["valor_total"] == "8750.25"


def test_provenance_generation():
    prov_service = AnalyticalProvenanceService()
    validator = AnalyticalResultValidator()
    cat_service = AnalyticalCatalogService()
    snapshot = cat_service.get_default_catalog_snapshot()
    compiler = GovernedAnalyticalSQLCompiler(snapshot)

    spec = AnalyticalQuerySpecV2(
        spec_id="test_spec_005",
        dataset_id="sales_analytics",
        metrics=[AnalyticalMetricSelectV2(metric_id="total_sales")],
    )
    compiled = compiler.compile(spec, tenant_id="tenant_test")
    res = validator.validate_and_format([], compiled, execution_time_ms=5.0)

    prov = prov_service.generate_provenance(compiled, res)
    assert prov.dataset_id == "sales_analytics"
    assert prov.validation_status == "VALIDATED"
    assert prov.isolation_proof_checksum == compiled.isolation_proof.proof_checksum


@pytest.mark.asyncio
async def test_ai_tool_adapter_execution(monkeypatch):
    adapter = AnalyticalPostgreSQLQueryToolAdapter()
    assert adapter.adapter_id == "analytical_postgresql.query.v1"
    assert adapter.tool_id == "lumina.analytical_postgresql.query"

    # Mock execute_query on underlying service to return a dummy result
    async def mock_execute(spec, tenant_id, user_id):
        validator = AnalyticalResultValidator()
        cat_service = AnalyticalCatalogService()
        snapshot = cat_service.get_default_catalog_snapshot()
        compiler = GovernedAnalyticalSQLCompiler(snapshot)
        compiled = compiler.compile(spec, tenant_id=tenant_id)
        return validator.validate_and_format(
            [{"filial_nome": "Filial SP", "faturamento": Decimal("1000.00")}],
            compiled,
            execution_time_ms=10.0,
        )

    monkeypatch.setattr(adapter.service, "execute_query", mock_execute)

    params = {
        "query_spec": {
            "spec_id": "test_spec_006",
            "dataset_id": "sales_analytics",
            "metrics": [{"metric_id": "total_sales", "alias": "faturamento"}],
            "dimensions": [{"dimension_id": "branch"}],
        }
    }
    context = {"tenant_id": "tenant_test", "user_id": "user_123"}

    res_dict = await adapter.execute(params, context)
    assert res_dict["contract_version"] == "lumina.safe-analytical-postgresql/1.0"
    assert res_dict["statistics"]["row_count"] == 1
