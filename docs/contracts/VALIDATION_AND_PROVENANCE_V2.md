# Contrato Canônico V2: Validação Analítica e Proveniência (`lumina.validation-provenance/1.0`)

## 1. Identificação do Contrato
- **Namespace**: `lumina.validation-provenance/1.0`
- **Diretório Backend**: `backend/contracts/validation_provenance_v2/`
- **Diretório Frontend**: `frontend/types/validation_provenance.ts`

## 2. Estrutura de Contratos Pydantic v2
- `AnalyticalFactV2`: Fato numérico/analítico extraído da execução PostgreSQL.
  - `fact_id`: UUID do fato.
  - `tenant_id`: Identificador do tenant.
  - `metric_code`: Código da métrica governada.
  - `decimal_value`: Representação string do valor `Decimal` para evitar imprecisão flutuante.
  - `source_query_fingerprint`: Hash da query analítica de origem.
- `AnalyticalClaimV2`: Afirmação textual ou numérica gerada pela IA.
  - `claim_id`: UUID da claim.
  - `claim_type`: Enum (`NUMERIC`, `COMPARATIVE`, `TEMPORAL`, `RANKING`, `COMPLETENESS`).
  - `fact_references`: Lista de UUIDs de fatos exigidos para provar a claim.
- `ProvenanceGraphV2`: Grafo DAG de proveniência de dados.
  - `nodes`: Nós do grafo representando entidades, ferramentas, fatos e claims.
  - `edges`: Arestas direcionadas com validação anti-ciclo e isolamento estrito por `tenant_id`.
- `ResultCertificationV2`: Certificado de resultado de validação.
  - `status`: Status da certificação (`CERTIFIED`, `BLOCKED`, `SUPERSEDED`, `UNVERIFIED`).
  - `policy_version`: Versão da política aplicada.
  - `stage_results`: Detalhamento dos 18 estágios de validação.
- `CertificationEnvelopeV2`: Envelope público com checksum SHA-256 e proveniência resumida.

## 3. Garantias e Propriedades
- **Idempotência Hash**: Exportações de schemas e specs OpenAPI geram hashes estáticos idênticos.
- **Fail-Closed**: Qualidade e autorização são verificadas em tempo de execução pré-persistência.
- **Não Alteração do Legado**: Em `LEGACY_ONLY`, os contratos V2 permanecem inativos sem impacto no fluxo V1.
