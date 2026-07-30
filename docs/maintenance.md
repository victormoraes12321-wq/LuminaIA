# Guia De Manutencao

## Indice Semantico

Monitore versions, source manifest, stale sources, contagens, avaliacoes,
ambiguity/unresolved, CAS conflicts e audit timeline. Nao edite snapshots
publicados. Para alteracao de fonte, execute build, avaliacao e publication.

Em incidente, retorne a `LEGACY_ONLY`, desligue flags opcionais e use rollback
para uma versao anteriormente publicada. O down da migration v16 e somente
para PostgreSQL de teste descartavel.

## Migration V12

`backend/database/migration_v12_0.py` adiciona o estado conversacional
PostgreSQL. `up` e idempotente, transacional e verificavel, sem execucao no
startup. `down --confirm-test-only` e destrutiva e bloqueada fora do banco
descartavel. O rollback operacional e `CONVERSATION_STATE_MODE=LEGACY_ONLY`,
preservando tabelas e dados.

## Boas Praticas

- Rodar testes backend e frontend antes de mudancas.
- Preservar contratos de API e tipos TypeScript.
- Nao alterar regra de negocio no frontend.
- Nao permitir IA consultar banco diretamente.
- Criar ADR para mudancas arquiteturais.

## Comandos De Validacao

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run lint
npm run build
npm run test:visual
```

Para mudancas pequenas em orquestrador/frontend de chat, executar no minimo:

```powershell
python -m py_compile backend\services\new_query_orchestrator.py backend\services\metadata_catalog\resolver.py backend\services\data_transformer.py

cd frontend
npm run build
```

Depois validar manualmente ou via Playwright uma pergunta critica no dashboard.

## Atualizacoes

- Atualizar dependencias em janela controlada.
- Rodar `npm audit` e `pip check`.
- Validar import cycles com `scripts/import_cycle_check.py`.
- Regenerar documentacao automatica com `backend\venv\Scripts\python.exe scripts\generate_docs_reference.py`.
- Atualizar `docs/current-status.md` e `CHANGELOG.md` quando houver correcao funcional.

## Monitoramento

Monitorar latencia API, erros 5xx, tempo OpenAI, sync, pool DB, uso CPU/memoria e render frontend.

## Migration V13

`backend/database/migration_v13_0.py` adiciona a Base de Conhecimento
governada. O rollout operacional deve seguir
[`operation/KNOWLEDGE_GOVERNANCE_RUNBOOK.md`](operation/KNOWLEDGE_GOVERNANCE_RUNBOOK.md).
Produção deve permanecer em `LEGACY_ONLY` até migration, verificação e rollout
serem aprovados. O comando `down --confirm-test-only` é proibido fora do banco
descartável guardado.

## Migration V14

`backend/database/migration_v14_0.py` adiciona perfil, preferencias,
consentimentos, eventos, exportacoes e pedidos de exclusao. O `up` e
idempotente e verificavel. O `down --confirm-test-only` e permitido somente
com `ENVIRONMENT=test`, `LUMINA_TESTING=true` e PostgreSQL descartavel
validado.

O startup nao aplica v14. Rollback operacional usa
`USER_ANALYTICAL_PROFILE_MODE=LEGACY_ONLY`, preservando dados e auditoria.
Procedimento completo:
[`operation/USER_PROFILE_PRIVACY_RUNBOOK.md`](operation/USER_PROFILE_PRIVACY_RUNBOOK.md).

## Migration V15

`backend/database/migration_v15_0.py` adiciona feedback, correcoes, manifests
de redacao, reviews, eventos, candidates, exemplos, snapshots, members,
exports e pedidos de exclusao. A migration e aditiva, idempotente e depende
das FKs compostas de usuario e Conversation State.

O startup nao aplica v15. Execute `up` e `verify` em staging antes do rollout.
O rollback operacional e `SUPERVISED_FEEDBACK_MODE=LEGACY_ONLY` com todas as
flags desligadas. `down` e permitido somente no PostgreSQL descartavel de
testes e deve remover v15 antes de v14, v13 e v12.

O rollout funcional usa `V2_COLLECT`, `V2_REVIEW` e `V2_CURATE`. Retencao
pendente pode ser processada pela rota administrativa de expiracao; pedidos
de exclusao permanecem pendentes ate existir worker aprovado pela politica
legal. Exportacoes publicadas usam cursor, spool em disco e resposta em chunks.
