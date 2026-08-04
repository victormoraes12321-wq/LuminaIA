# Runbook Operacional: Validação Analítica Consolidada e Proveniência (`lumina.validation-provenance/1.0`)

## 1. Visão Geral
Este runbook descreve a operação, monitoramento e procedimentos de emergência do motor de validação analítica e proveniência do LuminaAI (`lumina.validation-provenance/1.0`).

## 2. Modos de Operação (`VALIDATION_PROVENANCE_MODE`)
- `LEGACY_ONLY`: Desligado em produção (padrão). Nenhuma validação V2 é executada.
- `SHADOW_VALIDATE`: Executa validação e gera proveniência em segundo plano para auditoria sem bloquear respostas aos usuários.
- `V2_VALIDATE`: Valida respostas e inclui proveniência nos metadados de resposta.
- `V2_ENFORCE`: Exige certificação V2 imutável pré-persistência. Respostas com inconsistências são bloqueadas de forma fail-closed.

## 3. Validação de 18 Estágios
1. `CONTRACT_VALIDATION`: Valida contrato analítico e conformidade de payload.
2. `TENANT_ISOLATION`: Confirma que o `tenant_id` corresponde estritamente ao token autenticado.
3. `SECURITY_AUTHORIZATION`: Executa checagem de permissões RBAC e validação contra prompt injection.
4. `SEMANTIC_CONSISTENCY`: Verifica se as entidades e métricas do intent correspondem ao catálogo governado.
5. `TEMPORAL_ALIGNMENT`: Garante limites temporais determinísticos e sem sobreposição inconsistente.
6. `NUMERIC_PRECISION`: Extrai fatos numéricos em `Decimal` exato e verifica integridade matemática.
7. `COMPLETENESS_CHECK`: Garante que todos os campos e dimensões solicitadas foram atendidos.
8. `TOOL_ORCHESTRATION`: Valida o checksum e comportamento de execução de ferramentas.
9. `FACT_EXTRACTION`: Converte resultados analíticos PostgreSQL em fatos numéricos com hash de proveniência.
10. `CLAIM_BINDING`: Vincula afirmações textuais e numéricas da IA aos fatos provados.
11. `CLAIM_VERIFICATION`: Valida a correspondência entre claims e fatos com regras matemáticas determinísticas.
12. `PROVENANCE_DAG_BUILD`: Constrói o grafo direcionado acíclico de proveniência (`ProvenanceGraphV2`).
13. `CYCLE_DETECTION`: Garante ausência de dependências circulares na linhagem de dados.
14. `CROSS_TENANT_LEAK_CHECK`: Impede qualquer aresta entre dados de tenants distintos.
15. `CERTIFICATION_STAMP`: Emite o certificado imutável com checksum SHA-256 (`CertificationEnvelopeV2`).
16. `AUDIT_LOGGING`: Registra eventos auditáveis sem vazamento de SQL, binds ou segredos.
17. `SUPERSEDING_CHECK`: Atualiza certificados de respostas anteriores da mesma conversa via CAS (`lock_version`).
18. `PUBLIC_SUMMARY_GENERATION`: Gera o resumo público desprovido de metadados técnicos sensíveis.

## 4. Troubleshooting e Procedimentos de Emergência
- **Respostas Bloqueadas Falsamente**: Alterar `VALIDATION_PROVENANCE_MODE` para `SHADOW_VALIDATE` via variável de ambiente ou parâmetro de configuração para permitir respostas enquanto investiga logs de auditoria.
- **Falha de Migração DB**: Reverter a migração v20 com `python -m backend.database.migration_v20_0 down` em banco de teste descartável.
- **Verificação de Saúde**: Endpoint `/api/v2/validation/policy/default` deve retornar status HTTP 200 com política padrão ativa.
