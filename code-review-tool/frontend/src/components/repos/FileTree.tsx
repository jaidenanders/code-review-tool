import type { FileTreeItem } from '../../types'

interface Props {
  items: FileTreeItem[]
  onSelectFile: (path: string) => void
  selectedPath?: string
  loading?: boolean
}

export function FileTree({ items, onSelectFile, selectedPath, loading }: Props) {
  if (loading) {
    return <div className="text-sm text-gray-400 px-4 py-3">Loading file tree…</div>
  }

  const sorted = [...items].sort((a, b) => {
    if (a.type !== b.type) return a.type === 'tree' ? -1 : 1
    return a.path.localeCompare(b.path)
  })

  return (
    <ul className="text-sm">
      {sorted.map(item => {
        const name = item.path.split('/').pop() ?? item.path
        const isSelected = item.path === selectedPath
        const isDir = item.type === 'tree'

        return (
          <li
            key={item.sha}
            data-type={item.type}
            onClick={() => !isDir && onSelectFile(item.path)}
            className={`flex items-center gap-2 px-3 py-1.5 transition-colors ${
              isDir ? 'cursor-default text-gray-700' : 'cursor-pointer hover:bg-gray-50 text-gray-600'
            } ${isSelected ? 'bg-brand-100' : ''}`}
          >
            {isDir ? <FolderIcon /> : <FileIcon />}
            <span>{name}</span>
          </li>
        )
      })}
    </ul>
  )
}

function FolderIcon() {
  return (
    <svg className="w-4 h-4 text-yellow-500 shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden>
      <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg className="w-4 h-4 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
}
