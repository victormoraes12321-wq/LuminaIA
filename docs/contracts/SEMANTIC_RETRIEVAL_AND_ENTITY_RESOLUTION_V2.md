# Semantic Retrieval And Entity Resolution V2

## Status

- Contrato: `lumina.semantic-retrieval/1.0`.
- Normalizador: `lumina.semantic-normalizer.pt-BR/1.0`.
- Ranking: `lumina.semantic-ranking/1.0`.
- Thresholds: `lumina.semantic-thresholds/1.0`.
- Provider local: `lumina.deterministic-feature-hash/1.0`.
- Migration: v16, explicita e aditiva.
- Producao: `SEMANTIC_RETRIEVAL_MODE=LEGACY_ONLY`.
- Autoridade V2: desligada por padrao.

## Objetivo

O modulo recupera referencias empresariais publicadas, resolve mencoes para
IDs canonicos e produz um patch tipado para o `QueryIntentV2`. Ele nao calcula
metricas, nao gera SQL, nao executa consultas analiticas e nao altera o
conhecimento empresarial.

## Fronteiras De Autoridade

| Area | Autoridade |
|---|---|
| Definicoes e aliases empresariais | Enterprise Knowledge publicada |
| Formula e unidade numerica | `MetricRegistry` |
| Periodo | `TemporalNormalizer` |
| Contexto ativo | Context Resolution e Conversation State |
| Preferencia pessoal consentida | User Analytical Profile |
| Exemplos supervisionados | Feedback aprovado e corpus explicitamente habilitado |
| Planejamento | Planner V2 |
| Numeros | Executor governado |
| Recuperacao e resolucao | Semantic Retrieval V2 |

Oracle, OpenAI, banco operacional, SQL livre, dataset de resposta e historico
bruto do chat sao fontes proibidas.

## Fluxo

1. O Context Resolution aplica precedencia explicita e heranca governada.
2. O User Profile pode fornecer somente desempate fraco consentido.
3. O extrator deterministico identifica mencoes de metrica, dimensao, entidade,
   campo de filtro e valor de filtro.
4. O retrieval consulta somente a versao `PUBLISHED` ativa do tenant.
5. Permissoes, tipo esperado e dominio sao filtrados antes do ranking.
6. Candidatos limitados recebem score deterministico e breakdown.
7. Threshold e margem produzem `RESOLVED`, `AMBIGUOUS` ou `UNRESOLVED`.
8. Ambiguidade cria clarification persistida, com opcoes assinadas.
9. Somente em `V2_AUTHORITATIVE` um resultado `READY` altera o intent.
10. O planner recebe IDs canonicos; o executor nunca consulta este indice.

## Document Types

- `BUSINESS_TERM`
- `METRIC`
- `KPI`
- `DIMENSION`
- `ENTITY_TYPE`
- `ENTITY_INSTANCE`
- `BUSINESS_RULE`
- `ALIAS`
- `RELATION`
- `APPROVED_EXAMPLE`
- `SYSTEM_CONCEPT`

## Entity Types

O contrato tipa metrica, dimensao, conceito, filial, regiao, vendedor, cliente,
produto, categoria, fornecedor e outras entidades permitidas. `UNKNOWN` nao e
indexado na definicao padrao. Instancias pessoais ficam desabilitadas no
rollout inicial.

## Classificacao

Permitidas no indice padrao:

- `PUBLIC_BUSINESS_METADATA`
- `TENANT_BUSINESS_METADATA`

`RESTRICTED_BUSINESS_METADATA` exige politica e permissao explicitas.
`PERSONAL_DATA`, `SENSITIVE_PERSONAL_DATA` e `FORBIDDEN` nao entram no indice
padrao. Vetores nao sao criados para classificacao proibida.

## Fontes

Fontes iniciais:

- Enterprise Knowledge: somente versoes publicadas e vigentes.
- `MetricRegistry`: IDs, labels, unidades e dimensoes permitidas; nunca valores.

Fontes opcionais, todas desligadas por padrao:

- instancias de entidades analiticas;
- exemplos de feedback aprovados;
- catalogo tecnico curado;
- conceitos de sistema.

Drafts, review comments, feedback bruto e resposta do usuario nao sao fontes.

## Normalizacao pt-BR

O normalizador usa NFKC, case fold, remocao deterministica de diacriticos,
pontuacao controlada, colapso de espacos, stopwords controladas e trigramas.
Codigos com digitos preservam zeros a esquerda e separadores permitidos.
Palavras comuns com hifen sao tokenizadas; o texto original nao e mutado.

