import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { IssueCard } from '../components/review/IssueCard'
import { mockReviewResult } from './fixtures'

const criticalIssue = mockReviewResult.issues[0]
const warningIssue = mockReviewResult.issues[1]
const infoIssue = mockReviewResult.issues[2]

describe('IssueCard', () => {
  it('renders issue title', () => {
    render(<IssueCard issue={criticalIssue} />)
    expect(screen.getByText('Null pointer dereference')).toBeInTheDocument()
  })

  it('renders description', () => {
    render(<IssueCard issue={criticalIssue} />)
    expect(screen.getByText('Variable may be null here')).toBeInTheDocument()
  })

  it('renders suggestion', () => {
    render(<IssueCard issue={criticalIssue} />)
    expect(screen.getByText(/add null check before accessing property/i)).toBeInTheDocument()
  })

  it('renders line number when present', () => {
    render(<IssueCard issue={criticalIssue} />)
    expect(screen.getByText(/line 12/i)).toBeInTheDocument()
  })

  it('does not render line when null', () => {
    render(<IssueCard issue={infoIssue} />)
    expect(screen.queryByText(/line/i)).not.toBeInTheDocument()
  })

  it('applies red border for critical severity', () => {
    const { container } = render(<IssueCard issue={criticalIssue} />)
    expect(container.firstChild).toHaveClass('border-red-400')
  })

  it('applies yellow border for warning severity', () => {
    const { container } = render(<IssueCard issue={warningIssue} />)
    expect(container.firstChild).toHaveClass('border-yellow-400')
  })

  it('applies blue border for info severity', () => {
    const { container } = render(<IssueCard issue={infoIssue} />)
    expect(container.firstChild).toHaveClass('border-blue-400')
  })

  it('shows category badge', () => {
    render(<IssueCard issue={criticalIssue} />)
    expect(screen.getByText('bug')).toBeInTheDocument()
  })

  it('shows severity badge', () => {
    render(<IssueCard issue={criticalIssue} />)
    expect(screen.getByText('critical')).toBeInTheDocument()
  })
})
