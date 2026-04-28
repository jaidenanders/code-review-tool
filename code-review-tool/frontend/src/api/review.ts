import type {
  OllamaHealth,
  ReviewRequest,
  ReviewSession,
  ReviewDiff,
  FileInput,
  MultiFileReviewResponse,
  ReviewProfile,
} from '../types'

const BASE = '/api/v1'

export interface SubmitReviewResponse {
  session_id: string
  review_id: string
  result: import('../types').ReviewResult
}

export async function getProfiles(): Promise<ReviewProfile[]> {
  const res = await fetch(`${BASE}/review/profiles`)
  if (!res.ok) throw new Error('Failed to load profiles')
  return res.json()
}

export async function checkHealth(): Promise<OllamaHealth> {
  const res = await fetch(`${BASE}/review/health`)
  if (!res.ok) throw new Error('Health check failed')
  return res.json()
}

export async function submitReview(
  request: ReviewRequest,
  sessionId?: string,
): Promise<SubmitReviewResponse> {
  const url = sessionId
    ? `${BASE}/review/?session_id=${encodeURIComponent(sessionId)}`
    : `${BASE}/review/`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!res.ok) throw new Error('Review submission failed')
  return res.json()
}

export async function listSessions(): Promise<ReviewSession[]> {
  const res = await fetch(`${BASE}/review/sessions`)
  if (!res.ok) throw new Error('Failed to list sessions')
  return res.json()
}

export async function getSession(id: string): Promise<ReviewSession> {
  const res = await fetch(`${BASE}/review/sessions/${encodeURIComponent(id)}`)
  if (!res.ok) throw new Error('Failed to get session')
  return res.json()
}

export async function deleteSession(id: string): Promise<void> {
  const res = await fetch(`${BASE}/review/sessions/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to delete session')
}

export async function submitMultiReview(
  files: FileInput[],
  sessionId?: string,
  context?: string,
): Promise<MultiFileReviewResponse> {
  const url = sessionId
    ? `${BASE}/review/multi?session_id=${encodeURIComponent(sessionId)}`
    : `${BASE}/review/multi`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ files, context }),
  })
  if (!res.ok) throw new Error('Multi-file review failed')
  return res.json()
}

export async function getDiff(
  sessionId: string,
  reviewAId: string,
  reviewBId: string,
): Promise<ReviewDiff> {
  const params = new URLSearchParams({ review_a: reviewAId, review_b: reviewBId })
  const res = await fetch(`${BASE}/review/sessions/${encodeURIComponent(sessionId)}/diff?${params}`)
  if (!res.ok) throw new Error('Failed to get diff')
  return res.json()
}
