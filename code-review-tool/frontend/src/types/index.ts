export type Severity = 'critical' | 'warning' | 'info'
export type IssueCategory = 'bug' | 'complexity' | 'security' | 'style' | 'performance'
export type ChangeType = 'added' | 'removed' | 'unchanged'

export interface DeviceCodeResponse {
  device_code: string
  user_code: string
  verification_uri: string
  expires_in: number
  interval: number
}

export interface GitHubRepo {
  id: number
  name: string
  full_name: string
  private: boolean
  description: string | null
  language: string | null
  default_branch: string
  updated_at: string
}

export interface FileTreeItem {
  path: string
  type: 'blob' | 'tree'
  size: number | null
  sha: string
}

export interface FileContent {
  path: string
  content: string
  encoding: string
  size: number
  sha: string
}

export interface CodeIssue {
  category: IssueCategory
  severity: Severity
  line: number | null
  title: string
  description: string
  suggestion: string
}

export interface ReviewResult {
  summary: string
  score: number
  issues: CodeIssue[]
  strengths: string[]
  raw_response: string
}

export type ProfileId = 'general' | 'security' | 'performance' | 'style'

export interface ReviewProfile {
  id: ProfileId
  name: string
  description: string
}

export interface ReviewRequest {
  code: string
  language?: string
  filename?: string
  context?: string
  profile?: ProfileId
}

export interface SessionReview {
  id: string
  session_id: string
  code_snapshot: string
  result: ReviewResult
  created_at: string
}

export interface ReviewSession {
  id: string
  filename: string | null
  repo: string | null
  created_at: string
  reviews: SessionReview[]
}

export interface DiffLine {
  line_number: number
  content: string
  change_type: ChangeType
}

export interface ReviewDiff {
  session_id: string
  review_a_id: string
  review_b_id: string
  lines: DiffLine[]
  score_delta: number
}

export interface OllamaHealth {
  ollama: 'online' | 'offline'
  models: string[]
  active_model: string
}

export interface PollResult {
  status: 'pending' | 'authorized'
  token?: string
}

// ── Multi-file review ──────────────────────────────────────────────────────────

export interface FileInput {
  filename: string
  code: string
}

export interface FileReviewResult {
  filename: string
  language: string
  result: ReviewResult
  chunks_reviewed: number
}

export interface MultiFileReviewResponse {
  session_id: string
  review_id: string
  result: ReviewResult
  per_file: FileReviewResult[]
  total_chunks: number
}
