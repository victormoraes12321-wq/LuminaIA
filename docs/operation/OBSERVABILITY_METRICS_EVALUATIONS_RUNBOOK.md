# Runbook Operacional — Observabilidade e Suítes de Avaliação V2

- **Serviço:** LuminaAI Observability & Evaluations V2
- **Versão:** `lumina.observability-metrics-evaluations/1.0`

---

## 1. Ativação Gradual de Modos Operacionais

Por padrão em produção, o sistema opera em modo desativado `OBSERVABILITY_MODE="LEGACY_ONLY"`.

Para progredir o ambiente em rollout seguro:

1. **Modo Shadow (Somente Coleta Interna):**
   ```env
   OBSERVABILITY_MODE="SHADOW"
   OBSERVABILITY_APIS_ENABLED=false
   OBSERVABILITY_FRONTEND_ENABLED=false
   ```

2. **Modo Métricas (APIs Habilitadas para Admin):**
   ```env
   OBSERVABILITY_MODE="V2_METRICS"
   OBSERVABILITY_APIS_ENABLED=true
   OBSERVABILITY_FRONTEND_ENABLED=true
   ```

3. **Modo Avaliações e Governança Plena:**
   ```env
   OBSERVABILITY_MODE="V2_GOVERNED"
   OBSERVABILITY_APIS_ENABLED=true
   OBSERVABILITY_FRONTEND_ENABLED=true
   ```

---

## 2. Diagnóstico de Degradabilidade e Falhas em SLOs

Quando o painel `/admin/observability` sinalizar status `AT_RISK` ou `UNHEALTHY`:

1. Verifique os Error Budgets restantes de cada SLO;
2. Se a latência p95 exceder a meta (SLO `slo_query_latency`), analise o tempo de execução no clone analítico PostgreSQL;
3. Se a taxa de disponibilidade indicar erros 5xx (SLO `slo_request_success`), consulte os logs sanitizados com a correlação de `trace_id`.

---

## 3. Execução Manual de Suítes de Avaliação

Em tarefas de homologação antes de deploys operacionais:

1. Acesse o painel `/admin/evaluations`;
2. Clique no botão "Executar" ao lado da suíte desejada (ex.: `SECURITY`, `TENANT_ISOLATION`);
3. Se qualquer caso registrar resultado `FAIL`, o painel indicará a regressão detectada contra o baseline de código certificado (`880477a980aeaef840ac0a5c66f8541eb6c7c349`).
