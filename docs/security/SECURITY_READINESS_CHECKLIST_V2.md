# Security Readiness Checklist V2

Versão: `lumina.security-migration-rollout/1.0`.

- [x] threat model produzido antes da implementação;
- [x] tenant e usuário removidos de headers arbitrários em Validation V2;
- [x] roles/capabilities extraídos de autoridade autenticada e deny-by-default;
- [x] IDOR de evaluation run usa tenant + concealment 404;
- [x] trace in-memory sem owner é ocultado até storage tenant-scoped;
- [x] inspector valida path, sanitiza trace e replay falha fechado;
- [x] raw SQL, binds, dataset, traceback, secret e CoT redigidos;
- [x] exceção genérica pública é constante;
- [x] cookie auth mutável exige Origin permitido; bearer não depende de CSRF;
- [x] CORS wildcard + credentials é recusado;
- [x] headers nosniff/frame/referrer/permissions/CSP; HSTS só em produção;
- [x] input e paginação existentes permanecem limitados;
- [x] queue stats tenant-scoped; replay apenas `DEAD_LETTER`;
- [x] performance é ADMIN, `test` e modo explícito;
- [x] configuração produtiva inválida falha fechada;
- [x] oito kill switches mais emergency disable ativos por padrão;
- [x] canary determinístico, server-side, production-denied pelo baseline;
- [x] migration v27 `NOT_REQUIRED`; V1–V26 não editadas pelo Prompt 26;
- [x] schema future/drift/missing migration bloqueiam readiness;
- [x] advisory lock possui aquisição, contenção e release testados;
- [x] rollback matrix cobre todas as oito features;
- [x] sete suites de segurança adicionadas ao registry Prompt 24;
- [x] métricas novas têm labels fechadas e sem tenant/user/request/resource ID;
- [ ] canary/SLO/load/penetration/DR produtivos — dependem de ambiente real futuro.
