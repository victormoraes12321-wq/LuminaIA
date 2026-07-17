# Guia Do Desenvolvedor

## Onboarding Rapido

1. Leia `README.md`.
2. Leia `docs/architecture.md`.
3. Configure backend e frontend conforme `docs/installation.md`.
4. Rode testes e build.
5. Consulte `docs/source-inventory.md` para localizar modulos.

## Como Adicionar Modulos Backend

- Criar service em `backend/services`.
- Criar schema em `backend/schemas` se houver contrato HTTP.
- Criar router em `backend/routers` quando exposto por API.
- Registrar router em `backend/main.py`.
- Criar testes em `backend/tests`.

## Como Adicionar KPIs

- Registrar conceito/KPI na Business Layer.
- Garantir validacao em Business Validation Engine.
- Expor metadata/catalogo se aplicavel.
- Nao calcular KPI no frontend.

## Como Adicionar Dashboards

- Preferir Blueprint/Analytical Package/Runtime payload.
- Criar ou reutilizar componentes em `frontend/components/dashboard-runtime` e `component-library`.
- Garantir responsividade e teste visual quando possivel.

## Como Criar Novas Views

- Registrar no catalogo (`ViewCatalog`).
- Atualizar metadata via CatalogAPI/Metadata Catalog.
- Validar sync/clone quando aplicavel.
- Rodar EXPLAIN/validacao em banco real.

## Como Criar Blueprints

- Usar Business Intent e Visual Strategy.
- Nao incluir SQL bruto nem dados finais.
- Versionar e registrar historico.
- Validar compatibilidade com packages/dashboard runtime.

## Como Evoluir A IA

- Manter engines com responsabilidade unica.
- Nao permitir acesso direto a banco/calculo final.
- Atualizar schemas e testes.
- Preservar modos operacional, analitico e executivo.

## Como Evoluir Perguntas Criticas

- Antes de alterar prompts, resolver ou orquestrador, validar as perguntas prioritarias listadas em `docs/current-status.md`.
- Nao remover o caminho deterministico do `NewQueryOrchestrator` sem substituir por testes equivalentes.
- Preservar exclusoes de negocio para `PADRAO` e `LAGES E LOPES LTDA`.
- Garantir continuidade por `session_id`, historico recente e `parent_id`.
- Se adicionar novo label tecnico, humanizar em `data_transformer.py` ou no contrato apropriado.

## Como Atualizar Documentacao

- Rodar `backend\venv\Scripts\python.exe scripts\generate_docs_reference.py` a partir da raiz para atualizar API e inventario.
- Atualizar `docs/current-status.md` quando houver correcao funcional validada.
- Registrar mudancas em `CHANGELOG.md`.
- Manter relatorios historicos como baseline quando nao forem reexecutados integralmente.

## Compatibilidade

- Nao remover campos de resposta sem migracao.
- Manter adaptadores legados quando clientes existentes dependem deles.
- Documentar mudancas em CHANGELOG e ADR quando arquitetural.
