export type FeedbackLifecycle =
  | 'RECEIVED' | 'VALIDATED' | 'TRIAGED' | 'IN_REVIEW'
  | 'APPROVED' | 'REJECTED' | 'NEEDS_INFORMATION'
  | 'WITHDRAWN' | 'EXPIRED' | 'ARCHIVED'

export type FeedbackReviewDecision =
  | 'CORRECT' | 'ACCEPTABLE' | 'PARTIALLY_CORRECT' | 'INCORRECT'
  | 'UNVERIFIABLE' | 'AMBIGUOUS' | 'OUT_OF_SCOPE'
  | 'UNSAFE' | 'TECHNICAL_FAILURE'

export interface FeedbackRecord {
  feedback_id: string
  user_id: string
  target: {
    response_node_id: string
    session_id: string
    response_checksum: string
  }
  category: string
  explanation: string | null
  lifecycle: FeedbackLifecycle
  triage: {
    severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
    priority: 'P1' | 'P2' | 'P3' | 'P4'
    review_queue: string
    rule_ids: string[]
    warnings: string[]
  } | null
  reviewer_user_id: string | null
  review_decision: FeedbackReviewDecision | null
  lock_version: number
  checksum: string
  created_at: string
  updated_at: string
}

export interface FeedbackApiError {
  error?: {
    code?: string
    message?: string
  }
  detail?: string
}

export interface TrainingCandidate {
  candidate_id: string
  feedback_id: string
  status: 'CANDIDATE' | 'VALIDATED' | 'APPROVED' | 'REJECTED' | 'IN_DATASET' | 'DEPRECATED' | 'ARCHIVED'
  quality_status: 'VALID' | 'INCOMPLETE' | 'AMBIGUOUS' | 'SENSITIVE' | 'CONFLICTING' | 'OUTDATED_CONTRACT' | 'BLOCKED'
  quality_rule_ids: string[]
  lock_version: number
  checksum: string
}

export interface ApprovedTrainingExample {
  example_id: string
  candidate_id: string
  domain: string
  quality_score: number
  checksum: string
}

export interface TrainingDatasetSnapshot {
  snapshot_id: string
  dataset_id: string
  version: number
  name: string
  purpose: string
  status: 'DRAFT' | 'IN_REVIEW' | 'APPROVED' | 'PUBLISHED' | 'REJECTED' | 'DEPRECATED' | 'ARCHIVED'
  example_ids: string[]
  lock_version: number
  checksum: string
}
