import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FileTree } from '../components/repos/FileTree'
import { mockFileTree } from './fixtures'

describe('FileTree', () => {
  it('renders file and directory entries', () => {
    render(<FileTree items={mockFileTree} onSelectFile={vi.fn()} />)
    expect(screen.getByText('src')).toBeInTheDocument()
    expect(screen.getByText('README.md')).toBeInTheDocument()
  })

  it('shows folder icon for directories', () => {
    render(<FileTree items={mockFileTree} onSelectFile={vi.fn()} />)
    const folder = screen.getByText('src').closest('[data-type="tree"]')
    expect(folder).toBeInTheDocument()
  })

  it('shows file icon for blobs', () => {
    render(<FileTree items={mockFileTree} onSelectFile={vi.fn()} />)
    const file = screen.getByText('README.md').closest('[data-type="blob"]')
    expect(file).toBeInTheDocument()
  })

  it('calls onSelectFile with path when blob is clicked', async () => {
    const onSelectFile = vi.fn()
    const user = userEvent.setup()
    render(<FileTree items={mockFileTree} onSelectFile={onSelectFile} />)
    await user.click(screen.getByText('README.md'))
    expect(onSelectFile).toHaveBeenCalledWith('README.md')
  })

  it('does not call onSelectFile when directory is clicked', async () => {
    const onSelectFile = vi.fn()
    const user = userEvent.setup()
    render(<FileTree items={mockFileTree} onSelectFile={onSelectFile} />)
    await user.click(screen.getByText('src'))
    expect(onSelectFile).not.toHaveBeenCalled()
  })

  it('highlights selected file', () => {
    render(<FileTree items={mockFileTree} onSelectFile={vi.fn()} selectedPath="README.md" />)
    const item = screen.getByText('README.md').closest('li')
    expect(item).toHaveClass('bg-brand-100')
  })

  it('shows loading state', () => {
    render(<FileTree items={[]} onSelectFile={vi.fn()} loading />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })
})
