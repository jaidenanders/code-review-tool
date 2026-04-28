import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DiffViewer } from '../components/diff/DiffViewer'
import { mockSession, mockDiff } from './fixtures'

vi.mock('../api/review', () => ({
  getDiff: vi.fn(),
}))

import { getDiff } from '../api/review'
const mockGetDiff = vi.mocked(getDiff)

beforeEach(() => vi.clearAllMocks())

describe('DiffViewer', () => {
  it('renders review selection dropdowns', () => {
    render(<DiffViewer session={mockSession} />)
    const selects = screen.getAllByRole('combobox')
    expect(selects).toHaveLength(2)
  })

  it('shows review timestamps in dropdowns', () => {
    render(<DiffViewer session={mockSession} />)
    expect(screen.getAllByText(/jan/i).length).toBeGreaterThan(0)
  })

  it('fetches diff when both reviews selected', async () => {
    mockGetDiff.mockResolvedValueOnce(mockDiff)
    const user = userEvent.setup()
    render(<DiffViewer session={mockSession} />)

    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'review-1')
    await user.selectOptions(selects[1], 'review-2')

    await waitFor(() => expect(mockGetDiff).toHaveBeenCalledWith('session-1', 'review-1', 'review-2'))
  })

  it('renders diff lines with correct colours', async () => {
    mockGetDiff.mockResolvedValueOnce(mockDiff)
    const user = userEvent.setup()
    render(<DiffViewer session={mockSession} />)

    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'review-1')
    await user.selectOptions(selects[1], 'review-2')

    await waitFor(() => {
      expect(screen.getByText('const x = 1')).toBeInTheDocument()
      expect(screen.getByText('const y = 2')).toBeInTheDocument()
    })
  })

  it('shows score delta', async () => {
    mockGetDiff.mockResolvedValueOnce(mockDiff)
    const user = userEvent.setup()
    render(<DiffViewer session={mockSession} />)

    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'review-1')
    await user.selectOptions(selects[1], 'review-2')

    await waitFor(() => expect(screen.getByText(/\+7/)).toBeInTheDocument())
  })

  it('shows prompt when reviews not yet selected', () => {
    render(<DiffViewer session={mockSession} />)
    expect(screen.getByText(/select two reviews/i)).toBeInTheDocument()
  })

  it('shows error when getDiff fails', async () => {
    mockGetDiff.mockRejectedValueOnce(new Error('Diff error'))
    const user = userEvent.setup()
    render(<DiffViewer session={mockSession} />)

    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'review-1')
    await user.selectOptions(selects[1], 'review-2')

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })

  it('added lines get green background class', async () => {
    mockGetDiff.mockResolvedValueOnce(mockDiff)
    const user = userEvent.setup()
    const { container } = render(<DiffViewer session={mockSession} />)

    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'review-1')
    await user.selectOptions(selects[1], 'review-2')

    await waitFor(() => {
      const added = container.querySelector('[data-change="added"]')
      expect(added).toHaveClass('bg-green-50')
    })
  })
})
