# Walkthrough — Data Platform, Analytics Engine & Business Knowledge Engine (LuminaAI)

## 1. Módulos Implementados

### A. Sync Engine (Motor de Sincronização)
- **Staging Atômico**: Sincroniza dados do Oracle ERP para tabelas analíticas intermediárias (`*_staging`) e efetua chaveamento (Rename) em transação atômica. Se falhar, faz rollback automático.
- **Incremental Inteligente**: Importa novos registros a partir da maior data (`data_ref`) ou ID na tabela analítica.
- **Invalidação Seletiva de Cache**: Adicionados métodos `clear_pattern` no Cache para invalidar unicamente as chaves associadas às views atualizadas.

### B. Sync Scheduler (Orquestrador de Sincronização)
- **Lock Global**: Proteção de concorrência que impede execuções de sincronização simultâneas para o mesmo Tenant.
- **Políticas de Fusos Horários e Dias da Semana**: Suporte a timezone configurável (ex: `America/Sao_Paulo`) e dias úteis/finais de semana.
- **Janelas de Execução**: Emite alertas de estouro de tempo limite sem interromper os jobs em andamento.
- **Dashboard Admin**: Método `get_admin_dashboard_metrics` para consolidar o histórico de filas, volumes e percentuais de saúde.

### C. Analytics Engine Corporativo
- **Query Resolver**: Localiza e resolve metadados de Views, Datasets e KPIs sem tocar no ERP Oracle.
- **Calculation Engine**: Biblioteca matemática e estatística determinística para calcular KPIs de BI (CMV, Margem, ROI, CAC, LTV, Ticket Médio, etc.), desvios padrão, percentis e Curva ABC.
- **Comparison Engine**: Comparações temporais clássicas (`Mês x Mês`, `Ano x Ano`, etc.) com indicações direcionais.
- **Trend Engine**: Regressão linear sobre séries temporais para projeção de tendências sem IA.
- **Business Rules Engine**: Validação de restrições lógicas e conformidade multi-tenant em memória.
- **Dataset Builder**: Normalização e serialização de dados estruturados com schemas e checksums MD5.
- **Dashboard Payload Builder**: Formata o payload final de widgets (tabelas, cartões e gráficos) otimizado para o Frontend.

### D. Analytical Package Layer
- **Camada de Conhecimento Reutilizável**: O LuminaAI deixa de trabalhar apenas com consultas isoladas e passa a acumular conhecimento reutilizável a cada análise executada.
- **Lookup 3 camadas**: Consulta exata, de compatibilidade e semântica para buscar layouts analíticos pré-existentes.
- **Cache L1**: Cache isolado por Tenant com TTL de 5 minutos e descarte LRU.
- **Deteção de Mudança de Schema**: Proteção de versão que detecta quando o banco subjacente mudou e depreca pacotes automaticamente.

---

## 2. Business Knowledge Engine (BKE) — O Motor de Gestão Corporativa

O Business Knowledge Engine (BKE) reestrutura completamente a antiga Business Layer, transformando-a na central oficial de conhecimento, governança e consistência de regras de gestão da empresa. Ele opera exclusivamente sobre metadados, regras e validações sem executar consultas pesadas à base de dados.

### A. Estruturas Analíticas Criadas (ORM & Migrations)
- **Dicionário Corporativo**: Cadastro de conceitos de negócios, resolvendo sinônimos de forma unificada.
- **Registro Oficial de KPIs**: Definições estritas de KPIs, restrições e faixas ideais de tolerância (sem duplicações).
- **Fórmulas Analíticas**: Cadastro de equações matemáticas.
- **Relacionamentos e Influências**: Mapeamento de redes de causa/efeito entre indicadores (ex: CAC influencia margem).
- **Logs e Governança**: Audit trail completo com snapshot detalhado e suporte à reversão de alterações (Rollback).

### B. Submotores da Camada de Negócios

| Submotor | Caminho do Arquivo | Função Principal |
|---|---|---|
| Dicionário de Conceitos | [business_dictionary.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/business/business_dictionary.py) | Registro único e case-insensitive de termos empresariais |
| Registro de KPIs | [business_kpi_registry.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/business/business_kpi_registry.py) | Validação e garantia de KPIs não-duplicados |
| Central de 23 Fórmulas | [business_formula_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/business/business_formula_engine.py) | Avaliação em Python com seeding de 23 fórmulas de BI padrão |
| Motor de Relações | [business_relationship_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/business/business_relationship_engine.py) | Mapeia relações causa/efeito com seeding de 6 relacionamentos padrão |
| Classificador de Contexto | [business_context_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/business/business_context_engine.py) | Categorização dinâmica em 11 contextos de gestão por tags |
| Validador de Planos | [business_validation_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/business/business_validation_engine.py) | Bloqueia ativamente agregações errôneas (SOMA em %) e agrupamentos inválidos |
| Análise de Impacto | [business_dependency_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/business/business_dependency_engine.py) | Identifica pacotes analíticos e blueprints impactados caso métricas mudem |
| Governança & Rollback | [business_governance.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/business/business_governance.py) | Histórico de versões e rollback de conceitos, KPIs e fórmulas |
| Fachada BKE | [business_knowledge_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/business/business_knowledge_engine.py) | Fachada unificada (Facade) para todas as ações do BKE |

