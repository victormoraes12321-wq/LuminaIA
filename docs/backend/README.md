# Backend

## Estado Conversacional

`services/conversation_state/` contem protector Fernet, repository async com
escopo tenant/usuario, service transacional, adapter e importador legado.
`database/migration_v12_0.py` cria o schema sem `create_all` e nunca roda no
startup.

## Stack

- FastAPI
- SQLAlchemy async
- Pydantic v2
- PostgreSQL/asyncpg
- Oracle/oracledb ou mock local
- OpenAI SDK
- PyJWT
- pytest

## Entrada Principal

`backend/main.py` configura FastAPI, lifespan, CORS, middlewares, exception handlers, routers e endpoints `/health`, `/health/deep` e `/`.

## Controllers/Routers

- `auth.py`: login, sessao, logout e troca de senha.
- `users.py`: administracao de usuarios por tenant.
- `tenant.py`: configuracoes de tenant, testes de conexao e sync.
- `catalog.py`: catalogo de views.
- `query.py`: consulta inteligente, historico, favoritos, cache, performance e seguranca.
- `metadata_catalog.py`: metadata, lineage, impacto, health e versoes.
- `business_knowledge.py`: conceitos, KPIs, formulas, governanca e rollback.
- `analytical_packages.py`: pacotes analiticos e instancias.
- `dashboard_studio.py`: templates, instances, versoes, import/export e validacao.
- `dashboard.py`: SSE, refresh e telemetria de dashboard.
- `dashboard_preferences.py`: preferencias de resposta/dashboard por usuario e tenant.

## Services

Services centralizam regra de aplicacao. Routers devem ser finos e delegar execucao.

### Consulta Inteligente

- `new_query_orchestrator.py`: orquestra o novo pipeline e possui caminho deterministico para perguntas criticas de vendas.
- `contracts/analytical_v2`: contratos Pydantic estritos e versionados para
  intencao, periodos, comparacao, plano, resultado, proveniencia e validacao.
- `query_response_governance.py`: adiciona sidecar V2 aos pipelines novo e
  legado quando as feature flags permitem.
- `metric_registry.py`: dicionario oficial de metricas, fontes, formulas, filtros, confianca e limites conhecidos.
- `comparison_planning/`: planner comparativo deterministico, providers
  governados, modelos internos, adapters e rollout sem acesso a dados.
- `sales_value_breakdown.py`: decomposicao deterministica de faturamento comercial, saida RB, devolucao, bonificacoes, transferencias, remessa, total bruto sem transferencias e total geral de movimentos por periodo/filial.
- `metadata_catalog/resolver.py`: resolve metricas, dimensoes, joins e expressoes canonicas.
- `data_transformer.py`: normaliza linhas, formata moeda/percentuais e humaniza labels para exibicao.

Regras de negocio recentes:

- `PADRAO` e ignorado em ranking de vendedores.
- `LAGES E LOPES LTDA` e ignorado em ranking/top cliente externo.
- Desconto e derivado por item quando a view nao fornece coluna explicita.
- Saida RB e devolucao sao metricas separadas; transferencias ficam em coluna propria e nao entram em faturamento/lucro/total bruto.
- Periodo, metrica e dimensao podem ser herdados do historico da conversa quando a pergunta seguinte e curta ou ambigua.
- Perguntas com base/visualizacao ambigua podem usar preferencia persistida em `dashboard_preferences`.
- Respostas criticas de vendas incluem `bi_intelligence.metric_definitions`, `calculation_steps` e `trust_center.metric_registry`.
- O helper temporal canonico e plural; o helper singular existe somente como
  compatibilidade para fluxos antigos.
- Falha do intent engine retorna erro tipado e nao pode criar Cliente como
  fallback.

### Feature Flags Dos Contratos

- `ANALYTICAL_CONTRACTS_V2_ENABLED=false`;
- `ANALYTICAL_CONTRACTS_V2_SHADOW_MODE=true`;
- `ANALYTICAL_CONTRACTS_V2_FRONTEND_ENABLED=false`;
- `ANALYTICAL_COMPARISON_V2_EXECUTION_ENABLED=false`.
- `TEMPORAL_NORMALIZER_V2_ENABLED=true`;
- `TEMPORAL_NORMALIZER_V2_SHADOW_MODE=true`.
- `COMPARISON_PLANNER_V2_ENABLED=true`;
- `COMPARISON_PLANNER_V2_SHADOW_MODE=true`.

Veja [Contratos Analiticos V2](../contracts/ANALYTICAL_CONTRACTS_V2.md) e
[Compatibilidade V1/V2](../contracts/COMPATIBILITY_V1_V2.md).

### Normalizacao Temporal

Perguntas passam por `backend/services/temporal/` antes da autoridade final de
datas. `lumina.temporal.pt-BR/1.0` usa contexto injetado, nao chama IA ou banco
e distingue periodo, range, lista e comparacao. Consulte
[Normalizador Temporal V2](../contracts/TEMPORAL_NORMALIZER_V2.md).

### Planejamento Comparativo

`backend/services/comparison_planning/` transforma comparacoes normalizadas em
`QueryPlanV2`. `lumina.comparison-planner/1.0` preserva N operandos, particiona
filtros, seleciona baseline, valida alinhamento/permissoes/complexidade e
produz hints de estrategia. O pacote nao executa SQL, nao acessa banco,
Oracle/OpenAI e nao calcula valores. Consulte
[Planner Generico De Comparacoes V2](../contracts/COMPARISON_PLANNER_V2.md).

## Middlewares E Erros

- CORS configurado por `settings.CORS_ORIGINS`.
- Middleware de timing adiciona diagnostico de latencia.
- Handlers globais padronizam HTTPException e excecoes genericas.
- Em producao, detalhes tecnicos nao devem ser expostos ao cliente.

## Validacao

```powershell
docker compose -f docker-compose.test.yml up -d --wait
.\scripts\run-backend-tests-safe.ps1 --selection all -q
docker compose -f docker-compose.test.yml down -v
```

O runner exige PostgreSQL descartavel, valida o destino antes de importar a
aplicacao e usa mocks de Oracle/OpenAI. Consulte
[`docs/testing/README.md`](../testing/README.md). Nao execute o pytest contra
uma `DATABASE_URL` operacional.
