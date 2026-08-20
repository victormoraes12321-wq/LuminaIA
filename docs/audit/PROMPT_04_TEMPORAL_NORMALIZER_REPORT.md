# Relatorio Do Prompt 04 - Normalizador Temporal Universal

Data: 2026-07-27.

## Resultado

Foi implementado `lumina.temporal.pt-BR/1.0`, normalizador central,
deterministico, stateless e sem acesso a IA, Oracle ou banco. Ele usa relogio e
timezone injetaveis, produz `TimeWindow` V2, preserva multiplos periodos e
distingue range, lista e comparacao.

Arquitetura:

- `models.py`: contexto, politicas, spans, itens, grupos e resultado;
- `lexicon_pt_br.py`: meses, ordinais, conectores e aliases;
- `tokenizer.py`: Unicode, acentos, mojibake e tokens;
- `parser.py`: expressoes e relacoes estruturais;
- `resolver.py`: limites civis, relativos, moveis, acumulados e fiscais;
- `normalizer.py`: pipeline, confianca, ambiguidade e observabilidade;
- `legacy_adapter.py`: binds inclusivos/exclusivos e recusa plural;
- `feature_flags.py`: rollout e shadow mode;
- `context.py`: prioridade governada de timezone.

## Integracoes

- `QueryIntentV2.time_windows` recebe o resultado canonico.
- `QueryPlanV2` preserva as janelas do intent.
- `ComparisonSpecification` preserva operandos na ordem.
- `ContractMetadata.extensions.temporal` expoe versao, timezone, relacao,
  rule IDs, warnings e readiness.
- o orquestrador usa uma referencia unica por requisicao;
- o intent engine recebe apenas resumo temporal compacto;
- `resolve_relative_date_range` delega ao novo servico;
- `extract_time_windows` preserva IDs V1 no wrapper;
- frontend tipa os metadados sem alterar dashboard.

## Politicas E Evidencias

- limites publicos inclusivos e `end_exclusive` no adapter de timestamp;
- `FULL_PERIOD` por padrao e `TO_DATE` configuravel;
- ano ausente: atual, ocorrencia recente ou esclarecimento;
- ano de dois digitos: rejeitado por padrao, century/pivot configuraveis;
- timezone: autorizado, usuario, tenant, aplicacao e fallback;
- fiscal: mes inicial e rotulo `STARTING_YEAR`/`ENDING_YEAR`;
- ambiguidade material bloqueia execucao;
- lista e comparacao nunca passam por wrapper singular.

Resultados de referencia:

- junho/julho: `2026-06-01..30`, `2026-07-01..31`, dois operandos;
- mes atual vs anterior: julho e junho de 2026, nessa ordem;
- ultimos tres meses: `2026-04-28..2026-07-27`;
- ultimos tres meses fechados: `2026-04-01..2026-06-30`;
- FY2026 com inicio em julho/starting: `2026-07-01..2027-06-30`;
- fevereiro de 2024 termina em 29; fevereiro de 2025 em 28;
- Sao Paulo e UTC mudam corretamente o dia perto da meia-noite;
- `data_fim=2026-06-30` gera `end_exclusive=2026-07-01`.

## Testes E Validacoes

O corpus possui 55 casos e a bateria temporal possui 99 testes. Resultado
final:

| Validacao | Resultado |
| --- | --- |
| Suite temporal | 99 passed |
| Unitarios completos | 227 passed, 2 xfailed antes do ultimo teste aditivo |
| Baseline | 12 passed, 2 xfailed |
| Seguranca | 20 passed |
| Multitenant | 6 passed, 1 xfailed |
| Backend completo | 671 coletados; 667 passed; 4 xfailed |
| Falhas / XPASS | 0 / 0 |
| Duracao backend final | 660,00 s |
| Schemas V2 | 5 hashes identicos em duas geracoes |
| Goldens V1/V2 | aprovados na suite |
| ESLint | aprovado, sem warnings |
| TypeScript | aprovado |
| Next.js build | aprovado, 15 paginas |
| Playwright | 16/16 passed |

Xfails mantidos:

- `LUMINA-GAP-DASH-001`: contrato de atualizacao visual local;
- `LUMINA-GAP-CONTEXT-001`: continuidade estruturada de quatro turnos;
- `LUMINA-GAP-CONTEXT-002`: cache conversacional PostgreSQL;
- `LUMINA-GAP-TENANT-001`: isolamento definitivo do core summary.

Nenhum xfail foi removido ou adicionado e nenhum teste temporal usa xfail.

Comandos principais executados:

```powershell
.\scripts\run-backend-tests-safe.ps1 --selection unit -q --tb=short
.\scripts\run-backend-tests-safe.ps1 --selection baseline -q --tb=short
.\scripts\run-backend-tests-safe.ps1 --selection security -q --tb=short
.\scripts\run-backend-tests-safe.ps1 --selection multitenant -q --tb=short
.\scripts\run-backend-tests-safe.ps1 --selection all -q --tb=short
backend\.venv\Scripts\python.exe scripts\export_analytical_contract_schemas.py
cd frontend
npm run lint
npx tsc --noEmit
npm run build
npm run test:visual
```

O backend completo foi repetido apos cada ajuste final relevante. Duas
execucoes intermediarias detectaram e corrigiram uma compatibilidade legada de
mes movel e um teto de benchmark instavel; a execucao final ficou verde.

Oracle, OpenAI e banco operacional nao foram acessados. Somente PostgreSQL 17
descartavel em `127.0.0.1:55432/luminaai_test` foi usado. Nenhuma migration,
dependencia ou alteracao de lockfile foi criada. Nenhum segredo foi lido ou
incluido no diff. Ao final, o PostgreSQL descartavel foi encerrado, seu
diretorio temporario foi removido e as portas `55432`, `3100` e `8000` foram
confirmadas sem listeners.

## Limitacoes

- pt-BR e o unico locale;
- calendario 4-4-5, feriados e dias uteis nao foram implementados;
- aliases governados persistentes dependem de etapa futura;
- comparacao financeira generica continua no Prompt 05;
- o fallback Sao Paulo sem tzdata cobre o regime moderno UTC-03:00.

Proxima etapa: `Prompt 05 - Planner generico de comparacoes`.
