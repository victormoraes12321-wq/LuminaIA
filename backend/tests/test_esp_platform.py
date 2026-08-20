"""
Testes de Unidade e Integração — Enterprise Security Platform (ESP)
---------------------------------------------------------------------
Verifica conformidade OWASP/LGPD:
- Isolamento Multi-Tenant estrito
- Row Level Security (RLS) no banco analítico
- Prevenção contra SQL Injection, XSS, SSRF e Path Traversal
- Controle de Sessões e Rate Limiting
- Backups criptografados e restore auditado
- Monitoramento de incidentes e cálculo de Security Score
"""
import uuid
import pytest
from services.security.enterprise_security_platform import esp_platform

def test_esp_tenant_isolation():
    """Valida que o Tenant Isolation Engine bloqueia acessos cross-tenant."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    
    # Acesso ao próprio tenant deve ser permitido
    esp_platform.enforce_tenant_isolation(tenant_a, tenant_a)
    
    # Acesso cross-tenant deve lançar exceção 403
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        esp_platform.enforce_tenant_isolation(tenant_a, tenant_b)
    assert exc.value.status_code == 403

def test_esp_row_level_security():
    """Valida aplicação automática de RLS para isolamento analítico."""
    query_sem_rls = "SELECT * FROM fat_vendas WHERE valor > 1000"
    tenant_id = uuid.uuid4()
    
    query_com_rls = esp_platform.apply_row_level_security(query_sem_rls, tenant_id)
    assert "tenant_id =" in query_com_rls
    assert str(tenant_id) in query_com_rls

def test_esp_xss_protection():
    """Valida sanitização de strings contra ataques XSS (injeção de scripts)."""
    malicious = "<script>alert('hack')</script><b>Texto Seguro</b>"
    clean = esp_platform.sanitize_input(malicious)
    assert "<script>" not in clean
    assert "Texto Seguro" in clean

def test_esp_sql_injection_protection():
    """Valida que tentativas de SQL Injection são detectadas e bloqueadas."""
    malicious_sql = "SELECT * FROM usuarios WHERE email = 'a' OR 1=1; DROP TABLE logs;"
    with pytest.raises(ValueError) as exc:
        esp_platform.protect_query_injection(malicious_sql)
    assert "bloqueada pelo Enterprise Security Engine" in str(exc.value)

def test_esp_ssrf_protection():
    """Valida bloqueio de requisições maliciosas SSRF contra hosts internos ou metadata."""
    local_url = "http://169.254.169.254/latest/meta-data/"
    with pytest.raises(ValueError) as exc:
        esp_platform.prevent_ssrf(local_url)
    assert "Conexão externa rejeitada" in str(exc.value)

def test_esp_path_traversal_protection():
    """Valida bloqueio de tentativas de directory traversal."""
    malicious_path = "../../../etc/passwd"
    with pytest.raises(ValueError) as exc:
        esp_platform.prevent_path_traversal(malicious_path)
    assert "Caminho de arquivo rejeitado" in str(exc.value)

def test_esp_rate_limiter():
    """Valida controle e limites do Rate Limiter de segurança."""
    client_key = "192.168.1.55"
    
    # Simula requisições sob o limite
    for _ in range(5):
        assert esp_platform.check_rate_limit(client_key) is True
        
    # Força estouro de limite injetando timestamps fictícios no store
    from services.security.enterprise_security_platform import RATE_LIMIT_MAX_REQUESTS
    import time
    esp_platform._rate_limiter_store[client_key] = [time.time()] * (RATE_LIMIT_MAX_REQUESTS + 5)
    
    # Deve ser bloqueado
    assert esp_platform.check_rate_limit(client_key) is False

def test_esp_backup_and_restore():
    """Valida integridade e auditoria de backups criptografados e restores."""
    payload = {"meta": "schema_v1", "roles": ["ADMIN"]}
    
    # Cria backup criptografado
    backup_str = esp_platform.perform_secured_backup(payload)
    assert len(backup_str) > 0
    
    # Restaura backup e valida integridade
    restored = esp_platform.perform_secured_restore(backup_str)
    assert restored == payload

def test_esp_security_score_and_report():
    """Valida cálculo do Security Score e consolidação no Security Center."""
    # Reseta incidentes e rate limiters
    esp_platform._incidents.clear()
    esp_platform._rate_limiter_store.clear()
    
    # Score inicial deve ser 100
    assert esp_platform.calculate_security_score() == 100.0
    
    # Simula um incidente
    esp_platform.register_incident("XSS_ATTEMPT", "IP_TEST", {})
    
    # Score deve sofrer redução
    score_pos = esp_platform.calculate_security_score()
    assert score_pos < 100.0
    
    # Relatório deve conter metadados e logs
    report = esp_platform.get_security_center_report()
    assert report["security_score"] == score_pos
    assert report["compliance"]["owasp_top_10"] == "COMPLIANT"
    assert len(report["recent_incidents"]) > 0
