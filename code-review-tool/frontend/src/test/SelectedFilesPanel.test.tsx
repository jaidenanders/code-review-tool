import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SelectedFilesPanel } from '../components/review/SelectedFilesPanel'

const selectedFiles = ['src/index.ts', 'src/utils.ts', 'README.md']

describe('SelectedFilesPanel', () => {
  it('renders all selected file names', () => {
    render(<SelectedFilesPanel selectedPaths={selectedFiles} onRemove={vi.fn()} onReviewAll={vi.fn()} loading={false} />)
    expect(screen.getByText('src/index.ts')).toBeInTheDocument()
    expect(screen.getByText('src/utils.ts')).toBeInTheDocument()
    expect(screen.getByText('README.md')).toBeInTheDocument()
  })

  it('shows file count', () => {
    render(<SelectedFilesPanel selectedPaths={selectedFiles} onRemove={vi.fn()} onReviewAll={vi.fn()} loading={false} />)
    expect(screen.getByText(/3 files? selected/i)).toBeInTheDocument()
  })

  it('shows singular when 1 file selected', () => {
    render(<SelectedFilesPanel selectedPaths={['a.ts']} onRemove={vi.fn()} onReviewAll={vi.fn()} loading={false} />)
    expect(screen.getByText(/1 file selected/i)).toBeInTheDocument()
  })

  it('calls onRemove with path when remove button clicked', async () => {
    const onRemove = vi.fn()
    const user = userEvent.setup()
    render(<SelectedFilesPanel selectedPaths={selectedFiles} onRemove={onRemove} onReviewAll={vi.fn()} loading={false} />)
    const removeButtons = screen.getAllByRole('button', { name: /remove/i })
    await user.click(removeButtons[0])
    expect(onRemove).toHaveBeenCalledWith(selectedFiles[0])
  })

  it('renders Review All button', () => {
    render(<SelectedFilesPanel selectedPaths={selectedFiles} onRemove={vi.fn()} onReviewAll={vi.fn()} loading={false} />)
    expect(screen.getByRole('button', { name: /review all/i })).toBeInTheDocument()
  })

  it('calls onReviewAll when button clicked', async () => {
    const onReviewAll = vi.fn()
    const user = userEvent.setup()
    render(<SelectedFilesPanel selectedPaths={selectedFiles} onRemove={vi.fn()} onReviewAll={onReviewAll} loading={false} />)
    await user.click(screen.getByRole('button', { name: /review all/i }))
    expect(onReviewAll).toHaveBeenCalled()
  })

  it('disables Review All when loading', () => {
    render(<SelectedFilesPanel selectedPaths={selectedFiles} onRemove={vi.fn()} onReviewAll={vi.fn()} loading />)
    expect(screen.getByRole('button', { name: /review all/i })).toBeDisabled()
  })

  it('shows loading text while loading', () => {
    render(<SelectedFilesPanel selectedPaths={selectedFiles} onRemove={vi.fn()} onReviewAll={vi.fn()} loading />)
    expect(screen.getByText(/reviewing/i)).toBeInTheDocument()
  })

  it('shows empty state when no files selected', () => {
    render(<SelectedFilesPanel selectedPaths={[]} onRemove={vi.fn()} onReviewAll={vi.fn()} loading={false} />)
    expect(screen.getByText(/no files selected/i)).toBeInTheDocument()
  })

  it('disables Review All when no files selected', () => {
    render(<SelectedFilesPanel selectedPaths={[]} onRemove={vi.fn()} onReviewAll={vi.fn()} loading={false} />)
    expect(screen.getByRole('button', { name: /review all/i })).toBeDisabled()
  })
})
