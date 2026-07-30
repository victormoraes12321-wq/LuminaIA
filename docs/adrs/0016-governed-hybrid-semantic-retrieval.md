# ADR 0016: Recuperacao Hibrida Governada Antes Da Resolucao Canonica

## Status

Aceita para rollout controlado. Producao permanece `LEGACY_ONLY`.

## Contexto

Aliases, abreviacoes, erros de grafia e nomes iguais exigem recuperacao alem de
um mapa estatico. Um modelo generativo ou SQL livre nao pode ser autoridade de
IDs, filtros ou valores. A solucao tambem precisa respeitar tenant, RBAC,
publicacao da Knowledge Base e precedencia conversacional.

## Decisao

Adotar `lumina.semantic-retrieval/1.0` entre Context Resolution/User Profile e
Planner V2.

O indice e versionado e publicado explicitamente no PostgreSQL analitico. A
recuperacao combina canais lexicais e um feature hash local opcional. Ranking,
threshold e ambiguity sao deterministas e versionados. Somente uma decisao
unica acima do score e da margem pode produzir patch canonico.

Enterprise Knowledge publicada e `MetricRegistry` sao fontes iniciais.
Knowledge continua autoridade semantica e MetricRegistry continua autoridade
numerica. O executor nao consulta o indice.

## Consequencias Positivas

- aliases e grafias variaveis resolvem para IDs governados;
- empates exigem clarification;
- score e provenance sao auditaveis;
- nenhum modelo, rede, Oracle ou OpenAI e necessario;
- versoes publicadas sao imutaveis e permitem rollback;
- rollout shadow/hybrid nao altera comportamento legado.

## Custos

- build, publication, avaliacao e operacao do indice;
- schema v16 e novas politicas;
- estado de staleness precisa ser monitorado;
- feature hash melhora recall, mas nao equivale a embedding neural;
- build incremental inicial ainda recompila o snapshot.

## Alternativas Rejeitadas

1. LLM como canonicalizer: nao deterministico e sem autoridade de tenant.
2. Primeiro resultado sempre vence: resolve ambiguity silenciosamente.
3. Embedding externo: exporia metadados e criaria dependencia de rede.
4. JSON/RAM como indice: nao suporta replicas, CAS, auditoria ou rollback.
5. Consultar Oracle: viola a fronteira da IA e do clone analitico.

## Guardrails

- tenant e usuario derivados da autenticacao;
- permission filter antes do ranking;
- drafts, feedback bruto e dados proibidos excluidos;
- versao ativa deve estar `PUBLISHED`;
- publicacao explicita e atomica;
- patch somente em `V2_AUTHORITATIVE` e resultado `READY`;
- clarification assinada e session-scoped;
- nenhuma alteracao automatica de Knowledge, Profile ou Feedback.

## Rollback

1. Definir `SEMANTIC_RETRIEVAL_MODE=LEGACY_ONLY`.
2. Desligar flags frontend/admin/vetor/perfil.
3. Invalidar cache em memoria reiniciando replicas.
4. Se necessario, publicar snapshot anterior pelo endpoint de rollback.
5. Preservar tabelas e eventos para auditoria.

O down da migration v16 e permitido somente em PostgreSQL de teste
descartavel.
