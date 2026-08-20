# IA Do LuminaAI

## Visao Geral

A IA do LuminaAI atua como Corporate Intelligence Engine. Ela interpreta linguagem natural, estrutura intencoes, identifica contexto de negocio, sugere estrategia visual e construi blueprints. Ela nao deve consultar banco, executar SQL, calcular KPIs finais ou renderizar dashboards.

## Modulos Implementados

| Engine | Arquivo | Responsabilidade |
| --- | --- | --- |
| Corporate Intelligence Engine | `backend/services/ai/corporate_intelligence_engine.py` | Orquestracao dos motores de IA |
| Intent Engine | `backend/services/ai/intent_engine.py` | Identificacao de objetivo, entidade, periodo, filtros e complexidade |
| Semantic Engine | `backend/services/ai/semantic_engine.py` | Interpretacao semantica, sinonimos e variacoes linguisticas |
| Context Engine | `backend/services/ai/context_engine.py` | Montagem de contexto de empresa/tenant/catalogos |
| Business Understanding Engine | `backend/services/ai/business_understanding_engine.py` | Entendimento de conceitos de negocio |
| KPI Discovery Engine | `backend/services/ai/kpi_discovery_engine.py` | Seleciona KPIs a partir de conhecimento disponivel |
| Visualization Strategy Engine | `backend/services/ai/visualization_strategy_engine.py` | Sugere componentes e layout logico |
| Blueprint Builder | `backend/services/ai/blueprint_builder.py` | Monta blueprint sem SQL/dados |
| Package Matcher | `backend/services/ai/package_matcher.py` | Busca pacote analitico compativel |
| Confidence Engine | `backend/services/ai/confidence_engine.py` | Calcula nivel de confianca |
| Memory Context Engine | `backend/services/ai/memory_context_engine.py` | Usa historico/contexto evitando dados sensiveis |
| Executive Analysis Engine | `backend/services/ai/executive_analysis_engine.py` | Analise executiva quando solicitada |
| Response Builder | `backend/services/ai/response_builder.py` | Resposta natural estruturada |

## Fluxo Da IA

```text
Pergunta
-> Intent Engine
-> Semantic Engine
-> Context Engine
-> Business Understanding
-> KPI Discovery
-> Visualization Strategy
-> Blueprint Builder
-> Package Matcher
-> Confidence Engine
-> Response Builder
```

## Guardrail Deterministico

Perguntas criticas de vendas com periodo claro podem ser respondidas antes da etapa generativa por um caminho deterministico no `NewQueryOrchestrator`. Esse guardrail existe para evitar erro em indicadores operacionais essenciais, como faturamento, ticket medio, desconto e rankings. A IA continua responsavel por interpretacao e contexto; calculos e SQL permanecem no backend.

Quando a pergunta seguinte nao informa periodo, o historico da conversa pode fornecer o periodo anterior por `session_id` e `parent_id`.

## Modos De Resposta

- Resposta Rapida: modo operacional no frontend, prioriza objetividade.
- Modo Inteligente: modo analitico, equilibra contexto, explicacao e dashboard.
- Consultor Executivo: modo executivo, usa analise mais ampla, riscos, oportunidades e correlacoes.

## Prompt Engine E Gateway

`backend/services/ai_service.py` centraliza chamadas OpenAI, validacao de modelo autorizado, cliente por tenant e prompts estruturados. O modelo configurado e carregado via `OPENAI_MODEL`.

## Limitacoes

- A IA depende do contexto fornecido por catalogos, Business Layer e pacotes existentes.
- A IA nao deve inventar indicadores fora do conhecimento disponivel.
- Interpretacoes de baixa confianca devem solicitar refinamento/confirmacao conforme fluxo implementado.
- Perguntas prioritarias de vendas devem manter regressao automatizada/deterministica antes de alteracoes no prompt.

## Dashboard AI Assistance V2

A assistência de dashboards usa o roteamento governado existente somente para
extração de intenção. O provider não retorna Blueprint, patch, SQL, permissão,
identificador físico, dados ou valores. Tools são uma allowlist estática de
metadados/validação. O builder determinístico produz a proposta, e o Prompt 20
aplica somente após aceite humano. Provider real e rollout estão desabilitados.
# Gate de rollout Prompt 26

Provider/model/role/tenant enviados pelo cliente ou modelo nunca são autoridade.
Dashboard AI continua `LEGACY_ONLY`; kill switch e security readiness precedem
qualquer execução futura. Prompt/CoT/raw provider output não entram em trace público.
