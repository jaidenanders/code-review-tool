import { useState, useCallback } from 'react'
import type { ReviewRequest, ReviewResult } from '../types'

const BASE = '/api/v1'

export type SseStatus = 'idle' | 'streaming' | 'done' | 'error'

export interface SseReviewState {
  status: SseStatus
  tokens: string[]
  result: ReviewResult | null
  error: string | null
  sessionId: string | null
  reviewId: string | null
  startReview: (request: ReviewRequest, sessionId?: string) => Promise<void>
  reset: () => void
}

const INITIAL_STATE = {
  status: 'idle' as SseStatus,
  tokens: [] as string[],
  result: null as ReviewResult | null,
  error: null as string | null,
  sessionId: null as string | null,
  reviewId: null as string | null,
}

export function useSseReview(): SseReviewState {
  const [state, setState] = useState(INITIAL_STATE)

  const reset = useCallback(() => {
    setState(INITIAL_STATE)
  }, [])

  const startReview = useCallback(async (request: ReviewRequest, sessionId?: string) => {
    setState({ ...INITIAL_STATE, status: 'streaming' })

    const url = sessionId
      ? `${BASE}/review/stream?session_id=${encodeURIComponent(sessionId)}`
      : `${BASE}/review/stream`

    let response: Response
    try {
      response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      })
    } catch (err) {
      setState(s => ({ ...s, status: 'error', error: (err as Error).message }))
      return
    }

    if (!response.ok || !response.body) {
      setState(s => ({ ...s, status: 'error', error: 'Stream request failed' }))
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() ?? ''

        for (const block of blocks) {
          if (!block.trim()) continue
          let eventType = ''
          let dataStr = ''
          for (const line of block.split('\n')) {
            if (line.startsWith('event:')) eventType = line.slice(6).trim()
            else if (line.startsWith('data:')) dataStr = line.slice(5).trim()
          }
          if (!eventType || !dataStr) continue

          let payload: Record<string, unknown>
          try {
            payload = JSON.parse(dataStr)
          } catch {
            continue
          }

          if (eventType === 'token') {
            const text = payload.text as string
            setState(s => ({ ...s, tokens: [...s.tokens, text] }))
          } else if (eventType === 'result') {
            setState(s => ({
              ...s,
              status: 'done',
              result: payload.result as ReviewResult,
              sessionId: payload.session_id as string,
              reviewId: payload.review_id as string,
            }))
          } else if (eventType === 'error') {
            setState(s => ({
              ...s,
              status: 'error',
              error: payload.message as string,
            }))
            return
          }
        }
      }
    } catch (err) {
      setState(s => ({ ...s, status: 'error', error: (err as Error).message }))
    }
  }, [])

  return { ...state, startReview, reset }
}
