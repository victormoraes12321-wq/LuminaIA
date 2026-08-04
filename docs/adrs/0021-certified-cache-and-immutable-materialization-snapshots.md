# ADR 0021 — Cache certificado e snapshots imutáveis de materialização

Status: aceito para implementação isolada; rollout não autorizado.

## Contexto

Reutilizar respostas analíticas sem prova de tenant, permissions, freshness e
certificação pode servir dados incorretos ou de outro escopo. Materializações
mutáveis também dificultam auditoria, refresh seguro e rollback.

## Decisão

Adotar `lumina.smart-cache-materialization/1.0`. Cacheability é decidida por
motor determinístico sobre resultados do Safe Analytical PostgreSQL já
certificados por Validation & Provenance. A key é server-controlled e inclui
tenant, permissions, versões, fingerprints, watermark e generations.

Materializações são definitions versionadas e snapshots imutáveis. Build gera
somente snapshot `READY`; publicação troca um ponteiro por CAS e mantém o
anterior. Refresh não publica. Rollback é nova troca auditada de ponteiro.
Dependency tags e generations governam invalidação; leases tenant-scoped
evitam stampede; GC é limitado e preserva rollback.

A migration V21 é explícita, idempotente e tenant-scoped. O runtime permanece
`LEGACY_ONLY` e a API experimental exige também a flag administrativa.

## Consequências

Há mais metadados, fingerprints, estados e operações CAS, mas números nunca
são recalculados pelo cache, publicação é reversível e cross-tenant falha no
banco e na aplicação. V21, writes, materializações e frontend permanecem
desligados até rollout operacional futuro.

## Alternativas rejeitadas

- cachear por texto da pergunta: aliases e permissions tornam a chave insegura;
- TTL enviado pelo cliente: contorna a política de freshness;
- materialização mutável: perde proveniência e rollback;
- auto-publicar após build: mistura execução, validação e decisão governada;
- Redis/novo pacote nesta fase: cria dependência e não substitui a governança.
