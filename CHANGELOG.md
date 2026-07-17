# Changelog

## 2026-07-17 - Correcao De Perguntas Criticas, Sessao E Encoding

- Adicionado caminho deterministico no orquestrador para perguntas prioritarias de faturamento, ticket medio, desconto, maior vendedor e maior cliente.
- Corrigida continuidade de conversa com `session_id`, historico recente e `parent_id`, incluindo heranca de periodo quando a pergunta seguinte nao informa nova data.
- Ranking de vendedores passou a ignorar o cadastro tecnico `PADRAO`; ranking/top clientes passou a ignorar `LAGES E LOPES LTDA` quando representa a loja interna.
- Desconto total e desconto medio passaram a usar derivacao deterministica por item sobre a view de vendas.
- Clique na logo do sistema passou a limpar a conversa atual.
- Criada camada defensiva de reparo de encoding no frontend para textos de API, historico, favoritos, dashboard runtime, tabelas e mensagens de autenticacao.
- Labels tecnicos de tabelas passaram por humanizacao centralizada no `data_transformer`, incluindo `Observacao`, `Ticket medio` e `Valor formatado`.
- Corrigida a base da API em ambiente local para preservar `localhost` ou `127.0.0.1`, evitando perda de cookie HttpOnly entre hosts loopback diferentes.
- Regeneradas referencias automaticas de API e inventario de codigo.
- Validacoes executadas: `python -m py_compile` nos arquivos alterados, `npm run build`, E2E Playwright em `http://127.0.0.1:3000/login` com login, pergunta real e verificacao de ausencia de mojibake renderizado.

## 2026-07-17 - Documentacao Atualizada

- Criado `docs/current-status.md` como fonte curta do estado atual pos-correcoes.
- READMEs, guias operacionais, arquitetura, IA, frontend, backend, Data Platform, performance, seguranca, manutencao e relatorios receberam addenda ou referencias ao estado atual.
- A certificacao de 2026-07-09 foi mantida como baseline historico; validacoes de 2026-07-17 foram registradas como validacao incremental.

## 2026-07-09 - Documentacao Enterprise Oficial

- Gerada documentacao tecnica oficial do LuminaAI.
- Criados guias de arquitetura, APIs, IA, backend, frontend, Data Platform, banco analitico, cache, scheduler, seguranca, performance, instalacao, deploy, operacao, manutencao, desenvolvimento e governanca.
- Criados ADRs iniciais para decisoes arquiteturais centrais.
- Documentacao alinhada ao estado validado: backend `303 passed`, certificacao Enterprise `7 passed`, frontend lint/build OK, Playwright `16 passed`, load smoke `50 ok` e import cycles runtime `0`.

## 2026-07-09 - Hardening Semantico Corporativo

- Centralizada a canonicalizacao de metricas no Semantic Layer para aliases, sinonimos dinamicos, variacoes com espaco/underscore, plural/singular e similaridade segura.
- Business Layer, Semantic Engine, KPI Discovery e Plan Validator passaram a compartilhar a mesma fonte semantica corporativa.
- Adicionados testes de regressao para `total_vendas`, `valor das vendas`, `pedidos_totais`, `ticket medio`, `churn`, `LTV`, `CAC`, conversao e typo leve.
- Regressao backend completa reexecutada com `303 passed`.

## 2026-07-09 - Certificacao Automatizada Por Testes

- Criada suite `backend/tests/test_enterprise_production_certification.py` para validar contratos criticos, separacao arquitetural, seguranca JWT, Dashboard Studio, documentacao e gates operacionais.
- Cobertura Playwright ampliada com projeto mobile alem de desktop, tablet e ultrawide.
- Reexecutadas validacoes completas: backend `303 passed`, certificacao Enterprise `7 passed`, frontend lint/build OK, Playwright `16 passed`, import cycles `0`, `npm audit` sem vulnerabilidades, `pip check` OK e load smoke local `50 ok`.

## 2026-07-09 - Revisao Final De Producao

- Score Enterprise final documentado: 98/100.
- Removidas supressoes ESLint/TS restantes.
- Dockerfile frontend ajustado para `npm ci`.
- Artefatos gerados de lint removidos.
- Encoding reparado em arquivos de codigo/UI/logs sem alterar dados persistidos.

## 2026-07-08 - Hardening Enterprise

- JWT migrado para PyJWT.
- Frontend lint zerado.
- Build/testes visuais/load smoke validados.
- Import cycles runtime zerados.
- Scorecard e auditoria arquitetural atualizados.
