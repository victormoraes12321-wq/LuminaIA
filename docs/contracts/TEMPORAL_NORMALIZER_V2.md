# Normalizador Temporal V2

## Contrato

`lumina.temporal.pt-BR/1.0` e o normalizador temporal deterministico que
precede a interpretacao de negocio. O servico principal e
`TemporalNormalizer.normalize(text, context)`.

Ele e puro, stateless e independente de FastAPI, SQLAlchemy, PostgreSQL,
Oracle e OpenAI. O relogio, timezone, politicas e calendario fiscal entram por
`TemporalContext`; regras nunca chamam `date.today()` ou `datetime.now()`.

## Fluxo

1. reparo controlado de texto e normalizacao Unicode;
2. tokenizacao e reconhecimento pelo lexico pt-BR;
3. producao de expressoes temporais discriminadas;
4. resolucao com referencia e timezone explicitos;
5. validacao de limites, ambiguidade e futuro autorizado;
6. producao de `TimeWindow` de `lumina.analytics/2.0`;
7. classificacao estrutural como periodo, range, lista ou comparacao;
8. adaptacao legada somente na fronteira.

O codigo vive em `backend/services/temporal/`. IDs de regra estaveis ficam em
`rule_registry.py`; aliases ficam em `lexicon_pt_br.py`.

## Contexto E Prioridade

`build_temporal_context()` aplica a ordem:

1. timezone explicito previamente autorizado;
2. preferencia valida do usuario;
3. configuracao do tenant;
4. configuracao da aplicacao;
5. fallback documentado `America/Sao_Paulo`.

Todo timezone passa por `ZoneInfo`. No Windows sem base IANA existe fallback
controlado para `UTC` e, para datas modernas, `America/Sao_Paulo` em UTC-03:00.
Outros nomes invalidos produzem erro ou esclarecimento tipado.

`reference_datetime` deve ser timezone-aware. Testes usam
`2026-07-27T12:00:00-03:00`; producao injeta uma referencia unica por
requisicao.

## Limites

`TimeWindow` publico preserva inicio e fim inclusivos por compatibilidade. O
adapter legado produz tambem `end_exclusive`, igual ao dia posterior ao fim,
para filtros de timestamp. Nao existe fim artificial `23:59:59.999999`.

Datas `DATE` usam os dias civis. A conversao de `TIMESTAMP` usa o timezone do
contexto. Range invertido exige esclarecimento; nao e reordenado
silenciosamente.

## Politicas

- `CurrentPeriodMode.FULL_PERIOD`: periodo civil completo.
- `CurrentPeriodMode.TO_DATE`: periodo corrente termina na referencia.
- `DefaultYearPolicy.CURRENT_YEAR`: usa o ano da referencia.
- `MOST_RECENT_OCCURRENCE`: usa a ocorrencia mais recente.
- `REQUIRE_CLARIFICATION`: nao infere ano.
- `TwoDigitYearPolicy.REJECT`: padrao seguro.
- `CURRENT_CENTURY` e `PIVOT_YEAR`: permitidos somente por contexto explicito.
- periodos futuros relativos exigem `allow_future_periods=true`.

Ano inferido e ano de dois digitos reduzem a confianca para `MEDIUM` e geram
warning. Expressoes absolutas completas ficam em `HIGH`. Ambiguidade material
fica em `LOW`, exige confirmacao e bloqueia prontidao.

## Calendario Fiscal

O contexto define `fiscal_year_start_month` e, quando diferente de janeiro,
`FiscalYearLabelMode.STARTING_YEAR` ou `ENDING_YEAR`. A configuracao nao vem de
texto livre. Configuracao incompleta produz erro tipado ou esclarecimento.

Sao suportados ano fiscal, trimestre fiscal absoluto, periodo fiscal atual e
anterior. Persistencia adicional nao foi criada; o provider de contexto esta
preparado para receber configuracao governada do tenant.

## Range, Lista E Comparacao

- `de junho a agosto` e `entre junho e agosto`: `RANGE`;
- `junho, julho e agosto`: `PERIOD_LIST`;
- `junho e agosto`: `PERIOD_LIST`;
- `compare junho e agosto`, `versus`, `vs`, `contra`: `COMPARISON`.

Range produz uma janela continua. Lista e comparacao preservam todas as
janelas e a ordem. Deduplicacao e estavel e considera inicio, fim,
granularidade e timezone.

## Compatibilidade E Rollout

| Flag | Padrao | Efeito |
| --- | --- | --- |
| `TEMPORAL_NORMALIZER_V2_ENABLED` | `true` | Seleciona janelas canonicas |
| `TEMPORAL_NORMALIZER_V2_SHADOW_MODE` | `true` | Compara parser antigo e novo |

Shadow mode registra somente fingerprint, rule IDs, contagens e diferenca
estrutural. A pergunta integral, SQL, binds e dataset nao sao registrados.

`extract_time_windows()` delega ao normalizador e preserva IDs legados
`period_N`. Adapters singulares recusam lista/comparacao. O caminho depreciado
que ainda requer um envelope plural emite warning explicito.

`QueryIntentV2` e `QueryPlanV2` recebem `time_windows`; comparacoes recebem
operandos na ordem. Versao, timezone, relacao, rules, warnings e readiness
ficam em `contract.extensions.temporal`.

O resultado temporal pode ser passado diretamente a `build_intent_v2`, evitando
uma segunda interpretacao da mesma pergunta. O `ComparisonPlanner` consome as
janelas canonicas da intencao e nao reinterpreta datas nem o texto integral.
O `UniversalComparisonExecutor` recebe essas mesmas janelas no `QueryPlanV2`,
converte o fim inclusivo em limite exclusivo no bind e nao chama relogio ou
parser temporal para alterar o periodo.

## Expressoes E Limites

Cobertura inclui datas brasileiras e ISO, mes/ano, ano, trimestre, semestre,
semana ISO, quinzena, hoje/ontem/anteontem, periodos atuais e anteriores,
janelas moveis, periodos fechados, MTD/YTD/QTD, ranges, listas, comparacoes e
calendario fiscal.

Ainda nao sao suportados locale diferente de pt-BR, calendario 4-4-5,
feriados/dias uteis e aliases persistentes do tenant. O planejamento
comparativo pertence a `lumina.comparison-planner/1.0`; execucao e calculo
financeiro pertencem a `lumina.comparison-executor/1.0`.

O corpus versionado esta em
`backend/tests/fixtures/temporal_cases_pt_br.json`. Nenhum teste temporal usa
`xfail`.
