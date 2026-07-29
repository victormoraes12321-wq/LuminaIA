# Baseline Seguro De Testes

Data da execucao: 2026-07-28.

## Veredito

**Baseline V2 com estado conversacional PostgreSQL aprovado e tres gaps
funcionais explicitos.**

A infraestrutura de teste e fail-closed, usa PostgreSQL descartavel, dados
sinteticos e mocks de Oracle/OpenAI. Nenhuma falha inesperada permaneceu na
suite. Tres contratos corretos ainda nao sao atendidos pelo produto e foram
mantidos como `xfail(strict=True)`, sem alterar expectativas para aceitar
respostas erradas.

## Resultado Consolidado

| Validacao | Resultado |
| --- | --- |
| Coleta pytest | 997 testes, sem erro |
| Suite backend completa | 994 passed, 3 xfailed, 0 failed, 0 xpassed |
| Estado conversacional + migration | 27 passed, sem warning |
| Executor comparativo dedicado | 233 passed, sem xfail |
| Contratos + temporal + planner + executor puro | 454 passed |
| Duracao backend completa final | 859,14 s |
| Planner comparativo dedicado | 66 passed |
| Baseline de banco/contrato | 14 passed, 2 xfailed |
| Multitenancy dedicado | 10 passed, 1 xfailed |
| Seguranca dedicada | 37 passed |
| Guardas dedicadas | 20 passed |
| Integracao auth/admin/security/query | 9 passed |
| ESLint | 0 erros, 0 warnings |
| TypeScript `--noEmit` | aprovado |
| Next.js build | aprovado |
| Playwright visual | 192 casos na matriz final |
| Presentation model comparativo | 56 passed (14 cenarios x 4 projetos) |
| Renderer comparativo | 96 passed (24 cenarios x 4 projetos) |
| Porta Playwright | 3100 |
| Oracle real | nao acessado |
| OpenAI real | nao acessada |
| Portas operacionais | nao usadas |

O Docker CLI estava disponivel, mas o servico Docker do Windows nao pode ser
iniciado pela sessao atual. Para validar o runtime sem reduzir a contencao, foi
iniciado um cluster
PostgreSQL 17 separado e descartavel em `127.0.0.1:55432`, fora da instancia
operacional `5432`. Ele foi usado somente pela suite e removido ao final.

## Numeros Validados

O tenant A confirmou, por SQL deterministico:

- junho/2026: comercial `300,00`, RB `30,00`, devolucao `-20,00`,
  bonificacao `40,00`, transferencia `500,00`, bruto sem transferencia
`350,00`;
- julho/2026: comercial `400,00`, RB `50,00`, devolucao `-10,00`,
  transferencia `600,00`, bruto sem transferencia `440,00`;
- ticket medio comercial de junho: `150,00`;
- desconto total de junho: `40,00`;
- desconto medio de junho: `20,00`;
- filtros por filial, vendedor, produto e categoria;
- separacao de RB, devolucao, bonificacao e transferencia;
- transferencia excluida do faturamento;
- totais do tenant B diferentes apesar de nomes coincidentes.

## Falhas Corrigidas Nesta Etapa

1. Pytest podia herdar `DATABASE_URL` e escrever no banco ativo.
2. Reset e bootstrap nao possuiam guarda conectada.
3. Testes dependiam de usuarios e senhas reais da empresa.
4. Oracle e OpenAI podiam ser acionados por testes.
5. Conexoes async eram compartilhadas entre event loops.
6. Dataset sintetico usava e-mails rejeitados pelo schema.
7. Teste administrativo esperava Oracle real em vez de mock.
8. Treinamento semantico dependia de IA externa.
9. Sincronizacao colidia com a view SQL do baseline.
10. Playwright usava/reutilizava porta operacional.
11. Frontend tinha 8 erros e 27 warnings de lint.
12. Configuracao visual continha tipos frouxos que bloqueavam lint/type check.

