import type { ReviewResult as ReviewResultType } from '../../types'
import { ScoreRing } from './ScoreRing'
import { IssueCard } from './IssueCard'

interface Props {
  result: ReviewResultType
}

const SEVERITY_ORDER = ['critical', 'warning', 'info'] as const

export function ReviewResult({ result }: Props) {
  const grouped = SEVERITY_ORDER.reduce(
    (acc, sev) => {
      acc[sev] = result.issues.filter(i => i.severity === sev)
      return acc
    },
    {} as Record<string, typeof result.issues>,
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-6">
        <ScoreRing score={result.score} />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-700 leading-relaxed">{result.summary}</p>
          <p className="text-xs text-gray-400 mt-1">{result.issues.length} issues detected</p>
        </div>
      </div>

      {result.strengths.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-green-700 mb-2">Strengths</h3>
          <ul className="space-y-1">
            {result.strengths.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <span className="text-green-500 mt-0.5">✓</span>
                {s}
              </li>
            ))}
          </ul>
        </section>
      )}

      {result.issues.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Issues <span className="font-normal text-gray-400">({result.issues.length})</span>
          </h3>
          <div className="space-y-4">
            {SEVERITY_ORDER.map(sev =>
              grouped[sev].length > 0 ? (
                <div key={sev}>
                  <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                    {sev}
                  </p>
                  <div className="space-y-2">
                    {grouped[sev].map((issue, i) => (
                      <IssueCard key={i} issue={issue} />
                    ))}
                  </div>
                </div>
              ) : null,
            )}
          </div>
        </section>
      )}
    </div>
  )
}
