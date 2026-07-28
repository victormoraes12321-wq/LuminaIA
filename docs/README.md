# Documentacao Oficial Do LuminaAI

Esta pasta contem a documentacao tecnica oficial do LuminaAI. Os documentos foram organizados para onboarding, manutencao, auditoria, operacao e evolucao segura da plataforma.

## Leituras Principais

- [Estado atual do sistema](current-status.md)
- [Arquitetura](architecture.md)
- [Modulos](modules.md)
- [Inventario de codigo](source-inventory.md)
- [Referencia de APIs](api-reference.md)
- [IA](ai/README.md)
- [Backend](backend/README.md)
- [Frontend](frontend/README.md)
- [Data Platform](data-platform/README.md)
- [Banco Analitico](analytical-database/README.md)
- [Blueprint Repository](blueprint-repository/README.md)
- [Business Layer](business-layer/README.md)
- [Scheduler](scheduler/README.md)
- [Cache](cache/README.md)
- [Seguranca](security.md)
- [Performance](performance.md)
- [Fluxos](flows.md)
- [Padroes](patterns.md)
- [Contratos Analiticos V2](contracts/ANALYTICAL_CONTRACTS_V2.md)
- [Compatibilidade V1/V2](contracts/COMPATIBILITY_V1_V2.md)
- [Normalizador Temporal V2](contracts/TEMPORAL_NORMALIZER_V2.md)
- [Planner Generico de Comparacoes V2](contracts/COMPARISON_PLANNER_V2.md)

## Guias Operacionais

- [Instalacao](installation.md)
- [Deploy](deploy.md)
- [Operacao](operation.md)
- [Manutencao](maintenance.md)
- [Desenvolvimento](developer-guide.md)
- [Governanca](governance.md)
- [Changelog](../CHANGELOG.md)
- [ADRs](adrs/README.md)

## Documentos De Certificacao

- [Relatorio de certificacao por testes](production_test_certification_report.md)
- [Parecer final de producao](final_production_readiness_review.md)
- [Scorecard de hardening](enterprise_hardening_scorecard.md)
- [Auditoria arquitetural](architecture_audit_enterprise.md)
- [Relatorio final de hardening 2026-07-20](reports/2026-07-20-hardening-final-audit.md)

## Auditoria As-Is 2026-07-27

- [Estado atual auditado](audit/CURRENT_STATE_AUDIT.md)
- [Arquitetura as-is](audit/ARCHITECTURE_AS_IS.md)
- [Divergencias entre documentacao e codigo](audit/DOCUMENTATION_CODE_DIVERGENCES.md)
- [Mapa de implementacao LuminaAI V2](audit/LUMINAAI_V2_IMPLEMENTATION_MAP.md)
- [Baseline seguro de testes](audit/TEST_BASELINE.md)
- [Como executar os testes seguros](testing/README.md)
- [Contencao de testes e segredos](security/TEST_AND_SECRET_CONTAINMENT.md)
- [Relatorio do Prompt 03](audit/PROMPT_03_CONTRACTS_V2_REPORT.md)
- [Relatorio do Prompt 04](audit/PROMPT_04_TEMPORAL_NORMALIZER_REPORT.md)
- [Relatorio do Prompt 05](audit/PROMPT_05_COMPARISON_PLANNER_REPORT.md)
- [Contrato do Executor Comparativo V2](contracts/COMPARISON_EXECUTOR_V2.md)
- [Relatorio do Prompt 06](audit/PROMPT_06_COMPARISON_EXECUTOR_REPORT.md)
- [Apresentacao Comparativa V2](contracts/COMPARISON_PRESENTATION_V2.md)
- [Relatorio do Prompt 07](audit/PROMPT_07_COMPARISON_RENDERING_REPORT.md)

Esses documentos distinguem codigo confirmado, configuracao, testes,
documentacao historica e itens que ainda necessitam validacao em runtime.

## Nota De Atualizacao

A certificacao completa de 2026-07-09 permanece como baseline historico. O documento [Estado atual do sistema](current-status.md) registra as correcoes e validacoes incrementais executadas em 2026-07-17, 2026-07-18 e 2026-07-20.
