import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ScoreRing } from '../components/review/ScoreRing'

describe('ScoreRing', () => {
  it('renders the score number', () => {
    render(<ScoreRing score={78} />)
    expect(screen.getByText('78')).toBeInTheDocument()
  })

  it('renders /100 label', () => {
    render(<ScoreRing score={78} />)
    expect(screen.getByText('/100')).toBeInTheDocument()
  })

  it('applies green color for score >= 80', () => {
    const { container } = render(<ScoreRing score={85} />)
    const circle = container.querySelector('circle.score-arc')
    expect(circle).toHaveClass('text-green-500')
  })

  it('applies yellow color for score 60-79', () => {
    const { container } = render(<ScoreRing score={70} />)
    const circle = container.querySelector('circle.score-arc')
    expect(circle).toHaveClass('text-yellow-500')
  })

  it('applies red color for score < 60', () => {
    const { container } = render(<ScoreRing score={45} />)
    const circle = container.querySelector('circle.score-arc')
    expect(circle).toHaveClass('text-red-500')
  })

  it('renders SVG element', () => {
    const { container } = render(<ScoreRing score={78} />)
    expect(container.querySelector('svg')).toBeInTheDocument()
  })
})
