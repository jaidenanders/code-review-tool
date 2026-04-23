import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MultiFileReviewResult } from '../components/review/MultiFileReviewResult'
import { mockReviewResult } from './fixtures'
import type { MultiFileReviewResponse } from '../types'

const mockMultiResult: MultiFileReviewResponse = {
  session_id: 's1',
  review_id: 'r1',
  result: { ...mockReviewResult, summary: 'Reviewed 2 files with aggregate score of 78/100.', score: 78 },
  per_file: [
    {
      filename: 'src/index.ts',
      language: 'typescript',
      result: { ...mockReviewResult, score: 85, summary: 'Great file.' },
      chunks_reviewed: 1,
    },
    {
      filename: 'src/utils.ts',
      language: 'typescript',
      result: { ...mockReviewResult, score: 71, summary: 'Needs improvement.' },
      chunks_reviewed: 2,
    },
  ],
  total_chunks: 3,
}

describe('MultiFileReviewResult', () => {
  it('renders aggregate score', () => {
    render(<MultiFileReviewResult data={mockMultiResult} />)
    expect(screen.getByText('78')).toBeInTheDocument()
  })

  it('renders aggregate summary', () => {
    render(<MultiFileReviewResult data={mockMultiResult} />)
    expect(screen.getByText(/reviewed 2 files/i)).toBeInTheDocument()
  })

  it('renders per-file section headers', () => {
    render(<MultiFileReviewResult data={mockMultiResult} />)
    expect(screen.getByText('src/index.ts')).toBeInTheDocument()
    expect(screen.getByText('src/utils.ts')).toBeInTheDocument()
  })

  it('renders per-file scores', () => {
    render(<MultiFileReviewResult data={mockMultiResult} />)
    expect(screen.getByText('85')).toBeInTheDocument()
    expect(screen.getByText('71')).toBeInTheDocument()
  })

  it('renders language badge for each file', () => {
    render(<MultiFileReviewResult data={mockMultiResult} />)
    const tsBadges = screen.getAllByText('typescript')
    expect(tsBadges.length).toBeGreaterThanOrEqual(2)
  })

  it('shows total chunks reviewed', () => {
    render(<MultiFileReviewResult data={mockMultiResult} />)
    expect(screen.getByText(/3 chunks/i)).toBeInTheDocument()
  })

  it('shows chunks_reviewed per file', () => {
    render(<MultiFileReviewResult data={mockMultiResult} />)
    expect(screen.getByText(/2 chunks/i)).toBeInTheDocument()
  })

  it('can expand per-file details to see per-file summary', async () => {
    const user = userEvent.setup()
    render(<MultiFileReviewResult data={mockMultiResult} />)
    // Per-file summaries are only visible when expanded
    expect(screen.queryByText('Great file.')).not.toBeInTheDocument()
    const expandButtons = screen.getAllByRole('button', { name: /details/i })
    await user.click(expandButtons[0])
    expect(screen.getByText('Great file.')).toBeInTheDocument()
  })

  it('renders overall issues section', () => {
    render(<MultiFileReviewResult data={mockMultiResult} />)
    expect(screen.getByText(/overall issues/i)).toBeInTheDocument()
  })

  it('renders strengths section', () => {
    render(<MultiFileReviewResult data={mockMultiResult} />)
    expect(screen.getByText(/strengths/i)).toBeInTheDocument()
  })
})
