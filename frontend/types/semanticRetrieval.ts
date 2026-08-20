export type SemanticLifecycle =
  | 'DRAFT'
  | 'BUILDING'
  | 'VALIDATING'
  | 'READY'
  | 'PUBLISHED'
  | 'FAILED'
  | 'DEPRECATED'
  | 'ARCHIVED'

export interface SemanticCapabilities {
  contract_version: 'lumina.semantic-retrieval/1.0'
  mode: 'LEGACY_ONLY' | 'SHADOW' | 'HYBRID_READ' | 'V2_AUTHORITATIVE'
  frontend_enabled: boolean
  entity_instance_indexing_enabled: boolean
  vector_channel_enabled: boolean
  profile_tie_breaker_enabled: boolean
  admin_inspector_enabled: boolean
  cache_enabled: boolean
  incremental_build_enabled: boolean
  permission_fingerprint: string
}

export interface SemanticIndexDefinition {
  index_id: string
  tenant_id: string
  name: string
  locale: string
  document_types: string[]
  entity_policies: Array<{ entity_type: string; enabled: boolean }>
  source_policies: string[]
  allowed_classifications: string[]
  representation_provider: string
  representation_version: string
  ranking_policy: { policy_version: string }
  threshold_policy: {
    policy_version: string
    minimum_retrieval_score: number
    minimum_automatic_resolution_score: number
    ambiguity_margin: number
  }
  status: string
  owner_user_id: string
  lock_version: number
  active_version_id: string | null
  created_at: string
  updated_at: string
}

export interface SemanticIndexVersion {
  version_id: string
  tenant_id: string
  index_id: string
  version: number
  lifecycle: SemanticLifecycle
  source_manifest: {
    sources: Array<{
      source_type: string
      source_id: string
      source_version: string
      source_checksum: string
      stale: boolean
    }>
    checksum: string
  }
  document_count: number
  entity_count: number
  alias_count: number
  relation_count: number
  representation_version: string
  build_mode: 'FULL' | 'INCREMENTAL'
  watermark: string | null
  build_started_at: string
  build_completed_at: string | null
  checksum: string | null
  created_by: string
  reviewed_by: string | null
  published_by: string | null
  published_at: string | null
  superseded_version_id: string | null
  failure_summary: string | null
  lock_version: number
}

export interface SemanticIndexSource {
  source_type: string
  source_id: string
  source_version: string
  source_checksum: string
  tenant_scoped: boolean
  effective_at: string | null
  watermark: string | null
  stale: boolean
}

export interface SemanticEvaluationResult {
  evaluation_id: string
  tenant_id: string
  index_version_id: string
  corpus_version: string
  case_count: number
  passed: boolean
  metrics: Array<{ name: string; value: number }>
  checksum: string
  executed_at: string
}

export interface SemanticSearchResult {
  decision: string
  normalized_query: string
  public_explanation: string
  index_version_id: string | null
  candidates: Array<{
    document_id: string
    public_label: string
    entity_type: string
    domain: string
    score: number
    confidence_band: string
    matched_channels: string[]
    canonical_reference: {
      canonical_id: string
      display_label: string
      source_type: string
      source_version: string
    }
    breakdown: {
      final_score: number
      positive_score: number
      penalties: number
      channels: Array<{
        channel: string
        raw_score: number
        contribution: number
        reason_code: string
      }>
    }
  }>
}

export interface SemanticAuditEvent {
  event_id: string
  index_id: string | null
  version_id: string | null
  event_type: string
  reason_code: string
  created_at: string
}

export interface SemanticApiError {
  error?: { code?: string; message?: string }
}
