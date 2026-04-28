import type { GitHubRepo } from '../../types'

interface Props {
  repos: GitHubRepo[]
  onSelect: (repo: GitHubRepo) => void
  selectedId?: number
}

export function RepoList({ repos, onSelect, selectedId }: Props) {
  if (repos.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm">No repositories found.</div>
    )
  }

  return (
    <ul className="divide-y divide-gray-100">
      {repos.map(repo => (
        <li
          key={repo.id}
          onClick={() => onSelect(repo)}
          className={`px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors ${
            selectedId === repo.id ? 'bg-brand-100' : ''
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium text-gray-800 text-sm">{repo.name}</span>
            <div className="flex items-center gap-1.5 shrink-0">
              {repo.language && (
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                  {repo.language}
                </span>
              )}
              {repo.private && (
                <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">
                  Private
                </span>
              )}
            </div>
          </div>
          {repo.description && (
            <p className="text-xs text-gray-500 mt-0.5 truncate">{repo.description}</p>
          )}
        </li>
      ))}
    </ul>
  )
}
