import { useState, useEffect, useCallback } from 'react'
import { DeviceFlow } from './components/auth/DeviceFlow'
import { RepoList } from './components/repos/RepoList'
import { FileTree } from './components/repos/FileTree'
import { CodePanel } from './components/review/CodePanel'
import { ReviewResult } from './components/review/ReviewResult'
import { SessionSidebar } from './components/history/SessionSidebar'
import { DiffViewer } from './components/diff/DiffViewer'
import { listRepos, getFileTree, getFileContent } from './api/github'
import { listSessions, getSession, deleteSession } from './api/review'
import type { GitHubRepo, FileTreeItem, ReviewResult as ReviewResultType, ReviewSession } from './types'
import type { SubmitReviewResponse } from './api/review'

type Tab = 'review' | 'diff'

export default function App() {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem('gh_token'))

  const [repos, setRepos] = useState<GitHubRepo[]>([])
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepo | null>(null)
  const [fileTree, setFileTree] = useState<FileTreeItem[]>([])
  const [treeLoading, setTreeLoading] = useState(false)
  const [selectedPath, setSelectedPath] = useState<string | undefined>()
  const [fileCode, setFileCode] = useState<string | undefined>()

  const [sessions, setSessions] = useState<ReviewSession[]>([])
  const [activeSession, setActiveSession] = useState<ReviewSession | null>(null)
  const [latestResult, setLatestResult] = useState<ReviewResultType | null>(null)
  const [tab, setTab] = useState<Tab>('review')

  const [repoError, setRepoError] = useState<string | null>(null)

  const refreshSessions = useCallback(async () => {
    try {
      const list = await listSessions()
      setSessions(list)
    } catch {
      // non-fatal
    }
  }, [])

  useEffect(() => {
    if (!token) return
    listRepos(token)
      .then(setRepos)
      .catch(e => setRepoError(e.message))
    refreshSessions()
  }, [token, refreshSessions])

  function handleAuthorized(t: string) {
    sessionStorage.setItem('gh_token', t)
    setToken(t)
  }

  async function handleSelectRepo(repo: GitHubRepo) {
    setSelectedRepo(repo)
    setFileTree([])
    setSelectedPath(undefined)
    setFileCode(undefined)
    if (!token) return
    setTreeLoading(true)
    try {
      const tree = await getFileTree(token, ...repo.full_name.split('/') as [string, string], repo.default_branch)
      setFileTree(tree)
    } catch {
      // silently leave tree empty
    } finally {
      setTreeLoading(false)
    }
  }

  async function handleSelectFile(path: string) {
    if (!token || !selectedRepo) return
    setSelectedPath(path)
    const [owner, repo] = selectedRepo.full_name.split('/')
    try {
      const content = await getFileContent(token, owner, repo, path)
      setFileCode(content.content)
    } catch {
      setFileCode(undefined)
    }
  }

  async function handleReviewComplete(response: SubmitReviewResponse) {
    setLatestResult(response.result)
    const session = await getSession(response.session_id)
    setActiveSession(session)
    setSessions(prev => {
      const idx = prev.findIndex(s => s.id === session.id)
      if (idx >= 0) {
        const copy = [...prev]
        copy[idx] = session
        return copy
      }
      return [session, ...prev]
    })
  }

  async function handleSelectSession(session: ReviewSession) {
    const full = await getSession(session.id)
    setActiveSession(full)
    const last = full.reviews[full.reviews.length - 1]
    if (last) setLatestResult(last.result)
  }

  async function handleDeleteSession(id: string) {
    await deleteSession(id)
    setSessions(prev => prev.filter(s => s.id !== id))
    if (activeSession?.id === id) {
      setActiveSession(null)
      setLatestResult(null)
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-gray-100">
        <div className="bg-white shadow-xl rounded-2xl p-2 w-full max-w-md">
          <DeviceFlow onAuthorized={handleAuthorized} />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <h1 className="font-semibold text-gray-800">Code Review Tool</h1>
        <button
          onClick={() => { sessionStorage.removeItem('gh_token'); setToken(null) }}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          Sign out
        </button>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — repos + file tree */}
        <aside className="w-64 border-r border-gray-200 bg-white flex flex-col overflow-hidden shrink-0">
          <div className="px-3 py-2 border-b border-gray-100">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Repositories</p>
          </div>
          <div className="overflow-y-auto flex-1">
            {repoError && (
              <p className="text-xs text-red-500 px-4 py-2">{repoError}</p>
            )}
            <RepoList
              repos={repos}
              onSelect={handleSelectRepo}
              selectedId={selectedRepo?.id}
            />
          </div>

          {selectedRepo && (
            <>
              <div className="px-3 py-2 border-t border-b border-gray-100">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider truncate">
                  {selectedRepo.name}
                </p>
              </div>
              <div className="overflow-y-auto flex-1">
                <FileTree
                  items={fileTree}
                  onSelectFile={handleSelectFile}
                  selectedPath={selectedPath}
                  loading={treeLoading}
                />
              </div>
            </>
          )}
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="bg-white border-b border-gray-200 px-4 flex gap-1 pt-2">
            {(['review', 'diff'] as Tab[]).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-1.5 text-sm rounded-t-lg font-medium capitalize transition-colors ${
                  tab === t
                    ? 'bg-brand-50 text-brand-700 border border-b-0 border-gray-200'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {t === 'diff' ? 'Compare Reviews' : 'Code Review'}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {tab === 'review' && (
              <div className="grid grid-cols-2 gap-6 h-full">
                <section>
                  <h2 className="text-sm font-semibold text-gray-600 mb-3">Code</h2>
                  <CodePanel
                    onReviewComplete={handleReviewComplete}
                    initialCode={fileCode}
                    filename={selectedPath}
                    sessionId={activeSession?.id}
                  />
                </section>
                <section>
                  <h2 className="text-sm font-semibold text-gray-600 mb-3">Result</h2>
                  {latestResult ? (
                    <ReviewResult result={latestResult} />
                  ) : (
                    <p className="text-sm text-gray-400">Submit code to see review results.</p>
                  )}
                </section>
              </div>
            )}

            {tab === 'diff' && (
              <div className="max-w-3xl mx-auto">
                {activeSession ? (
                  activeSession.reviews.length >= 2 ? (
                    <DiffViewer session={activeSession} />
                  ) : (
                    <p className="text-sm text-gray-400">
                      Submit at least two reviews in the same session to compare.
                    </p>
                  )
                ) : (
                  <p className="text-sm text-gray-400">
                    Select a session from the history to compare reviews.
                  </p>
                )}
              </div>
            )}
          </div>
        </main>

        {/* Right sidebar — session history */}
        <aside className="w-56 border-l border-gray-200 bg-white flex flex-col overflow-hidden shrink-0">
          <div className="px-3 py-2 border-b border-gray-100">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">History</p>
          </div>
          <div className="overflow-y-auto flex-1">
            <SessionSidebar
              sessions={sessions}
              onSelectSession={handleSelectSession}
              onDeleteSession={handleDeleteSession}
              activeSessionId={activeSession?.id}
            />
          </div>
        </aside>
      </div>
    </div>
  )
}
