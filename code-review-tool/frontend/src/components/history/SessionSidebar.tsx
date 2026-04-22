import type { ReviewSession } from '../../types'

interface Props {
  sessions: ReviewSession[]
  onSelectSession: (session: ReviewSession) => void
  onDeleteSession: (id: string) => void
  activeSessionId?: string
}

export function SessionSidebar({ sessions, onSelectSession, onDeleteSession, activeSessionId }: Props) {
  if (sessions.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400 text-xs px-4">
        No review history yet. Submit code to start.
      </div>
    )
  }

  return (
    <ul className="divide-y divide-gray-100">
      {sessions.map(session => {
        const count = session.reviews.length
        const label = session.filename ?? 'Untitled'
        const date = new Date(session.created_at).toLocaleDateString('en-US', {
          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
        })

        return (
          <li
            key={session.id}
            className={`flex items-start gap-2 px-3 py-3 group cursor-pointer hover:bg-gray-50 transition-colors ${
              activeSessionId === session.id ? 'bg-brand-100' : ''
            }`}
            onClick={() => onSelectSession(session)}
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800 truncate">{label}</p>
              {session.repo && (
                <p className="text-xs text-gray-400 truncate">{session.repo}</p>
              )}
              <p className="text-xs text-gray-400">{date}</p>
              <p className="text-xs text-gray-400">
                {count} {count === 1 ? 'review' : 'reviews'}
              </p>
            </div>
            <button
              aria-label="Delete session"
              onClick={e => {
                e.stopPropagation()
                onDeleteSession(session.id)
              }}
              className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all p-1 rounded shrink-0"
            >
              <TrashIcon />
            </button>
          </li>
        )
      })}
    </ul>
  )
}

function TrashIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  )
}
