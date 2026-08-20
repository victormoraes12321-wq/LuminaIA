export const KNOWLEDGE_CONTRACT_VERSION = 'lumina.enterprise-knowledge/1.0' as const

export type KnowledgeAssetType =
  | 'BUSINESS_TERM'
  | 'METRIC'
  | 'KPI'
  | 'DIMENSION'
  | 'ENTITY'
  | 'BUSINESS_RULE'
  | 'ALIAS_SET'
  | 'CALENDAR_POLICY'
  | 'DATA_QUALITY_POLICY'
  | 'SEMANTIC_RELATION'

export type KnowledgeLifecycle =
  | 'DRAFT'
  | 'IN_REVIEW'
  | 'APPROVED'
  | 'PUBLISHED'
  | 'REJECTED'
  | 'DEPRECATED'
  | 'ARCHIVED'

export interface KnowledgeOwnership {
  owner_user_id: string
  steward_label: string
  accountable_area: string
  transferred_at: string | null
}

export interface KnowledgeAsset {
  schema_version: typeof KNOWLEDGE_CONTRACT_VERSION
  asset_id: string
  tenant_id: string
  canonical_key: string
  asset_type: KnowledgeAssetType
  domain: string
  ownership: KnowledgeOwnership
  status: 'ACTIVE' | 'ARCHIVED' | 'DELETED'
  current_published_version_id: string | null
  lock_version: number
  created_at: string
  updated_at: string
}

export interface BusinessTermContent {
  kind: 'BUSINESS_TERM'
  canonical_name: string
  display_name: string
  definition: string
  domain: string
  short_description: string
  full_description: string
  allowed_examples: string[]
  incorrect_examples: string[]
  aliases: string[]
  related_terms: string[]
  source_references: Array<{
    reference_type: string
    title: string
    authority: string
    reference_uri: string | null
    reference_version: string | null
    verified_at: string | null
  }>
  locale: string
  tags: string[]
}

export interface KnowledgeContent extends Record<string, unknown> {
  kind: KnowledgeAssetType
  display_name: string
  definition?: string
  description?: string
  full_description?: string
  aliases?: string[]
  source_references?: BusinessTermContent['source_references']
  locale?: string
}

export interface KnowledgeVersion {
  schema_version: typeof KNOWLEDGE_CONTRACT_VERSION
  version_id: string
  tenant_id: string
  asset_id: string
  version_number: number
  lifecycle: KnowledgeLifecycle
  content: KnowledgeContent
  checksum: string
  author_user_id: string
  previous_version_id: string | null
  effective_from: string | null
  effective_to: string | null
  lock_version: number
  created_at: string
  updated_at: string
}

export interface KnowledgeAssetDetail {
  asset: KnowledgeAsset
  versions: KnowledgeVersion[]
}

export interface KnowledgeCandidate {
  asset_id: string
  version_id: string
  canonical_key: string
  asset_type: KnowledgeAssetType
  display_name: string
  domain: string
  score: number
  match_type: string
  matched_field: string
  matched_text: string
  checksum: string
  provenance: Array<{
    reference_type: string
    title: string
    authority: string
  }>
}

export interface KnowledgeSearchResult {
  schema_version: typeof KNOWLEDGE_CONTRACT_VERSION
  query_normalized: string
  candidates: KnowledgeCandidate[]
  next_cursor: string | null
  ambiguous: boolean
  duration_ms: number
}

export interface KnowledgeAuditEvent {
  event_id: string
  asset_id: string | null
  version_id: string | null
  actor_user_id: string
  event_type: string
  reason_code: string
  created_at: string
}

export interface KnowledgeDiff {
  asset_id: string
  from_version: number
  to_version: number
  added_fields: string[]
  removed_fields: string[]
  changed_fields: string[]
  from_checksum: string
  to_checksum: string
}

export interface KnowledgeApiError {
  error?: {
    code?: string
    message?: string
  }
  detail?: string
}
