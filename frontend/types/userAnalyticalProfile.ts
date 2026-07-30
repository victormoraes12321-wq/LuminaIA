export type ProfileMode = 'LEGACY_ONLY' | 'SHADOW' | 'V2_READ' | 'V2_READ_WRITE'
export type ProfileStatus = 'ACTIVE' | 'DISABLED' | 'DELETION_PENDING' | 'DELETED'
export type PreferenceStatus =
  | 'ACTIVE'
  | 'DISABLED'
  | 'EXPIRED'
  | 'REVOKED'
  | 'DELETED'
  | 'PENDING_CONFIRMATION'

export type PreferenceType =
  | 'PRESENTATION'
  | 'LOCALE'
  | 'ACCESSIBILITY'
  | 'ANALYTICAL_DEFAULT'
  | 'FAVORITE_METRIC'
  | 'FAVORITE_DIMENSION'
  | 'FAVORITE_ENTITY'
  | 'SAVED_FILTER_REFERENCE'
  | 'SAVED_QUERY_REFERENCE'
  | 'SAVED_DASHBOARD_REFERENCE'
  | 'INTERACTION'
  | 'PRIVACY'
  | 'RETENTION'

export interface ProfileCapabilities {
  mode: ProfileMode
  frontend_enabled: boolean
  defaults_enabled: boolean
  saved_filters_enabled: boolean
  export_enabled: boolean
  deletion_enabled: boolean
  legacy_import_enabled: boolean
}

export interface PreferenceConsent {
  consent_id: string
  status: 'GRANTED' | 'REVOKED' | 'NOT_REQUIRED' | 'MISSING'
  purpose: string
  scope: string
  policy_version: string
  lock_version: number
  granted_at: string | null
  revoked_at: string | null
}

export interface PreferenceOrigin {
  kind:
    | 'USER_EXPLICIT'
    | 'SYSTEM_DEFAULT'
    | 'ADMIN_POLICY'
    | 'LEGACY_IMPORT'
    | 'MIGRATED'
    | 'FEEDBACK_CANDIDATE'
    | 'INFERRED_UNCONFIRMED'
  source_label: string
  confirmed_at: string | null
}

export interface UserPreference {
  preference_id: string
  preference_type: PreferenceType
  preference_key: string
  content: Record<string, string | number | boolean | string[] | null>
  risk: 'SAFE_PRESENTATION' | 'VISIBLE_ANALYTICAL_DEFAULT' | 'REFERENCE_ONLY' | 'RESTRICTED' | 'FORBIDDEN'
  origin: PreferenceOrigin
  status: PreferenceStatus
  consent: PreferenceConsent | null
  effective_from: string | null
  effective_to: string | null
  expires_at: string | null
  version: number
  lock_version: number
  updated_at: string
}

export interface UserAnalyticalProfile {
  profile_id: string
  status: ProfileStatus
  profile_version: number
  lock_version: number
  checksum: string
  preferences: UserPreference[]
  updated_at: string
  disabled_at: string | null
}

export interface AppliedPreferenceItem {
  preference_type: PreferenceType
  label: string
  value_label: string
  origin_label: string
  removable_this_turn: boolean
  settings_path: string
  expires_at: string | null
}

export interface AppliedPreferenceSummary {
  applied: AppliedPreferenceItem[]
  ignored: string[]
  consent_required: string[]
  has_visible_analytical_default: boolean
  schema_version: string
}

export interface ProfileApiError {
  error?: {
    code?: string
    message?: string
  }
  detail?: string
}
