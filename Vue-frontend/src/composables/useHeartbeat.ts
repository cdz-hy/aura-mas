import { ref, onUnmounted } from 'vue'
import request from '@/api/request'
import { useAuthStore } from '@/stores/auth'

const HEARTBEAT_INTERVAL = 30_000 // 30 seconds

export function useHeartbeat() {
  const isRunning = ref(false)
  let timer: ReturnType<typeof setInterval> | null = null
  let lastTick = 0
  let currentPlanId: number | null = null
  let currentResourceId: number | null = null

  function start(planId: number, resourceId: number) {
    // Switching resource — flush accumulated time for old resource
    if (isRunning.value && (currentPlanId !== planId || currentResourceId !== resourceId)) {
      flush()
    }

    currentPlanId = planId
    currentResourceId = resourceId
    if (isRunning.value) return

    isRunning.value = true
    lastTick = Date.now()

    timer = setInterval(() => {
      _sendHeartbeat()
    }, HEARTBEAT_INTERVAL)
  }

  function stop() {
    flush()
    isRunning.value = false
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    currentPlanId = null
    currentResourceId = null
  }

  function _sendHeartbeat() {
    if (!currentPlanId || !currentResourceId) return
    const now = Date.now()
    const elapsed = Math.round((now - lastTick) / 1000)
    if (elapsed <= 0) return
    lastTick = now

    request.post('/progress/heartbeat', null, {
      params: {
        planId: currentPlanId,
        resourceId: currentResourceId,
        elapsedSeconds: elapsed,
      },
    }).catch(() => {})
  }

  function flush() {
    if (!currentPlanId || !currentResourceId) return
    const now = Date.now()
    const elapsed = Math.round((now - lastTick) / 1000)
    if (elapsed <= 0) return
    lastTick = now

    // Use fetch with keepalive for unload scenarios (supports auth header)
    try {
      const authStore = useAuthStore()
      const url = `/api/progress/heartbeat?planId=${currentPlanId}&resourceId=${currentResourceId}&elapsedSeconds=${elapsed}`
      fetch(url, {
        method: 'POST',
        keepalive: true,
        headers: {
          'Authorization': `Bearer ${authStore.token}`,
        },
      })
    } catch {
      // Fallback
      request.post('/progress/heartbeat', null, {
        params: {
          planId: currentPlanId,
          resourceId: currentResourceId,
          elapsedSeconds: elapsed,
        },
      }).catch(() => {})
    }
  }

  // Flush on page unload
  if (typeof window !== 'undefined') {
    const _beforeUnload = () => flush()
    window.addEventListener('beforeunload', _beforeUnload)
    onUnmounted(() => {
      window.removeEventListener('beforeunload', _beforeUnload)
    })
  }

  onUnmounted(() => {
    stop()
  })

  return { start, stop, isRunning }
}
