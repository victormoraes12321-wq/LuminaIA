"""
LuminaAI — Test Suite: Adaptive Dashboard Engine (ADE)
------------------------------------------------------
Cobertura de testes automatizados completa do motor adaptável ADE.
"""
from __future__ import annotations

import uuid
import pytest
from fastapi import HTTPException

from services.context_guard import ScopeViolationError
from services.data_platform.adaptive_dashboard_engine.schemas import DashboardLayoutSchema
from services.data_platform.adaptive_dashboard_engine.interpreter import blueprint_interpreter
from services.data_platform.adaptive_dashboard_engine.grid_engine import adaptive_grid_engine
from services.data_platform.adaptive_dashboard_engine.personalization import personalization_engine
from services.data_platform.adaptive_dashboard_engine.optimizer import rendering_optimizer
from services.data_platform.adaptive_dashboard_engine.diagnostics import dashboard_diagnostics
from services.data_platform.adaptive_dashboard_engine.security import dashboard_security
from services.data_platform.adaptive_dashboard_engine import adaptive_dashboard_engine


# ── Component 1: Interpreter Tests ───────────────────────────────────────────

def test_interpreter_hierarchy_sorting():
    """Testa a ponderação e hierarquização de componentes com base no tipo e categoria."""
    components = [
        {"id": "comp-table-1", "category": "TABLES", "type": "TABLE"},
        {"id": "comp-kpi-1", "category": "KPI", "type": "KPI_CARD"},
        {"id": "comp-filter-1", "category": "CONTROLS", "type": "FILTROS"},
        {"id": "comp-chart-1", "category": "CHARTS", "type": "BAR"}
    ]
    
    hierarchy = blueprint_interpreter.interpret_hierarchy(
        blueprint=None,
        components=components,
        visual_strategy={"primary_chart_type": "BAR"}
    )
    
    # Devem ser retornados ordenados por peso:
    # 1. KPI (Recebe maior peso)
    # 2. FILTROS (Recebe peso de controles de topo)
    # 3. Gráfico de BAR (tipo primário da estratégia visual)
    # 4. Tabela (Peso menor de final de leitura)
    assert len(hierarchy) == 4
    ordered_ids = [item[0] for item in hierarchy]
    assert ordered_ids[0] == "comp-kpi-1"
    assert ordered_ids[1] == "comp-filter-1"
    assert ordered_ids[2] == "comp-chart-1"
    assert ordered_ids[3] == "comp-table-1"


# ── Component 2: Grid Engine Tests ────────────────────────────────────────────

def test_grid_engine_packing_no_overlap():
    """Testa o empacotamento 2D dinâmico gerando coordenadas válidas sem sobreposições."""
    tenant_id = uuid.uuid4()
    components = [
        {
            "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
            "category": "KPI",
            "type": "KPI_CARD",
            "responsiveness_config": {
                "priority": "ALTA",
                "breakpoints": {
                    "desktop": {"cols": 4, "rows": 2}
                }
            }
        },
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
            "category": "KPI",
            "type": "KPI_CARD",
            "responsiveness_config": {
                "priority": "ALTA",
                "breakpoints": {
                    "desktop": {"cols": 4, "rows": 2}
                }
            }
        },
        {
            "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
            "category": "TABLES",
            "type": "TABLE",
            "responsiveness_config": {
                "priority": "BAIXA",
                "breakpoints": {
                    "desktop": {"cols": 12, "rows": 4}
                }
            }
        }
    ]
    
    layouts = adaptive_grid_engine.compute_layouts(components, blueprint=None)
    desktop_layout = layouts.get("desktop", [])
    
    # Devem ser posicionados os 3 componentes
    assert len(desktop_layout) == 3
    
    # KPIs devem estar na primeira linha (y=0) lado a lado
    # Componente 1: x=0, y=0, w=4, h=2
    # Componente 2: x=4, y=0, w=4, h=2
    # Tabela: x=0, y=2, w=12, h=4 (ocupa a largura inteira abaixo deles)
    comp1 = next(p for p in desktop_layout if p.component_id == uuid.UUID("11111111-1111-1111-1111-111111111111"))
    comp2 = next(p for p in desktop_layout if p.component_id == uuid.UUID("22222222-2222-2222-2222-222222222222"))
    comp3 = next(p for p in desktop_layout if p.component_id == uuid.UUID("33333333-3333-3333-3333-333333333333"))
    
    assert comp1.x == 0
    assert comp1.y == 0
    assert comp2.x == 4
    assert comp2.y == 0
    assert comp3.x == 0
    assert comp3.y == 2


# ── Component 3: Personalization & Optimizer Tests ────────────────────────────

