# Testes Seguros Do LuminaAI

## Semantic Retrieval V2

Os testes cobrem contratos, normalizacao, provider local, ranking, migration
v16, build idempotente, publication, rollback, stale source, busca, ambiguity,
clarification, RBAC, multi-tenant, APIs, schemas e goldens. Use exclusivamente
o runner seguro com PostgreSQL Docker na porta 55432.

O Playwright semantico usa API simulada e `127.0.0.1:3100`; nao reutiliza
frontend ou backend operacional.

## Contrato Obrigatorio

Os testes backend usam exclusivamente um PostgreSQL descartavel. A execucao
falha antes de importar a aplicacao ou executar SQL quando qualquer requisito
abaixo nao for atendido:

- `ENVIRONMENT=test`;
- `LUMINA_TESTING=true`;
- `TEST_DATABASE_URL` explicita, sem fallback para `DATABASE_URL`;
- PostgreSQL em loopback ou no servico isolado do Compose;
- porta diferente de `5432` em loopback;
- banco `luminaai_test` ou `luminaai_test_<worker>`;
- destino diferente de qualquer `DATABASE_URL` operacional informada.

Oracle, OpenAI e rede externa sao substituidos por mocks deterministicos.
Segredos reais nao sao necessarios e nao devem ser copiados para o ambiente.

## Windows

```powershell
docker compose -f docker-compose.test.yml up -d --wait
.\scripts\run-backend-tests-safe.ps1 --selection all -q
docker compose -f docker-compose.test.yml down -v
```

Selecoes disponiveis:

```powershell
.\scripts\run-backend-tests-safe.ps1 --selection unit -q
.\scripts\run-backend-tests-safe.ps1 --selection baseline -q
.\scripts\run-backend-tests-safe.ps1 --selection security -q
.\scripts\run-backend-tests-safe.ps1 --selection multitenant -q
.\scripts\run-backend-tests-safe.ps1 --selection ai-mock -q
.\scripts\run-backend-tests-safe.ps1 --selection oracle-mock -q
.\scripts\run-backend-tests-safe.ps1 --selection guard -q
```

## Linux E macOS

```bash
docker compose -f docker-compose.test.yml up -d --wait
./scripts/run-backend-tests-safe.sh --selection all -q
docker compose -f docker-compose.test.yml down -v
```

O runner:

1. define somente configuracao sintetica de teste;
2. valida o destino sem exibir credenciais;
3. aguarda apenas o PostgreSQL de teste;
4. confirma banco, host e porta na conexao aberta;
5. cria schema e dataset sinteticos;
6. executa o pytest e preserva seu codigo de saida.

Nao execute `pytest` diretamente por conveniencia. A coleta direta tambem
possui guarda fail-closed, mas o runner e o caminho operacional documentado.

O Prompt 09 adiciona suites dedicadas
`test_context_resolution_engine_v2.py` e
`test_context_resolution_postgresql_v2.py`, alem do golden
`golden/context_resolution_v2.json`. Elas participam de `--selection all` e
nao acessam Oracle ou OpenAI.

## Dataset Deterministico

O bootstrap cria dois tenants, perfis `ADMIN`, `GESTOR` e `CONSULTA`, filiais,
clientes, vendedores, produtos, catalogos e movimentos sinteticos. Existem
dados de junho e julho de 2026 e referencia em 2025.

Totais principais do tenant A:

| Periodo | Venda comercial | RB | Devolucao | Bonificacao | Transferencia | Total bruto sem transferencia |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 06/2026 | 300,00 | 30,00 | -20,00 | 40,00 | 500,00 | 350,00 |
| 07/2026 | 400,00 | 50,00 | -10,00 | 0,00 | 600,00 | 440,00 |

Em junho, o ticket medio comercial esperado e `150,00`, o desconto total e
`40,00` e o desconto medio e `20,00`. O tenant B usa nomes coincidentes e
valores diferentes para detectar mistura entre tenants.

O reset ocorre antes de cada teste com `TRUNCATE ... CASCADE`, somente depois
das validacoes de ambiente e da conexao. Testes assincronos usam `NullPool`
para nao compartilhar conexoes entre event loops.

## Contratos Analiticos V2

Os testes puramente contratuais usam `unit` e `no_database`. Eles cobrem versao,
serializacao, adaptadores, periodos plurais, visualizacoes multiplas, tenant,
Oracle proibido, proveniencia, validacao, schemas e goldens.

O baseline oficial atual coleta 970 testes. O Prompt 06 adicionou 233 testes
do executor comparativo, todos aprovados e sem xfail; os quatro xfails
historicos continuam estritos. Mesmo para selecoes unitarias, prefira o runner
seguro da raiz.

## Executor Universal De Comparacoes

