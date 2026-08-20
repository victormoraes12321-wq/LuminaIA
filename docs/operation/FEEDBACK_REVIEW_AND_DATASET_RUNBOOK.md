# Runbook de Feedback, Revisao e Dataset

## Objetivo

Operar `lumina.supervised-feedback/1.0` sem expor dados empresariais, quebrar
isolamento de tenant ou transformar feedback em mudanca automatica de producao.

## Pre-condicoes

- backup aprovado;
- migration v15 revisada;
- PostgreSQL analitico acessivel;
- Conversation State PostgreSQL habilitado para o grupo piloto;
- perfis ADMIN e GESTOR separados para curadoria e revisao;
- flags de producao inicialmente desligadas.

## Rollout

1. Execute a migration v15 pelo mecanismo oficial, fora do startup.
2. Execute `verify` e confira as 11 tabelas, constraints e indices.
3. Configure `SUPERVISED_FEEDBACK_MODE=V2_COLLECT`.
4. Valide `/api/v2/feedback/capabilities`.
5. Mude para `V2_REVIEW` apenas no ambiente piloto.
6. Ative `SUPERVISED_FEEDBACK_FRONTEND_ENABLED`.
7. Ative `SUPERVISED_FEEDBACK_ADMIN_ENABLED` para revisores treinados.
8. Mude para `V2_CURATE` e ative dataset/exportacao somente apos aprovacao de
   governanca.

## Triagem diaria

1. Abra a fila por prioridade.
2. Trate `P1/SECURITY` primeiro.
3. Confirme duplicate group sem mesclar identidades.
4. Atribua reviewer que nao seja o autor.
5. Registre justificativa e evidence references estruturais.
6. Aprove, rejeite ou solicite informacao.
7. Nunca copie SQL, binds, credenciais ou linhas brutas para a revisao.

## Curadoria

1. Crie candidato somente de feedback aprovado.
2. Confirme `quality_status=VALID`.
3. Verifique redaction manifest e contrato aplicavel.
4. Valide o candidato e somente depois aprove-o por acao explicita.
5. Crie snapshot tenant-scoped com versao explicita.
6. Mova `DRAFT -> IN_REVIEW -> APPROVED`.
7. Publique somente com permissao `feedback:publish_dataset`.
8. Exporte somente para finalidade offline registrada.
9. Use importacao apenas em dry-run; resultado valido nao persiste nem publica.

Feedback aprovado nao entra automaticamente em candidate. Candidate aprovado
nao entra automaticamente em snapshot. Snapshot publicado nao e consumido
automaticamente pelo runtime.

## Retirada e exclusao

Antes de publicacao, a retirada invalida o uso futuro do feedback. Se um
exemplo ja estiver em snapshot publicado, o snapshot antigo permanece
imutavel e uma nova versao deve exclui-lo. Pedidos de exclusao sao
idempotentes e auditados; a execucao depende da politica legal de retencao.

## Incidentes

### Suspeita de segredo

1. Suspenda a fila afetada.
2. Confirme que o manifest nao contem o valor original.
3. Restrinja acesso a ADMIN.
4. Registre evento sem reproduzir o segredo.
5. Gire a credencial no sistema de origem, se aplicavel.

### Suspeita cross-tenant

1. Desative as flags de escrita.
2. Preserve eventos estruturais.
3. Nao consulte o recurso por ID fora do tenant.
4. Rode testes de FK composta e IDOR.
5. Reative somente apos causa e remediacao documentadas.

### Concorrencia de revisores

O segundo escritor recebe `FEEDBACK_VERSION_CONFLICT`. Recarregue o registro,
nao force last-write-wins e nao altere `lock_version` manualmente.

### Exportacao incorreta

1. Desative `SUPERVISED_FEEDBACK_EXPORT_ENABLED`.
2. Preserve manifest e checksums.
3. Nao publique nova versao ate revisar o conjunto.
4. Gere nova versao; nunca edite snapshot publicado.

## Rollback

1. Volte `SUPERVISED_FEEDBACK_MODE` para `LEGACY_ONLY`.
2. Desligue todas as flags do modulo.
3. Preserve tabelas para auditoria.
4. O downgrade v15 e permitido somente em banco descartavel de teste.
5. Em producao, rollback e logico; remocao fisica exige janela, backup e
   aprovacao separada.

## Observabilidade segura

Monitore contagem por lifecycle, queue, severity, conflitos CAS, falhas de
redacao, latencia e volume de exportacao. Nao registre pergunta, explicacao,
correcao, valor empresarial, SQL, token ou identidade de outro usuario.
