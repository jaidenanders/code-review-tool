import type { CodeIssue } from '../../types'

interface Props {
  issue: CodeIssue
}

const severityStyles: Record<string, string> = {
  critical: 'border-red-400 bg-red-50',
  warning: 'border-yellow-400 bg-yellow-50',
  info: 'border-blue-400 bg-blue-50',
}

const severityBadge: Record<string, string> = {
  critical: 'bg-red-100 text-red-700',
  warning: 'bg-yellow-100 text-yellow-700',
  info: 'bg-blue-100 text-blue-700',
}

const categoryBadge: Record<string, string> = {
  bug: 'bg-red-100 text-red-600',
  security: 'bg-orange-100 text-orange-600',
  performance: 'bg-purple-100 text-purple-600',
  complexity: 'bg-indigo-100 text-indigo-600',
  style: 'bg-gray-100 text-gray-600',
}

export function IssueCard({ issue }: Props) {
  return (
    <div className={`border-l-4 rounded-r-lg p-3 ${severityStyles[issue.severity]}`}>
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <p className="font-medium text-sm text-gray-800">{issue.title}</p>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${categoryBadge[issue.category]}`}>
            {issue.category}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${severityBadge[issue.severity]}`}>
            {issue.severity}
          </span>
          {issue.line != null && (
            <span className="text-xs text-gray-400">Line {issue.line}</span>
          )}
        </div>
      </div>
      <p className="text-xs text-gray-600 mt-1">{issue.description}</p>
      <p className="text-xs text-gray-500 mt-1.5 italic">💡 {issue.suggestion}</p>
    </div>
  )
}
