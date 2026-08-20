# Guia de Manutenção — LuminaAI V2 RC4

Este documento reúne diretrizes para manutenção preventiva, aplicação de migrações de banco de dados, atualização de dependências e sustentação da integridade do **LuminaAI V2 RC4**.

---

## 1. Ciclo de Vida de Migrações (v1 a v26)

A cadeia de migrações do LuminaAI V2 segue o padrão *Expand-Contract* (aditivo e retrocompatível):

| Migração | Módulo / Escopo | Tabelas / Capacidades |
| :--- | :--- | :--- |
| `v12_0.py` | Estado Conversacional | Sessões, nós de diálogo, snapshots e eventos (`lumina.conversation-state/1.0`) |
| `v13_0.py` | Base de Conhecimento | Conceitos, KPIs, aliases e governança imutável (`lumina.enterprise-knowledge/1.0`) |
| `v14_0.py` | Perfil Analítico | Preferências, defaults e consentimentos de usuário (`lumina.user-analytical-profile/1.0`) |
| `v15_0.py` | Feedback Supervisionado | Avaliações, correções, manifestos e datasets (`lumina.supervised-feedback/1.0`) |
| `v16_0.py` | Recuperação Semântica | Índices lexicais, snapshots e resolução canônica (`lumina.semantic-retrieval/1.0`) |
| `v21_0.py` | Smart Cache & Materializações | Políticas de cache, gerações e snapshots analíticos (`lumina.smart-cache/1.0`) |
| `v22_0.py` | Backend de Dashboards V2 | Revisões imutáveis, publicações por CAS e colaboração (`lumina.dashboard-backend/1.0`) |
| `v23_0.py` | Assistência de IA em Dashboards | Propostas de IA, validações e workflows de aprovação (`lumina.dashboard-ai/1.0`) |
| `v24_0.py` | Insights Pós-Sincronização | Descoberta automática de variações e hipóteses (`lumina.post-sync-insights/1.0`) |
| `v25_0.py` | Observabilidade e Avaliações | Telemetria estruturada, SLOs e execuções de teste (`lumina.observability/1.0`) |
| `v26_0.py` | Fila de Trabalho e Performance | Jobs assíncronos, leases, heartbeats e DLQ (`lumina.work-queue/1.0`) |

### Regras Estritas de Migração
- **Sem Downgrades Destrutivos em Produção:** O comando `down` é restrito a ambientes de teste descartáveis (`ENVIRONMENT=test`, `LUMINA_TESTING=true`).
- **Rollback Operacional Seguro:** O rollback de qualquer módulo é realizado por *feature flag* (`MODE=LEGACY_ONLY`), preservando dados e integridade referencial.
- **Idempotência:** Todo script de migração deve ser reexecutável sem gerar erros de duplicidade.

---

## 2. Comandos de Validação e Qualidade de Código

### Validação Backend
```powershell
# Executar suíte de testes unitários e de integração
.\backend\.venv\Scripts\python.exe -m pytest -q

# Verificar ciclos de importação
.\backend\.venv\Scripts\python.exe scripts\import_cycle_check.py
```

### Validação Frontend
```powershell
cd frontend
# Verificação estática de tipos TypeScript
npx tsc --noEmit

# Lint de componentes e acessibilidade
npm run lint

# Compilação de produção
npm run build
```

---

## 3. Manutenção de Dependências e Segurança

- Executar auditoria de segurança de dependências periodicamente:
  - Backend: `pip check` e verificação de CVEs.
  - Frontend: `npm audit`.
- Preservar os arquivos de trava (`package-lock.json` no frontend) e dependências fixadas no `requirements.txt`.
- Nunca alterar dependências em produção sem validação prévia na suíte de testes e em ambiente de pré-produção.
