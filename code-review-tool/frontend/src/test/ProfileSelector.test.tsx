import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProfileSelector } from '../components/review/ProfileSelector'
import type { ProfileId } from '../types'

const profiles = [
  { id: 'general' as ProfileId, name: 'General', description: 'Balanced review.' },
  { id: 'security' as ProfileId, name: 'Security', description: 'Focus on vulnerabilities.' },
  { id: 'performance' as ProfileId, name: 'Performance', description: 'Focus on speed.' },
  { id: 'style' as ProfileId, name: 'Style', description: 'Focus on readability.' },
]

describe('ProfileSelector', () => {
  it('renders a button for each profile', () => {
    render(<ProfileSelector profiles={profiles} selected="general" onSelect={vi.fn()} />)
    expect(screen.getByRole('button', { name: /general/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /security/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /performance/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /style/i })).toBeInTheDocument()
  })

  it('marks the selected profile button as pressed', () => {
    render(<ProfileSelector profiles={profiles} selected="security" onSelect={vi.fn()} />)
    expect(screen.getByRole('button', { name: /security/i })).toHaveAttribute('aria-pressed', 'true')
  })

  it('other profiles are not pressed', () => {
    render(<ProfileSelector profiles={profiles} selected="security" onSelect={vi.fn()} />)
    expect(screen.getByRole('button', { name: /general/i })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: /performance/i })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: /style/i })).toHaveAttribute('aria-pressed', 'false')
  })

  it('calls onSelect with the profile id when a button is clicked', async () => {
    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(<ProfileSelector profiles={profiles} selected="general" onSelect={onSelect} />)
    await user.click(screen.getByRole('button', { name: /performance/i }))
    expect(onSelect).toHaveBeenCalledWith('performance')
  })

  it('calls onSelect with the correct id for each profile', async () => {
    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(<ProfileSelector profiles={profiles} selected="general" onSelect={onSelect} />)
    await user.click(screen.getByRole('button', { name: /security/i }))
    expect(onSelect).toHaveBeenCalledWith('security')
  })

  it('shows a tooltip or description on the selected profile', () => {
    render(<ProfileSelector profiles={profiles} selected="security" onSelect={vi.fn()} />)
    expect(screen.getByText(/focus on vulnerabilities/i)).toBeInTheDocument()
  })

  it('renders with general selected by default when selected prop is general', () => {
    render(<ProfileSelector profiles={profiles} selected="general" onSelect={vi.fn()} />)
    expect(screen.getByRole('button', { name: /general/i })).toHaveAttribute('aria-pressed', 'true')
  })

  it('does not call onSelect when clicking the already-selected profile', async () => {
    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(<ProfileSelector profiles={profiles} selected="general" onSelect={onSelect} />)
    await user.click(screen.getByRole('button', { name: /general/i }))
    expect(onSelect).not.toHaveBeenCalled()
  })
})
