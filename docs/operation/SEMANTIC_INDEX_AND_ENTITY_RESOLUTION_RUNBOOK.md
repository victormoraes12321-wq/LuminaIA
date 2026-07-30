# Runbook Do Indice Semantico E Resolucao De Entidades

## Escopo

Este runbook opera `lumina.semantic-retrieval/1.0`. Ele nao autoriza acesso ao
Oracle, ao banco operacional, a OpenAI ou a dados reais fora do tenant.

## Pre-condicoes

1. Backup e change aprovado para migration em ambiente alvo.
2. Migration v16 aplicada pelo mecanismo explicito do repositorio.
3. Enterprise Knowledge publicada e `MetricRegistry` valido.
4. Usuario `ADMIN` autenticado.
5. Flags de producao ainda em `LEGACY_ONLY`.
6. PostgreSQL analitico saudavel.

## Criar Definition

Use `POST /api/v2/semantic/admin/indexes/default`. A resposta informa
`index_id`, policies e `lock_version`. Repetir a operacao devolve a definition
padrao existente do tenant.

Nao habilite classificacoes pessoais ou fontes opcionais sem revisao de
privacidade, permissionamento e testes.

## Iniciar Build

Use `POST /api/v2/semantic/admin/indexes/{index_id}/build` com:

- o mesmo `index_id` na rota e no contrato;
- `expected_definition_lock_version`;
- `build_mode` FULL ou INCREMENTAL;
- `idempotency_key` unica da operacao.

A chave bruta nao e persistida. Retry com a mesma chave retorna a mesma versao
concluida. Uma chave em build/failed gera conflito tipado.

O build deve terminar `READY`, nunca `PUBLISHED`.

## Inspecionar

Verifique:

- source manifest e checksums;
- source versions;
- document/entity/alias/relation counts;
- provider e representation version;
- blocked document count;
- build start/completion;
- version checksum;
- audit events;
- avaliacao sintetica.

Use o Search Inspector apenas com termos sinteticos ou empresariais permitidos.
Ele nao persiste a consulta por padrao.

## Validar

Antes da primeira publicacao:

1. Execute corpus sintetico versionado.
2. Confirme `passed=true`.
3. Confirme forbidden leakage e cross-tenant leakage iguais a zero.
4. Confirme deterministic repeatability igual a um.
5. Teste alias, ambiguity, unresolved, tipo e dominio.
6. Confirme que `CONSULTA` nao recebe score interno ou vetor.
7. Confirme que outro tenant recebe not found sem enumeracao.

O endpoint nao altera ranking ou publica automaticamente.

## Publicar

Use `POST /api/v2/semantic/admin/indexes/{index_id}/publish` com version,
lock version esperado e motivo.

A operacao exige:

- version `READY`;
- checksum e build completo;
- fonte tenant-scoped;
- manifest nao vazio;
- provider compativel;
- revisao registrada;
- CAS da definition.

Depois da publicacao, confirme:

- ponteiro ativo;
- version `PUBLISHED`;
- versao anterior `DEPRECATED`;
- publication history;
- evento;
- cache invalidado.

## Detectar Stale Source

Use `GET /api/v2/semantic/admin/indexes/{index_id}/stale-sources`.

O sistema compara source version e checksum do manifest ativo com o snapshot
governado atual. A leitura nao muta a versao publicada. Havendo item stale:

1. verifique a publicacao da fonte;
2. execute novo FULL/INCREMENTAL build;
3. avalie;
4. publique explicitamente;
5. confirme lista stale vazia.

Nunca edite o manifest ativo.

## Rollback

Use `POST /api/v2/semantic/admin/indexes/{index_id}/rollback` com uma versao
anteriormente publicada, lock version atual e motivo.

Confirme novo registro de publication, evento de rollback, ponteiro ativo e
invalidation do cache. O historico anterior deve permanecer.

## Deprecation

Uma version `READY` nao ativa pode ser depreciada. A version ativa e recusada.
Para substituir a ativa, publique outra versao primeiro.

## Clarification

Quando o chat exibir opcoes:

- cada opcao deve ter label, tipo, dominio e provenance publica;
- o cliente devolve apenas o token assinado recebido;
- tenant, usuario e sessao devem ser os mesmos;
- expiracao ou replay falham;
- IDs arbitrarios nao sao aceitos.

Para incidentes, procure apenas IDs e reason codes na auditoria. Nao registre a
pergunta integral.

## Modos De Rollout

1. `LEGACY_ONLY`: baseline e rollback.
2. `SHADOW`: mede estrutura; nao altera intent.
3. `HYBRID_READ`: habilita busca/API; nao altera intent.
4. `V2_AUTHORITATIVE`: aplica patch `READY`.

Promova um tenant por vez. Exija janela de observacao, zero leakage, taxa de
ambiguity conhecida e rollback ensaiado.

## Flags

- `SEMANTIC_RETRIEVAL_MODE`
- `SEMANTIC_RETRIEVAL_FRONTEND_ENABLED`
- `SEMANTIC_ENTITY_INSTANCE_INDEXING_ENABLED`
- `SEMANTIC_VECTOR_CHANNEL_ENABLED`
- `SEMANTIC_PROFILE_TIE_BREAKER_ENABLED`
- `SEMANTIC_APPROVED_FEEDBACK_CORPUS_ENABLED`
- `SEMANTIC_RESTRICTED_ENTITIES_ENABLED`
- `SEMANTIC_ADMIN_INSPECTOR_ENABLED`
- `SEMANTIC_RETRIEVAL_CACHE_ENABLED`
- `SEMANTIC_INCREMENTAL_BUILD_ENABLED`

Todas ficam desligadas por padrao, exceto parametros inertes de tamanho/TTL.

## Alertas

Investigue:

- aumento de `ambiguous`, `unresolved` ou `blocked`;
- `cross_tenant_denial`;
- `forbidden_content`;
- `build_failed`;
- `stale_source`;
- conflitos repetidos de CAS;
- queda de repeatability;
- leakage diferente de zero;
- crescimento anormal de latencia.

Telemetria nao contem pergunta, valor, SQL ou dataset.

## Recuperacao De Incidente

1. Defina modo `LEGACY_ONLY`.
2. Desligue frontend/admin e canais opcionais.
3. Reinicie apenas replicas do LuminaAI para limpar cache em memoria.
4. Preserve banco e logs de auditoria.
5. Identifique index/version/tenant pelos IDs estruturais.
6. Valide fonte e checksum.
7. Faça rollback ou novo build, conforme causa.
8. Repita suite isolada e avaliacao antes de reativar.

## Migration

`migration_v16_0.py` possui up aditivo/idempotente, verificacao e down
test-only. Nao roda no startup. Nao usa Alembic, `create_all` ou extensao
obrigatoria.

No teste:

```powershell
docker compose -f docker-compose.test.yml up -d --wait
.\scripts\run-backend-tests-safe.ps1 tests/test_semantic_retrieval_migration.py -q
docker compose -f docker-compose.test.yml down -v
```

Nunca aponte o runner para porta 5432 ou banco sem nome de teste.

## Checklist De Encerramento

- active version publicada e checksum presente;
- stale sources vazias;
- avaliacao aprovada;
- audit timeline coerente;
- `CONSULTA` redigido;
- cross-tenant negado;
- cache invalidado;
- producao no modo aprovado;
- rollback documentado;
- nenhum segredo ou dado real no relatorio.
