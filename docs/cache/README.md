# Cache

## Implementacao Atual

O cache identificado no codigo e majoritariamente em memoria, com foco em intencoes, planos, packages e diagnosticos.

## Modulos

- `backend/services/cache_service.py`: IntelligentCachingPlatform.
- `backend/services/data_platform/package_cache.py`: cache de Analytical Packages.
- Endpoints em `backend/routers/query.py`: stats e limpeza de cache.

## Tipos Documentados

- Blueprint Cache: reuso de blueprint/fingerprint.
- Query Cache: cache de interpretacao/plano, quando usado pelo QIE.
- Analytical Package Cache: package cache intelligence.
- Metadata/Runtime/Dashboard Cache: representados em payloads e centros de cache/trust quando fornecidos pela Data Platform.

## Invalidation E TTL

TTL e invalidacao dependem da implementacao dos caches em memoria e endpoints de limpeza. Para producao multi-instancia, avaliar cache distribuido se necessario.

## Restricao Oficial

Cache nao deve substituir consulta atualizada de dados quando a politica exigir atualizacao. Reutiliza-se inteligencia/blueprint, nao resposta factual obsoleta.
