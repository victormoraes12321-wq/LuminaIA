# ADR 0027 — Governed Operational Observability, Metrics, and Regression Evaluations V2

- **Status:** APPROVED
- **Data:** 2026-08-07
- **Autores:** Arquiteto de Software & Engenheiro de Software Sênior
- **Contexto:** Prompt 24 do monorepo LuminaAI

---

## Contexto e Problema

Com a maturação das capacidades analíticas, inteligentes e determinísticas do LuminaAI (Prompts 1 a 23.1), tornou-se indispensável garantir observabilidade operacional padronizada, telemetria estruturada sanitizada, cálculo preciso de orçamentos de erro (SLOs) e avaliação automatizada de regressões funcionais, de segurança e de multitenancy.

---

## Decisão de Arquitetura

1. **Separação de Autoridade:** A camada de observabilidade registra telemetria operacional (`http_requests_total`, latência, disponibilidade). O `MetricRegistry` de negócios permanece a única autoridade para métricas empresariais.
2. **Redação Fail-Closed:** Todos os eventos e atributos de rastreamento passam por sanitização estrita para remover senhas, tokens, SQL bruto, binds e PII.
3. **Trava de Cardinalidade:** Rótulos dinâmicos não cadastrados ou UUIDs são mapeados para `"OTHER"`, prevenindo degradação de performance por cardinalidade descontrolada.
4. **19 Suítes de Avaliação Determinísticas:** Executadas sem dependências externas (OpenAI ou Oracle mockadas) para certificar invariantes de segurança, multitenancy e reprodutibilidade.
5. **Rollout por Modos de Transição:** Produção permanece em `LEGACY_ONLY` por padrão e pode progredir incrementalmente para `SHADOW`, `V2_METRICS`, `V2_EVALUATIONS` e `V2_GOVERNED`.

---

## Consequências

- **Positivas:** Prevenção proativa de regressões em produções futuras; visibilidade em tempo real de latências e taxas de erro; conformidade estrita com LGPD e auditorias de segurança.
- **Riscos Mitigados:** Degradação de banco por excesso de rótulos mitigada pelo `OperationalMetricCardinalityGuard`; alteração acidental de baselines evitada por gatilhos de imutabilidade e hashing SHA-256.
