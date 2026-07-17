# ADR 0005 - Guardrail Deterministico Para Perguntas Criticas De Vendas

Status: Aceita

## Contexto

Perguntas como faturamento do mes, ticket medio, desconto total, desconto medio, maior vendedor e top clientes sao usadas operacionalmente e precisam retornar numeros corretos e previsiveis. O fluxo generativo pode interpretar linguagem natural, mas nao deve ser a unica camada responsavel por indicadores criticos quando o periodo e a metrica estao claros.

Tambem havia regras de negocio especificas que precisavam ser preservadas:

- `PADRAO` representa cadastro tecnico e nao deve vencer ranking de vendedores.
- `LAGES E LOPES LTDA` representa a loja interna e nao deve aparecer como top cliente externo.
- Perguntas subsequentes na mesma conversa podem depender do periodo perguntado antes.

## Decisao

O `NewQueryOrchestrator` mantem um caminho deterministico para perguntas criticas de vendas quando houver periodo explicito ou periodo herdado do contexto da conversa.

Esse caminho:

- Executa consultas SQL controladas no backend.
- Calcula faturamento, ticket medio, desconto total e desconto medio de forma deterministica.
- Aplica exclusoes de negocio para ranking.
- Usa `session_id`, historico recente e `parent_id` para continuidade.
- Entrega payload compatibilidade `QueryResponse`/dashboard sem delegar calculo ao frontend.

## Consequencias

- Indicadores criticos ficam mais previsiveis.
- A IA continua responsavel por interpretacao, contexto e resposta, mas nao substitui calculo deterministico quando o caso e claro.
- Mudancas futuras nessas perguntas devem ter teste/regressao focada.
- Novas excecoes de negocio devem ser documentadas aqui, no changelog e em `docs/current-status.md`.

