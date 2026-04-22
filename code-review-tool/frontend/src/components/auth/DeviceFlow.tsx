import { useState, useEffect, useRef } from 'react'
import { startDeviceFlow, pollDeviceFlow } from '../../api/github'
import type { DeviceCodeResponse } from '../../types'

interface Props {
  onAuthorized: (token: string) => void
}

type State = 'idle' | 'requesting' | 'polling' | 'error'

export function DeviceFlow({ onAuthorized }: Props) {
  const [state, setState] = useState<State>('idle')
  const [deviceInfo, setDeviceInfo] = useState<DeviceCodeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [secondsLeft, setSecondsLeft] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  async function handleStart() {
    setState('requesting')
    setError(null)
    try {
      const info = await startDeviceFlow()
      setDeviceInfo(info)
      setSecondsLeft(info.expires_in)
      setState('polling')

      intervalRef.current = setInterval(() => {
        setSecondsLeft(s => {
          if (s <= 1) {
            if (intervalRef.current) clearInterval(intervalRef.current)
            if (pollRef.current) clearInterval(pollRef.current)
            setState('error')
            setError('Code expired. Please try again.')
            return 0
          }
          return s - 1
        })
      }, 1000)

      pollRef.current = setInterval(async () => {
        try {
          const result = await pollDeviceFlow(info.device_code)
          if (result.status === 'authorized' && result.token) {
            if (intervalRef.current) clearInterval(intervalRef.current)
            if (pollRef.current) clearInterval(pollRef.current)
            onAuthorized(result.token)
          }
        } catch {
          // polling errors are transient, keep trying
        }
      }, (info.interval + 1) * 1000)
    } catch (e) {
      setState('error')
      setError(e instanceof Error ? e.message : 'Failed to start sign-in')
    }
  }

  if (state === 'idle' || state === 'error') {
    return (
      <div className="flex flex-col items-center gap-4 p-8">
        <h2 className="text-xl font-semibold text-gray-800">Sign in with GitHub</h2>
        <p className="text-sm text-gray-500 text-center max-w-sm">
          Authenticate via GitHub Device Flow — no redirect needed.
        </p>
        {error && (
          <div role="alert" className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-4 py-2">
            {error}
          </div>
        )}
        <button
          onClick={handleStart}
          className="flex items-center gap-2 bg-gray-900 text-white px-6 py-2.5 rounded-lg hover:bg-gray-700 transition-colors font-medium"
        >
          <GitHubIcon />
          Sign in with GitHub
        </button>
      </div>
    )
  }

  if (state === 'requesting') {
    return (
      <div className="flex flex-col items-center gap-4 p-8">
        <Spinner />
        <p className="text-gray-500">Requesting device code…</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-6 p-8 max-w-sm mx-auto">
      <h2 className="text-xl font-semibold text-gray-800">Authorize with GitHub</h2>
      <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
        <li>
          Go to{' '}
          <span className="font-mono text-brand-700">{deviceInfo?.verification_uri}</span>
        </li>
        <li>Enter the code below</li>
      </ol>
      <div className="bg-gray-100 rounded-xl px-8 py-4 text-center">
        <p className="font-mono text-3xl font-bold tracking-widest text-gray-900">
          {deviceInfo?.user_code}
        </p>
      </div>
      <p className="text-xs text-gray-400">
        Expires in{' '}
        <span className="font-medium text-gray-600">
          {Math.floor(secondsLeft / 60)}:{String(secondsLeft % 60).padStart(2, '0')}
        </span>
      </p>
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Spinner size="sm" />
        Waiting for authorization…
      </div>
    </div>
  )
}

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden>
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
  )
}

function Spinner({ size = 'md' }: { size?: 'sm' | 'md' }) {
  const cls = size === 'sm' ? 'w-4 h-4' : 'w-8 h-8'
  return (
    <svg className={`${cls} animate-spin text-brand-500`} fill="none" viewBox="0 0 24 24" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}
