# ESPECIFICAÇÃO DE CONTRATOS V2: ORQUESTRAÇÃO GOVERNADA DA IA E CONTROLE DE TOKENS (`lumina.ai-orchestration/1.0`)

## 1. Visão Geral
A especificação `lumina.ai-orchestration/1.0` estabelece o contrato formal de orquestração de Inteligência Artificial para o monorepo LuminaAI.

### 1.1 Objetivos Fundamentais
- **Máquina de Estados Governada**: Transições de estado allowlisted e transacionais com verificação de optimistic concurrency (`lock_version`).
- **Controle Estrito de Recursos (Budgeting)**: Limites configuráveis para Tokens (Input/Output/Reserva), Ferramentas (Chamadas/Depth/Distinct), Tempo (ms) e Custo.
- **Autoridade Server-Controlled de Prompts e Modelos**: Proibição total de system prompts enviados por usuários e roteamento server-side.
- **Minimização e Priorização de Contexto**: Montagem determinística por seções com truncamento seguro de seções opcionais.
- **Validação de Propostas e Autoridade Financeira (`Decimal`)**: Fatos numéricos validados das ferramentas prevalecem sobre texto gerado pela IA.
- **Proibição de Chain of Thought**: Monólogos internos e scratchpads privados não são persistidos.

## 2. Estrutura de Contratos Pydantic V2
O pacote `backend/contracts/ai_orchestration_v2/` exporta:
- `identity.py`: Versão `lumina.ai-orchestration/1.0` e enums estritos.
- `budgets.py`: Orçamentos de tokens, ferramentas, tempo, custo e contexto.
- `registry.py`: Definições e políticas de modelos, provedores e templates de prompt.
- `context.py`: Envelope de contexto montado com decisões de inclusão/truncamento.
- `proposals.py`: Proposta de ferramentas da IA e validação governada.
- `orchestration.py`: Requisição, execução, corrida (`Run`), alegações e resposta final.
- `evaluations.py`: Casos de teste sintéticos e resultados de avaliação automatizada.

## 3. Endpoints da API HTTP (`/api/v2/ai-orchestration`)
- `POST /api/v2/ai-orchestration/run`: Execução da orquestração governada.
- `POST /api/v2/ai-orchestration/cancel`: Cancelamento cooperativo da corrida.
- `GET /api/v2/ai-orchestration/models`: Catálogo de modelos autorizados.
- `GET /api/v2/ai-orchestration/providers`: Catálogo de provedores registrados.
- `GET /api/v2/ai-orchestration/prompts`: Registro versionado de templates de prompt.
- `GET /api/v2/ai-orchestration/policies`: Consulta de políticas ativas (ADMIN).
- `POST /api/v2/ai-orchestration/inspector/simulate`: Simulador sintético para inspeção (ADMIN).