## Contratos V2 Validados

- `lumina.analytics/2.0` rejeita versao desconhecida;
- pergunta exata junho/julho preserva os dois periodos e operandos;
- quatro variacoes temporais e ordem invertida foram aprovadas;
- tabela e grafico preservam os dois formatos e a ordem;
- V1, sidecar V2 e round-trip permanecem compativeis;
- fora de escopo nao vira ambiguidade;
- falha do intent engine nao vira Cliente;
- readiness diferente de `READY` nao executa banco;
- schemas Pydantic foram exportados de forma deterministica;
- frontend aceita V1 e sidecar V2 pelo adaptador central.

## Normalizador Temporal V2

- `lumina.temporal.pt-BR/1.0` usa relogio e timezone injetaveis;
- corpus pt-BR com 55 casos versionados;
- 99 testes temporais aprovados sem xfail;
- datas absolutas, relativas, moveis, fechadas e acumuladas;
- trimestre, semestre, semana ISO, quinzena e calendario fiscal;
- range, lista e comparacao estruturalmente distintos;
- wrappers singulares recusam pluralidade;
- limites inclusivos geram o dia seguinte como fim exclusivo no adapter;
- shadow mode registra fingerprint e diferenca estrutural, sem pergunta;
- parser nao importa OpenAI, Oracle, SQLAlchemy ou acesso a banco.

## Planner Generico De Comparacoes V2

- `lumina.comparison-planner/1.0` aprovado em 66 testes dedicados sem xfail;
- periodo, N periodos, entidade, N entidades, metrica e meta oficial;
- filtros compartilhados e especificos permanecem separados;
- ordem, baseline, calculos declarados e field origins sao preservados;
- alinhamento, granularidade e complexidade sao validados;
- tenant, permissoes, fontes, entidades e metas usam contexto confiavel;
- Oracle, metrica desconhecida, SQL em filtro e meta inventada sao bloqueados;
- feature flag, rollback legado e shadow mode sanitizado foram validados;
- 12 golden plans revisados e deterministas;
- pacote sem import de banco, Oracle ou OpenAI e sem SQL.

## Executor Universal De Comparacoes

- `lumina.comparison-executor/1.0` aprovado em 233 testes dedicados sem xfail;
- executa periodo, multi-periodo, entidade, multi-entidade, metrica, meta
  oficial e comparacoes compostas;
- preserva todos os operandos, ordem, filtros especificos, baseline e
  dimensoes;
- compila somente `SELECT` a partir de catalogo governado e valores em binds;
- bloqueia Oracle, SQL livre, fonte, metrica, dimensao e tenant nao autorizados;
- usa `Decimal`, arredondamento final e politica explicita para denominador
  zero, bucket ausente e null;
- limita queries, operandos, linhas, payload, concorrencia e tempo;
- produz validacao matematica, proveniencia, partial e fingerprints;
- integra Planner V2, orquestrador, AnalyticalResponseV2, V1 e sidecar;
- feature flag e shadow mode iniciam desligados;
- junho/julho no PostgreSQL descartavel resultou em `300,00`, `400,00`,
  delta `100,00` e `33,33%`, sem transferencia e sem tenant B;
- 15 golden results e cinco testes de desempenho foram aprovados.

## Apresentacao Comparativa

- `lumina.comparison-presentation/1.0` adapta V2 e V1 sem recalcular numeros;
- 14 testes de modelo e 24 testes de renderer aprovados nos quatro projetos;
- periodo, multi-periodo, entidade, multi-entidade, metrica, meta, meta ausente,
  area, pizza governada e multiplas visualizacoes foram renderizados;
- null, missing, zero, denominador zero, parcial, truncado, timeout e blocked
  permanecem estados distintos;