### C. Pontos de Integração e APIs
1. **Semantic Catalog Integration**: `sync_from_semantic_catalog` em [semantic_layer.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/semantic_layer.py) atualiza o dicionário e o cache de sinônimos dinamicamente a partir dos conceitos e KPIs ativos no BKE (com isolamento multi-tenant).
2. **Query Intelligence Engine (QIE)**: Integrado no [query_intelligence_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/query_intelligence_engine.py) na etapa da Business Layer para aplicar a validação estrutural do plano antes da sua execução e enriquecer o contexto de saída com fórmulas e relações de causa/efeito.
3. **API Router REST**: Endpoints expostos sob `/api/v1/business-knowledge/` para consulta (`/dictionary`, `/kpis`, `/formulas`, `/observability`), análise de impacto (`/impact`), governança (`/rollback`) e inicialização (`/seed`).

---

---

## 3. Corporate Intelligence Engine (CIE) — O Motor de Inteligência Corporativa

O Corporate Intelligence Engine (CIE) reestrutura completamente a camada de Inteligência Artificial do LuminaAI, elevando o antigo modelo de chatbot para um orquestrador cognitivo de nível executivo. O CIE trabalha com base em 12 sub-motores especializados, garantindo que a IA nunca faça consultas diretas ao banco de dados, nunca execute cálculos e nunca reescreva regras de negócios.

### A. Submotores da Camada de IA

| Submotor | Caminho do Arquivo | Função Principal |
|---|---|---|
| Gerenciador de Contexto | [context_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/context_engine.py) | Inicializa e constrói o contexto de execução `CIEContextSchema`. |
| Memória de Sessão | [memory_context_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/memory_context_engine.py) | Extrai preferências implícitas de gráficos e entidades do histórico recente. |
| Processador Semântico | [semantic_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/semantic_engine.py) | Limpa termos de entrada, resolve sinônimos e corrige ortografia/gírias. |
| Compreensão de Negócios | [business_understanding_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/business_understanding_engine.py) | Consulta conceitos e terminologias de gestão no Dicionário Corporativo do BKE. |
| Motor de Intenções (NLU) | [intent_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/intent_engine.py) | Realiza extração estruturada de intenções de negócio a partir da linguagem natural. |
| Descoberta de KPIs | [kpi_discovery_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/kpi_discovery_engine.py) | Identifica e mapeia os indicadores oficiais associados aos termos do usuário. |
| Estrategista de Visualização | [visualization_strategy_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/visualization_strategy_engine.py) | Sugere o layout de gráficos/tabelas ideal com base nas intenções e histórico. |
| Construtor de Blueprints | [blueprint_builder.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/blueprint_builder.py) | Constrói a especificação lógica do plano de análise (Blueprint) sem conter SQL. |
| Seletor de Pacotes | [package_matcher.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/package_matcher.py) | Verifica a existência de pacotes analíticos prontos e compatíveis na Data Platform. |
| Motor de Confiança | [confidence_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/confidence_engine.py) | Calcula o índice de confiança da interpretação e bloqueia sob incerteza. |
| Motor de Análise Executiva | [executive_analysis_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/executive_analysis_engine.py) | Interpreta os resultados determinísticos retornados pela Engine de Analytics. |
| Construtor de Resposta C-Level | [response_builder.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/response_builder.py) | Formata o texto final com linguagem de negócios refinada, sem jargões de TI. |
| Fachada CIE | [corporate_intelligence_engine.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai/corporate_intelligence_engine.py) | Orquestrador central que executa o fluxo completo do pipeline cognitivo. |

### B. Integração e Compatibilidade
- **Ponte de Compatibilidade**: O arquivo [services/ai_service.py](file:///c:/Users/wccto11ti1/Desktop/Sistema%20IA%20Empresa/backend/services/ai_service.py) foi refatorado para encaminhar as chamadas legadas de `identify_intention` e `generate_data_insights` de forma transparente para o novo Corporate Intelligence Engine, preservando 100% das assinaturas e dos tipos de retorno esperados pelos demais componentes do sistema.

---

## 4. Cobertura de Testes Automatizados

A suíte de testes do LuminaAI conta com **206 testes ativos**, todos executando com sucesso (100% verde):

1. **Testes do Corporate Intelligence Engine (`tests/test_corporate_intelligence_engine.py`)**:
   - 9 testes unitários e de integração detalhados validando cada um dos 12 submotores do CIE e a orquestração da fachada.
2. **Testes do Business Knowledge Engine (`tests/test_business_knowledge_engine.py`)**:
   - 13 testes cobrindo isolamento multi-tenant, motor de 23 fórmulas de BI (ROI, LTV, CAC, Curva ABC), motor de contextos, validação de agregações proibidas, detecção de impacto e rollback governado de versões.
3. **Testes do Analytical Package Suite (`tests/test_analytical_package_suite.py`)**:
   - 47 testes validando hashes de compatibilidade sem período, deprecamento automático por score, cache L1 tenant-isolated e versionamento.
4. **Testes do Analytics Engine Suite (`tests/test_analytics_engine_suite.py`)**:
   - 20 testes unitários e de integração validando contas matemáticas, ABC, regressão slope linear e payloads JSON.
5. **Testes do Sync Scheduler & Sync Engine**:
   - 15 testes verificando locks globais, janelas locais de fuso horário, staging atômico e switches de rename.
6. **Suíte Geral e Regressões**:
   - Total de **206 Passed / 206 ✅** em execuções de testes do backend.
