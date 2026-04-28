import { useState } from 'react'
import { useSseReview } from '../../hooks/useSseReview'
import { ReviewResult } from './ReviewResult'

interface Props {
  sessionId?: string
}

export function StreamingCodePanel({ sessionId }: Props) {
  const [code, setCode] = useState('')
  const [filename, setFilename] = useState('')
  const { status, tokens, result, error, startReview, reset } = useSseReview()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await startReview({ code, filename: filename || undefined }, sessionId)
  }

  const isStreaming = status === 'streaming'
  const isDone = status === 'done'
  const isError = status === 'error'

  if (isDone && result) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-400">Review complete</span>
          <button
            onClick={reset}
            className="text-sm text-brand-600 hover:text-brand-700 font-medium"
          >
            New Review
          </button>
        </div>
        <ReviewResult result={result} />
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <input
        type="text"
        value={filename}
        onChange={e => setFilename(e.target.value)}
        placeholder="Filename (e.g. main.py)"
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-400"
      />
      <textarea
        value={code}
        onChange={e => setCode(e.target.value)}
        placeholder="Paste your code here…"
        rows={12}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-400 resize-y"
      />

      {isError && (
        <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
      )}

      {isStreaming && (
        <div className="border border-gray-200 rounded-lg p-3 bg-gray-50 min-h-[80px]">
          <p className="text-xs text-brand-600 font-semibold mb-2">Reviewing…</p>
          <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono leading-relaxed">
            {tokens.join('')}
          </pre>
        </div>
      )}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isStreaming || !code.trim()}
          className="flex items-center gap-2 bg-brand-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {isStreaming ? (
            <>
              <Spinner />
              Reviewing…
            </>
          ) : (
            'Review'
          )}
        </button>
      </div>
    </form>
  )
}

function Spinner() {
  return (
    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}