- tabela, cards, barras, linha, area, pizza, actual vs target e fallback seguro;
- Trust Center e metadados respeitam `ADMIN`, `GESTOR` e `CONSULTA`;
- CSV preserva valores brutos e exclui SQL, binds e credenciais;
- claro, escuro, desktop, tablet, mobile, ultrawide, teclado e fullscreen;
- feature flag e shadow mode iniciam desligados;
- golden presentation models e carga de 10 operandos/500 linhas aprovados;
- nenhuma formula financeira, dependencia, migration ou mudanca de lockfile.

## Estado Conversacional PostgreSQL

- contrato canonico `lumina.conversation-state/1.0`;
- PostgreSQL armazena sessoes, nos, snapshots, eventos e ledger de importacao;
- tenant e usuario autenticados compoem todas as leituras e mutacoes;
- `client_message_id` torna retry idempotente e rejeita conteudo divergente;
- `context_version` usa compare-and-swap, sem last-write-wins;
- parent e active head pertencem obrigatoriamente a mesma sessao;
- snapshots estruturados possuem checksum e nao armazenam dataset, SQL ou binds;
- conteudo permitido usa Fernet com versao de chave; SQL e segredos sao
  minimizados por redacao antes da persistencia;
- reset incrementa epoch, archive/reopen/expiration/delete respeitam estado;
- retention possui dry-run, lote, cutoff e purge por cascade;
- importacao JSON e explicita, dry-run por padrao, governada por flag e ledger;
- 16 golden states, quatro turnos, reinicio, duas instancias, 20 operacoes
  concorrentes, mil nos e paginacao foram aprovados;
- frontend mantem somente session ID, versao e parent em chave tenant+usuario;
- logout elimina todos os bindings e reset pela logo cria uma sessao nova;
- producao permanece `LEGACY_ONLY`; scheduler e importacao real ficam desligados;
- detalhes e evidencias: `PROMPT_08_POSTGRES_CONVERSATION_STATE_REPORT.md`.

## Xfails Estritos

- `LUMINA-GAP-DASH-001`: atualizacao visual local retorna
  `FULL_RENDERING`, nao `UI_MODIFIED`. Futuro dashboard V2.
- `LUMINA-GAP-TENANT-001`: core summary consulta `vw_vendas_lm` sem filtro
  `tenant_id`. Futuro gateway analitico isolado.

Foram removidos onze casos `xfail`: `VIS-001`, `VIS-002`, `COMP-001`, quatro
variacoes `COMP-002`, `ORCH-001`, `ORCH-002` e `CONTEXT-002`. Os dez casos
anteriores ao Prompt 09 possuem teste regular aprovado.
`LUMINA-GAP-CONTEXT-001` foi substituido por teste regular do motor
`lumina.context-resolution/1.0`, cuja execucao PostgreSQL desta etapa ficou
pendente pelas restricoes locais registradas abaixo. Permanecem somente
`DASH-001` e `TENANT-001`.

## Evidencias De Contencao

- sem `TEST_DATABASE_URL`: coleta recusada;
- `127.0.0.1:5432`: coleta recusada;
- `ENVIRONMENT=development`: reset recusado;
- senha nao apareceu nas mensagens;
- subprocessos provaram que pytest direto tambem carrega a guarda;
- teste conectado confirmou banco, endereco e porta do servidor;
- bloqueio de rede ficou ativo durante toda a sessao.

## Classificacao Das Falhas Encontradas

- ambiente antigo: corrigido;
- fixtures: corrigidas;
- dependencias externas: substituidas por mocks;
- compatibilidade de testes: corrigida;
- bugs introduzidos nesta tarefa: nenhum remanescente;
- bugs funcionais preexistentes: 2 casos visiveis como `xfail(strict=True)`.

## Comandos Executados

```powershell
.\scripts\run-backend-tests-safe.ps1 --selection all -q --tb=short
cd frontend
npm run lint
npx tsc --noEmit
npm run build
npm run test:visual
```

Tambem foram executadas selecoes de guarda, baseline, multitenancy, mocks e
integracao. Consulte [`docs/testing/README.md`](../testing/README.md) para
reproducao.

