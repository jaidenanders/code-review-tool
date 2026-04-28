import { useState } from 'react'
import type { MultiFileReviewResponse, FileReviewResult } from '../../types'
import { ScoreRing } from './ScoreRing'
import { IssueCard } from './IssueCard'

interface Props {
  data: MultiFileReviewResponse
}

export function MultiFileReviewResult({ data }: Props) {
  const [expandedFile, setExpandedFile] = useState<string | null>(null)

  return (
    <div className="space-y-6">
      {/* Aggregate header */}
      <div className="flex items-center gap-6">
        <ScoreRing score={data.result.score} />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-700 leading-relaxed">{data.result.summary}</p>
          <p className="text-xs text-gray-400 mt-1">
            {data.total_chunks} chunk{data.total_chunks !== 1 ? 's' : ''} reviewed across{' '}
            {data.per_file.length} file{data.per_file.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* Per-file breakdown */}
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Files</h3>
        <div className="space-y-2">
          {data.per_file.map(pfr => (
            <FileRow
              key={pfr.filename}
              file={pfr}
              expanded={expandedFile === pfr.filename}
              onToggle={() =>
                setExpandedFile(prev => (prev === pfr.filename ? null : pfr.filename))
              }
            />
          ))}
        </div>
      </section>

      {/* Aggregate strengths */}
      {data.result.strengths.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-green-700 mb-2">Strengths</h3>
          <ul className="space-y-1">
            {data.result.strengths.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <span className="text-green-500 mt-0.5">✓</span>
                {s}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Aggregate issues */}
      {data.result.issues.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Overall Issues{' '}
            <span className="font-normal text-gray-400">({data.result.issues.length})</span>
          </h3>
          <div className="space-y-2">
            {data.result.issues.map((issue, i) => (
              <IssueCard key={i} issue={issue} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function FileRow({ file, expanded, onToggle }: { file: FileReviewResult; expanded: boolean; onToggle: () => void }) {
  const scoreColor =
    file.result.score >= 80
      ? 'text-green-600'
      : file.result.score >= 60
        ? 'text-yellow-600'
        : 'text-red-600'

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        aria-label={`Show details for ${file.filename}`}
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <span className={`text-lg font-bold tabular-nums ${scoreColor}`}>
          {file.result.score}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800 truncate">{file.filename}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
              {file.language}
            </span>
            <span className="text-xs text-gray-400">
              {file.chunks_reviewed} chunk{file.chunks_reviewed !== 1 ? 's' : ''}
            </span>
            <span className="text-xs text-gray-400">
              {file.result.issues.length} issue{file.result.issues.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
        <ChevronIcon expanded={expanded} />
      </button>

      {expanded && (
        <div className="p-4 space-y-3 border-t border-gray-100">
          <p className="text-xs text-gray-600 leading-relaxed">{file.result.summary}</p>
          {file.result.issues.map((issue, i) => (
            <IssueCard key={i} issue={issue} />
          ))}
          {file.result.strengths.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-green-700 mb-1">Strengths</p>
              <ul className="space-y-0.5">
                {file.result.strengths.map((s, i) => (
                  <li key={i} className="text-xs text-gray-600 flex gap-1.5">
                    <span className="text-green-500">✓</span>{s}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      className={`w-4 h-4 text-gray-400 transition-transform shrink-0 ${expanded ? 'rotate-180' : ''}`}
      fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  )
}
