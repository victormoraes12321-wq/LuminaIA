-- LuminaAI core query performance checks.
-- Run against the production-like PostgreSQL clone with tenant parameters.

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT *
FROM view_catalog
WHERE tenant_id = :tenant_id
  AND ativo = TRUE
ORDER BY nome_view_oracle;

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT *
FROM search_history
WHERE user_id = :user_id
ORDER BY criado_em DESC
LIMIT 50;

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT *
FROM metadata_catalog
WHERE tenant_id = :tenant_id
  AND status = 'ACTIVE'
ORDER BY updated_at DESC
LIMIT 100;