## Proxima Etapa

Executar `Prompt 10 - Base de Conhecimento Empresarial`,
preservando:

1. `lumina.temporal.pt-BR/1.0` como autoridade de datas;
2. contrato plural de periodos;
3. `lumina.comparison-planner/1.0` como autoridade de planejamento;
4. compatibilidade V1/V2 e sidecar;
5. isolamento fail-closed dos testes;
6. quatro gaps futuros sem mascaramento;
7. `lumina.comparison-executor/1.0` como unica autoridade numerica comparativa;
8. `lumina.comparison-presentation/1.0` como camada somente de apresentacao.

## Incremento Prompt 09

- contrato `lumina.context-resolution/1.0`;
- heranca deterministica por campo, sem concatenacao textual no caminho V2;
- quatro turnos: junho/Centro, julho, comparacao e produto;
- patch discriminado, checksums e idempotencia;
- snapshot do parent para branch e CAS por epoch/versao;
- reset total avanca epoch apenas na conclusao;
- negacao, correcao, remocao, conflito e mudanca de assunto fail-closed;
- resumo publico e diagnostico tecnico restrito a `ADMIN`;
- 2 xfails estritos remanescentes: `DASH-001` e `TENANT-001`;
- AST dos arquivos Python alterados aprovado;
- frontend ESLint e TypeScript aprovados;
- 7 cenarios Playwright desktop produziram `ok`; o comando excedeu o timeout
  apenas durante encerramento do webserver, sem porta 3100 remanescente;
- build frontend bloqueado exclusivamente pelo acesso externo as fontes Google;
- pytest/PostgreSQL descartavel nao executado nesta sandbox porque o named pipe
  Docker retornou acesso negado e o Python 3.12 do host nao e executavel pela
  sandbox. As suites e fixtures foram adicionadas, sem declarar aprovacao.

## Certificacao Prompt 09.1 - 2026-07-28

As limitacoes registradas no incremento original foram resolvidas em uma nova
sessao de certificacao, sem apagar a evidencia historica anterior.

| Verificacao | Resultado certificado |
|---|---:|
| Backend coletado | 1080 |
| Backend passed | 1078 |
| Backend failed | 0 |
| Backend xfailed | 2 |
| Backend XPASS | 0 |
| Duracao backend | 719.95 s |
| Prompt 09 direcionado | 88 passed |
| Estado/concorrencia/PostgreSQL | 28 passed |
| Contratos/schemas/goldens focalizados | 43 passed |
| Playwright | 196 passed, exit code 0 |

Os dois xfails continuam exatamente:

- `LUMINA-GAP-DASH-001`;
- `LUMINA-GAP-TENANT-001`.

`LUMINA-GAP-CONTEXT-001` passou como teste regular. O cenario de quatro turnos
tambem passou integrado ao PostgreSQL, produzindo quatro snapshots, versoes
`1, 2, 3, 4`, faturamento e filial Centro herdados, junho/julho ordenados,
comparacao ativa e dimensao produto no estado final.

Validacoes complementares:

- PostgreSQL 16 Alpine descartavel em `127.0.0.1:55432/luminaai_test`;
- CAS, concorrencia, replay, restart, duas instancias, branches, cross-tenant,
  cross-user, parent invalido, reset e falha tecnica aprovados;
- cinco schemas exportados duas vezes com hashes identicos e sem diff;
- 18 golden transitions validas;
- OpenAPI com 83 paths, dos quais 6 conversacionais, e campos novos aditivos;
- ESLint, TypeScript e build Next.js aprovados;
- Playwright completo aprovado em quatro viewports e webserver encerrado;
- AST de 382 arquivos Python aprovado;
- Oracle, OpenAI e banco operacional nao acessados;
- nenhuma migration, dependencia ou lockfile alterado;
- portas `55432`, `3100`, `3002` e `8000` fechadas ao final.