Os testes do executor cobrem compilacao, SQL allowlisted, binds, operandos,
alinhamento, `Decimal`, metas oficiais, partial, timeout, budgets, cache,
goldens, propriedades e adaptadores. Dois testes executam contra o PostgreSQL
descartavel e provam os valores junho/julho e a invisibilidade do tenant B.

```powershell
.\backend\venv\Scripts\python.exe -m pytest `
  backend\tests\test_comparison_executor_v2.py `
  backend\tests\test_comparison_executor_matrix_v2.py `
  backend\tests\test_comparison_executor_properties_v2.py `
  backend\tests\test_comparison_executor_golden_v2.py `
  backend\tests\test_comparison_executor_performance_v2.py `
  backend\tests\test_comparison_executor_postgresql_v2.py -q
```

## Normalizador Temporal V2

O corpus `tests/fixtures/temporal_cases_pt_br.json` possui 55 casos. Os cinco
modulos temporais executam 99 testes `unit`/`no_database` de calendario,
timezone, fiscal, rollout, adapters, contratos, propriedades e performance.
Todos passam normalmente; nenhum usa `xfail`.

## Planner De Comparacoes V2

Os modulos `test_comparison_planner_*_v2.py` cobrem tipos de comparacao,
periodos, N operandos, entidades, metricas, metas, filtros, baseline,
alinhamento, granularidade, complexidade, propriedades, cache, seguranca,
multitenancy, rollout, adapters e goldens. Nenhum teste do planner usa
`xfail`.

Os 12 planos revisados ficam em
`backend/tests/golden/comparison_plans_v2.json`. O planner e exercitado sem
banco, Oracle, OpenAI ou SQL.

## Markers

- `unit`: logica local;
- `integration`: integracao de componentes;
- `database`: PostgreSQL descartavel;
- `security`: autenticacao, autorizacao e contencao;
- `multitenant`: isolamento entre tenants;
- `ai_mock`: IA deterministica;
- `oracle_mock`: Oracle simulado;
- `baseline`: contratos e numeros conhecidos;
- `known_gap`: comportamento correto ainda nao implementado;
- `slow`: testes demorados.

`known_gap` usa somente `xfail(strict=True)`. Um defeito corrigido transforma o
XPASS em falha, obrigando a remover a marcacao e revisar o contrato.

## Frontend

```powershell
cd frontend
npm run lint
npx tsc --noEmit
npm run build
npm run test:visual
```

O Playwright usa `127.0.0.1:3100`, recusa as portas operacionais
`3000`, `3001`, `3002`, `3333` e `8000`, e nao reutiliza servidor existente.

## Diagnostico

- `TEST_DATABASE_URL ausente`: use o runner ou configure o Compose.
- `porta operacional 5432`: o destino foi recusado corretamente.
- banco/host divergente apos conectar: destrua o container e recrie o volume.
- Docker indisponivel: instale/inicie Docker Desktop; nao aponte o runner para
  um PostgreSQL operacional como alternativa.
- `xfail` virou `XPASS`: o defeito foi possivelmente corrigido; remova a
  marcacao somente apos validar todo o contrato.

O resultado oficial desta implementacao esta em
[`docs/audit/TEST_BASELINE.md`](../audit/TEST_BASELINE.md).

## Enterprise Knowledge V2

Testes direcionados:

```powershell
.\scripts\run-backend-tests-safe.ps1 --selection all -q --tb=short `
  tests/test_enterprise_knowledge_contracts.py `
  tests/test_enterprise_knowledge_service.py `
  tests/test_enterprise_knowledge_api.py `
  tests/test_enterprise_knowledge_migration.py `
  tests/test_enterprise_knowledge_goldens.py
```

O conjunto cobre contracts, lifecycle, CAS, self-approval, publication,
rollback, MetricRegistry binding, alias ambiguity, effective date, RBAC,
IDOR, import/export, migration `down/up/up` e goldens. O frontend usa
`tests/visual/enterprise-knowledge.spec.ts` sem backend operacional.

## Perfil Analitico V2

Testes direcionados:

```powershell
.\scripts\run-backend-tests-safe.ps1 --selection all -q --tb=short `
  tests/test_user_analytical_profile_contracts.py `
  tests/test_user_analytical_profile_service.py `
  tests/test_user_analytical_profile_api.py `
  tests/test_user_analytical_profile_migration.py `
  tests/test_user_analytical_profile_goldens.py `
  tests/test_user_analytical_profile_performance.py
```

O conjunto cobre unioes discriminadas, policies, precedencia, consentimento,
quatro turnos, lifecycle, CAS concorrente, checksum, cache, retencao,
Knowledge references, IDOR, cross-tenant, exportacao, exclusao, migration
`up -> up -> down -> up`, goldens e carga estrutural. O frontend usa
`tests/visual/user-analytical-profile.spec.ts` em quatro viewports.
