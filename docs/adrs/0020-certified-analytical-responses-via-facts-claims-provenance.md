# ADR 0020 - Respostas Analíticas Certificadas por Fatos, Claims e Proveniência

## Status
Aceito (`lumina.validation-provenance/1.0`)

## Contexto
Respostas produzidas por modelos de linguagem exigem garantia determinística de integridade antes da entrega ao usuário final. Números, comparações, rankings, agregações e filtros de visualização precisam ser validados contra a fonte de verdade do banco clone analítico PostgreSQL (`lumina.analytics/2.0`), garantindo que nenhuma claim feita pela IA permaneça sem prova factual ou proveniência auditável.

## Decisão
1. **Validação de 18 Estágios Pré-Persistência**: Toda resposta gerada pela IA em modo V2 deve passar por uma pipeline de validação determinística de 18 estágios (`GovernedValidationPipeline`), executando antes da persistência final no banco conversacional.
2. **Autoridade Factual `Decimal`**: Fatos analíticos (`AnalyticalFactV2`) são extraídos com precisão financeira `Decimal` armazenada em string JSON para eliminar perdas por ponto flutuante.
3. **Vinculação Obrigatória de Claims**: Claims numéricas, comparativas, temporais, de ranking e completude (`AnalyticalClaimV2`) exigem vinculação explícita a fatos provados. Claims não vinculadas ou divergentes bloqueiam a certificação da resposta.
4. **Grafo DAG de Proveniência**: A linhagem completa (tenant, sessão, intents, planos, queries SQL, ferramentas, fatos e claims) é organizada em um grafo direcionado acíclico (`ProvenanceGraphV2`). A detecção de ciclos ou arestas cross-tenant causa falha imediata.
5. **Certificação Imutável**: Respostas aprovadas recebem um envelope imutável com checksum SHA-256 (`CertificationEnvelopeV2`). Respostas bloqueadas são sinalizadas sem exposição de dados sensíveis ou datasets ao usuário.
6. **Desligamento Fail-Closed em `LEGACY_ONLY`**: Em modo legado, a validação de proveniência V2 não altera a execução atual.

## Consequências
- Respostas analíticas passam a ter certificado auditável de proveniência com prova de tenant.
- Respostas com alucinações numéricas ou divergências de fórmula são interceptadas deterministicamente.
- O pipeline legado permanece preservado sem regressões.
