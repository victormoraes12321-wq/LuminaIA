# Dashboard AI Assistance V2

Versão: `lumina.dashboard-ai-assistance/1.0`.

## Escopo e autoridades

Esta camada cria propostas governadas para novos dashboards e para alterações semânticas ou visuais. O modelo serve apenas para interpretar intenção. IDs canônicos são resolvidos por catálogo governado; o Blueprint V2 e os patches são sintetizados e validados deterministicamente. O Prompt 20 é a única autoridade de persistência de dashboards e revisões, e o Prompt 21 é a autoridade de apresentação.

A camada não consulta dados analíticos, não executa SQL, não abre Oracle, não publica, não aprova, não faz rollback, não gerencia colaboradores e não transfere ownership. Nenhum número empresarial é inventado ou exibido no preview.

## Contratos e fluxo

Os contratos Pydantic v2 ficam em `backend/contracts/dashboard_ai_assistance_v2/`, com `strict=True`, `extra="forbid"`, objetos congelados, enums fechados e limites de tamanho. O lifecycle estático é:

`RECEIVED → ANALYZING → RESOLVING → SYNTHESIZING → VALIDATING → READY_FOR_REVIEW → ACCEPTED → APPLYING → APPLIED`.

Há saídas governadas para `NEEDS_CLARIFICATION`, `REJECTED`, `BLOCKED`, `FAILED`, `CANCELLED`, `SUPERSEDED` e `EXPIRED`. Aceite e aplicação são operações distintas. Revisão cria nova `proposal version` imutável e usa CAS.

## Segurança

Tenant, usuário, papel, ownership e grants vêm exclusivamente da autenticação e do backend do Prompt 20. `CONSULTA` não cria nem aplica propostas. `GESTOR` e `ADMIN` operam somente dentro das capacidades efetivas do recurso. Entradas que tentem injetar instruções, SQL, shell, HTML/JavaScript, provider, tools, permissões ou blueprint bruto falham de forma fechada.

Somente tools estáticas de metadados, catálogo, normalização temporal, validação de Blueprint e validação de patch são permitidas. A allowlist não contém executor analítico, Oracle, SQL, filesystem, shell ou rede.

## Persistência e aplicação

A migration explícita v23 cria propostas, versões, clarificações, evidências, decisões, runs, auditoria e avaliações. Histórico é imutável por trigger. Chaves compostas preservam tenant, ator, dashboard e revisão. O `create_all` não cria essas tabelas.

Aplicar uma proposta exige versão aceita, decisão humana persistida, checksum íntegro, CAS e idempotência. Criação gera apenas dashboard `DRAFT`; patches geram apenas nova revisão `DRAFT`. Publicação continua exclusivamente no workflow humano do Prompt 20.

## Rollout

Modos: `LEGACY_ONLY`, `SHADOW_ANALYZE`, `AI_PROPOSAL_PREVIEW`, `AI_DRAFT_CREATE` e `AI_ASSISTED_EDIT`. Produção permanece em `LEGACY_ONLY`, APIs e frontend desligados, allowlist vazia e provider fake desligado. O provider fake determinístico existe apenas sob `LUMINA_TESTING=true`; nenhum provider real foi habilitado.

Schemas exportados: `docs/contracts/dashboard_ai_assistance_v2/schemas.json`. Goldens sintéticos: `backend/tests/golden/dashboard_ai_assistance_v2.json`.
