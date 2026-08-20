# ADR 0019: Orquestração da IA como Máquina de Estados Limitada por Budgets e Policies

## Status
Aceito

## Contexto
O monorepo LuminaAI exige uma camada de orquestração de Inteligência Artificial previsível, auditável e segura. Agentes autônomos ilimitados que executam loops indeterminados de reflexão/chamada de ferramenta trazem riscos de estouro de tokens, latência imprevisível, custos descontrolados e vulnerabilidade a injeções de prompt.

## Decisão
1. **Versão**: Adotar a especificação `lumina.ai-orchestration/1.0`.
2. **Máquina de Estados Restrita**: A orquestração é guiada por uma máquina de estados finita com transições allowlisted (`GovernedAIStateMachine`).
3. **Orçamentos Estritos (Budgeting)**: Cada requisição possui orçamentos fixos para tokens, chamadas de ferramenta, profundidade sequencial, tempo total e custo.
4. **Proibição de Prompt Overrides e SQL Livre**: System prompts são definidos exclusivamente pelo servidor em `AIPromptTemplateService`. Propostas com SQL bruto ou injeção de campos de autoridade são rejeitadas.
5. **Autoridade de Valores Numéricos (`Decimal`)**: Números financeiros obtidos das ferramentas estruturadas possuem autoridade absoluta sobre qualquer texto gerado pelo modelo.
6. **Proibição de Persistence de Chain of Thought**: Monólogos internos e scratchpads privados não são persistidos em log ou banco de dados.

## Consequências
- Garantia de previsibilidade, auditabilidade e controle de custos em todas as requisições.
- Prevenção total contra loops infinitos ou recursão não autorizada.
- Isolamento multitenant estrito em todas as etapas da orquestração.
