import { useState, useEffect } from 'react'
import { submitReview, checkHealth, getProfiles } from '../../api/review'
import type { SubmitReviewResponse } from '../../api/review'
import { ProfileSelector } from './ProfileSelector'
import type { ProfileId, ReviewProfile } from '../../types'

const DEFAULT_PROFILES: ReviewProfile[] = [
  { id: 'general', name: 'General', description: 'Balanced review covering bugs, style, security, and performance.' },
  { id: 'security', name: 'Security', description: 'Deep-dive into vulnerabilities, injection flaws, and secrets.' },
  { id: 'performance', name: 'Performance', description: 'Focus on algorithmic complexity and runtime bottlenecks.' },
  { id: 'style', name: 'Style', description: 'Focus on readability, naming conventions, and code organisation.' },
]

interface Props {
  onReviewComplete: (response: SubmitReviewResponse) => void
  initialCode?: string
  filename?: string
  sessionId?: string
}

export function CodePanel({ onReviewComplete, initialCode = '', filename, sessionId }: Props) {
  const [code, setCode] = useState(initialCode)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [offline, setOffline] = useState(false)
  const [profile, setProfile] = useState<ProfileId>('general')
  const [profiles, setProfiles] = useState<ReviewProfile[]>(DEFAULT_PROFILES)

  useEffect(() => {
    checkHealth()
      .then(h => setOffline(h.ollama === 'offline'))
      .catch(() => setOffline(true))
    getProfiles().then(setProfiles).catch(() => { /* use defaults */ })
  }, [])

  useEffect(() => {
    setCode(initialCode)
  }, [initialCode])

  async function handleSubmit() {
    if (!code.trim()) return
    setLoading(true)
    setError(null)
    try {
      const result = await submitReview(
        { code, filename, language: guessLanguage(filename), profile },
        sessionId,
      )
      onReviewComplete(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Review failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-3 h-full">
      {filename && (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <FileIcon />
          <span className="font-mono">{filename}</span>
        </div>
      )}

      {offline && (
        <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-1.5">
          Ollama is offline — reviews will fail until the service is available.
        </div>
      )}

      <textarea
        className="flex-1 min-h-[240px] font-mono text-sm p-3 border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-brand-500 bg-gray-50"
        placeholder="Paste your code here…"
        value={code}
        onChange={e => setCode(e.target.value)}
        spellCheck={false}
      />

      <ProfileSelector
        profiles={profiles}
        selected={profile}
        onSelect={setProfile}
        disabled={loading}
      />

      {error && (
        <div role="alert" className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={!code.trim() || loading}
        className="self-end flex items-center gap-2 bg-brand-600 text-white px-5 py-2 rounded-lg hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors font-medium text-sm"
      >
        {loading ? (
          <>
            <Spinner />
            Reviewing…
          </>
        ) : (
          'Review Code'
        )}
      </button>
    </div>
  )
}

function guessLanguage(filename?: string): string | undefined {
  if (!filename) return undefined
  const ext = filename.split('.').pop()?.toLowerCase()
  const map: Record<string, string> = {
    ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
    py: 'python', rs: 'rust', go: 'go', java: 'java', rb: 'ruby',
    cpp: 'cpp', c: 'c', cs: 'csharp', php: 'php', swift: 'swift',
    kt: 'kotlin', scala: 'scala', sh: 'bash',
  }
  return ext ? map[ext] : undefined
}

function Spinner() {
  return (
    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
}
