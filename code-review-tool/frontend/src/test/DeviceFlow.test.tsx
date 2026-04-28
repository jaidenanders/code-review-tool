import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DeviceFlow } from '../components/auth/DeviceFlow'
import { deviceCode } from './fixtures'

vi.mock('../api/github', () => ({
  startDeviceFlow: vi.fn(),
  pollDeviceFlow: vi.fn(),
}))

import { startDeviceFlow, pollDeviceFlow } from '../api/github'

const mockStart = vi.mocked(startDeviceFlow)
const mockPoll = vi.mocked(pollDeviceFlow)

// Stub setInterval/clearInterval to give us manual control
let registeredIntervals: Array<{ fn: () => void; id: number }> = []
let nextId = 1

beforeEach(() => {
  vi.clearAllMocks()
  registeredIntervals = []
  nextId = 1
  vi.spyOn(globalThis, 'setInterval').mockImplementation((fn: TimerHandler) => {
    const id = nextId++
    registeredIntervals.push({ fn: fn as () => void, id })
    return id as unknown as ReturnType<typeof setInterval>
  })
  vi.spyOn(globalThis, 'clearInterval').mockImplementation((id) => {
    registeredIntervals = registeredIntervals.filter(i => i.id !== (id as unknown as number))
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

async function tickIntervals() {
  await act(async () => {
    for (const { fn } of [...registeredIntervals]) fn()
  })
}

describe('DeviceFlow', () => {
  it('renders sign-in button initially', () => {
    render(<DeviceFlow onAuthorized={vi.fn()} />)
    expect(screen.getByRole('button', { name: /sign in with github/i })).toBeInTheDocument()
  })

  it('calls startDeviceFlow on button click and shows user_code', async () => {
    mockStart.mockResolvedValueOnce(deviceCode)
    mockPoll.mockResolvedValue({ status: 'pending' })
    const user = userEvent.setup()

    render(<DeviceFlow onAuthorized={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /sign in with github/i }))

    await waitFor(() => {
      expect(screen.getByText('ABCD-1234')).toBeInTheDocument()
    })
    expect(screen.getByText(/github\.com\/login\/device/i)).toBeInTheDocument()
  })

  it('shows loading state while starting flow', async () => {
    let resolve: (v: typeof deviceCode) => void
    mockStart.mockReturnValueOnce(
      new Promise<typeof deviceCode>(r => { resolve = r }),
    )
    const user = userEvent.setup()

    render(<DeviceFlow onAuthorized={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /sign in with github/i }))

    expect(screen.getByText(/requesting/i)).toBeInTheDocument()

    // clean up
    await act(async () => { resolve!(deviceCode) })
  })

  it('calls onAuthorized with token when poll succeeds', async () => {
    mockStart.mockResolvedValueOnce(deviceCode)
    mockPoll
      .mockResolvedValueOnce({ status: 'pending' })
      .mockResolvedValueOnce({ status: 'authorized', token: 'tok_secret' })

    const onAuthorized = vi.fn()
    const user = userEvent.setup()

    render(<DeviceFlow onAuthorized={onAuthorized} />)
    await user.click(screen.getByRole('button', { name: /sign in with github/i }))

    await waitFor(() => expect(screen.getByText('ABCD-1234')).toBeInTheDocument())

    // Trigger poll interval twice
    await tickIntervals()
    await tickIntervals()

    await waitFor(() => expect(onAuthorized).toHaveBeenCalledWith('tok_secret'))
  })

  it('displays expiry countdown', async () => {
    mockStart.mockResolvedValueOnce(deviceCode)
    mockPoll.mockResolvedValue({ status: 'pending' })
    const user = userEvent.setup()

    render(<DeviceFlow onAuthorized={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /sign in with github/i }))

    await waitFor(() => expect(screen.getByText(/expires/i)).toBeInTheDocument())
  })

  it('shows error when startDeviceFlow fails', async () => {
    mockStart.mockRejectedValueOnce(new Error('Network error'))
    const user = userEvent.setup()

    render(<DeviceFlow onAuthorized={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /sign in with github/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })
})
