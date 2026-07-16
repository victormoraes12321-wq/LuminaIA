"""
LuminaAI — Test Suite: Enterprise Component Engine (ECE)
--------------------------------------------------------
Cobertura de testes automatizados completa do motor visual ECE.
"""
from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi import HTTPException

from services.context_guard import ScopeViolationError
from services.data_platform.enterprise_component_engine.schemas import ComponentSchema
from services.data_platform.enterprise_component_engine.registry import component_registry
from services.data_platform.enterprise_component_engine.factory import ComponentFactory
from services.data_platform.enterprise_component_engine.renderer import component_renderer
from services.data_platform.enterprise_component_engine.state_manager import component_state_manager
from services.data_platform.enterprise_component_engine.lifecycle import component_lifecycle
from services.data_platform.enterprise_component_engine.cache import component_cache
from services.data_platform.enterprise_component_engine.events import component_events
from services.data_platform.enterprise_component_engine.diagnostics import component_diagnostics
from services.data_platform.enterprise_component_engine.security import component_security
from services.data_platform.enterprise_component_engine import enterprise_component_engine


# ── Component 1: Registry Tests ──────────────────────────────────────────────

def test_registry_registration_and_duplication():
    """Testa cadastro correto no catálogo e rejeição de componentes duplicados."""
    component_registry.clear()
    tenant_id = uuid.uuid4()
    
    comp1 = ComponentFactory.create_component(type="BAR", name="Faturamento Vendedor", tenant_id=tenant_id)
    comp2 = ComponentFactory.create_component(type="BAR", name="Faturamento Vendedor", tenant_id=tenant_id) # Duplicado!
    
    # Sucesso no primeiro registro
    registered = component_registry.register(comp1)
    assert registered.id == comp1.id
    
    # Falha de duplicidade no segundo registro
    with pytest.raises(ValueError, match="já registrado na categoria"):
        component_registry.register(comp2)


def test_registry_multi_tenant_isolation():
    """Testa que os componentes cadastrados de um Tenant são isolados de outros Tenants."""
    component_registry.clear()
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    
    comp_a = ComponentFactory.create_component(type="KPI_CARD", name="KPI Receita", tenant_id=tenant_a)
    comp_b = ComponentFactory.create_component(type="KPI_CARD", name="KPI Receita", tenant_id=tenant_b)
    
    component_registry.register(comp_a)
    component_registry.register(comp_b)
    
    # Tenant A lista apenas os seus componentes
    list_a = component_registry.list_components(tenant_a)
    assert len(list_a) == 1
    assert list_a[0].id == comp_a.id
    
    # Tenant B lista apenas os seus componentes
    list_b = component_registry.list_components(tenant_b)
    assert len(list_b) == 1
    assert list_b[0].id == comp_b.id


# ── Component 2: Factory Tests ────────────────────────────────────────────────

def test_factory_predefined_configurations():
    """Testa as configurações predefinidas de acessibilidade, responsividade e animações pela Factory."""
    tenant_id = uuid.uuid4()
    
    # Cria Gráfico
    chart_comp = ComponentFactory.create_component(type="PIE", name="Participacao Canais", tenant_id=tenant_id)
    assert chart_comp.category == "CHARTS"
    assert chart_comp.accessibility_config["role"] == "img"
    assert chart_comp.responsiveness_config["priority"] == "ALTA"
    assert chart_comp.animation_config["enter_animation"] == "fade-in"
    assert "onExport" in chart_comp.allowed_events
    
    # Cria Skeleton de Status
    skeleton_comp = ComponentFactory.create_component(type="SKELETON", name="Loading Grid", tenant_id=tenant_id)
    assert skeleton_comp.category == "STATUS"
    assert skeleton_comp.state == "Loading"


# ── Component 3: Renderer & KPI Tests ──────────────────────────────────────────