Entradas vazias, maiores que 500 caracteres ou com controles proibidos falham.
O checksum inclui tokens, codigo possivel, locale e versao do normalizador.

## Canais De Recuperacao

- canonical ID exato;
- alias publicado exato;
- label exato;
- igualdade normalizada;
- prefixo controlado;
- token overlap;
- similaridade de trigramas;
- feature hash local opcional;
- compatibilidade de tipo;
- compatibilidade de dominio;
- compatibilidade de contexto;
- desempate fraco de perfil.

O runtime busca um conjunto lexical limitado antes de qualquer similaridade
local. Ele nao carrega todo o indice em memoria.

## Provider Local

O provider obrigatorio inicial usa SHA-256 signed feature hashing, dimensao 256
por padrao e normalizacao L2. E deterministico, nao neural, nao baixa modelo e
declara `network_required=false`. Cosine e calculado somente em candidatos
limitados quando a flag vetorial esta habilitada.

## Ranking E Thresholds

O score usa a maior contribuicao de identidade, acrescida apenas de boosts
governados e subtraida de penalidades. Ordem de entrada nao altera o resultado.
Pesos, precisao, penalidades e checksum pertencem a
`lumina.semantic-ranking/1.0`.

Politica padrao:

- score minimo de recuperacao: `0.30`;
- score minimo de resolucao automatica: `0.72`;
- margem minima contra segundo candidato: `0.08`;
- maximo publico: 10 candidatos;
- maximo interno: 100 candidatos;
- bands: LOW, MEDIUM, HIGH e EXACT.

Empate ou margem insuficiente nunca seleciona arbitrariamente o primeiro.

## Compatibilidade

Tipo explicito e dominio explicito sao filtros fail-closed antes do ranking.
Contexto e perfil nunca substituem um pedido explicito. Perfil possui peso
maximo fraco e so participa quando consentido e habilitado.

Referencias `DEPRECATED` nao entram em novos resultados. Versoes de indice
depreciadas continuam disponiveis apenas para rollback e auditoria.

## Patch Do Intent

Operacoes:

- `SET_CANONICAL_METRIC`
- `SET_CANONICAL_DIMENSION`
- `SET_CANONICAL_ENTITY`
- `SET_CANONICAL_FILTER_FIELD`
- `SET_CANONICAL_FILTER_VALUE`
- `ATTACH_PROVENANCE`
- `CREATE_CLARIFICATION`
- `MARK_UNRESOLVED`

Campo e valor de filtro sao mencoes independentes. A aplicacao associa cada
operacao ao `mention_id` e ao identificador de origem, preservando operador,
cardinalidade, explicitness e filtros nao relacionados.

## Clarification

Uma ambiguidade pode criar uma clarification `PENDING` com tenant, usuario,
sessao, mencao, versao do indice, expiracao e checksum das opcoes. Cada opcao
usa token HMAC. A resposta valida:

- tenant e usuario autenticados;
- sessao;
- estado pendente;
- prazo;
- token integrante das opcoes persistidas;
- assinatura;
- compare-and-swap de `PENDING` para `RESOLVED`.

IDs arbitrarios enviados pelo cliente nao sao aceitos.

## Indices E Versoes

Uma definition guarda locale, tipos, fontes, classificacoes, provider,
policies, owner, ponteiro ativo e `lock_version`.

Cada build cria uma nova version imutavel com:

- numero crescente;
- lifecycle;
- source manifest;
- contagens;
- provider version;
- modo FULL ou INCREMENTAL;
- watermark;
- hash de idempotencia;
- checksum;
- atores e timestamps.

A idempotency key bruta nao e persistida. Seu hash e unico por tenant e indice.
Um retry concluido retorna a mesma versao.

## Build E Publicacao

O build valida escopo de tenant, fontes, classificacao, conteudo, provider,
normalizacao, representacoes, contagens e checksum. Ele termina em `READY` e
nunca publica automaticamente.

A publicacao exige `READY`, manifest nao vazio, fontes tenant-scoped, checksum,
build completo, provider compativel, revisao registrada e CAS da definition.
Ponteiro ativo, lifecycle e publication history pertencem a mesma transacao.
O cache do tenant/indice e invalidado.

O trigger PostgreSQL recusa mudanca estrutural de versoes publicadas,
depreciadas ou arquivadas.

## Incremental, Tombstone E Stale

