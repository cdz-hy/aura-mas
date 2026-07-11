import { beforeEach, describe, expect, it, vi } from 'vitest'

const post = vi.fn(() => Promise.resolve())
vi.mock('@/api/request', () => ({
  default: { post },
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ token: 'test-token' }),
}))

describe('useHeartbeat', () => {
  beforeEach(() => {
    post.mockClear()
    vi.useFakeTimers()
  })

  it('does not start heartbeat for negative placeholder resource ids', async () => {
    const { useHeartbeat } = await import('./useHeartbeat')
    const heartbeat = useHeartbeat()
    heartbeat.start(11, -Date.now())
    expect(heartbeat.isRunning.value).toBe(false)
    vi.advanceTimersByTime(35_000)
    expect(post).not.toHaveBeenCalled()
    heartbeat.stop()
  })

  it('starts heartbeat for positive resource ids', async () => {
    const { useHeartbeat } = await import('./useHeartbeat')
    const heartbeat = useHeartbeat()
    heartbeat.start(11, 87)
    expect(heartbeat.isRunning.value).toBe(true)
    vi.advanceTimersByTime(30_000)
    expect(post).toHaveBeenCalled()
    heartbeat.stop()
  })
})