def test_renderer_visual_elements_and_kpis():
    """Testa a renderização síncrona de componentes analíticos e KPIs pelo Renderer."""
    tenant_id = uuid.uuid4()
    component_registry.clear()
    
    datasets = {
        "vendas": {
            "metadata": {"view_name": "VW_VENDAS", "quantidade_registros": 20},
            "schema": {"regiao": "string", "valor": "float"},
            "data": [
                {"regiao": "Sul", "valor": 500.0},
                {"regiao": "Norte", "valor": 300.0}
            ]
        }
    }
    
    analytics_results = {
        "kpis": {
            "receita_total": {
                "valor_atual": 150000.00,
                "diferenca_absoluta": 15000.00,
                "variacao_percentual": 10.00,
                "direcao": "UP"
            }
        }
    }
    
    components = component_renderer.render_components(
        tenant_id=tenant_id,
        datasets=datasets,
        blueprint=None,
        visual_strategy={"primary_chart_type": "LINE"},
        theme_name="DARK",
        analytics_results=analytics_results
    )
    
    # Devem ser renderizados:
    # 1. Filtros (padrão)
    # 2. KPI Receita Total
    # 3. Tabela Vendas
    # 4. Gráfico Vendas (tipo LINE)
    assert len(components) == 4
    
    # Filtra por tipo
    kpi_comps = [c for c in components if c.type == "KPI_CARD"]
    assert len(kpi_comps) == 1
    assert kpi_comps[0].name == "RECEITA TOTAL"
    assert kpi_comps[0].data_snapshot["value"] == 150000.0
    
    # Verifica tema Dark injetado
    assert kpi_comps[0].theme_config["background_color"] == "#0F172A"


# ── Component 4: State Manager & Lifecycle Tests ──────────────────────────────

def test_state_transitions_and_destroyed_lock():
    """Testa transições de estados e travamento de componentes destruídos."""
    tenant_id = uuid.uuid4()
    comp = ComponentFactory.create_component(type="BAR", name="Vendas", tenant_id=tenant_id)
    assert comp.state == "Ready"
    
    # Transição permitida
    component_state_manager.transition_state(comp, "Updating")
    assert comp.state == "Updating"
    
    # Destrói o componente
    component_state_manager.transition_state(comp, "Destroyed")
    assert comp.state == "Destroyed"
    
    # Travamento de segurança: não pode mais alterar estado
    with pytest.raises(RuntimeError, match="Não é possível alterar o estado de um componente já destruído"):
        component_state_manager.transition_state(comp, "Ready")


def test_lifecycle_events():
    """Testa transições do ciclo de vida físico integradas a transições de estados."""
    tenant_id = uuid.uuid4()
    comp = ComponentFactory.create_component(type="BAR", name="Vendas", tenant_id=tenant_id)
    
    # Inicia fase REFRESH
    component_lifecycle.trigger_phase(comp, "REFRESH")
    assert comp.state == "Refreshing"
    assert comp.diagnostics["lifecycle_events"][-1]["phase"] == "REFRESH"


# ── Component 5: Cache & Events Tests ─────────────────────────────────────────

def test_component_level_cache():
    """Testa set, get, cache hit e hashes MD5 de dados no Component Cache."""
    component_cache.clear()
    tenant_id = uuid.uuid4()
    
    data_snapshot = [{"label": "Sul", "value": 50.0}]
    rendered_payload = {"id": "123", "name": "Gráfico"}
    
    # Cache miss inicial
    cached = component_cache.get(tenant_id, "BAR", "Gráfico Vendas", data_snapshot)
    assert cached is None
    
    # Salva no cache
    component_cache.set(tenant_id, "BAR", "Gráfico Vendas", data_snapshot, rendered_payload)
    
    # Cache hit
    cached = component_cache.get(tenant_id, "BAR", "Gráfico Vendas", data_snapshot)
    assert cached == rendered_payload


def test_component_events_binding():
    """Testa assinaturas de eventos válidos e recusa de não-suportados."""
    tenant_id = uuid.uuid4()
    comp = ComponentFactory.create_component(type="BAR", name="Vendas", tenant_id=tenant_id)
    
    # Bind de evento permitido
    component_events.bind_event(comp, "onExport", "/api/v1/export/vendas")
    assert comp.interaction_config["events"]["onExport"] == "/api/v1/export/vendas"
    
    # Recusa de evento não suportado (ex: Filtros no gráfico)
    with pytest.raises(ValueError, match="não é permitido para componentes do tipo BAR"):
        component_events.bind_event(comp, "onFilter", "/api/v1/filter")


# ── Component 6: Security & Diagnostics Tests ─────────────────────────────────