O contrato aceita watermark e modo `INCREMENTAL`, mas o provider inicial
reconstroi o snapshot completo governado. Tombstones diferenciais e job
assincorno permanecem divida registrada. Nenhuma versao publicada e mutada.

Staleness e calculada comparando source version e checksum do manifest ativo
com o snapshot governado atual. A inspecao e read-only e exige novo build para
alterar o runtime.

## Rollback E Deprecation

Rollback promove uma versao anteriormente publicada e cria novo registro de
publication. Historico nao e apagado. Deprecation explicita recusa a versao
ativa; uma publicacao substituta deve ocorrer primeiro.

## Cache

A chave inclui tenant, fingerprint de permissoes, indice, versao, policies,
locale, hash da consulta normalizada, tipo, dominio, contexto, perfil e `top_k`.
O cache e limitado, usa copia profunda e TTL curto. Nao e autoridade.

Invalidacoes ocorrem em publicacao e rollback. Mudanca de versao torna chaves
anteriores inacessiveis mesmo antes da expiracao.

## RBAC

`CONSULTA` pode buscar, resolver e ler detalhe publico permitido. Nao recebe
vetor bruto nem breakdown tecnico. `GESTOR` pode inspecionar score, avaliar e
ler auditoria. `ADMIN` possui as permissoes administrativas; a feature
administrativa tambem precisa estar habilitada.

O backend aplica a decisao final. O tenant e o usuario nunca vem do payload.

## APIs

Runtime:

- `GET /api/v2/semantic/capabilities`
- `POST /api/v2/semantic/search`
- `POST /api/v2/semantic/resolve`
- `POST /api/v2/semantic/entities/resolve`
- `GET /api/v2/semantic/candidates/{document_id}`
- `POST /api/v2/semantic/clarifications/{id}/resolve`

Admin:

- create/list/update definitions;
- list/inspect versions;
- build, publish, rollback e deprecate;
- export manifest;
- inspect score;
- inspect stale sources;
- run/list evaluations;
- observability e audit timeline.

Listas possuem limites; audit e evaluation usam cursor temporal. Payloads
Pydantic usam `extra=forbid`.

## Erros

Erros usam codigos `SEMANTIC_*` e `ENTITY_*`, status HTTP tipado e mensagem
publica sem enumerar outro tenant. Casos principais cobrem not found, denied,
tenant mismatch, conflict, not ready, immutable, provider, query, ambiguity,
unresolved, invalid reference, expired clarification, invalid option, stale e
forbidden content.

## Auditoria E Observabilidade

Eventos guardam somente IDs de escopo, tipo, reason code, fingerprint
estrutural e metadados sem pergunta ou dado empresarial. Contadores usam
allowlist e nao registram texto, score individual, SQL ou dataset.

## Avaliacao

O corpus e sintetico, tenant-scoped e versionado. A avaliacao usa a versao
publicada e mede top-1, top-k, ambiguity, unresolved, leakage, exact match,
alias, repetibilidade e latencia. Decisao e canais obrigatorios fazem parte do
resultado; avaliacao nao publica nem altera ranking.

## Rollout

- `LEGACY_ONLY`: nenhum read ou autoria V2.
- `SHADOW`: executa estruturalmente; nao altera intent.
- `HYBRID_READ`: APIs e leitura V2; nao altera intent.
- `V2_AUTHORITATIVE`: aplica patch apenas quando `READY`.

Todas as flags iniciam desligadas. Ativacao exige migration v16, indice
publicado, avaliacao aprovada, teste multi-tenant, observabilidade e rollback
ensaiado.

## Seguranca

- nenhuma chamada Oracle ou OpenAI;
- nenhum download de modelo;
- sem SQL livre;
- permission filter antes de score e exposicao;
- bloqueio de PII, credencial, prompt injection e instrucoes executaveis;
- vetores e breakdown interno ocultos de `CONSULTA`;
- checksum, HMAC, CAS, limites e escopo composto;
- nenhuma pergunta, resposta, dataset, SQL, bind ou credencial persistida.

## Limitacoes Conhecidas

- build incremental ainda reconstroi snapshot completo;
- tombstones diferenciais ainda nao possuem provider;
- build e avaliacao sao jobs sincronos;
- provider vetorial e feature hash, nao embedding neural;
- entidades pessoais/restritas permanecem desligadas;
- integracao permanece atras de feature flags.

Essas limitacoes estao registradas no Technical Debt Register e nao autorizam
afrouxar tenant, permission, imutabilidade ou threshold.
