# ADR 0022 — Dashboard blueprints como contratos declarativos versionados

- Status: Accepted for contract-only foundation
- Data: 2026-08-04
- Contrato: `lumina.dashboard-blueprint/2.0`

## Contexto

Os blueprints existentes combinam formatos livres, JSON operacional, modelos de
banco e estratégias visuais. Eles sustentam o runtime legado e não podem ser
substituídos com segurança numa única etapa. Backend, renderer e IA futuros
precisam de linguagem fechada que não carregue SQL, fórmula, valor empresarial,
identificador físico ou autoridade de tenant/RBAC.

## Decisão

Adotar Dashboard Blueprint V2 como contrato declarativo, imutável, estrito,
versionado, separado do legado e inicialmente `CONTRACT_ONLY`.

- layouts, widgets, bindings, filtros e interações são unions/registries fechados;
- permissões no documento são requisitos, nunca grants;
- métricas/dimensões são referências canônicas, não definições;
- visual patch e semantic patch têm allowlists e revisões distintas;
- canonicalização e SHA-256 independentes viabilizam CAS/auditoria futuros;
- provenance e acessibilidade são obrigatórias;
- adapter legado produz proposta e nunca migração automática;
- versão desconhecida e conteúdo executável falham de forma fechada.

## Consequências

O contrato pode ser validado/exportado offline sem alterar produção. Há custo de
convivência com schemas/widgets legados e de adaptação explícita. Um renderer
futuro não poderá assumir suporte apenas porque um tipo existe no contrato.

## Alternativas rejeitadas

- ampliar dicionários livres legados;
- armazenar componente frontend ou código no blueprint;
- permitir SQL/fórmula no documento;
- ativar API/persistência antes de certificar tenant, CAS e rollback.

## Etapas futuras

Prompt 20 poderá implementar backend/persistência após migration aditiva,
tenant/RBAC, publicação imutável, CAS e rollback aprovados. Prompt 21 poderá
implementar renderer/editor sem recalcular números. Prompt 22 poderá propor
blueprints por IA, ainda sujeito a validação e revisão humana. Esta ADR não
autoriza nenhuma dessas etapas.

