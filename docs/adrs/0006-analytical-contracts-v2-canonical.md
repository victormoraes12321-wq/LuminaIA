# ADR 0006 - Contratos Analiticos V2 Como Representacao Canonica

## Status

Aceito em 2026-07-27.

## Contexto

Os pipelines novo e legado usam estruturas diferentes e campos singulares que
podem perder o segundo periodo ou formato visual. Ambiguidade, fora de escopo e
falha tecnica tambem podiam convergir para respostas semanticamente incorretas.

## Decisao

Adotar `lumina.analytics/2.0`, em Pydantic v2, como representacao canonica de
intencao, plano e resposta. A adocao sera aditiva por adaptadores, sidecar,
feature flags e shadow mode.

O contrato:

- usa listas para periodos e visualizacoes;
- exige dois operandos em comparacoes;
- separa readiness, erro, esclarecimento e fora de escopo;
- exige tenant autenticado em plano pronto;
- referencia metricas oficiais sem copiar formulas;
- proibe Oracle como fonte de consulta do usuario;
- registra origem, confianca, proveniencia e checks;
- mantem `QueryResponse` V1 durante a migracao.

## Consequencias

Positivas:

- perdas silenciosas tornam-se invalidas estruturalmente;
- os dois pipelines passam a produzir a mesma semantica;
- schemas e goldens tornam mudancas auditaveis;
- frontend pode migrar sem big bang.

Custos e limites:

- V1 ainda possui formato visual primario singular;
- executor universal de comparacoes nao foi implementado;
- memoria e gateway multi-tenant definitivos continuam futuros;
- quatro flags precisam de governanca de rollout.

## Alternativas Rejeitadas

- Alterar diretamente o payload V1: quebraria clientes existentes.
- Espalhar condicionais por pipeline: aumentaria divergencia.
- Confiar em dicionarios livres: nao impediria perda ou estado invalido.
- Fazer o modelo de IA produzir numeros: viola a fonte deterministica.
