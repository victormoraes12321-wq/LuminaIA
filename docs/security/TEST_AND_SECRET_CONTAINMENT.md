# Contencao De Testes E Segredos

## Objetivo

Impedir que pytest, bootstrap, reset, mocks ou Playwright alcancem bancos,
servicos e portas operacionais. A politica e fail-closed: configuracao ausente,
ambigua ou divergente encerra a execucao antes de SQL.

## Fronteiras

- `TEST_DATABASE_URL` e a unica fonte de banco em `ENVIRONMENT=test`.
- `DATABASE_URL` nunca e usada como fallback e, se existir, serve apenas para
  detectar colisao com o destino operacional.
- Apenas PostgreSQL e aceito.
- Loopback `5432`, nomes de bancos operacionais, hosts publicos/corporativos e
  Oracle sao recusados.
- A conexao aberta confirma `current_database()`, endereco e porta do servidor.
- Bootstrap, seed, reset e startup repetem a guarda antes de escrita.
- O bloqueio de socket rejeita destinos nao locais durante pytest.
- `MOCK_ORACLE=true` e `MOCK_OPENAI=true` sao forcados em teste.
- Nem `ignore_mock_global=True` pode liberar Oracle em ambiente de teste.
- Scheduler, sincronizacao semantica e gerenciador real de credenciais nao
  iniciam no lifespan de teste.

Implementacao principal:

- `backend/testing/database_guard.py`;
- `backend/testing/network_guard.py`;
- `backend/testing/test_database.py`;
- `backend/testing/ai_mock.py`;
- `backend/tests/conftest.py`;
- `scripts/run_backend_tests_safe.py`.

## Segredos

Use somente `backend/.env.test.example` como referencia de nomes. Os valores
nele sao sinteticos e locais. Nao copie `.env`, chaves reais, credenciais de
tenant, dumps ou logs para fixtures, snapshots, comandos ou documentacao.

Arquivos `.env*`, logs, traces, caches e artefatos de teste estao ignorados no
Git, com excecao explicita do exemplo seguro. Arquivos sensiveis ja rastreados
historicamente exigem remocao e rotacao em uma tarefa de seguranca separada;
esta tarefa nao reescreve historico nem remove alteracoes do usuario.

Mensagens da guarda nunca incluem URL completa, usuario ou senha.

## Provas Negativas

As seguintes situacoes possuem testes unitarios e subprocessos:

- URL ausente;
- ambiente diferente de `test`;
- flag de teste ausente;
- driver diferente de PostgreSQL;
- Oracle;
- host externo ou publico;
- porta loopback `5432`;
- nome de banco operacional;
- URL igual a `DATABASE_URL`;
- banco/host/porta reais divergentes apos conectar;
- reset chamado fora do contrato;
- pytest direto, sem passar pelo runner;
- tentativa de rede externa;
- tentativa de ignorar o mock Oracle;
- falha e timeout controlados do mock de IA.

Comandos manuais de auditoria devem usar apenas credenciais ficticias:

```powershell
cd backend
$env:ENVIRONMENT = "test"
$env:LUMINA_TESTING = "true"
Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
.\venv\Scripts\python.exe -m pytest --collect-only -q tests\test_auth.py
```

O resultado esperado e erro `Banco de teste recusado` antes da coleta.

## Rede E Portas

- PostgreSQL de teste: `127.0.0.1:55432`;
- frontend Playwright: `127.0.0.1:3100`;
- portas operacionais proibidas no Playwright: `3000`, `3001`, `3002`,
  `3333`, `8000`;
- o Compose publica somente a porta de teste em loopback;
- a rede Docker de teste e dedicada;
- o volume PostgreSQL usa `tmpfs` e e removido com `down -v`.

## Limitacoes Conhecidas

A guarda evita acesso acidental, mas nao substitui:

- rotacao de segredos historicamente expostos;
- CI em host dedicado;
- regras de firewall/egress fora do processo Python;
- isolamento definitivo do caminho `vw_vendas_lm` por tenant;
- memoria conversacional PostgreSQL.

Esses pontos permanecem visiveis no baseline e no mapa V2.
