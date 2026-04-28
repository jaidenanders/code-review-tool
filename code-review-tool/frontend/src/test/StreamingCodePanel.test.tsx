import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { StreamingCodePanel } from '../components/review/StreamingCodePanel'
import type { ReviewResult } from '../types'

const mockResult: ReviewResult = {
  summary: 'Solid implementation.',
  score: 91,
  issues: [],
  strengths: ['Well structured'],
  raw_response: 'SUMMARY: Solid implementation.\nSCORE: 91\nEND',
}

// Factory: returns a hook-shaped object to be returned by the mock
function makeHookState(overrides = {}) {
  return {
    status: 'idle' as const,
    tokens: [] as string[],
    result: null as ReviewResult | null,
    error: null as string | null,
    sessionId: null as string | null,
    reviewId: null as string | null,
    startReview: vi.fn(),
    reset: vi.fn(),
    ...overrides,
  }
}

vi.mock('../hooks/useSseReview', () => ({
  useSseReview: vi.fn(),
}))

import { useSseReview } from '../hooks/useSseReview'

describe('StreamingCodePanel', () => {
  beforeEach(() => {
    vi.mocked(useSseReview).mockReturnValue(makeHookState())
  })

  it('renders a textarea for code input', () => {
    render(<StreamingCodePanel />)
    expect(screen.getByPlaceholderText(/paste your code/i)).toBeInTheDocument()
  })

  it('renders the submit button', () => {
    render(<StreamingCodePanel />)
    expect(screen.getByRole('button', { name: /review/i })).toBeInTheDocument()
  })

  it('calls startReview when form is submitted', async () => {
    const startReview = vi.fn()
    vi.mocked(useSseReview).mockReturnValue(makeHookState({ startReview }))

    const user = userEvent.setup()
    render(<StreamingCodePanel />)
    await user.type(screen.getByPlaceholderText(/paste your code/i), 'const x = 1')
    await user.click(screen.getByRole('button', { name: /^review$/i }))
    expect(startReview).toHaveBeenCalledWith(
      expect.objectContaining({ code: 'const x = 1' }),
      undefined,
    )
  })

  it('shows streaming tokens while in streaming state', () => {
    vi.mocked(useSseReview).mockReturnValue(
      makeHookState({ status: 'streaming', tokens: ['SUMMARY', ': ok\n', 'SCORE: 88'] }),
    )
    render(<StreamingCodePanel />)
    expect(screen.getByText(/SUMMARY/)).toBeInTheDocument()
  })

  it('shows ReviewResult component when done', () => {
    vi.mocked(useSseReview).mockReturnValue(
      makeHookState({ status: 'done', result: mockResult, tokens: ['SUMMARY: Solid'] }),
    )
    render(<StreamingCodePanel />)
    expect(screen.getByText('91')).toBeInTheDocument()
    expect(screen.getByText(/solid implementation/i)).toBeInTheDocument()
  })

  it('shows error message when in error state', () => {
    vi.mocked(useSseReview).mockReturnValue(
      makeHookState({ status: 'error', error: 'Ollama is offline' }),
    )
    render(<StreamingCodePanel />)
    expect(screen.getByText(/ollama is offline/i)).toBeInTheDocument()
  })

  it('disables submit button while streaming', () => {
    vi.mocked(useSseReview).mockReturnValue(
      makeHookState({ status: 'streaming', tokens: ['tok'] }),
    )
    render(<StreamingCodePanel />)
    expect(screen.getByRole('button', { name: /review/i })).toBeDisabled()
  })

  it('shows a reset/new review button after done', () => {
    vi.mocked(useSseReview).mockReturnValue(
      makeHookState({ status: 'done', result: mockResult }),
    )
    render(<StreamingCodePanel />)
    expect(screen.getByRole('button', { name: /new review/i })).toBeInTheDocument()
  })

  it('calls reset when new review button clicked', async () => {
    const reset = vi.fn()
    vi.mocked(useSseReview).mockReturnValue(
      makeHookState({ status: 'done', result: mockResult, reset }),
    )
    const user = userEvent.setup()
    render(<StreamingCodePanel />)
    await user.click(screen.getByRole('button', { name: /new review/i }))
    expect(reset).toHaveBeenCalled()
  })

  it('shows a streaming indicator label while streaming', () => {
    vi.mocked(useSseReview).mockReturnValue(
      makeHookState({ status: 'streaming', tokens: ['tok'] }),
    )
    render(<StreamingCodePanel />)
    // The indicator label is in a <p> tag inside the streaming output box
    const indicators = screen.getAllByText(/reviewing/i)
    expect(indicators.length).toBeGreaterThan(0)
  })
})
