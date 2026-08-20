"""
LuminaAI — Test Suite: Live Dashboard Runtime & Event Engine
--------------------------------------------------------------
Cobertura completa dos componentes de Live Dashboard Runtime.
"""
from __future__ import annotations

import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from models.tenant import Tenant
from models.view_catalog import ChartType
from models.analytical_package import AnalyticalPackage, PackageStatus
from models.package_dashboard_instance import PackageDashboardInstance
from services.data_platform import execution_engine
from services.data_platform.dataset_builder import dataset_builder
from services.data_platform.analytics_engine import analytics_engine
from services.data_platform.event_engine import event_engine
from services.data_platform.live_dashboard_runtime import live_dashboard_runtime


# ── Component 1: Event Engine Tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_event_engine_pub_sub():
    """Testa inscrição, publicação de eventos válidos e desinscrição."""
    tenant_id = uuid.uuid4()
    
    # Se inscreve
    q = await event_engine.subscribe(tenant_id)
    
    # Publica evento de teste
    event_data = {"test_key": "test_value"}
    delivered = await event_engine.publish(tenant_id, "SYNC_FINISHED", event_data)
    assert delivered == 1
    
    # Verifica recebimento
    received = await q.get()
    assert received["event_type"] == "SYNC_FINISHED"
    assert received["tenant_id"] == str(tenant_id)
    assert received["payload"] == event_data
    
    # Desinscreve
    await event_engine.unsubscribe(tenant_id, q)
    
    # Publica novamente e garante que nenhum ouvinte recebe
    delivered = await event_engine.publish(tenant_id, "SYNC_FINISHED", event_data)
    assert delivered == 0


