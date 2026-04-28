import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ReviewResult } from '../components/review/ReviewResult'
import { mockReviewResult } from './fixtures'

describe('ReviewResult', () => {
  it('renders summary text', () => {
    render(<ReviewResult result={mockReviewResult} />)
    expect(screen.getByText(mockReviewResult.summary)).toBeInTheDocument()
  })

  it('renders score ring with score', () => {
    render(<ReviewResult result={mockReviewResult} />)
    expect(screen.getByText('78')).toBeInTheDocument()
  })

  it('renders all issues grouped by severity', () => {
    render(<ReviewResult result={mockReviewResult} />)
    expect(screen.getAllByText(/critical/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/warning/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/info/i).length).toBeGreaterThan(0)
  })

  it('renders strengths section', () => {
    render(<ReviewResult result={mockReviewResult} />)
    expect(screen.getByText('Good separation of concerns')).toBeInTheDocument()
    expect(screen.getByText('Well-typed interfaces')).toBeInTheDocument()
    expect(screen.getByText('Clear function names')).toBeInTheDocument()
  })

  it('renders strengths heading', () => {
    render(<ReviewResult result={mockReviewResult} />)
    expect(screen.getByText(/strengths/i)).toBeInTheDocument()
  })

  it('renders issues count', () => {
    render(<ReviewResult result={mockReviewResult} />)
    expect(screen.getByText(/3 issues/i)).toBeInTheDocument()
  })

  it('renders all issue titles', () => {
    render(<ReviewResult result={mockReviewResult} />)
    expect(screen.getByText('Null pointer dereference')).toBeInTheDocument()
    expect(screen.getByText('Inconsistent naming')).toBeInTheDocument()
    expect(screen.getByText('Consider memoization')).toBeInTheDocument()
  })
})
