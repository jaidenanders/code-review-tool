import type {
  DeviceCodeResponse,
  GitHubRepo,
  FileTreeItem,
  ReviewResult,
  ReviewSession,
  ReviewDiff,
} from '../types'

export const deviceCode: DeviceCodeResponse = {
  device_code: 'dev-code-123',
  user_code: 'ABCD-1234',
  verification_uri: 'https://github.com/login/device',
  expires_in: 900,
  interval: 5,
}

export const mockRepo: GitHubRepo = {
  id: 1,
  name: 'my-repo',
  full_name: 'user/my-repo',
  private: false,
  description: 'A test repo',
  language: 'TypeScript',
  default_branch: 'main',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockRepos: GitHubRepo[] = [
  mockRepo,
  {
    id: 2,
    name: 'private-repo',
    full_name: 'user/private-repo',
    private: true,
    description: null,
    language: 'Python',
    default_branch: 'main',
    updated_at: '2024-01-02T00:00:00Z',
  },
]

export const mockFileTree: FileTreeItem[] = [
  { path: 'src', type: 'tree', size: null, sha: 'sha1' },
  { path: 'src/index.ts', type: 'blob', size: 1024, sha: 'sha2' },
  { path: 'src/utils.ts', type: 'blob', size: 512, sha: 'sha3' },
  { path: 'README.md', type: 'blob', size: 256, sha: 'sha4' },
]

export const mockReviewResult: ReviewResult = {
  summary: 'Code is generally well-written with minor improvements needed.',
  score: 78,
  issues: [
    {
      category: 'bug',
      severity: 'critical',
      line: 12,
      title: 'Null pointer dereference',
      description: 'Variable may be null here',
      suggestion: 'Add null check before accessing property',
    },
    {
      category: 'style',
      severity: 'warning',
      line: 5,
      title: 'Inconsistent naming',
      description: 'Use camelCase consistently',
      suggestion: 'Rename to camelCase',
    },
    {
      category: 'performance',
      severity: 'info',
      line: null,
      title: 'Consider memoization',
      description: 'This calculation runs on every render',
      suggestion: 'Wrap in useMemo',
    },
  ],
  strengths: [
    'Good separation of concerns',
    'Well-typed interfaces',
    'Clear function names',
  ],
  raw_response: 'raw llm output here',
}

export const mockSession: ReviewSession = {
  id: 'session-1',
  filename: 'index.ts',
  repo: 'user/my-repo',
  created_at: '2024-01-01T10:00:00Z',
  reviews: [
    {
      id: 'review-1',
      session_id: 'session-1',
      code_snapshot: 'const x = 1',
      result: mockReviewResult,
      created_at: '2024-01-01T10:00:00Z',
    },
    {
      id: 'review-2',
      session_id: 'session-1',
      code_snapshot: 'const x = 1\nconst y = 2',
      result: { ...mockReviewResult, score: 85 },
      created_at: '2024-01-01T10:05:00Z',
    },
  ],
}

export const mockDiff: ReviewDiff = {
  session_id: 'session-1',
  review_a_id: 'review-1',
  review_b_id: 'review-2',
  lines: [
    { line_number: 1, content: 'const x = 1', change_type: 'unchanged' },
    { line_number: 2, content: 'const y = 2', change_type: 'added' },
  ],
  score_delta: 7,
}
