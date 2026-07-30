# Perfil Analitico Governado V2

## Contrato

O contrato `lumina.user-analytical-profile/1.0` representa preferencias
pessoais, explicitas, versionadas e isoladas por `tenant_id` e `user_id`. Ele
nao e memoria conversacional, historico de busca, base de conhecimento,
registro de metricas nem fonte numerica.

Fontes de verdade:

1. `backend/contracts/user_analytical_profile_v2/`;
2. `backend/services/user_analytical_profile/`;
3. `backend/models/user_analytical_profile.py`;
4. `backend/database/migration_v14_0.py`;
5. schemas em `docs/contracts/schemas/`.

## Autoridade E Precedencia

O motor e puro e deterministico. Ele e executado depois da resolucao de
contexto e antes do planner. A precedencia e:

1. seguranca e allowlists do tenant;
2. reset;
3. remocao explicita;
4. correcao explicita;
5. pedido atual explicito;
6. normalizacao temporal;
7. identificador canonico;
8. contexto conversacional;
9. esclarecimento pendente;
10. perfil consentido;
11. politica administrativa;
12. default deterministico;
13. inferencia de intencao;
14. adaptador legado.

Uma preferencia preenche somente um campo semanticamente vazio. Ela nao altera
formula, valor, SQL, bind, tenant, papel, Knowledge Base, `MetricRegistry`,
planner ou executor. Reset, remocao e negacao impedem a reaplicacao no mesmo
turno.

## Conteudo Permitido

O perfil aceita:

- apresentacao, localidade e acessibilidade;
- defaults analiticos consentidos;
- metricas, dimensoes e entidades favoritas por identificador canonico;
- referencias a filtros, consultas e dashboards salvos;
- preferencias de interacao, privacidade e retencao.

O perfil nao persiste perguntas, respostas, datasets, documentos, SQL, binds,
credenciais, schema fisico, valores empresariais ou texto livre executavel.
Referencias a conhecimento so sao validas quando o ativo esta publicado,
vigente, acessivel e pertence ao tenant autenticado.

## Risco E Consentimento

| Classe | Uso |
|---|---|
| `SAFE_PRESENTATION` | Pode ser aplicada sem alterar semantica analitica. |
| `VISIBLE_ANALYTICAL_DEFAULT` | Exige consentimento ativo e divulgacao na resposta. |
| `REFERENCE_ONLY` | Guarda somente identificador governado. |
| `RESTRICTED` | Exige politica especifica; falha fechada por padrao. |
| `FORBIDDEN` | Nunca e persistida nem aplicada. |

Consentimento possui finalidade, escopo, versao de politica, checksum e
controle otimista. Revogacao interrompe a aplicacao imediatamente, sem apagar
o evento minimo de auditoria.

## Ciclo De Vida

Perfis: `ACTIVE`, `DISABLED`, `DELETION_PENDING`, `DELETED`.

Preferencias: `ACTIVE`, `DISABLED`, `EXPIRED`, `REVOKED`, `DELETED`,
`PENDING_CONFIRMATION`.

Toda escrita usa `lock_version` e compare-and-swap. Checksums sao calculados
sobre representacao JSON canonica. Exclusao de item e soft delete. Solicitacao
de exclusao do perfil exige chave de idempotencia.

## Integracao

- O frontend usa exclusivamente `/api/v2/me/...`; o dono nao vem do path nem
  do payload.
- O backend deriva tenant, usuario e papel da sessao autenticada.
- O resumo publico lista preferencias efetivamente aplicadas e permite remocao
  no turno seguinte.
- O contexto PostgreSQL continua sendo a autoridade conversacional.
- O planner recebe um `QueryIntentV2` resolvido; nao consulta o perfil.
- O executor permanece alheio ao perfil e continua sendo a unica autoridade
  numerica.
- `SemanticMemory` e historico de busca nao promovem preferencias.

## API

As rotas aditivas cobrem capacidades, leitura, resumo, CRUD de preferencia,
consentimento, disable/reactivate, exportacao, solicitacao de exclusao e
importacao legada em dry-run/confirmacao. Erros usam codigos tipados, incluindo
nao encontrado, proibido, conflito de versao, consentimento ausente e
referencia governada invalida.

## Rollout

`USER_ANALYTICAL_PROFILE_MODE` aceita `LEGACY_ONLY`, `SHADOW`, `V2_READ` e
`V2_READ_WRITE`. Producao permanece em `LEGACY_ONLY`; todos os recursos e o
cache iniciam desligados. Consulte
`docs/operation/USER_PROFILE_PRIVACY_RUNBOOK.md`.
