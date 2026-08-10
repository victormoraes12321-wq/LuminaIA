# Especificação Contratual — Observabilidade, Métricas Operacionais e Avaliações V2

- **Versão Canônica:** `lumina.observability-metrics-evaluations/1.0`
- **Feature Flag:** `OBSERVABILITY_MODE` (valores: `LEGACY_ONLY`, `SHADOW`, `V2_METRICS`, `V2_EVALUATIONS`, `V2_GOVERNED`)
- **Padrão em Produção:** `LEGACY_ONLY`

---

## 1. Visão Geral

O contrato `lumina.observability-metrics-evaluations/1.0` governa a telemetria estruturada, rastreamento de correlação (`trace_id`, `span_id`), cálculo determinístico de métricas operacionais e SLIs/SLOs, além da execução automatizada de 19 suítes de avaliação determinísticas para prever regressões de qualidade, segurança e multitenancy.

---

## 2. Estrutura de Contratos Pydantic v2

Os schemas Pydantic v2 estritos com `extra = "forbid"` estão definidos em:
- `backend/contracts/observability_v2/enums.py`
- `backend/contracts/observability_v2/models.py`

Schemas JSON exportados para verificação externa em:
- `docs/contracts/observability_v2/schemas/`

---

## 3. Redação e Segurança de Dados

A redação `ObservabilityRedactionService` sanitiza:
- Passwords, secrets, tokens, bearer headers, cookies e API keys;
- SQL bruto, parâmetros de bind e connection strings;
- Prompts de sistema e respostas brutas da IA;
- Dados sensíveis e PII.

---

## 4. Proteção de Cardinalidade

O `OperationalMetricCardinalityGuard` impõe:
- Allowlist fixa por metrica operacional;
- Truncamento de rótulos para no máximo 64 caracteres;
- Mapeamento de UUIDs ou rótulos não permitidos para `"OTHER"`;
- Proteção estrita contra explosão de cardinalidade em bancos de dados e TSDBs.

---

## 5. Suítes de Avaliação (19 Suítes Gobernadas)

1. `SECURITY`: Prompt injection, vazamento de segredos, isolamento.
2. `TENANT_ISOLATION`: Garantia de segregação de tenant por sessão e query.
3. `REPRODUCIBILITY`: Idempotência de respostas e seeds deterministicos.
4. `DETERMINISTIC_SQL`: Validação de compilação SQL sem mutação.
5. `ACCURACY`: Precisão matemática financeira e Decimal.
6. `FINANCIAL_MATH`: Arredondamento HALF_UP e baseline zero.
7. `SLI_SLO_COMPLIANCE`: Cálculo de erro acumulado e orçamentos.
8. `RBAC_AUTHORIZATION`: Restrições por perfis ADMIN, GESTOR, CONSULTA.
9. `PROVENANCE_AUDIT`: Rastreabilidade de origens de dados e visualizações.
10. `TIME_WINDOW`: Janelas temporais relativas e absolutas.
11. `COMPARISON_PLANNING`: Validação de QueryPlanV2 comparativos.
12. `COMPARISON_PRESENTATION`: Preservação de ordens e participações visuais.
13. `KNOWLEDGE_BASE`: Respeito a estados PUBLISHED da base empresarial.
14. `USER_PROFILE`: Respeito a preferências ativas com pedido explícito.
15. `POST_SYNC_INSIGHTS`: Validação do feed pós-sincronização.
16. `SMART_CACHE`: Invalidação e revalidação determinística de cache.
17. `DASHBOARD_V2`: Validação contratual declarativa de dashboards.
18. `LATENCY_BUDGET`: Orçamentos de latência e SLAs operacionais.
19. `RECOVERY_CIRCUIT`: Fallbacks seguros e fail-closed behavior.
# Extensão de segurança Prompt 26

O registry passa a incluir sete suites determinísticas: authorization, tenant
isolation, API input, secret leakage, error sanitization, rollout guard e migration
compatibility. Eventos de bloqueio são `RESTRICTED_OPERATIONAL`; métricas de security
e rollout usam apenas labels fechadas, sem tenant/user/request/resource IDs.
