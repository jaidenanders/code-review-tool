import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RepoList } from '../components/repos/RepoList'
import { mockRepos } from './fixtures'

describe('RepoList', () => {
  it('renders list of repos', () => {
    render(<RepoList repos={mockRepos} onSelect={vi.fn()} />)
    expect(screen.getByText('my-repo')).toBeInTheDocument()
    expect(screen.getByText('private-repo')).toBeInTheDocument()
  })

  it('shows language badges', () => {
    render(<RepoList repos={mockRepos} onSelect={vi.fn()} />)
    expect(screen.getByText('TypeScript')).toBeInTheDocument()
    expect(screen.getByText('Python')).toBeInTheDocument()
  })

  it('shows private badge for private repos', () => {
    render(<RepoList repos={mockRepos} onSelect={vi.fn()} />)
    expect(screen.getByText('Private')).toBeInTheDocument()
  })

  it('calls onSelect with repo when clicked', async () => {
    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(<RepoList repos={mockRepos} onSelect={onSelect} />)
    await user.click(screen.getByText('my-repo'))
    expect(onSelect).toHaveBeenCalledWith(mockRepos[0])
  })

  it('shows description when available', () => {
    render(<RepoList repos={mockRepos} onSelect={vi.fn()} />)
    expect(screen.getByText('A test repo')).toBeInTheDocument()
  })

  it('shows empty state when no repos', () => {
    render(<RepoList repos={[]} onSelect={vi.fn()} />)
    expect(screen.getByText(/no repositories/i)).toBeInTheDocument()
  })

  it('highlights selected repo', () => {
    render(<RepoList repos={mockRepos} onSelect={vi.fn()} selectedId={1} />)
    const item = screen.getByText('my-repo').closest('li')
    expect(item).toHaveClass('bg-brand-100')
  })
})
