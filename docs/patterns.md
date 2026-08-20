# Padroes E Convencoes

## Clean Architecture

O projeto separa entrada HTTP, DTOs, modelos, services e UI. Routers devem ser finos; services concentram regra de aplicacao.

## SOLID

- Responsabilidade unica por engines/servicos.
- Dependencias por contratos/schemas quando possivel.
- Extensao por novos engines/componentes sem alterar regra central.

## DRY, KISS, YAGNI

- Reutilizar Data Platform, Business Layer e componentes runtime.
- Evitar duplicar calculo no frontend.
- Evitar funcionalidade especulativa sem contrato real.

## Nomenclatura

- Backend Python: snake_case para funcoes/variaveis, PascalCase para classes.
- Frontend TypeScript: PascalCase para componentes, camelCase para funcoes/variaveis.
- Endpoints: kebab-case ou paths ja existentes em routers.
- IDs/tenant: UUID strings.

## Versionamento

- Blueprints, metadata catalog, analytical packages e dashboard studio possuem estruturas de versionamento.
- Mudancas arquiteturais devem receber ADR quando impactarem responsabilidade de camadas.

## Compatibilidade

- Nao remover contratos existentes sem fase de migracao.
- Manter rotas legadas documentadas enquanto clientes antigos existirem.
- Preservar adaptadores defensivos para payloads legados, incluindo reparo de encoding e normalizacao de Trust Center.

## Regras De Apresentacao

- Frontend pode reparar texto/encoding, mas nao recalcular metricas de negocio.
- Backend deve entregar labels humanizados quando possivel.
- Campos tecnicos novos devem ser documentados e, quando visiveis ao usuario, mapeados para nomes legiveis.
