import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CodePanel } from '../components/review/CodePanel'

vi.mock('../api/review', () => ({
  submitReview: vi.fn(),
  checkHealth: vi.fn(),
}))

import { submitReview, checkHealth } from '../api/review'
import { mockReviewResult } from './fixtures'

const mockSubmit = vi.mocked(submitReview)
const mockHealth = vi.mocked(checkHealth)

beforeEach(() => {
  vi.clearAllMocks()
  mockHealth.mockResolvedValue({ ollama: 'online', models: ['codellama'], active_model: 'codellama' })
})

describe('CodePanel', () => {
  it('renders textarea for code input', () => {
    render(<CodePanel onReviewComplete={vi.fn()} />)
    expect(screen.getByPlaceholderText(/paste your code/i)).toBeInTheDocument()
  })

  it('renders submit button', () => {
    render(<CodePanel onReviewComplete={vi.fn()} />)
    expect(screen.getByRole('button', { name: /review code/i })).toBeInTheDocument()
  })

  it('disables submit when textarea is empty', () => {
    render(<CodePanel onReviewComplete={vi.fn()} />)
    expect(screen.getByRole('button', { name: /review code/i })).toBeDisabled()
  })

  it('enables submit when code is entered', async () => {
    const user = userEvent.setup()
    render(<CodePanel onReviewComplete={vi.fn()} />)
    await user.type(screen.getByPlaceholderText(/paste your code/i), 'const x = 1')
    expect(screen.getByRole('button', { name: /review code/i })).toBeEnabled()
  })

  it('calls submitReview and fires onReviewComplete', async () => {
    const onReviewComplete = vi.fn()
    const response = { session_id: 's1', review_id: 'r1', result: mockReviewResult }
    mockSubmit.mockResolvedValueOnce(response)
    const user = userEvent.setup()

    render(<CodePanel onReviewComplete={onReviewComplete} />)
    await user.type(screen.getByPlaceholderText(/paste your code/i), 'const x = 1')
    await user.click(screen.getByRole('button', { name: /review code/i }))

    await waitFor(() => expect(onReviewComplete).toHaveBeenCalledWith(response))
  })

  it('shows loading indicator while submitting', async () => {
    let resolve: (v: ReturnType<typeof mockSubmit> extends Promise<infer T> ? T : never) => void
    mockSubmit.mockReturnValueOnce(new Promise(r => { resolve = r as typeof resolve }))
    const user = userEvent.setup()

    render(<CodePanel onReviewComplete={vi.fn()} />)
    await user.type(screen.getByPlaceholderText(/paste your code/i), 'const x = 1')
    await user.click(screen.getByRole('button', { name: /review code/i }))

    expect(screen.getByText(/reviewing/i)).toBeInTheDocument()
    resolve!({ session_id: 's1', review_id: 'r1', result: mockReviewResult })
  })

  it('shows error message on failed submission', async () => {
    mockSubmit.mockRejectedValueOnce(new Error('LLM error'))
    const user = userEvent.setup()

    render(<CodePanel onReviewComplete={vi.fn()} />)
    await user.type(screen.getByPlaceholderText(/paste your code/i), 'const x = 1')
    await user.click(screen.getByRole('button', { name: /review code/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })

  it('pre-populates with initialCode prop', () => {
    render(<CodePanel onReviewComplete={vi.fn()} initialCode="const x = 1" />)
    expect(screen.getByDisplayValue('const x = 1')).toBeInTheDocument()
  })

  it('shows filename when provided', () => {
    render(<CodePanel onReviewComplete={vi.fn()} filename="index.ts" />)
    expect(screen.getByText('index.ts')).toBeInTheDocument()
  })

  it('shows offline warning when ollama is offline', async () => {
    mockHealth.mockResolvedValueOnce({ ollama: 'offline', models: [], active_model: '' })
    render(<CodePanel onReviewComplete={vi.fn()} />)
    await waitFor(() => expect(screen.getByText(/ollama.*offline/i)).toBeInTheDocument())
  })
})
