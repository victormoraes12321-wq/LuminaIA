# ADR 0007 - Normalizacao Temporal Deterministica Antes Do Planejamento

## Status

Aceito em 2026-07-27.

## Contexto

O LuminaAI possuia interpretacoes concorrentes: contrato V2 limitado a
mes/ano, helper do orquestrador baseado no relogio real e validador com ancora
fixa. Campos singulares podiam descartar periodos, listas podiam virar ranges e
a IA podia reinterpretar limites.

## Decisao

Adotar `lumina.temporal.pt-BR/1.0` antes do intent e do planejamento. O servico
recebe texto e `TemporalContext`, usa regras deterministicas e produz
`TimeWindow` de `lumina.analytics/2.0`.

O normalizador:

- nao acessa IA, rede ou banco;
- usa referencia e timezone injetados;
- distingue periodo, range, lista e comparacao;
- preserva ordem e pluralidade;
- suporta calendario civil e fiscal configurado;
- bloqueia ambiguidade material;
- registra regra, origem, confianca e versao;
- convive com o legado por adapters, flags e shadow mode.

O intent engine recebe somente um resumo compacto. Datas explicitas
deterministicas prevalecem sobre inferencia da IA.

## Consequencias

Leap years, fins de mes e limites passam a ter uma autoridade unica. Wrappers
singulares nao descartam operandos e testes nao dependem do relogio do
computador.

O parser legado permanece somente atras do gateway. Windows sem base IANA usa
fallback moderno controlado para Sao Paulo. Calendario 4-4-5, dias uteis e o
executor generico de comparacoes continuam futuros.

## Alternativas Rejeitadas

- IA como autoridade de datas: nao e deterministica.
- `dateparser`, Pendulum ou Arrow: adicionariam dependencia.
- regex unica: ampliaria risco de backtracking e manutencao.
- substituir todo o orquestrador: ampliaria o risco sem necessidade.
- escolher o primeiro periodo no V1: perde informacao silenciosamente.
