import type { DeviceCodeResponse, GitHubRepo, FileTreeItem, FileContent, PollResult } from '../types'

const BASE = '/api/v1'

export async function startDeviceFlow(): Promise<DeviceCodeResponse> {
  const res = await fetch(`${BASE}/github/auth/device`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to start device flow')
  return res.json()
}

export async function pollDeviceFlow(deviceCode: string): Promise<PollResult> {
  const res = await fetch(`${BASE}/github/auth/poll?device_code=${encodeURIComponent(deviceCode)}`)
  if (!res.ok) throw new Error('Poll request failed')
  return res.json()
}

export async function listRepos(token: string): Promise<GitHubRepo[]> {
  const res = await fetch(`${BASE}/github/repos?token=${encodeURIComponent(token)}`)
  if (!res.ok) throw new Error('Failed to list repos')
  return res.json()
}

export async function getFileTree(
  token: string,
  owner: string,
  repo: string,
  branch?: string,
): Promise<FileTreeItem[]> {
  const params = new URLSearchParams({ token })
  if (branch) params.set('branch', branch)
  const res = await fetch(`${BASE}/github/repos/${owner}/${repo}/tree?${params}`)
  if (!res.ok) throw new Error('Failed to get file tree')
  return res.json()
}

export async function getFileContent(
  token: string,
  owner: string,
  repo: string,
  path: string,
): Promise<FileContent> {
  const params = new URLSearchParams({ token, path })
  const res = await fetch(`${BASE}/github/repos/${owner}/${repo}/file?${params}`)
  if (!res.ok) throw new Error('Failed to get file content')
  return res.json()
}
