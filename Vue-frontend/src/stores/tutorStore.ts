import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { issueTicket } from '@/api/auth'
import { getSessions, getSessionMessages } from '@/api/chat'
import { PYTHON_AI_BASE } from '@/api/request'
import { useAuthStore } from './auth'

export interface TutorMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface TutorSession {
  sessionId: string
  title: string
  messageCount: number
  lastMessageAt: string
}

export const useTutorStore = defineStore('tutor', () => {
  // ─── State ───
  const contextPlanId = ref(0)
  const contextResourceId = ref(0)

  const activeSessionId = ref('')
  const messages = ref<TutorMessage[]>([])
  const loading = ref(false)
  const progress = ref('')
  const eventSource = ref<EventSource | null>(null)

  const sessions = ref<TutorSession[]>([])
  const sessionsLoading = ref(false)

  let sessionCounter = 0

  // ─── Getters ───
  const hasActiveSession = computed(() => !!activeSessionId.value)

  // ─── Context ───
  function setPlanContext(planId: number, resourceId: number) {
    const changed = contextPlanId.value !== planId
    contextPlanId.value = planId
    contextResourceId.value = resourceId
    if (changed) {
      activeSessionId.value = ''
      messages.value = []
    }
  }

  function setPlanResourceId(resourceId: number) {
    contextResourceId.value = resourceId
  }

  // ─── Session ID generation ───
  function _buildSessionId(): string {
    const authStore = useAuthStore()
    const userId = authStore.user?.id || 0
    const base = `tutor-${contextPlanId.value}-${userId}`
    return sessionCounter > 0 ? `${base}-${sessionCounter}` : base
  }

  // Refresh session list metadata only (no message reload)
  async function _refreshSessionList() {
    try {
      const res = await getSessions('chat', contextPlanId.value)
      const allSessions = res.data || []
      const prefix = `tutor-${contextPlanId.value}-`
      sessions.value = allSessions.filter((s: any) => s.sessionId?.startsWith(prefix))
    } catch (e) {
      console.error('[TutorStore] 刷新会话列表失败:', e)
    }
  }

  // ─── Sessions ───
  async function loadSessions() {
    sessionsLoading.value = true
    try {
      const res = await getSessions('chat', contextPlanId.value)
      const allSessions = res.data || []
      const prefix = `tutor-${contextPlanId.value}-`
      sessions.value = allSessions.filter((s: any) => s.sessionId?.startsWith(prefix))

      // Don't reload messages while SSE is streaming — it would overwrite in-flight content
      if (loading.value) return

      // Auto-select latest session and load its messages
      if (sessions.value.length > 0) {
        const latest = sessions.value[0]
        if (activeSessionId.value !== latest.sessionId) {
          activeSessionId.value = latest.sessionId
        }
        await loadSessionMessages(latest.sessionId)
      } else if (!activeSessionId.value) {
        activeSessionId.value = _buildSessionId()
      }
    } catch (e) {
      console.error('[TutorStore] 加载会话列表失败:', e)
      if (!activeSessionId.value) {
        activeSessionId.value = _buildSessionId()
      }
    } finally {
      sessionsLoading.value = false
    }
  }

  async function loadSessionMessages(sessionId: string) {
    try {
      const res = await getSessionMessages(sessionId, 500)
      const dbMessages = res.data || []
      messages.value = dbMessages.map((m: any) => ({
        role: m.dialogueType === 'USER' ? 'user' as const : 'assistant' as const,
        content: m.conversationText || '',
      }))
    } catch (e) {
      console.error('[TutorStore] 加载会话消息失败:', e)
      messages.value = []
    }
  }

  async function selectSession(sessionId: string) {
    if (sessionId === activeSessionId.value) return
    closeConnection()
    activeSessionId.value = sessionId
    await loadSessionMessages(sessionId)
  }

  function newSession() {
    closeConnection()
    messages.value = []
    sessionCounter++
    activeSessionId.value = _buildSessionId()
    // Refresh session list in background
    loadSessions()
  }

  // ─── SSE Send ───
  async function sendMessage(text: string) {
    if (!text.trim() || loading.value) return

    messages.value.push({ role: 'user', content: text })
    messages.value.push({ role: 'assistant', content: '' })
    loading.value = true

    try {
      const ticketRes = await issueTicket()
      const ticket = ticketRes.data.ticket

      const params = new URLSearchParams({
        ticket,
        plan_id: String(contextPlanId.value),
        resource_id: String(contextResourceId.value),
        message: text,
        session_id: activeSessionId.value,
      })

      const es = new EventSource(`${PYTHON_AI_BASE}/api/ai/tutor/chat?${params}`)
      eventSource.value = es

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'chunk') {
            progress.value = ''
            const last = messages.value[messages.value.length - 1]
            if (last?.role === 'assistant') {
              last.content += data.content
            }
          } else if (data.type === 'progress') {
            progress.value = data.content
          } else if (data.type === 'replace') {
            // 后端修正消息内容（如插入图片到段落间）
            const last = messages.value[messages.value.length - 1]
            if (last?.role === 'assistant') {
              last.content = data.content
            }
          } else if (data.type === 'error') {
            const last = messages.value[messages.value.length - 1]
            if (last?.role === 'assistant') {
              last.content = data.content || '发生错误，请稍后再试'
            }
          } else if (data.type === 'done') {
            es.close()
            eventSource.value = null
            loading.value = false
            progress.value = ''
            // Only refresh session list metadata, don't reload messages (they're already local)
            _refreshSessionList()
          }
        } catch {}
      }

      es.onerror = () => {
        es.close()
        eventSource.value = null
        loading.value = false
        progress.value = ''
        const last = messages.value[messages.value.length - 1]
        if (last?.role === 'assistant' && !last.content) {
          last.content = '连接中断，请稍后再试'
        }
      }
    } catch (e) {
      loading.value = false
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant' && !last.content) {
        last.content = '发送失败，请稍后再试'
      }
    }
  }

  function closeConnection() {
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
    loading.value = false
  }

  function stopGeneration() {
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
    loading.value = false
  }

  return {
    // State
    contextPlanId,
    contextResourceId,
    activeSessionId,
    messages,
    loading,
    progress,
    sessions,
    sessionsLoading,
    // Getters
    hasActiveSession,
    // Actions
    setPlanContext,
    setPlanResourceId,
    loadSessions,
    loadSessionMessages,
    selectSession,
    newSession,
    sendMessage,
    closeConnection,
    stopGeneration,
  }
})
