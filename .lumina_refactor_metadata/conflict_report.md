# Conflict Report — LuminaAI
> Gerado por auditoria estática completa | Data: 2026-07-15 | Versão do Pipeline: 2.0

---

## 1. Conflitos de Responsabilidades e Código Duplicado

### A. Resolução de Aliases Semânticos
Existe uma redundância tripla na resolução de aliases semânticos e mapeamento de colunas físicas:
1. **`semantic_layer.py`** (`_STATIC_METRIC_ALIASES` e `canonicalize_metric_name()`): Mapeia sinônimos de métricas analíticas.
2. **`query_optimizer_engine.py`** (`VIEW_COLUMN_MAPPING` e `translate_expression()`): Mapeia aliases lógicos diretamente para nomes físicos específicos por view.
3. **`postgresql_clone_service.py`** (`_METRIC_COLUMN_ALIASES`): Mapeia aliases para o query builder do clone.
- **Conflito**: Se um alias for adicionado ou alterado, é necessário modificar 3 arquivos em pontos diferentes do sistema. Isso gera inconsistências em que certas consultas funcionam sob o pipeline legado mas quebram sob o pipeline determinístico (ou vice-versa).

### B. Gestão de Cache de Dados
- Mapeado tanto em `cache_service.py` (`IntelligentCachingPlatform`) quanto em `services/data_platform/package_cache.py`. As duas camadas operam com chaves e TTLs de forma isolada, gerando duplicação de dados em memória RAM.

---

## 2. Hardcodes de Controle Semântico (Ancoragem Temporal)

### A. Âncora de Data Fixo (Anchor Date)
- O arquivo `backend/services/plan_validator.py` (linha 22) fixa a data atual de forma estática:
  `ANCHOR_DATE = date(2026, 7, 3)`
- **Conflito**: Todas as consultas de períodos relativos (como "vendas de hoje", "vendas deste mês") são calculadas tendo como referência o dia 3 de Julho de 2026, em vez do relógio do sistema (`datetime.now()`). Isso gera desvios completos de datas na análise.

### B. Mapeamentos Estáticos e Falsos Positivos de Custo/Margem
- Em `query_optimizer_engine.py` (linha 135), as métricas `custo`, `preco_custo`, `preco_venda` e `margem` são todas mapeadas para a coluna **`estoque`** de forma fixa na view `VW_PRODUTOS_CAD_LM`.
- **Conflito**: Perguntas de usuários sobre lucro, preço médio ou custo do produto retornarão quantidades físicas de estoque físico cadastrado, induzindo o usuário a erros graves de interpretação comercial (faturamento incorreto).

---

## 3. Código Morto e Inconsistências de Tipos de Dados

### A. Redundância de Enums de Visualização
- **`models/view_catalog.py`** define o enum ORM `ChartType` com 12 opções de gráficos.
- **`models/new_pipeline_contracts.py`** define o enum Pydantic `VisualizationType` com 8 opções.
- **Conflito**: Várias opções (como SCATTER, HEATMAP, AREA) existem no banco mas não são aceitas pelo contrato do pipeline físico, gerando falhas de validação silenciosas.

### B. Referências Órfãs no Banco de Dados
- O campo `blueprint_repository.view_catalog_id` (UUID) é definido como nulo mas não possui constraint física de ForeignKey declarada no SQLAlchemy. O mesmo ocorre com `analytical_packages.blueprint_id`. Isto permite que registros sejam apagados e deixem dados órfãos na base operacional.

---

*Auditoria estática — nenhum arquivo modificado.*
