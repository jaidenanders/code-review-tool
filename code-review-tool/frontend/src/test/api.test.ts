import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { startDeviceFlow, pollDeviceFlow, listRepos, getFileTree, getFileContent } from '../api/github'
import { checkHealth, submitReview, listSessions, getSession, deleteSession, getDiff } from '../api/review'
import { deviceCode, mockRepos, mockFileTree, mockReviewResult, mockSession, mockDiff } from './fixtures'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

function ok(body: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(body),
  } as Response)
}

function fail(status = 500) {
  return Promise.resolve({ ok: false, status } as Response)
}

beforeEach(() => mockFetch.mockReset())
afterEach(() => vi.restoreAllMocks())

describe('GitHub API', () => {
  it('startDeviceFlow POSTs to /api/v1/github/auth/device', async () => {
    mockFetch.mockReturnValueOnce(ok(deviceCode))
    const result = await startDeviceFlow()
    expect(mockFetch).toHaveBeenCalledWith('/api/v1/github/auth/device', { method: 'POST' })
    expect(result).toEqual(deviceCode)
  })

  it('startDeviceFlow throws on error', async () => {
    mockFetch.mockReturnValueOnce(fail())
    await expect(startDeviceFlow()).rejects.toThrow('Failed to start device flow')
  })

  it('pollDeviceFlow GETs with device_code param', async () => {
    mockFetch.mockReturnValueOnce(ok({ status: 'pending' }))
    const result = await pollDeviceFlow('dev-code-123')
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/github/auth/poll?device_code=dev-code-123',
    )
    expect(result).toEqual({ status: 'pending' })
  })

  it('pollDeviceFlow returns authorized with token', async () => {
    mockFetch.mockReturnValueOnce(ok({ status: 'authorized', token: 'tok_abc' }))
    const result = await pollDeviceFlow('dev-code-123')
    expect(result).toEqual({ status: 'authorized', token: 'tok_abc' })
  })

  it('listRepos GETs with token param', async () => {
    mockFetch.mockReturnValueOnce(ok(mockRepos))
    const result = await listRepos('my-token')
    expect(mockFetch).toHaveBeenCalledWith('/api/v1/github/repos?token=my-token')
    expect(result).toHaveLength(2)
  })

  it('getFileTree encodes owner/repo/branch', async () => {
    mockFetch.mockReturnValueOnce(ok(mockFileTree))
    const result = await getFileTree('my-token', 'user', 'my-repo', 'main')
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/github/repos/user/my-repo/tree?token=my-token&branch=main',
    )
    expect(result).toHaveLength(4)
  })

  it('getFileContent encodes path param', async () => {
    const content = { path: 'src/index.ts', content: 'hello', encoding: 'utf-8', size: 5, sha: 'sha2' }
    mockFetch.mockReturnValueOnce(ok(content))
    const result = await getFileContent('tok', 'user', 'repo', 'src/index.ts')
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/github/repos/user/repo/file?token=tok&path=src%2Findex.ts',
    )
    expect(result.content).toBe('hello')
  })
})

describe('Review API', () => {
  it('checkHealth returns health status', async () => {
    const health = { ollama: 'online', models: ['codellama'], active_model: 'codellama' }
    mockFetch.mockReturnValueOnce(ok(health))
    const result = await checkHealth()
    expect(result.ollama).toBe('online')
  })

  it('submitReview POSTs code', async () => {
    const response = { session_id: 's1', review_id: 'r1', result: mockReviewResult }
    mockFetch.mockReturnValueOnce(ok(response))
    const result = await submitReview({ code: 'const x = 1', language: 'typescript' })
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/review/',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(result.session_id).toBe('s1')
  })

  it('submitReview appends session_id when provided', async () => {
    const response = { session_id: 's1', review_id: 'r2', result: mockReviewResult }
    mockFetch.mockReturnValueOnce(ok(response))
    await submitReview({ code: 'const x = 2' }, 's1')
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/review/?session_id=s1',
      expect.anything(),
    )
  })

  it('listSessions returns array', async () => {
    mockFetch.mockReturnValueOnce(ok([mockSession]))
    const result = await listSessions()
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('session-1')
  })

  it('getSession returns session with reviews', async () => {
    mockFetch.mockReturnValueOnce(ok(mockSession))
    const result = await getSession('session-1')
    expect(result.reviews).toHaveLength(2)
  })

  it('deleteSession sends DELETE', async () => {
    mockFetch.mockReturnValueOnce({ ok: true } as Response)
    await deleteSession('session-1')
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/review/sessions/session-1',
      { method: 'DELETE' },
    )
  })

  it('getDiff returns diff with score_delta', async () => {
    mockFetch.mockReturnValueOnce(ok(mockDiff))
    const result = await getDiff('session-1', 'review-1', 'review-2')
    expect(result.score_delta).toBe(7)
    expect(result.lines).toHaveLength(2)
  })
})
