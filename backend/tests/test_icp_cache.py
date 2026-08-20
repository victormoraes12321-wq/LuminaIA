"""
Testes unitários e de integração — Intelligent Caching Platform (ICP)
---------------------------------------------------------------------
Verifica conformidade corporativa:
- Hit/Miss e reutilização
- Invalidação seletiva por pattern, namespace e dependências de view
- Isolamento Multi-Tenant estrito
- Otimização de cache (evicção LFU/Custo)
- Thread-safety (concorrência)
"""
import uuid
import time
import pytest
import threading
from services.cache_service import IntelligentCachingPlatform

def test_icp_basic_hit_miss():
    """Valida fluxo básico de set e get com hit/miss."""
    icp = IntelligentCachingPlatform(max_items=10)
    tenant_id = uuid.uuid4()
    
    # Cache Miss inicial
    assert icp.get(tenant_id, "query", "key1") is None
    
    # Insere e valida Hit
    icp.set(tenant_id, "query", "key1", {"resultado": "ok"}, cost_ms=100.0)
    assert icp.get(tenant_id, "query", "key1") == {"resultado": "ok"}
    
    # Valida estatísticas
    stats = icp.get_statistics()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["total_time_saved_ms"] == 100.0

def test_icp_multi_tenant_isolation():
    """Garante isolamento absoluto de cache entre tenants diferentes (Multi-Tenant)."""
    icp = IntelligentCachingPlatform()
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    key = "faturamento_2026"
    
    icp.set(tenant_a, "kpi", key, 500000.0)
    icp.set(tenant_b, "kpi", key, 1200000.0)
    
    # Cada um deve recuperar apenas o seu respectivo valor
    assert icp.get(tenant_a, "kpi", key) == 500000.0
    assert icp.get(tenant_b, "kpi", key) == 1200000.0

def test_icp_selective_invalidation():
    """Testa invalidação seletiva e dependências de view analítica."""
    icp = IntelligentCachingPlatform()
    tenant_id = uuid.uuid4()
    
    # Registra dois itens dependendo da view VW_VENDAS
    icp.set(tenant_id, "query", "q1", "dados_vendas", dependencies=["VW_VENDAS"])
    icp.set(tenant_id, "query", "q2", "dados_faturamento", dependencies=["VW_FATURAMENTO"])
    
    # Invalida apenas o dependente de VW_VENDAS
    icp.invalidate_by_dependency("VW_VENDAS")
    
    assert icp.get(tenant_id, "query", "q1") is None
    assert icp.get(tenant_id, "query", "q2") == "dados_faturamento"

def test_icp_optimizer_eviction():
    """Valida a evicção inteligente baseada em score do Cache Optimizer."""
    # Instancia ICP com limite de 2 itens
    icp = IntelligentCachingPlatform(max_items=2)
    tenant_id = uuid.uuid4()
    
    # Insere item 1 (caro de gerar)
    icp.set(tenant_id, "query", "item1", "valor1", cost_ms=1000.0) # score alto
    # Insere item 2 (barato de gerar)
    icp.set(tenant_id, "query", "item2", "valor2", cost_ms=10.0)
    
    # Simula hits no item 1 para aumentar a prioridade dele
    icp.get(tenant_id, "query", "item1")
    icp.get(tenant_id, "query", "item1")
    
    # Insere item 3, forçando evicção de um item
    icp.set(tenant_id, "query", "item3", "valor3", cost_ms=100.0)
    
    # O item 2 (mais barato e com menos hits) deve ter sido evitado/removido
    assert icp.get(tenant_id, "query", "item1") == "valor1"
    assert icp.get(tenant_id, "query", "item2") is None
    assert icp.get(tenant_id, "query", "item3") == "valor3"

def test_icp_thread_safety_concurrency():
    """Testa concorrência e integridade em acessos paralelos multi-thread."""
    icp = IntelligentCachingPlatform(max_items=1000)
    tenant_id = uuid.uuid4()
    
    def worker(worker_id):
        for i in range(100):
            icp.set(tenant_id, "query", f"key_{worker_id}_{i}", f"value_{i}")
            icp.get(tenant_id, "query", f"key_{worker_id}_{i}")
            
    threads = []
    for t_id in range(10):
        t = threading.Thread(target=worker, args=(t_id,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    stats = icp.get_statistics()
    assert stats["active_items"] <= 1000
