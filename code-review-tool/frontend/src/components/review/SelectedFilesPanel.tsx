interface Props {
  selectedPaths: string[]
  onRemove: (path: string) => void
  onReviewAll: () => void
  loading: boolean
}

export function SelectedFilesPanel({ selectedPaths, onRemove, onReviewAll, loading }: Props) {
  const count = selectedPaths.length

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          {count === 0
            ? 'No files selected'
            : `${count} file${count === 1 ? '' : 's'} selected`}
        </p>
        <button
          aria-label="Review All"
          onClick={onReviewAll}
          disabled={count === 0 || loading}
          className="flex items-center gap-1.5 text-sm bg-brand-600 text-white px-3 py-1.5 rounded-lg hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {loading ? (
            <>
              <Spinner />
              Reviewing…
            </>
          ) : (
            'Review All'
          )}
        </button>
      </div>

      {count === 0 ? (
        <p className="text-xs text-gray-400 italic">
          Check files in the tree to add them here.
        </p>
      ) : (
        <ul className="space-y-1">
          {selectedPaths.map(path => {
            const name = path.split('/').pop() ?? path
            return (
              <li
                key={path}
                className="flex items-center gap-2 text-xs bg-gray-50 rounded-lg px-3 py-2"
              >
                <FileIcon />
                <span className="flex-1 font-mono text-gray-700 truncate" title={path}>
                  {path}
                </span>
                <button
                  aria-label={`Remove ${name}`}
                  onClick={() => onRemove(path)}
                  className="text-gray-400 hover:text-red-500 transition-colors shrink-0"
                >
                  <XIcon />
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
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

function XIcon() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg className="w-3.5 h-3.5 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
}
