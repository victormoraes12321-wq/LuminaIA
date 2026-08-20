# ADR 0002 - IA Como Corporate Intelligence Engine

Status: Aceita

## Contexto

A IA deixou de ser chatbot simples e passou a estruturar intencao, contexto, visual strategy e blueprints.

## Decisao

Manter a IA modular em engines: Intent, Semantic, Context, Business Understanding, KPI Discovery, Visualization Strategy, Blueprint Builder, Package Matcher, Confidence, Memory Context, Executive Analysis e Response Builder.

## Consequencias

- IA pode definir como apresentar, mas nao cria componente React/HTML/CSS.
- IA nao calcula metricas finais.
- IA deve usar Business Layer, Metadata Catalog e Semantic Catalog como fonte de contexto.
