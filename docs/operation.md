# Guia de Operação e Runbooks — LuminaAI V2 RC4

Este documento reúne os procedimentos operacionais padrão, rotinas de monitoramento, gestão de incidentes e referências para os runbooks especializados do **LuminaAI V2 RC4**.

---

## 1. Monitoramento e Verificação de Saúde (Health Checks)

| Serviço | Endpoint | Método | Objetivo | Status Esperado |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Liveness** | `/health` | `GET` | Verifica se o processo FastAPI está ativo e respondendo | `HTTP 200 {"status": "healthy"}` |
| **Backend Readiness** | `/health/deep` | `GET` | Diagnóstico profundo de PostgreSQL, pool, IA e migrações | `HTTP 200` com status de componentes |
| **Frontend Health** | `/healthz` | `GET` | Endpoint de integridade do container Next.js | `HTTP 200 {"status": "healthy"}` |
| **Nginx Proxy** | `/nginx-health` | `GET` | Verificação do servidor web Nginx | `HTTP 200 "healthy\n"` |

### Diagnóstico Rápido via Terminal
```bash
# Liveness do Backend
curl -s -f http://127.0.0.1:8000/health

# Readiness do Backend
curl -s -f http://127.0.0.1:8000/health/deep

# Health do Frontend
curl -s -f http://127.0.0.1:3000/healthz
```

---

## 2. Rotinas de Backup e Restauração

### Execução de Backup Automatizado
O script `scripts/backup-db.sh` executa o dump comprimido do banco principal com retenção de 7 dias:
```bash
# Executar backup manual
./scripts/backup-db.sh
```

### Restauração Segura (Disaster Recovery)
O script `scripts/restore-db.sh` realiza a restauração transacional em base isolada:
```bash
# Restaurar backup em banco isolado
./scripts/restore-db.sh /var/backups/luminaai/luminaai_db_20260817_120000.sql.gz
```

---

## 3. Gestão de Incidentes e Kill Switches

Em caso de degradação severa, anomalia matemática ou falha de segurança:

1. **Ativar Kill Switch Global de Emergência:**
   Definir no arquivo de ambiente (`.env` ou `.env.preprod`):
   ```bash
   V2_GLOBAL_EMERGENCY_DISABLE=true
   ```
2. **Recarregar Serviços sem Downtime:**
   ```bash
   docker compose -f docker-compose.preprod.yml exec nginx nginx -s reload
   ```
3. **Verificar Logs Estruturados:**
   ```bash
   docker compose -f docker-compose.preprod.yml logs --tail=200 backend-1 backend-2
   ```

---

## 4. Índice de Runbooks Operacionais V2

Os runbooks especializados estão disponíveis no diretório `docs/operation/`:

- [Plano de Rollout de Produção V2](operation/PRODUCTION_ROLLOUT_PLAN_V2.md)
- [Runbook de Rollback e Gestão de Incidentes V2](operation/ROLLBACK_AND_INCIDENT_RUNBOOK_V2.md)
- [Runbook de Governança da Base de Conhecimento](operation/KNOWLEDGE_GOVERNANCE_RUNBOOK.md)
- [Runbook de Retenção e Estado Conversacional](operation/CONVERSATION_RETENTION_RUNBOOK.md)
- [Runbook de Privacidade e Perfil do Usuário](operation/USER_PROFILE_PRIVACY_RUNBOOK.md)
- [Runbook de Triagem de Feedback Supervisionado](operation/FEEDBACK_REVIEW_AND_DATASET_RUNBOOK.md)
- [Runbook de Recuperação Semântica e Entidades](operation/SEMANTIC_INDEX_AND_ENTITY_RESOLUTION_RUNBOOK.md)
- [Runbook de Backend Governado de Dashboards](operation/GOVERNED_DASHBOARD_BACKEND_RUNBOOK.md)
- [Runbook de Assistência de IA em Dashboards](operation/DASHBOARD_AI_ASSISTANCE_RUNBOOK.md)
- [Runbook de Insights Pós-Sincronização](operation/POST_SYNC_INSIGHTS_RUNBOOK.md)
- [Runbook de Observabilidade, Métricas e Avaliações](operation/OBSERVABILITY_METRICS_EVALUATIONS_RUNBOOK.md)
- [Runbook de Filas de Trabalho e Performance](operation/SCALE_QUEUES_PERFORMANCE_RUNBOOK.md)
- [Runbook de Rollout Seguro e Migrações](operation/SECURITY_MIGRATION_ROLLOUT_RUNBOOK.md)
