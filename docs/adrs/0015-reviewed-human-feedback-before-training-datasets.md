# ADR 0015 - Feedback humano revisado antes de exemplos e datasets

Status: Aceito

Data: 2026-07-29

## Contexto

O LuminaAI precisava aprender com correcoes humanas sem permitir que uma
avaliacao isolada alterasse contexto, conhecimento, perfil, formulas, prompt
ou comportamento de producao. O mecanismo anterior era volatil e nao possuia
ownership, redacao, revisao ou versionamento.

## Decisao

Adotar `lumina.supervised-feedback/1.0` como autoridade separada e
deterministica. Uma resposta persistida e validada por tenant/usuario e o
target. Toda entrada e minimizada e redigida antes da fila. Um revisor humano
diferente do autor define a classificacao final.

Feedback aprovado apenas habilita a criacao explicita de um candidato.
Curadoria explicita transforma candidato valido em exemplo. Exemplos entram
somente em snapshot versionado. Snapshot publicado e imutavel e sua exportacao
e exclusivamente offline. Nao existe treinamento, fine-tuning, embedding,
publicacao de Knowledge ou mudanca de prompt automatica.

## Consequencias

Positivas:

- provenance e auditoria completas;
- isolamento por tenant e usuario;
- datasets reproduziveis;
- rollback por flags;
- correcoes nao contaminam producao;
- revisao e curadoria podem evoluir independentemente.

Custos:

- mais etapas humanas;
- migration v15 e operacao de filas;
- necessidade de governanca de retencao;
- dependencia de respostas persistidas no Conversation State PostgreSQL.

## Alternativas rejeitadas

- treinar diretamente de thumbs up/down;
- armazenar corpo integral da resposta;
- usar LLM para redacao ou triagem;
- promover feedback para Knowledge Base;
- manter dataset mutavel com alias `latest`;
- usar historico enviado pelo cliente como autoridade.
