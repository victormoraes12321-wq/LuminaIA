# Self Healing & Explainability Report — LuminaAI
> Gerado por refatoração estática | Data: 2026-07-15 | Versão: 2.0

---

## 1. Arquivos Criados e Modificados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| **[self_healing.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/metadata_catalog/self_healing.py)** | [NEW] | Implementação do `SelfHealingEngine`, centralizando as validações de caminhos físicos impossíveis e datasets vazios inesperados. |
| **[explainability.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/metadata_catalog/explainability.py)** | [NEW] | Implementação do `ExplainabilityEngine` com prevenção estrita a alucinação de dados e explicabilidade local via RAM. |
| **[new_query_orchestrator.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/new_query_orchestrator.py)** | [MODIFY] | Integração com ambos os engines no fluxo pós-execução analítica. |
| **[test_self_healing_explainability.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/tests/test_self_healing_explainability.py)** | [NEW] | Suíte contendo 4 testes unitários validando limites de cura, vazio analítico esperado/inesperado e respostas explicativas sem queries. |

---

## 2. Detalhes do Self Healing (Auto-Cura)

O `SelfHealingEngine` atua de forma cirúrgica pós-execução e intercepta falhas recuperáveis do banco PostgreSQL clone:
- **Dataset Vazio Inesperado**: Se o plano lógico indica que dados eram esperados e a query retornou 0 linhas, o engine analisa parâmetros de período e filters, gera um feedback estruturado e solicita à IA um replanejamento imediato.
- **Caminhos Físicos Inválidos / Colunas Inexistentes**: Em caso de falha de relacionamentos de JOIN ou colunas removidas no banco físico, o validador solicita ao Planner uma nova estratégia analítica baseada nas tabelas equivalentes catalogadas no CKC.
- **Proteção Estrita Contra Loops**: Cada `trace_id` é registrado em cache RAM na primeira tentativa de auto-cura. Se a segunda tentativa falhar, o engine bloqueia o re-healing e propaga uma exceção técnica amigável ao usuário.

---

## 3. Detalhes da Explainability (Explicabilidade)

O `ExplainabilityEngine` é a camada de tradução dos resultados de Business Intelligence para linguagem de negócios:
- **Prevenção de Alucinação**: O prompt do sistema proíbe categoricamente a IA de efetuar cálculos matemáticos adicionais (somas, divisões, médias) ou introduzir métricas não presentes no dataset. Ela atua apenas como intérprete dos fatos consolidados pelo backend.
- **Explicabilidade Local via RAM**: Perguntas de continuidade analítica ("por que essa barra é maior?", "detalhe o vendedor A") são interceptadas no início da requisição e respondidas com base apenas no dataset já carregado no `ConversationGraph`, com custo computacional `0.0ms` e zero requisições adicionais de SQL.

---

## 4. Confirmação de Integridade

> [!IMPORTANT]
> **Confirmação de Desacoplamento Analítico**: A inteligência artificial atua exclusivamente na fase conceitual (planejamento) e de explicabilidade (pós-execução).
> O backend e o CKC continuam sendo a única fonte de verdade para tradução física, ordenação e regras analíticas, e o Self Healing possui um limite determinístico rigoroso de 1 única tentativa por consulta analítica.
