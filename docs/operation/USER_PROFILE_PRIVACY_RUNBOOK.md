# Runbook De Privacidade Do Perfil Analitico

## Objetivo

Operar `lumina.user-analytical-profile/1.0` sem expor dados empresariais,
cruzar usuarios ou transformar comportamento observado em preferencia oculta.
Oracle, OpenAI e banco operacional nao participam deste fluxo.

## Pre-Requisitos

1. Backup aprovado do PostgreSQL analitico.
2. Migration v13 aplicada e verificada.
3. Migration v14 testada em PostgreSQL descartavel.
4. Testes completos com exatamente os xfails historicos aprovados.
5. Responsavel por privacidade e rollback identificado.

## Migration

```powershell
cd backend
$env:ENVIRONMENT='test'
$env:LUMINA_TESTING='true'
$env:TEST_DATABASE_URL='<postgresql-descartavel>'
.\.venv\Scripts\python.exe database\migration_v14_0.py up
.\.venv\Scripts\python.exe database\migration_v14_0.py verify
```

O startup nao aplica v14 automaticamente. O `down` existe apenas para ambiente
de teste guardado. Em producao, rollback e logico por feature flag; tabelas e
auditoria sao preservadas.

## Rollout

Promova um tenant por vez:

1. `LEGACY_ONLY`: V2 nao le nem escreve.
2. `SHADOW`: calcula decisoes e telemetria estrutural, sem alterar a intencao.
3. `V2_READ`: aplica somente preferencias ja confirmadas; escrita indisponivel.
4. `V2_READ_WRITE`: libera configuracao, consentimento e gestao pelo dono.

Ative separadamente frontend, defaults, filtros salvos, exportacao, exclusao,
importacao legada e cache. Nunca habilite tudo em um unico passo. A variavel
publica do frontend so exibe a navegacao; a autorizacao final continua no
backend.

## Rollback

1. Defina `USER_ANALYTICAL_PROFILE_MODE=LEGACY_ONLY`.
2. Desative todas as flags `USER_ANALYTICAL_PROFILE_*_ENABLED`.
3. Reinicie apenas os processos da aplicacao pela rotina operacional aprovada.
4. Confirme ausencia de `applied_preference_summary` em novas respostas.
5. Preserve tabelas, eventos, exportacoes e pedidos de exclusao.

O rollback nao executa migration down e nao restaura perfil em RAM ou JSON.

## Consentimento

- Defaults analiticos exigem consentimento explicito, finalidade e escopo.
- Revogacao tem efeito imediato e invalida cache do dono.
- Preferencia inferida permanece `INFERRED_UNCONFIRMED` e nunca e aplicada.
- Pedido atual, contexto, remocao e reset sempre vencem o perfil.
- A resposta deve divulgar todo default analitico aplicado.

## Exportacao E Exclusao

Exportacao retorna apenas o perfil do usuario autenticado, sem SQL, dataset,
bind, pergunta ou resposta. Neutralize valores ao gerar CSV em evolucoes
futuras; a versao atual exporta JSON tipado.

Solicitacao de exclusao:

1. exige `Idempotency-Key`;
2. muda o perfil para `DELETION_PENDING`;
3. interrompe novas aplicacoes;
4. e processada pela politica de retencao;
5. preserva somente auditoria minima obrigatoria.

## Incidentes

Em suspeita de cross-tenant, cross-user ou aplicacao oculta:

1. volte imediatamente para `LEGACY_ONLY`;
2. desative cache;
3. preserve request ID, evento estrutural e horario;
4. nao registre pergunta, valor, SQL ou payload;
5. valide escopo composto `(tenant_id, user_id)` no repositorio;
6. execute suites de IDOR, multitenancy, consentimento e CAS;
7. somente retome rollout depois de revisao de seguranca.

## Monitoramento

Monitore contagens e latencias por modo, resultado de aplicacao, conflitos de
CAS, referencias invalidas, revogacoes, exportacoes e pedidos de exclusao.
Telemetria nao inclui conteudo da preferencia, pergunta, dataset ou valor.
