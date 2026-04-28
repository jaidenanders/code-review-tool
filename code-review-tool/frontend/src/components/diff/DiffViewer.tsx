import { useState, useEffect } from 'react'
import { getDiff } from '../../api/review'
import type { ReviewSession, ReviewDiff } from '../../types'

interface Props {
  session: ReviewSession
}

const changeStyles: Record<string, string> = {
  added: 'bg-green-50 text-green-800',
  removed: 'bg-red-50 text-red-800 line-through opacity-70',
  unchanged: 'bg-white text-gray-700',
}

const changePrefix: Record<string, string> = {
  added: '+',
  removed: '-',
  unchanged: ' ',
}

export function DiffViewer({ session }: Props) {
  const [reviewAId, setReviewAId] = useState('')
  const [reviewBId, setReviewBId] = useState('')
  const [diff, setDiff] = useState<ReviewDiff | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!reviewAId || !reviewBId || reviewAId === reviewBId) return
    setLoading(true)
    setError(null)
    getDiff(session.id, reviewAId, reviewBId)
      .then(setDiff)
      .catch(e => setError(e instanceof Error ? e.message : 'Diff failed'))
      .finally(() => setLoading(false))
  }, [session.id, reviewAId, reviewBId])

  const label = (id: string) => {
    const r = session.reviews.find(r => r.id === id)
    if (!r) return id
    return new Date(r.created_at).toLocaleString('en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <select
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
          value={reviewAId}
          onChange={e => setReviewAId(e.target.value)}
        >
          <option value="">Review A…</option>
          {session.reviews.map(r => (
            <option key={r.id} value={r.id}>{label(r.id)}</option>
          ))}
        </select>

        <span className="text-gray-400">→</span>

        <select
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
          value={reviewBId}
          onChange={e => setReviewBId(e.target.value)}
        >
          <option value="">Review B…</option>
          {session.reviews.map(r => (
            <option key={r.id} value={r.id}>{label(r.id)}</option>
          ))}
        </select>
      </div>

      {(!reviewAId || !reviewBId) && (
        <p className="text-sm text-gray-400 text-center py-4">
          Select two reviews to compare
        </p>
      )}

      {error && (
        <div role="alert" className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      {loading && (
        <p className="text-sm text-gray-400 text-center py-4">Loading diff…</p>
      )}

      {diff && !loading && (
        <>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-600">Score delta:</span>
            <span
              className={`text-sm font-bold ${diff.score_delta >= 0 ? 'text-green-600' : 'text-red-600'}`}
            >
              {diff.score_delta >= 0 ? '+' : ''}{diff.score_delta}
            </span>
          </div>

          <div className="border border-gray-200 rounded-lg overflow-hidden font-mono text-xs">
            <div className="bg-gray-50 px-3 py-1.5 text-gray-400 text-xs border-b border-gray-200">
              Code diff
            </div>
            {diff.lines.map((line, i) => (
              <div
                key={i}
                data-change={line.change_type}
                className={`flex items-start px-3 py-0.5 ${changeStyles[line.change_type]}`}
              >
                <span className="w-8 text-gray-400 shrink-0 select-none">{line.line_number}</span>
                <span className="w-4 shrink-0 select-none">{changePrefix[line.change_type]}</span>
                <span className="whitespace-pre-wrap break-all">{line.content}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
