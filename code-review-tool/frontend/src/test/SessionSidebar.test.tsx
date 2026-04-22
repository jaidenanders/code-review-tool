import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SessionSidebar } from '../components/history/SessionSidebar'
import { mockSession } from './fixtures'

const mockSessions = [
  mockSession,
  {
    ...mockSession,
    id: 'session-2',
    filename: 'utils.py',
    repo: null,
    created_at: '2024-01-02T10:00:00Z',
    reviews: [mockSession.reviews[0]],
  },
]

describe('SessionSidebar', () => {
  it('renders session list', () => {
    render(<SessionSidebar sessions={mockSessions} onSelectSession={vi.fn()} onDeleteSession={vi.fn()} />)
    expect(screen.getByText('index.ts')).toBeInTheDocument()
    expect(screen.getByText('utils.py')).toBeInTheDocument()
  })

  it('shows repo name when available', () => {
    render(<SessionSidebar sessions={mockSessions} onSelectSession={vi.fn()} onDeleteSession={vi.fn()} />)
    expect(screen.getByText('user/my-repo')).toBeInTheDocument()
  })

  it('shows review count per session', () => {
    render(<SessionSidebar sessions={mockSessions} onSelectSession={vi.fn()} onDeleteSession={vi.fn()} />)
    expect(screen.getByText('2 reviews')).toBeInTheDocument()
    expect(screen.getByText('1 review')).toBeInTheDocument()
  })

  it('calls onSelectSession when session is clicked', async () => {
    const onSelectSession = vi.fn()
    const user = userEvent.setup()
    render(<SessionSidebar sessions={mockSessions} onSelectSession={onSelectSession} onDeleteSession={vi.fn()} />)
    await user.click(screen.getByText('index.ts'))
    expect(onSelectSession).toHaveBeenCalledWith(mockSession)
  })

  it('highlights active session', () => {
    render(
      <SessionSidebar
        sessions={mockSessions}
        onSelectSession={vi.fn()}
        onDeleteSession={vi.fn()}
        activeSessionId="session-1"
      />,
    )
    const item = screen.getByText('index.ts').closest('li')
    expect(item).toHaveClass('bg-brand-100')
  })

  it('calls onDeleteSession when delete button is clicked', async () => {
    const onDeleteSession = vi.fn()
    const user = userEvent.setup()
    render(<SessionSidebar sessions={mockSessions} onSelectSession={vi.fn()} onDeleteSession={onDeleteSession} />)
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    await user.click(deleteButtons[0])
    expect(onDeleteSession).toHaveBeenCalledWith('session-1')
  })

  it('shows empty state when no sessions', () => {
    render(<SessionSidebar sessions={[]} onSelectSession={vi.fn()} onDeleteSession={vi.fn()} />)
    expect(screen.getByText(/no review history/i)).toBeInTheDocument()
  })

  it('shows session created date', () => {
    render(<SessionSidebar sessions={mockSessions} onSelectSession={vi.fn()} onDeleteSession={vi.fn()} />)
    expect(screen.getAllByText(/jan/i).length).toBeGreaterThan(0)
  })
})
