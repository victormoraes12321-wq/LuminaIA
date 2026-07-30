# ADR 0014 - Perfil Analitico Pessoal Explicito E Governado

## Status

Aceito em 2026-07-29. Rollout de producao: desativado.

## Contexto

O LuminaAI precisa preservar preferencias de apresentacao e defaults pessoais
sem confundir perfil duravel com contexto de conversa, historico, memoria
semantica ou conhecimento empresarial. Aplicar filtros pessoais de forma
oculta produziria respostas corretas para uma pergunta diferente da feita.

## Decisao

Adotamos `lumina.user-analytical-profile/1.0` como contrato pessoal persistido
no PostgreSQL, sempre isolado por tenant e usuario. O motor de aplicacao e puro,
deterministico e executado depois de `lumina.context-resolution/1.0` e antes do
planner.

Pedido atual e contexto vencem o perfil. Defaults analiticos exigem
consentimento ativo e resumo publico. O perfil armazena apenas configuracao e
identificadores canonicos; nao armazena SQL, binds, datasets, perguntas,
respostas ou numeros. Knowledge Base e MetricRegistry validam referencias,
mas nao sao alterados pelo perfil.

O planner e o executor nao consultam perfil. O executor continua sendo a
autoridade numerica. Escritas usam compare-and-swap, checksum canonico e
eventos minimizados. Exportacao e exclusao sao operacoes explicitas do dono.

## Alternativas Rejeitadas

- Aprender defaults automaticamente pelo uso: nao ha consentimento verificavel.
- Usar historico ou `SemanticMemory` como autoridade: mistura sinais efemeros e
  duraveis.
- Persistir o perfil no frontend, RAM ou JSON local: quebra restart,
  multitenancy e auditoria.
- Injetar preferencias no prompt da IA: perde precedencia deterministica.
- Fazer o executor consultar o perfil: mistura personalizacao com autoridade
  numerica.

## Consequencias

Ha uma migration v14 aditiva e novas rotas `/api/v2/me`. A interface mostra o
que foi aplicado e permite remover no proximo turno. O rollout possui
`LEGACY_ONLY`, `SHADOW`, `V2_READ` e `V2_READ_WRITE`, com producao em
`LEGACY_ONLY`.

O adaptador legado permanece temporariamente para apresentacao segura. Defaults
legados, inferidos ou sem consentimento falham fechados.
