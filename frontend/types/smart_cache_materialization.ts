export type CacheType =
  | 'METADATA'
  | 'CONTRACT_SCHEMA'
  | 'POLICY'
  | 'TOOL_CATALOG'
  | 'ANALYTICAL_CATALOG'
  | 'SEMANTIC_METADATA'
  | 'COMPILED_PLAN'
  | 'CERTIFIED_ANALYTICAL_RESULT'
  | 'CERTIFICATION_ENVELOPE'
  | 'PUBLIC_PROVENANCE'
  | 'DETERMINISTIC_PRESENTATION'
  | 'NEGATIVE_METADATA'
  | 'FORBIDDEN';

export type MaterializationType =
  | 'SCALAR_AGGREGATE'
  | 'TIME_SERIES_AGGREGATE'
  | 'GROUPED_AGGREGATE'
  | 'RANKING_AGGREGATE'
  | 'DIMENSION_SUMMARY'
  | 'STATUS_SUMMARY'
  | 'CERTIFIED_FACT_SET'
  | 'ROW_LEVEL_DETAIL'
  | 'FORBIDDEN';

export type MaterializationLifecycle =
  | 'DRAFT'
  | 'IN_REVIEW'
  | 'APPROVED'
  | 'BUILDING'
  | 'VALIDATING'
  | 'READY'
  | 'PUBLISHED'
  | 'STALE'
  | 'FAILED'
  | 'DISABLED'
  | 'DEPRECATED'
  | 'ARCHIVED';

export type CacheDecision =
  | 'HIT'
  | 'MISS'
  | 'BYPASS'
  | 'STALE'
  | 'INVALID'
  | 'EXPIRED'
  | 'PERMISSION_CHANGED'
  | 'CLASSIFICATION_BLOCKED'
  | 'CERTIFICATION_INVALID'
  | 'CHECKSUM_MISMATCH'
  | 'REFRESH_REQUIRED'
  | 'LEASE_HELD'
  | 'ERROR';

export type FreshnessStatus =
  | 'FRESH'
  | 'STALE_SOFT'
  | 'STALE_HARD'
  | 'UNKNOWN'
  | 'INVALIDATED';

export interface CacheStatisticsV2 {
  tenant_id: string;
  total_lookups: number;
  hit_count: number;
  miss_count: number;
  bypass_count: number;
  stale_count: number;
  hit_rate: number;
  active_entries_count: number;
  active_payload_bytes: number;
  active_leases_count?: number;
  published_materializations_count?: number;
}

export interface CacheEvictionResultV2 {
  evicted_count: number;
  bytes_freed: number;
  dry_run: boolean;
}

export interface MaterializationPublicationV2 {
  publication_id: string;
  definition_id: string;
  tenant_id: string;
  active_snapshot_id: string;
  previous_snapshot_id?: string;
  published_by: string;
  published_at: string;
}
