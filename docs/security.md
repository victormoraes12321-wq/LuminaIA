# Seguranca

## Semantic Retrieval V2

O indice e tenant-scoped e permission-aware. Filtros de classificacao, papel,
tipo e dominio ocorrem antes de score e exposicao. Draft, feedback bruto, PII
proibida, credenciais, prompt injection e instrucoes executaveis sao
recusados no build.

Clarification usa token HMAC, tenant, usuario, sessao, expiracao e CAS. Cache
inclui fingerprint de permissoes. `CONSULTA` nao recebe vetores nem breakdown
interno. O modulo nao acessa Oracle, OpenAI, rede externa ou SQL livre.

## JWT E Sessoes

- JWT e gerado/validado em `backend/services/auth_service.py` com PyJWT.
- Login/logout/sessao em `backend/routers/auth.py`.
- Frontend usa `frontend/proxy.ts` para proteger rotas e redirecionar usuario conforme token/senha obrigatoria.
- Em desenvolvimento local, a API deve manter o mesmo host loopback do navegador (`localhost` ou `127.0.0.1`) para o cookie HttpOnly ser enviado corretamente.
- `Authorization: Bearer __lumina_cookie_session__` e tratado como sentinela para permitir que o backend leia o token real do cookie.

## Multi Tenant

- Tenant e associado ao usuario autenticado.
- Routers e services devem filtrar por `current_user.tenant_id`.
- RLS nativo de banco nao foi identificado; isolamento e aplicado na camada backend.

## Permissoes E Papeis

- Modelo `UserRole`: `ADMIN`, `GESTOR`, `CONSULTA`.
- Dependencias: `check_admin_role`, `check_admin_or_gestor_role`, `enforce_password_change`.
- Admin gerencia usuarios/catalogos/configuracoes conforme endpoints.

## Criptografia

- `ENCRYPTION_KEY` usa Fernet para dados sensiveis de conexao Oracle.
- Senhas usam Passlib/bcrypt.
- JWT usa `SECRET_KEY` e algoritmo configurado.

## Context Guard E Prompt Injection

- `backend/services/context_guard.py` valida consultas e parametros contra termos proibidos/injecao/escopo.
- IA recebe contexto estruturado, mas execucao passa por planner/validator/backend.
- Perguntas criticas de vendas passam por caminho deterministico no backend quando possivel, reduzindo dependencia de texto generativo para calculos sensiveis.

## OWASP E Headers

- Nginx define headers basicos: X-Frame-Options, X-Content-Type-Options, Referrer-Policy, HSTS e CSP.
- CSP atual contem `unsafe-inline`; recomendada evolucao futura com nonce/hash sem quebrar Next.js.

## Rate Limit

Middleware de rate limit dedicado nao foi identificado no codigo. Para producao publica, aplicar no Nginx/API Gateway ou implementar middleware especifico.

## Backup E Restore

- Script `scripts/backup-db.sh` existe para backup.
- Endpoints de security center/backup/restore existem em `routers/query.py` como parte da plataforma de seguranca.
- Teste real de restore deve ser feito no ambiente final.

## LGPD

O codigo possui multi-tenant, autenticacao, auditoria e controles administrativos. Politicas formais de retencao/exclusao LGPD devem ser definidas operacionalmente conforme contrato do cliente.

## Privacidade Do Perfil Analitico

O perfil V2 usa escopo composto de tenant e usuario em toda leitura e escrita.
Rotas `/api/v2/me` derivam o dono da autenticacao e recusam mass assignment.
Defaults analiticos exigem consentimento explicito, podem ser revogados e sao
divulgados na resposta.

O perfil nao guarda pergunta, resposta, dataset, SQL, bind, credencial ou
valor empresarial. Exportacao e pedido idempotente de exclusao pertencem
somente ao dono. `ADMIN` pode consultar politica e auditoria minimizada, mas
nao assumir silenciosamente o perfil privado de outro usuario. Runbook:
[`operation/USER_PROFILE_PRIVACY_RUNBOOK.md`](operation/USER_PROFILE_PRIVACY_RUNBOOK.md).
