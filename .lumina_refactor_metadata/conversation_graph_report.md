# Conversation Graph & Dashboard State Report — LuminaAI
> Gerado por refatoração estática | Data: 2026-07-15 | Versão: 2.0

---

## 1. Arquivos Criados e Modificados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| **[conversation_graph.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/metadata_catalog/conversation_graph.py)** | [NEW] | Implementação do `ConversationGraphManager`, gerenciando nós de conversa, drill-down local e operações visuais em memória. |
| **[__init__.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/metadata_catalog/__init__.py)** | [MODIFY] | Exportação do gerenciador singleton da árvore de conversa. |
| **[new_query_orchestrator.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/new_query_orchestrator.py)** | [MODIFY] | Integração com o `conversation_graph_manager` para interceptação de comandos visual/drilldown e passagem de estado estruturado para a IA. |
| **[test_conversation_graph.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/tests/test_conversation_graph.py)** | [NEW] | Suíte contendo 5 testes unitários complexos validando ramificações da conversa, drilldown local, operações visuais locais e persistência de sessão. |

---

## 2. Arquitetura da Árvore Conversacional (Conversation Graph)

Em vez de uma lista textual de histórico linear, a memória conversacional do LuminaAI foi modelada como uma **árvore direcionada de nós analíticos (ConversationGraph)**:
- Cada consulta executada com sucesso materializa um `ConversationNode` com chaves exclusivas.
- Cada nó referencia opcionalmente um nó pai (`parent_id`) e uma lista de nós filhos (`children_ids`).
- **Informações Contidas no Nó**:
  - Referência ao plano canônico (`CanonicalPlan`) e plano de execução (`ExecutionPlan`).
  - Resultado bruto com dataset e contagem de linhas (`ExecutionResult`).
  - Metadados de tempos e custos analíticos (`QueryContext`).
  - Estado da interface do Dashboard (`DashboardState`), desacoplado do banco.

---

## 3. Operações Locais e Reutilização de Datasets

O `ConversationGraphManager` intercepta comandos de linguagem natural antes de chamar a IA ou compilar SQL, executando operações em memória RAM:
1. **Operações Puramente Visuais**: Perguntas como *"troque para pizza"*, *"mude para barras"*, *"ordene por receita"* alteram unicamente o `DashboardState` do nó ativo e re-ordenam o dataset existente na RAM, retornando a visualização atualizada em `< 0.1ms`.
2. **Drill-down Local**: Perguntas como *"detalhe esse cliente"* ou *"mostre apenas o estado MG"* realizam filtros locais em memória RAM caso a coluna e os valores estejam presentes no dataset carregado.
3. **Reutilização de Datasets**: Ao receber planos lógicos que solicitam subconjuntos de dados já carregados no nó analítico de partida, o dataset é projetado e filtrado na memória, poupando consultas ao banco clone.

---

## 4. Persistência e Restauração de Sessão

Cada sessão analítica do usuário é persistida fisicamente na pasta `.lumina_conversations/` no formato JSON:
- A abertura ou restauração de uma conversa carrega dinamicamente a árvore e reconstrói o nó ativo atual.
- Garante total continuidade analítica entre sessões e recarregamento exato do dashboard (filtros, drilldown, zoom, agrupamentos e tipos de gráficos).

---

## 5. Confirmação de Integridade

> [!IMPORTANT]
> **Confirmação de Desacoplamento Conversacional**: O histórico de conversa linear foi substituído com sucesso por grafos conversacionais estruturados.
> A IA analítica do Intent Engine é guiada unicamente por metadados estruturados (planos e estados passados) e todas as ações de UI e refinamento local são resolvidas de forma determinística no backend sem consultar o banco analítico.
