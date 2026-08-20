# Runbook — Dashboard Blueprint V2

## Escopo operacional

O Prompt 19 não ativa runtime. Este runbook valida contratos e artefatos
offline, sem banco, Oracle, OpenAI, provider ou rede externa. Não use os scripts
operacionais `start-luminaai.ps1`/`stop-luminaai.ps1`.

## Pré-condições

- branch/HEAD devem corresponder à fase autorizada e o índice estar vazio;
- `backend/services/blueprints.json` deve ter SHA-256 conhecido;
- dependências existentes devem estar instaladas;
- nenhum `.env`, log ou arquivo operacional deve ser impresso ou alterado.

## Exportação reproduzível

```powershell
cd backend
.\.venv\Scripts\python.exe ..\scripts\export_dashboard_blueprint_v2_contracts.py
```

O comando deve informar `SUCCESS`, 91 schemas, 20 goldens, hashes iguais nas
duas execuções internas e OpenAPI com 190 paths/216 operações, zero path Prompt
18 e zero path Prompt 19.

## Testes dirigidos

Use o envelope fail-closed de `docs/testing/README.md` e rode:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest `
  tests/test_dashboard_blueprint_v2_contracts.py `
  tests/test_dashboard_blueprint_v2_validation.py `
  tests/test_dashboard_blueprint_v2_canonicalization.py `
  tests/test_dashboard_blueprint_v2_exports.py -q --tb=short
```

Os testes são `no_database`. Para a suíte completa, use exclusivamente o
PostgreSQL descartável e o runner seguro; nunca use `DATABASE_URL` como fallback.

## Diagnóstico e rollback

- `BLOCKED`: conteúdo executável/externo ou acima dos limites;
- `UNSUPPORTED_VERSION`: versão diferente de 2.0;
- `INVALID`: contrato, referência, shape, layout ou governança falhou;
- `VALID_WITH_WARNINGS`: íntegro com condição não bloqueante;
- `VALID`: íntegro e com checksums emitidos.

Não edite exports manualmente. Corrija fonte/fixture e reexporte. Como não há
migration, API ou runtime, rollback retira somente artefatos do Prompt 19; o
legado permanece autoridade. Preserve mudanças locais do usuário.

## Limpeza e evidência

Remova somente containers/networks/volumes descartáveis e relatórios temporários
criados pela validação. Confirme portas 55432, 3100, 3002 e 8000 fechadas,
índice vazio, hash de `blueprints.json` inalterado, `git diff --check` limpo e
nenhum commit, tag ou push novo.

