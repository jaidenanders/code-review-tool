import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSseReview } from '../hooks/useSseReview'
import type { ReviewResult } from '../types'

const mockResult: ReviewResult = {
  summary: 'Looks good.',
  score: 88,
  issues: [],
  strengths: ['Clean code'],
  raw_response: 'SUMMARY: Looks good.\nSCORE: 88\nEND',
}

function makeReadableStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  let index = 0
  return new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index++]))
      } else {
        controller.close()
      }
    },
  })
}

function buildSseBody(events: Array<{ event: string; data: object }>): string[] {
  return events.map(e => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`)
}

describe('useSseReview', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('starts in idle state', () => {
    const { result } = renderHook(() => useSseReview())
    expect(result.current.status).toBe('idle')
    expect(result.current.tokens).toEqual([])
    expect(result.current.result).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('transitions to streaming when startReview is called', async () => {
    const chunks = buildSseBody([
      { event: 'token', data: { text: 'Hello' } },
      { event: 'result', data: { session_id: 's1', review_id: 'r1', result: mockResult } },
    ])
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      body: makeReadableStream(chunks),
    } as unknown as Response)

    const { result } = renderHook(() => useSseReview())
    await act(async () => {
      await result.current.startReview({ code: 'x = 1', filename: 'a.py' })
    })
    expect(result.current.status).toBe('done')
  })

  it('accumulates token strings', async () => {
    const chunks = buildSseBody([
      { event: 'token', data: { text: 'SUMMARY' } },
      { event: 'token', data: { text: ': ok\n' } },
      { event: 'result', data: { session_id: 's1', review_id: 'r1', result: mockResult } },
    ])
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      body: makeReadableStream(chunks),
    } as unknown as Response)

    const { result } = renderHook(() => useSseReview())
    await act(async () => {
      await result.current.startReview({ code: 'x = 1', filename: 'a.py' })
    })
    expect(result.current.tokens).toContain('SUMMARY')
    expect(result.current.tokens).toContain(': ok\n')
  })

  it('sets result when result event received', async () => {
    const chunks = buildSseBody([
      { event: 'token', data: { text: 'SUMMARY: ok\n' } },
      { event: 'result', data: { session_id: 's1', review_id: 'r1', result: mockResult } },
    ])
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      body: makeReadableStream(chunks),
    } as unknown as Response)

    const { result } = renderHook(() => useSseReview())
    await act(async () => {
      await result.current.startReview({ code: 'x = 1', filename: 'a.py' })
    })
    expect(result.current.result).not.toBeNull()
    expect(result.current.result?.score).toBe(88)
    expect(result.current.sessionId).toBe('s1')
    expect(result.current.reviewId).toBe('r1')
  })

  it('sets error state when server error event received', async () => {
    const chunks = buildSseBody([
      { event: 'error', data: { message: 'Ollama offline' } },
    ])
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      body: makeReadableStream(chunks),
    } as unknown as Response)

    const { result } = renderHook(() => useSseReview())
    await act(async () => {
      await result.current.startReview({ code: 'x = 1', filename: 'a.py' })
    })
    expect(result.current.status).toBe('error')
    expect(result.current.error).toMatch(/ollama/i)
  })

  it('sets error state when fetch throws', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('Network failure'))

    const { result } = renderHook(() => useSseReview())
    await act(async () => {
      await result.current.startReview({ code: 'x = 1', filename: 'a.py' })
    })
    expect(result.current.status).toBe('error')
    expect(result.current.error).toMatch(/network failure/i)
  })

  it('sends correct POST body to stream endpoint', async () => {
    const chunks = buildSseBody([
      { event: 'result', data: { session_id: 's1', review_id: 'r1', result: mockResult } },
    ])
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      body: makeReadableStream(chunks),
    } as unknown as Response)

    const { result } = renderHook(() => useSseReview())
    await act(async () => {
      await result.current.startReview({ code: 'fn main() {}', filename: 'main.rs' })
    })

    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/review/stream')
    expect((init as RequestInit).method).toBe('POST')
    const body = JSON.parse((init as RequestInit).body as string)
    expect(body.code).toBe('fn main() {}')
    expect(body.filename).toBe('main.rs')
  })

  it('can be reset back to idle', async () => {
    const chunks = buildSseBody([
      { event: 'result', data: { session_id: 's1', review_id: 'r1', result: mockResult } },
    ])
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      body: makeReadableStream(chunks),
    } as unknown as Response)

    const { result } = renderHook(() => useSseReview())
    await act(async () => {
      await result.current.startReview({ code: 'x = 1', filename: 'a.py' })
    })
    expect(result.current.status).toBe('done')

    act(() => {
      result.current.reset()
    })
    expect(result.current.status).toBe('idle')
    expect(result.current.tokens).toEqual([])
    expect(result.current.result).toBeNull()
  })

  it('includes session_id in request URL when provided', async () => {
    const chunks = buildSseBody([
      { event: 'result', data: { session_id: 'existing', review_id: 'r2', result: mockResult } },
    ])
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      body: makeReadableStream(chunks),
    } as unknown as Response)

    const { result } = renderHook(() => useSseReview())
    await act(async () => {
      await result.current.startReview({ code: 'x = 1', filename: 'a.py' }, 'existing')
    })

    const [url] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('session_id=existing')
  })
})