def test_tenant_boundary_checks():
    """Testa a restrição de acesso Multi-Tenant e barreira contra invasões cruzadas."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    
    comp_a = ComponentFactory.create_component(type="BAR", name="Vendas A", tenant_id=tenant_a)
    
    # Tenant A pode acessar seu próprio componente
    component_security.validate_tenant_scope(comp_a, tenant_a)
    
    # Tenant B tenta acessar componente do Tenant A e é bloqueado
    with pytest.raises(ScopeViolationError, match="Acesso cruzado de dados de empresas"):
        component_security.validate_tenant_scope(comp_a, tenant_b)


def test_enforce_user_role_permissions():
    """Testa controle de permissões por papéis de acesso no componente."""
    tenant_id = uuid.uuid4()
    comp = ComponentFactory.create_component(type="BAR", name="Vendas", tenant_id=tenant_id)
    comp.permissions = ["MANAGER", "ADMIN"]
    
    # ADMIN acessa normalmente
    component_security.enforce_permissions(comp, "ADMIN")
    
    # USER é bloqueado com 403
    with pytest.raises(HTTPException) as exc_info:
        component_security.enforce_permissions(comp, "USER")
    assert exc_info.value.status_code == 403


def test_xss_sanitization():
    """Testa a sanitização contra injeção de HTML e scripts maliciosos (XSS)."""
    tenant_id = uuid.uuid4()
    malicious_title = "<script>alert('XSS')</script>Gráfico Vendas"
    malicious_event = "javascript:alert('Hack')"
    
    comp = ComponentFactory.create_component(type="BAR", name=malicious_title, tenant_id=tenant_id)
    component_events.bind_event(comp, "onExport", malicious_event)
    
    # Executa sanitização de segurança
    component_security.sanitize_component(comp)
    
    # Gráfico foi higienizado contra tags HTML
    assert "&lt;script&gt;" in comp.name
    assert "Gráfico Vendas" in comp.name
    
    # Callback malicioso de javascript: removido do dicionário de eventos
    assert "onExport" not in comp.interaction_config.get("events", {})


def test_component_diagnostics():
    """Testa auditoria do diagnóstico interno gerando Health/Quality scores."""
    tenant_id = uuid.uuid4()
    comp = ComponentFactory.create_component(type="BAR", name="Vendas", tenant_id=tenant_id)
    
    # Modifica integridade
    comp.diagnostics["errors"].append("Conexão falhou")
    comp.accessibility_config["aria_label"] = "" # Sem label de acessibilidade
    
    component_diagnostics.run_diagnostics(comp)
    
    assert comp.diagnostics["health_score"] < 1.0
    assert comp.diagnostics["quality_score"] < 1.0


# ── Component 7: Telemetry & Facade Integration ───────────────────────────────

@pytest.mark.asyncio
async def test_facade_render_layout_flow():
    """Testa fluxo completo de renderização do ECE Facade e telemetria gerada."""
    tenant_id = uuid.uuid4()
    component_registry.clear()
    component_cache.clear()
    
    datasets = {
        "vendas": {
            "metadata": {"view_name": "VW_VENDAS", "quantidade_registros": 5},
            "schema": {"data": "string", "valor": "float"},
            "data": [{"data": "2026-07-08", "valor": 100.0}]
        }
    }
    
    # 1. Renderiza primeira vez (Cache MISS)
    layout1 = enterprise_component_engine.render_dashboard_layout(
        tenant_id=tenant_id,
        datasets=datasets,
        blueprint=None,
        theme_name="CORPORATIVO"
    )
    assert len(layout1) == 3 # Filtro, Tabela, Gráfico
    
    report1 = enterprise_component_engine.get_telemetry_report(tenant_id)
    assert len(report1) == 1
    assert report1[0]["cache_hit"] is False
    
    # 2. Renderiza segunda vez com mesmos dados (Cache HIT)
    layout2 = enterprise_component_engine.render_dashboard_layout(
        tenant_id=tenant_id,
        datasets=datasets,
        blueprint=None,
        theme_name="CORPORATIVO"
    )
    assert len(layout2) == 3
    
    report2 = enterprise_component_engine.get_telemetry_report(tenant_id)
    assert len(report2) == 2
    assert report2[1]["cache_hit"] is True
