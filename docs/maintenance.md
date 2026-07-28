# Guia De Manutencao

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