def test_personalization_visibility_and_ordering():
    """Testa ocultação e reordenação de componentes baseando-se em preferências do usuário."""
    components = [
        {"id": "comp-1", "name": "Gráfico Vendas"},
        {"id": "comp-2", "name": "Tabela Lucro"},
        {"id": "comp-3", "name": "KPI Visitas"}
    ]
    
    prefs = {
        "hidden_components": ["comp-2"], # Oculta tabela
        "component_order": ["comp-3", "comp-1"], # KPI visitas no topo, depois vendas
        "theme_override": "DARK"
    }
    
    customized, applied = personalization_engine.apply_preferences(components, prefs)
    
    assert applied is True
    assert len(customized) == 2
    assert customized[0]["id"] == "comp-3"
    assert customized[1]["id"] == "comp-1"
    assert customized[0]["theme_config"]["theme_override"] == "DARK"


def test_optimizer_metrics():
    """Testa cálculo de telemetria de otimizações de CPU, FPS e economia."""
    components = [
        {"state": "Ready", "diagnostics": {"health_score": 1.0, "quality_score": 1.0}},
        {"state": "Ready", "diagnostics": {"health_score": 1.0, "quality_score": 1.0}}
    ]
    
    report = rendering_optimizer.evaluate_optimization(
        render_time_ms=5.0, # Muito rápido (<16ms)
        components=components,
        cache_hit=False
    )
    
    assert report["fps"] == 60
    assert report["avoided_renders_count"] == 2
    assert report["rendering_efficiency"] > 0.0


# ── Component 4: Security & Diagnostics Tests ─────────────────────────────────

def test_security_tenant_isolation_and_xss():
    """Testa restrições de Multi-Tenant e sanitização contra HTML malicioso em ADE."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    
    # 1. Multi-Tenant
    dashboard_security.validate_tenant_isolation(tenant_a, tenant_a)
    with pytest.raises(ScopeViolationError, match="cruzamento de dados de empresas"):
        dashboard_security.validate_tenant_isolation(tenant_a, tenant_b)
        
    # 2. XSS
    malicious = {
        "title": "<script>alert('hack')</script>Dashboard",
        "nested": {"key": "javascript:alert('malicious')"}
    }
    dashboard_security.sanitize_payload(malicious)
    assert "&lt;script&gt;" in malicious["title"]
    assert malicious["nested"]["key"] == "" # Removido!


def test_diagnostics_global_scores():
    """Testa auditoria diagnóstica geral agregando scores e warnings dos componentes."""
    components = [
        {"name": "Comp A", "diagnostics": {"health_score": 0.8, "quality_score": 0.9, "warnings": ["Aviso A"], "errors": []}},
        {"name": "Comp B", "diagnostics": {"health_score": 1.0, "quality_score": 1.0, "warnings": [], "errors": []}}
    ]
    
    report = dashboard_diagnostics.run_diagnostics(components, personalization_applied=True, render_time_ms=10.0)
    
    assert report["health_score"] == 0.90 # (0.8 + 1.0) / 2
    assert len(report["warnings"]) == 1


# ── Component 5: Facade Integration Test ──────────────────────────────────────

def test_facade_dashboard_assembly():
    """Testa o fluxo integrado de montagem do layout adaptável de dashboard via Facade."""
    tenant_id = uuid.uuid4()
    
    components = [
        {
            "id": uuid.uuid4(),
            "name": "Filtro Data",
            "category": "CONTROLS",
            "type": "FILTROS",
            "responsiveness_config": {"priority": "ALTA", "breakpoints": {}},
            "diagnostics": {"health_score": 1.0, "quality_score": 1.0}
        },
        {
            "id": uuid.uuid4(),
            "name": "Gráfico Vendas",
            "category": "CHARTS",
            "type": "BAR",
            "responsiveness_config": {"priority": "MEDIA", "breakpoints": {}},
            "diagnostics": {"health_score": 1.0, "quality_score": 1.0}
        }
    ]
    
    payload = adaptive_dashboard_engine.assemble_dashboard_layout(
        tenant_id=tenant_id,
        ece_components=components,
        blueprint=None,
        visual_strategy={"primary_chart_type": "BAR"},
        theme_name="CORPORATIVO",
        user_role="ADMIN"
    )
    
    assert payload["state"] == "Ready"
    assert len(payload["grid_layouts"]["desktop"]) == 2
    assert len(payload["components"]) == 2
    
    telemetry = adaptive_dashboard_engine.get_observability_report(tenant_id)
    assert len(telemetry) == 1
    assert telemetry[0]["components_count"] == 2
