# Corporate Intent Engine Report — LuminaAI
> Gerado por auditoria e refatoração estática | Data: 2026-07-15 | Versão: 2.0

---

## 1. Arquivos Modificados / Adicionados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| **[intent_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/metadata_catalog/intent_engine.py)** | [NEW] | Implementação da classe `CorporateIntentEngine` e dos esquemas Pydantic `IntentEngineOutput` e `SemanticPatch` |
| **[new_query_orchestrator.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/new_query_orchestrator.py)** | [MODIFY] | Integração com o novo motor conceitual da IA, suporte à aplicação de patches semânticos locais e cache de planos em memória |
| **[__init__.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/metadata_catalog/__init__.py)** | [MODIFY] | Exportação de novos contratos semânticos e da instância global do motor de intenções |
| **[test_refactored_intent_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/tests/test_refactored_intent_engine.py)** | [NEW] | Suíte de testes unitários validando isolamento físico, SemanticPatch, ambiguidades e perguntas fora do domínio |

---

## 2. Garantia de Isolamento Semântico

A partir desta refatoração, o prompt de sistema gerado dinamicamente para o interpretador de IA contém exclusivamente conceitos de negócio extraídos do Corporate Knowledge Catalog:
- **Entidades de Negócio lógicas**: `Cliente`, `Venda`, `Produto`, `Vendedor`, `Financeiro`.
- **Métricas conceituais amigáveis**: `Receita`, `Quantidade`, `Estoque`, `Valor Parcela`.
- **Dimensões conceituais amigáveis**: `Cliente`, `Produto`, `Vendedor`, `Cidade`, `Estado`, `Categoria`, `Data`.
- **Aliases semânticos de conversão**.

> [!IMPORTANT]
> **Nenhum termo ou detalhe físico do banco de dados (Views, tabelas, SQL, JOINs, PKs/FKs, ou colunas como `ptotal_`, `qtde_`, `dtemissao_`) é enviado ou conhecido pela IA.**
> Toda decisão física é realizada pelo backend de forma desacoplada após a produção do `SemanticPlan`.

---

## 3. Testes Unitários Executados

A suíte de testes unitários foi executada com sucesso (`4 passed in 4.55s`):

1. **`test_semantic_intent_engine_no_physical_references`**: Garante de forma estática que o prompt de sistema do LLM não contém termos físicos ou comandos SQL.
2. **`test_orchestrator_integration_simple_query`**: Valida a orquestração analítica de ponta a ponta a partir de um plano semântico lógico de saída.
3. **`test_orchestrator_continuity_semantic_patch`**: Valida o fluxo de continuidade analítica de conversa via `SemanticPatch` (ex: `ADD_FILTER` e `CHANGE_LIMIT`) mesclado de forma dinâmica em memória RAM.
4. **`test_orchestrator_ambiguity_and_out_of_scope`**: Valida que perguntas ambíguas ou fora de domínio analítico retornam os status correspondentes (`AMBIGUOUS`, `OUT_OF_SCOPE`) sem gerar falsos planos.

---

## 4. Compatibilidade com o Pipeline Existente

A integração com o orquestrador analítico unificado (`NewQueryOrchestrator`) mantém total retrocompatibilidade e atende a todos os contratos estabelecidos sem alterar nenhuma rota ou endpoint.

---

*Refatoração concluída com sucesso.*
