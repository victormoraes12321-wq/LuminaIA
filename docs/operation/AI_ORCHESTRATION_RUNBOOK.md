# RUNBOOK OPERACIONAL: ORQUESTRAÇÃO GOVERNADA DA IA E CONTROLE DE TOKENS (`lumina.ai-orchestration/1.0`)

## 1. Visão Geral
Este runbook fornece procedimentos operacionais para gerenciar e monitorar a máquina de estados de orquestração de IA e os orçamentos de tokens no LuminaAI.

## 2. Feature Flags e Modos de Rollout
O comportamento do orquestrador é controlado por flags em `backend/config.py`:
- `LEGACY_ONLY` (Padrão de produção): O pipeline legado responde às requisições do usuário.
- `SHADOW_PLAN`: Monta o envelope de contexto e calcula estimativas de token em background sem alterar as respostas do usuário.
- `V2_ASSISTED`: Utiliza o orquestrador V2 assistido por propostas estruturadas.
- `V2_GOVERNED`: Ativação total da máquina de estados governada V2.

## 3. Monitoramento e Inspeção (ADMIN)
Acesse a página administrativa `/dashboard/admin/orchestration`:
1. **Modelos Autorizados**: Verifique os modelos em `AIModelRouter`.
2. **Templates de Prompt**: Verifique se o template ativo para `TOOL_PROPOSAL` e `RESPONSE_DRAFTING` é o `v1`.
3. **Inspector de Orquestração**: Digite perguntas de teste no simulador para inspecionar a estratégia escolhida, consumo de tokens e fatos numéricos vinculados.

## 4. Resposta a Incidentes
### Excedimento de Orçamento de Tokens
- Se o campo `exceeded` em `AITokenBudgetV2` for disparado, o orquestrador omite seções opcionais (Perfil, Base de Conhecimento).
- Caso o contexto obrigatório exceda a janela, o sistema retorna o erro tipado `AI_ORCHESTRATION_CONTEXT_TOO_LARGE`.

### Indisponibilidade de Provedor (Timeout/Rate Limit)
- O orquestrador aciona a corrente de fallback definida em `AIModelPolicyV2` (`gpt-4o-mini` -> `fake-deterministic-v1`).
- Se todos os provedores falharem, o sistema retorna `AI_PROVIDER_UNAVAILABLE` sem vazar credenciais ou detalhes internos.
