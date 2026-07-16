# Business Layer

## Objetivo

Centralizar significado de negocio, KPIs, formulas, governanca e validacao. A IA pode compreender e sugerir, mas a Business Layer define consistencia e regras.

## Modulos

- `business_dictionary.py`: conceitos de negocio.
- `business_kpi_registry.py`: registro de KPIs.
- `business_formula_engine.py`: formulas.
- `business_validation_engine.py`: validacao de regras/planos.
- `business_dependency_engine.py`: dependencias.
- `business_relationship_engine.py`: relacionamentos.
- `business_governance.py`: governanca e logs.
- `business_context_engine.py`: contexto de negocio.
- `business_layer.py`: aplicacao de regras no fluxo Data Platform.

## Entradas E Saidas

- Entradas: metricas, conceitos, formulas, blueprint/plano, tenant e usuario.
- Saidas: validacoes, impacto, observabilidade, rollback e registros governados.

## Boas Praticas

- Nao duplicar regra de negocio no frontend.
- Nao permitir que a IA invente KPI fora do catalogo/regra disponivel.
- Registrar mudancas em governanca quando endpoint oferecer suporte.
