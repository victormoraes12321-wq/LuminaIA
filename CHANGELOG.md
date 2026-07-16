# Changelog

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
