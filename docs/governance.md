# Governanca

## Indice Semantico

Enterprise Knowledge publicada e `MetricRegistry` sao as fontes iniciais. O
indice nao aprova conhecimento, nao altera formulas e nao aprende com feedback
automaticamente. Build cria `READY`; publication e rollback sao atos
explicitos com CAS, historico e auditoria.

Versoes publicadas sao imutaveis. Staleness exige novo build. O rollout segue
`LEGACY_ONLY`, `SHADOW`, `HYBRID_READ` e `V2_AUTHORITATIVE`, com producao no
primeiro modo ate aprovacao operacional.

## Arquitetura Oficial

IA -> Planner -> Validator -> Business Layer -> Enterprise Knowledge Layer -> Backend -> Data Engine -> Frontend -> Insight Layer -> Cache Layer -> Security Layer

## Controle De Mudancas

- Mudancas de camada/responsabilidade exigem ADR.
- Mudancas de API exigem compatibilidade ou versao.
- Mudancas de banco exigem migration e plano de rollback.
- Mudancas de IA exigem validacao de nao alucinacao, modelo autorizado e testes.

## Responsabilidades

- IA: interpretacao, estrategia, blueprint/resposta.
- Backend: execucao, calculo, validacao, persistencia e integracoes.
- Business Layer: regra e semantica de negocio.
- Data Platform: catalogos, sync, runtime, packages e lineage.
- Frontend: renderizacao e interacao.
- Security Layer: autenticacao, autorizacao, auditoria e protecoes.

## Versionamento

Versionar blueprints, metadata, packages, templates, instances e documentos arquiteturais.

## Preferencias Pessoais

`lumina.user-analytical-profile/1.0` governa preferencias duraveis. Pedido
explicito e contexto vencem o perfil. Defaults analiticos requerem
consentimento e transparencia; inferencia observacional nunca e promovida sem
confirmacao. Referencias pessoais apontam para IDs canonicos publicados e nao
alteram Knowledge Base, `MetricRegistry`, planner ou executor.

Depreciacoes e dividas relacionadas ficam em
[`architecture/DEPRECATION_LEDGER.md`](architecture/DEPRECATION_LEDGER.md) e
[`architecture/TECHNICAL_DEBT_REGISTER.md`](architecture/TECHNICAL_DEBT_REGISTER.md).