@pytest.mark.asyncio
async def test_event_engine_multi_tenant_isolation():
    """Testa que os eventos são entregues estritamente para o Tenant correto."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    
    q_a = await event_engine.subscribe(tenant_a)
    q_b = await event_engine.subscribe(tenant_b)
    
    # Publica no Tenant A
    await event_engine.publish(tenant_a, "DATASET_UPDATED", {"view": "VW_VENDAS"})
    
    # Tenant A recebe, Tenant B não recebe
    assert q_a.qsize() == 1
    assert q_b.qsize() == 0
    
    event_a = await q_a.get()
    assert event_a["event_type"] == "DATASET_UPDATED"
    assert event_a["tenant_id"] == str(tenant_a)
    
    # Limpa conexões
    await event_engine.unsubscribe(tenant_a, q_a)
    await event_engine.unsubscribe(tenant_b, q_b)


# ── Component 2: Live Dashboard Runtime Diff Engine & Cache Tests ─────────────

def test_change_detection_diff():
    """Testa o algoritmo de Change Detection (Diff Rendering)."""
    prev_widgets = [
        {"type": "KPI_CARD", "title": "Faturamento", "value": 1000.0, "diff_percent": 5.0, "direction": "UP"},
        {"type": "BAR", "title": "Vendas Regiao", "data": [{"label": "Sul", "value": 500.0}]},
        {"type": "TABLE", "title": "Clientes", "rows": [{"id": 1, "nome": "Maria"}], "total_rows": 1}
    ]
    
    # Caso 1: Apenas o KPI Faturamento mudou
    new_widgets_1 = [
        {"type": "KPI_CARD", "title": "Faturamento", "value": 1100.0, "diff_percent": 10.0, "direction": "UP"}, # Alterado
        {"type": "BAR", "title": "Vendas Regiao", "data": [{"label": "Sul", "value": 500.0}]}, # Idêntico
        {"type": "TABLE", "title": "Clientes", "rows": [{"id": 1, "nome": "Maria"}], "total_rows": 1} # Idêntico
    ]
    
    updated, reused = live_dashboard_runtime.detect_changes(prev_widgets, new_widgets_1)
    assert len(updated) == 1
    assert updated[0]["title"] == "Faturamento"
    assert len(reused) == 2
    assert {w["title"] for w in reused} == {"Vendas Regiao", "Clientes"}

    # Caso 2: Tabela mudou
    new_widgets_2 = [
        {"type": "KPI_CARD", "title": "Faturamento", "value": 1000.0, "diff_percent": 5.0, "direction": "UP"}, # Idêntico
        {"type": "BAR", "title": "Vendas Regiao", "data": [{"label": "Sul", "value": 500.0}]}, # Idêntico
        {"type": "TABLE", "title": "Clientes", "rows": [{"id": 1, "nome": "Maria"}, {"id": 2, "nome": "Joao"}], "total_rows": 2} # Alterado
    ]
    updated, reused = live_dashboard_runtime.detect_changes(prev_widgets, new_widgets_2)
    assert len(updated) == 1
    assert updated[0]["title"] == "Clientes"
    assert len(reused) == 2


def test_component_cache():
    """Testa get, set e limpeza de caches de componentes individuais."""
    tenant_id = uuid.uuid4()
    package_id = uuid.uuid4()
    
    # Cache miss
    cached = live_dashboard_runtime.get_cached_component(tenant_id, package_id, "BAR", "Vendas Canal")
    assert cached is None
    
    # Cache set & hit
    widget_data = {"type": "BAR", "title": "Vendas Canal", "data": [10, 20]}
    live_dashboard_runtime.set_component_cache(tenant_id, package_id, "BAR", "Vendas Canal", widget_data)
    
    cached = live_dashboard_runtime.get_cached_component(tenant_id, package_id, "BAR", "Vendas Canal")
    assert cached == widget_data
    
    # Limpeza de cache do pacote
    live_dashboard_runtime.clear_package_caches(tenant_id, package_id)
    cached = live_dashboard_runtime.get_cached_component(tenant_id, package_id, "BAR", "Vendas Canal")
    assert cached is None


# ── Component 3: Smart Refresh Integration Tests ─────────────────────────────

@pytest.mark.asyncio
async def test_smart_refresh_execution():
    """Testa a execução completa do Smart Refresh reativo com mock do banco de dados."""
    tenant_id = uuid.uuid4()
    package_id = uuid.uuid4()
    
    # Mock do AnalyticalPackage
    mock_package = AnalyticalPackage()
    mock_package.id = package_id
    mock_package.tenant_id = tenant_id
    mock_package.status = PackageStatus.ACTIVE
    mock_package.visual_strategy = {"primary_chart_type": "BAR"}
    mock_package.analytical_structure = {"filters": {"date_range": "2026-07-01 to 2026-07-08"}}
    mock_package.blueprint_snapshot = {
        "consulta_principal": {
            "id": "principal",
            "view_catalog_id": str(uuid.uuid4()),
            "view_name": "VW_VENDAS",
            "parametros": {},
            "prioridade": "ALTA",
            "sugestao_visualizacao": "BAR",
            "depende_de": [],
            "objetivo": "Faturamento",
            "obrigatoria": True
        },
        "consultas_complementares": [],
        "kpis_planejados": [],
        "comparacoes_planejadas": [],
        "ordem_execucao": [["principal"]],
        "contexto": {}
    }
    mock_package.usage_count = 5
    mock_package.avg_execution_time_ms = 100.0
    mock_package.last_used_at = None

    # Mock do Tenant
    mock_tenant = Tenant()
    mock_tenant.id = tenant_id
    mock_tenant.nome = "Empresa Teste"
    mock_tenant.sync_config = {}

    # Mock do DashboardInstance anterior
    mock_prev_instance = MagicMock()
    mock_prev_instance.dashboard_payload = {
        "widgets": [
            {"type": "FILTROS", "title": "Painel de Filtros", "active_filters": {}},
            {"type": "BAR", "title": "Gráfico VENDAS", "data": [{"label": "Carlos", "value": 100.0}]},
            {"type": "TABLE", "title": "Tabela VENDAS", "columns": ["vendedor", "receita_total"], "rows": [{"vendedor": "Carlos", "receita_total": 120.0}], "total_rows": 1}
        ]
    }
    mock_prev_instance.bi_intelligence_snapshot = {"metrics": {}}

    # Mock da Sessão SQLAlchemy
    db_session = MagicMock(spec=AsyncSession)
    
    # Mock do select do pacote analítico, tenant e dashboard instance anterior
    mock_pkg_result = MagicMock()
    mock_pkg_result.scalar_one_or_none.return_value = mock_package
    
    mock_ten_result = MagicMock()
    mock_ten_result.scalar_one_or_none.return_value = mock_tenant
    
    mock_prev_result = MagicMock()
    mock_prev_result.scalar_one_or_none.return_value = mock_prev_instance

    db_session.execute = AsyncMock()
    db_session.execute.side_effect = [mock_pkg_result, mock_ten_result, mock_prev_result]
    db_session.commit = AsyncMock()

    # Mocks para sub-motores do Data Platform
    mock_query_results = {
        "principal": {
            "view_name": "VW_VENDAS",
            "raw_rows": [{"vendedor": "Carlos", "receita_total": 120.0}], # Mudou de 100.0 para 120.0
            "sugestao_visualizacao": "BAR"
        }
    }
    
    mock_datasets = {
        "principal": {
            "metadata": {"view_name": "VW_VENDAS", "quantidade_registros": 1},
            "schema": {"vendedor": "string", "receita_total": "float"},
            "data": [{"vendedor": "Carlos", "receita_total": 120.0}]
        }
    }
    
    mock_analytics = {"kpis": {}}

    with patch.object(execution_engine, "execute_blueprint", AsyncMock(return_value=mock_query_results)), \
         patch.object(dataset_builder, "build_dataset", MagicMock(side_effect=lambda **kwargs: mock_datasets["principal"])), \
         patch.object(analytics_engine, "process_analytics", AsyncMock(return_value=mock_analytics)), \
         patch.object(event_engine, "publish", AsyncMock(return_value=1)) as mock_publish:
         
        # Dispara o Smart Refresh
        event_data = await live_dashboard_runtime.refresh_runtime(tenant_id, package_id, db_session)
        
        # Verificações
        assert event_data["package_id"] == str(package_id)
        assert len(event_data["updated_widgets"]) == 1
        assert event_data["updated_widgets"][0]["title"] == "Gráfico VENDAS"
        assert event_data["updated_widgets"][0]["data"][0]["value"] == 120.0 # Valida novo valor atualizado no Diff
        
        # Garante que incrementou contador de reuso no pacote analítico
        assert mock_package.usage_count == 6
        assert mock_package.last_used_at is not None
        
        # Garante que publicou eventos de atualização
        assert mock_publish.call_count >= 3
        mock_publish.assert_any_call(tenant_id, "DASHBOARD_UPDATED", event_data)


def test_telemetry_history():
    """Testa que os logs de observabilidade são salvos e filtrados por Tenant."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    
    live_dashboard_runtime._telemetry_history = [
        {"tenant_id": str(tenant_a), "update_time_ms": 50},
        {"tenant_id": str(tenant_a), "update_time_ms": 70},
        {"tenant_id": str(tenant_b), "update_time_ms": 120}
    ]
    
    report_a = live_dashboard_runtime.get_telemetry_report(tenant_a)
    assert len(report_a) == 2
    assert report_a[0]["update_time_ms"] == 50
    
    report_all = live_dashboard_runtime.get_telemetry_report()
    assert len(report_all) == 3
