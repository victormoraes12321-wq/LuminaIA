# Arquitetura Do LuminaAI

## Visao Geral

O LuminaAI e uma plataforma de BI corporativo orientada por IA. A IA interpreta a intencao, estrutura estrategia analitica/visual e gera blueprints. O backend executa regras, consultas, calculos e persistencia. O frontend renderiza dashboards e interacoes sem calcular regra de negocio.

## Objetivos

- Transformar perguntas em analises estruturadas.
- Reutilizar blueprints e pacotes analiticos sem reutilizar dados de resposta.
- Preservar separacao entre inteligencia analitica, execucao e apresentacao.
- Oferecer dashboard runtime, studio visual e centros de confianca/performance/seguranca.

## Principios Arquiteturais

- Responsabilidade unica por camada.
- IA nao consulta banco e nao calcula metricas finais.
- Backend centraliza execucao, calculos e validacoes.
- Frontend renderiza e interage com payloads prontos.
- Blueprints sao reutilizaveis; dados devem ser consultados novamente conforme politicas de cache.
- Multi-tenant deve ser aplicado por usuario autenticado e `tenant_id`.

## Arquitetura Enterprise Oficial

```text
IA
-> Planner
-> Validator
-> Business Layer
-> Enterprise Knowledge Layer
-> Backend
-> Data Engine
-> Frontend
-> Insight Layer
-> Cache Layer
-> Security Layer
```

## Arquitetura Modular Implementada

```text
backend/
  main.py                    # FastAPI, routers, middlewares, lifespan
  routers/                   # Controllers HTTP
  schemas/                   # DTOs Pydantic
  models/                    # Modelos SQLAlchemy
  services/
    ai/                      # Corporate Intelligence Engine modular
    business/                # Business Knowledge Engine
    data_platform/           # Catalogos, blueprints, packages, runtime e sync
    performance/             # Performance Optimization Platform
    security/                # Enterprise Security Platform
frontend/
  app/                       # Rotas Next.js
  components/                # UI, charts, runtime e studio
  hooks/                     # Hooks de API/runtime/performance/SSE
  engines/                   # Grid, responsividade, layout e performance client-side
  types/                     # Contratos TS
scripts/                     # Backup, load smoke, import cycle check e seeds
docs/                        # Documentacao oficial e auditorias
```

## Fluxo Geral

```text
Usuario -> Frontend -> API Query -> Query Intelligence Engine -> IA/CIE
-> Planner -> Validator -> Business/Data Platform -> Data Engine
-> Transformacao/BI/Runtime Payload -> Frontend -> Dashboard -> Usuario
```

## Fluxo De Dados

1. Usuario envia pergunta pelo chat.
2. Frontend chama `/api/v1/query/` com JWT.
3. Backend valida sessao, tenant, escopo e senha obrigatoria.
4. IA identifica intencao e/ou CIE estrutura Business Intent, visual strategy e blueprint.
5. Planner e Validator normalizam plano, filtros, datas, metricas e view alvo.
6. Backend executa dados via clone PostgreSQL/mock/Oracle conforme configuracao.
7. Data Transformer e BI Engine montam dados de grafico, KPIs e inteligencia BI.
8. Data Platform pode gerar blueprint, runtime payload, trust center e telemetria.
9. Frontend renderiza resposta e dashboard runtime.

## Fluxo Do Scheduler E Sync

O scheduler inicia no lifespan do FastAPI e chama tarefas de sincronizacao. O Sync Engine possui travas por tenant para evitar concorrencia indevida. A sincronizacao trabalha com catalogo, views e clone analitico conforme servicos `sync_service`, `sync_engine` e `sync_scheduler`.

## Fluxo Do Blueprint Repository

1. Query Intelligence Engine tenta localizar blueprint compativel.
2. Intent fingerprint e similaridade orientam reuso/evolucao.
3. Quando necessario, um novo blueprint e criado e persistido.
4. Data Platform pode registrar blueprint no repositorio e vincular analytical packages/dashboard runtime.

## Fluxo Do Metadata Catalog

1. View Manager/Catalog API registra ou atualiza metadados.
2. Metadata Catalog armazena entidades, colunas, qualidade, lineage e versoes.
3. Health Monitor calcula scores e alertas.
4. Endpoints `/api/v1/metadata-catalog/*` expoem resumo, busca, lineage, impacto e versoes.

## Limites E Observacoes

- Ha rotas duplicadas `/api/v1/api/v1/query` por compatibilidade, mantidas intencionalmente.
- Docker compose nao foi validado localmente por ausencia do binario Docker.
- RLS nativo em banco nao foi identificado; isolamento ocorre na camada de aplicacao.
