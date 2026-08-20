# ADR 0024 — Interface governada e side chat contextual de dashboards

- Status: Accepted for controlled rollout, disabled by default
- Data: 2026-08-05
- Contrato: `lumina.dashboard-ui-sidechat/1.0`

## Contexto

Prompts 19 e 20 criaram contrato declarativo e backend governado, mas não havia
página, renderer, editor ou conversa contextual. O grafo legado também executava
corretamente mudanças visuais locais, porém as rotulava `FULL_RENDERING`,
mantendo `LUMINA-GAP-DASH-001` aberto.

## Decisão

Adotar interface V2 server-guarded, registry estático de 16 widgets, renderer
sem matemática analítica, editor manual separado em visual/semântico e side chat
sobre a API conversacional existente. O contexto e a ação são unions fechadas.
UI_MODIFIED exige confirmação backend e checksum semântico preservado. Produção
continua LEGACY_ONLY; Sidebar e requests V2 desaparecem nesse modo.

Corrigir o grafo legado para copiar profundamente o estado anterior e devolver
UI_MODIFIED quando a operação realmente é visual-only. Não criar endpoint,
migration, tabela, runtime, cache, SQL compiler ou autoridade de IA.

## Consequências

Frontend e backend precisam estar habilitados. Há custo adicional de testes em
quatro viewports e conflitos CAS são apresentados ao usuário em vez de serem
resolvidos por last-write-wins. O query schema ganha envelope/contexto e ação
opcionais, mas paths/operações HTTP não aumentam.

Chart type continua semântico no Blueprint 2.0; uma troca persistente não pode
ser disfarçada de visual patch. Ela fica bloqueada/encaminhada ao editor até uma
decisão versionada futura. Prompt 22 não é autorizado e não poderá publicar,
aprovar ou executar rollback automaticamente.

## Alternativas rejeitadas

- segunda plataforma ou endpoint de chat;
- executar texto livre, HTML, JavaScript ou URL do modelo;
- confiar em tenant/role/capability do browser;
- recalcular delta, percentual, ranking ou “Outros” no frontend;
- registry/import path vindo do blueprint;
- full rendering como fallback genérico;
- alterar o teste DASH-001 para aceitar o comportamento incorreto;
- ativar V2 por padrão ou modificar lockfiles.
