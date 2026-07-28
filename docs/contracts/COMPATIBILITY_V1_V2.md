# Compatibilidade V1 E V2

## Estrategia

O endpoint `POST /api/v1/query/` continua retornando `QueryResponse`. Quando a
flag V2 esta habilitada, a resposta pode conter o campo opcional:

```json
{
  "query_id": "00000000-0000-0000-0000-000000000000",
  "chart_type": "TABLE",
  "chart_data": {},
  "analytical_contract": {
    "contract": {
      "schema_name": "lumina.analytics",
      "schema_version": "2.0",
      "pipeline": "NEW"
    }
  }
}
```

Clientes V1 continuam usando os campos existentes. Clientes V2 leem o sidecar.
Versao desconhecida e rejeitada; nao existe fallback silencioso para V1.

## Adaptadores

- `legacy_payload_to_v2`: converte resposta do pipeline novo ou legado para
  `AnalyticalResponseV2`.
- `v2_response_to_legacy`: preserva o payload recebido, define o formato
  primario V1 e anexa o contrato completo.
- `attach_v2_sidecar`: composicao usada pela governanca HTTP.
- Os adaptadores sao puros: nao abrem banco, nao chamam IA e nao calculam valor
  empresarial.

Consultas simples fazem round-trip sem perda. Comparacoes e multiplas
visualizacoes permanecem completas no V2; o V1 pode consumir apenas o formato
primario, e essa limitacao fica explicita em `legacy_compatibility`.

## Rollout

| Flag | Padrao | Efeito |
| --- | --- | --- |
| `ANALYTICAL_CONTRACTS_V2_ENABLED` | `false` | Gera e valida contrato V2 |
| `ANALYTICAL_CONTRACTS_V2_SHADOW_MODE` | `true` | Valida sem expor o sidecar |
| `ANALYTICAL_CONTRACTS_V2_FRONTEND_ENABLED` | `false` | Reserva ativacao de consumo V2 |
| `ANALYTICAL_COMPARISON_V2_EXECUTION_ENABLED` | `false` | Mantem executor universal desligado |
| `TEMPORAL_NORMALIZER_V2_ENABLED` | `true` | Seleciona periodos canonicos V2 |
| `TEMPORAL_NORMALIZER_V2_SHADOW_MODE` | `true` | Compara parser antigo e novo sem texto sensivel |

Ordem recomendada: disabled, shadow, sidecar exposto, consumo frontend e somente
depois execucao comparativa universal.

O wrapper temporal V1 preserva IDs `period_N`. Adapters singulares recusam
listas e comparacoes; binds existentes continuam com `data_inicio` e
`data_fim` inclusiva, alem do limite exclusivo calculado pelo adapter temporal.

## Frontend

`frontend/lib/analyticalContractAdapter.ts` e a fronteira central. Ela:

- aceita V1 sem sidecar;
- valida nome/versao e estrutura minima do V2;
- preserva os campos V1 usados pelo renderer atual;
- nao cria datasets, numeros ou visualizacoes;
- rejeita sidecar invalido.

`DynamicRenderer` e o dashboard runtime nao foram redesenhados nesta etapa.

## Planner Comparativo

Comparacoes V2 usam `lumina.comparison-planner/1.0` quando
`COMPARISON_PLANNER_V2_ENABLED=true`. O sidecar recebe metadados estruturais
em `comparison_planner`; o payload V1 permanece inalterado.

Com a flag desligada, `_build_plan_v2_legacy` continua sendo a selecao
principal. Shadow mode pode construir os dois caminhos e registrar divergencia
sanitizada, sem mudar a resposta escolhida. O adaptador legado recusa planos
com N operandos ou readiness bloqueada quando a conversao perderia informacao;
ele nunca trunca silenciosamente.

## Compatibilidade Com Tenant E Erro

O tenant do contrato vem do usuario/tenant autenticado no router, nao do campo
enviado pelo cliente. Erro V2 remove dados V1 e continua erro. Fora de escopo
mantem `OUT_OF_SCOPE`; esclarecimento mantem `AMBIGUOUS` apenas no adaptador V1
e `CLARIFICATION_REQUIRED` no V2.
