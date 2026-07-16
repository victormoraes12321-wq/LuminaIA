# Performance Map — LuminaAI
> Gerado por auditoria estática completa | Data: 2026-07-15 | Versão do Pipeline: 2.0

---

## 1. Intelligent Caching Platform (ICP)

O núcleo de performance do LuminaAI reside em `backend/services/cache_service.py`. O cache é multinível e opera sobre os seguintes namespaces:

| Namespace | TTL Padrão | Escopo de Dados |
|-----------|------------|-----------------|
| `blueprint` | 4 horas (14.400s) | Estruturas de dashboard homologadas |
| `package` | 12 horas (43.200s) | Pacotes analíticos reutilizáveis |
| `semantic` | 2 horas (7.200s) | Definições e aliases da camada semântica |
| `metadata` | 1 hora (3.600s) | Metadados físicos de views e tabelas |
| `runtime` | 30 minutos (1.800s) | Datasets temporários em execução |
| `dashboard` | 30 minutos (1.800s) | Configurações de layout de telas |
| `view` | 30 minutos (1.800s) | Estruturas de colunas físicas |
| `query` | 5 minutos (300s) | Resultados de consultas idênticas do usuário |
| `sync` | 5 minutos (300s) | Fila e logs de sincronização do ERP |

### Algoritmo de Evacuação (Eviction Policy)
O cache utiliza um algoritmo **LFU ponderado pelo custo de reconstrução (Cost-Effective LFU)**.
Quando o limite de memória ou de itens é atingido, cada item recebe um score de prioridade:
$$\text{Score} = \frac{\text{Hit Count} \times \text{Cost Ms} + 1}{\text{Idade em Segundos}}$$
O item com o **menor score** é removido. Isso preserva no cache consultas que demoraram muito tempo para rodar no PostgreSQL clone ou exigiram tokens caros de IA.

---

## 2. Gerenciamento de Pools de Conexão

O sistema gerencia conexões de banco de dados analíticos via `postgresql_clone_service.py` utilizando o driver **`asyncpg`**:
- **Tamanho do Pool**: Cache dinâmico por `tenant_id` (`_pg_pools`) com `min_size=1` e `max_size=4` conexões ativas por tenant.
- **Timeout**: Timeout de comando fixado em 30.0 segundos.
- **Reciclagem**: A conexão é validada antes de cada uso com `pool_pre_ping=True` no PostgreSQL de metadados.

---

## 3. Estratégias de Sincronização In-Memory e Batching

A sincronização Oracle ── PostgreSQL Clone utiliza o `SyncEngine`:
- **Staging Tables**: O motor de sincronização cria tabelas temporárias (`staging_...`) e copia os registros do Oracle em lotes. Após a conclusão bem-sucedida, realiza a substituição de tabelas analíticas reais sob uma **transação atômica (`RENAME`)**.
- **Invalidação Seletiva**: Após sincronizar uma view do Oracle, o sistema busca no cache todas as chaves associadas a essa view e as invalida de forma seletiva (`invalidate_by_dependency`).

---

## ⚠️ ACHADOS CRÍTICOS & GARGALOS DE PERFORMANCE DETECTADOS

1. **Pooling Dinâmico Destrutivo no Novo Pipeline**:
   > [!CAUTION]
   > Conforme auditado no `new_query_orchestrator.py` (linha 212-222), a execução das queries físicas de produção realiza um `create_async_engine` e `engine.dispose()` a cada requisição, em vez de reutilizar as conexões gerenciadas pelo pool cacheado do `postgresql_clone_service.py`. Isto anula o sistema de pools de conexão e causa alta latência de handshake TCP a cada requisição de consulta do usuário.

2. **Invalidação de Cache Baseada em Substrings**:
   - O método `clear_pattern()` do cache realiza varreduras em loop linear (`dict.keys()`) procurando chaves que contenham o padrão de texto. Isto pode se tornar um gargalo de uso de CPU caso o cache acumule dezenas de milhares de itens ativos.

---

*Auditoria estática — nenhum arquivo modificado.*
