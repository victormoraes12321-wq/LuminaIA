"""
Testes de Unidade e Integração — Performance Optimization Platform (POP)
-------------------------------------------------------------------------
Verifica governança de performance, otimização de CPU/Memória,
concorrência do Scheduler e precisão do Performance Center.
"""
import uuid
import pytest
import asyncio
from unittest.mock import AsyncMock
from services.performance.performance_optimization_platform import pop_platform

def test_pop_query_normalization():
    """Valida normalização e remoção de espaços pelo Query Optimizer."""
    raw_sql = "  SELECT   id,   nome   FROM   VW_VENDAS   WHERE   ano = 2026   "
    expected = "select id, nome from vw_vendas where ano = 2026"
    
    optimized = pop_platform.normalize_and_optimize_query(raw_sql)
    assert optimized == expected

def test_pop_ia_optimizer():
    """Valida decisão do IA Optimizer para evitar chamadas de NLU redundantes."""
    tenant_id = uuid.uuid4()
    nlu_cache_key = "intent_cache_vendas_mes"
    
    # Simula inserção prévia de intenções no cache global
    from services.cache_service import global_cache
    global_cache.set(tenant_id, "nlu", nlu_cache_key, {"intent": "vendas", "status": "approved"})
    
    # Executa verificação da POP
    should_run, cached_val = pop_platform.should_execute_ia(tenant_id, "Vendas deste mês", nlu_cache_key)
    
    assert should_run is False
    assert cached_val == {"intent": "vendas", "status": "approved"}

def test_pop_memory_optimizer():
    """Testa liberação e otimização automática de memória."""
    res = pop_platform.optimize_memory()
    assert "current_memory_mb" in res
    assert "garbage_collected_objects" in res
    assert res["status"] in ("NORMAL", "WARNING")

@pytest.mark.asyncio
async def test_pop_scheduler_concurrency():
    """Valida que o Concurrency Manager e o Semaphore do Scheduler limitam tarefas simultâneas."""
    # Instancia POP com limite de 2 concorrências
    from services.performance.performance_optimization_platform import PerformanceOptimizationPlatform
    pop = PerformanceOptimizationPlatform(concurrency_limit=2)
    
    active_tasks = 0
    max_parallel_tasks = 0
    
    async def mock_sync_job():
        nonlocal active_tasks, max_parallel_tasks
        active_tasks += 1
        max_parallel_tasks = max(max_parallel_tasks, active_tasks)
        await asyncio.sleep(0.05)
        active_tasks -= 1
        return "SUCCESS"
        
    tenant_id = uuid.uuid4()
    # Aciona 5 jobs em paralelo sob a governança da POP
    jobs = [
        pop.execute_optimized_sync(tenant_id, mock_sync_job),
        pop.execute_optimized_sync(tenant_id, mock_sync_job),
        pop.execute_optimized_sync(tenant_id, mock_sync_job),
        pop.execute_optimized_sync(tenant_id, mock_sync_job),
        pop.execute_optimized_sync(tenant_id, mock_sync_job)
    ]
    
    results = await asyncio.gather(*jobs)
    
    assert len(results) == 5
    # O limite de concorrência é 2, logo nunca deve ter havido mais de 2 tarefas paralelas ao mesmo tempo
    assert max_parallel_tasks <= 2

def test_pop_performance_score_calculation():
    """Valida cálculo dinâmico do score de performance com base em latências de módulo."""
    from services.performance.performance_optimization_platform import PerformanceOptimizationPlatform
    pop = PerformanceOptimizationPlatform()
    
    # Latências normais -> Score alto
    pop.record_latency("ia", 1200.0)
    pop.record_latency("backend", 50.0)
    pop.record_latency("data_platform", 100.0)
    
    score_bom = pop.calculate_performance_score()
    assert score_bom == 100.0
    
    # Cria um novo monitor e adiciona latências elevadas -> Score reduzido
    pop_ruim = PerformanceOptimizationPlatform()
    pop_ruim.record_latency("ia", 3500.0)
    pop_ruim.record_latency("backend", 650.0)
    pop_ruim.record_latency("data_platform", 900.0)
    
    score_ruim = pop_ruim.calculate_performance_score()
    assert score_ruim < 100.0

def test_pop_report_observability():
    """Valida que o relatório técnico para o Performance Center contém todos os metadados."""
    report = pop_platform.get_performance_center_report()
    
    assert "health_score_geral" in report
    assert "performance_score" in report
    assert "avg_latencies_ms" in report
    assert "engine_health_scores" in report
    assert "system_resources" in report
    assert "cache_efficiency" in report
