import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { issueTicket } from '@/api/auth'
import { getSessions, getSessionMessages } from '@/api/chat'
import { PYTHON_AI_BASE } from '@/api/request'
import { useAuthStore } from './auth'

export interface SearchSource {
  title: string
  url: string
  snippet?: string
  score?: number
}

export interface TutorMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  thinkings?: Array<{ agent: string, content: string }>
  searchSources?: SearchSource[]
  searchQuery?: string
  isSearching?: boolean
}

export interface TutorSession {
  sessionId: string
  title: string
  messageCount: number
  lastMessageAt: string
}

const TUTOR_SESSION_KEY = 'tutor_activeSessionId'
const TUTOR_PLAN_KEY = 'tutor_currentPlanId'

export const useTutorStore = defineStore('tutor', () => {
  // ─── State ───
  const contextPlanId = ref(Number(localStorage.getItem(TUTOR_PLAN_KEY)) || 0)
  const contextResourceId = ref(0)
  const contextType = ref('')
  const contextData = ref<Record<string, any>>({})

  const activeSessionId = ref(localStorage.getItem(TUTOR_SESSION_KEY) || '')
  const messages = ref<TutorMessage[]>([])
  const loading = ref(false)
  const progress = ref('')
  const eventSource = ref<EventSource | null>(null)

  const sessions = ref<TutorSession[]>([])
  const sessionsLoading = ref(false)

  // 用 Set 跟踪新创建的会话 ID，避免模块级变量的竞态问题
  const newlyCreatedSessions = new Set<string>()

  // ─── Per-planId state cache (prevents cross-panel state overwrite) ───
  interface PlanState {
    messages: TutorMessage[]
    activeSessionId: string
  }
  const planStates = new Map<number, PlanState>()

  function _savePlanState(planId: number) {
    planStates.set(planId, {
      messages: [...messages.value],
      activeSessionId: activeSessionId.value,
    })
  }

  function _restorePlanState(planId: number): boolean {
    const state = planStates.get(planId)
    if (state) {
      messages.value = state.messages
      activeSessionId.value = state.activeSessionId
      return true
    }
    return false
  }

  // ─── Getters ───
  const hasActiveSession = computed(() => !!activeSessionId.value)

  // ─── Context ───
  function setPlanContext(planId: number, resourceId: number) {
    const changed = contextPlanId.value !== planId
    if (changed) {
      // 保存当前 planId 的状态
      _savePlanState(contextPlanId.value)
      contextPlanId.value = planId
      contextResourceId.value = resourceId
      localStorage.setItem(TUTOR_PLAN_KEY, String(planId))
      // 恢复目标 planId 的状态（如果有缓存）
      if (!_restorePlanState(planId)) {
        _setActiveSession('')
        messages.value = []
      }
    } else {
      contextResourceId.value = resourceId
    }
  }

  function setPlanResourceId(resourceId: number) {
    contextResourceId.value = resourceId
  }

  function setPageContext(type: string, data: Record<string, any>) {
    contextType.value = type
    contextData.value = data
  }

  // ─── Session ID generation ───
  function _buildSessionId(): string {
    const authStore = useAuthStore()
    const userId = authStore.user?.id || 0
    let rand = ''
    while (rand.length < 12) {
      rand += Math.random().toString(36).slice(2)
    }
    rand = rand.slice(0, 12)
    const id = `tutor-${contextPlanId.value}-${userId}-${rand}`
    return id.slice(0, 36)
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

  function _setActiveSession(sessionId: string) {
    activeSessionId.value = sessionId
    if (sessionId) {
      localStorage.setItem(TUTOR_SESSION_KEY, sessionId)
    } else {
      localStorage.removeItem(TUTOR_SESSION_KEY)
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
    } catch (e) {
      console.error('[TutorStore] 加载会话列表失败:', e)
    } finally {
      sessionsLoading.value = false
    }

    // Don't reload messages while SSE is streaming — it would overwrite in-flight content
    if (loading.value) return

    // 新建会话后跳过自动选择，避免覆盖用户刚创建的空会话
    if (newlyCreatedSessions.size > 0) {
      newlyCreatedSessions.clear()
      return
    }

    // 优先用 localStorage 持久化的 activeSessionId 直接加载消息
    // 不依赖 getSessions 的返回结果（Java 后端可能返回空或失败）
    if (activeSessionId.value) {
      const ok = await loadSessionMessages(activeSessionId.value)
      if (!ok) {
        // 持久化的会话在后端已不存在，清理并创建新会话
        _setActiveSession('')
        _setActiveSession(_buildSessionId())
      }
    } else if (sessions.value.length > 0) {
      _setActiveSession(sessions.value[0].sessionId)
      await loadSessionMessages(sessions.value[0].sessionId)
    } else {
      _setActiveSession(_buildSessionId())
    }
  }

  async function loadSessionMessages(sessionId: string): Promise<boolean> {
    try {
      const res = await getSessionMessages(sessionId, 500)
      const dbMessages = res.data || []
      messages.value = dbMessages.map((m: any) => ({
        id: m.id,
        role: m.dialogueType === 'USER' ? 'user' as const : 'assistant' as const,
        content: m.conversationText || '',
      }))
      return true
    } catch (e) {
      console.error('[TutorStore] 加载会话消息失败:', e)
      messages.value = []
      return false
    }
  }

  async function selectSession(sessionId: string) {
    if (sessionId === activeSessionId.value) return
    closeConnection()
    _setActiveSession(sessionId)
    await loadSessionMessages(sessionId)
  }

  function newSession() {
    closeConnection()
    messages.value = []
    const sid = _buildSessionId()
    _setActiveSession(sid)
    newlyCreatedSessions.add(sid)
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
      if (contextType.value) {
        params.set('context_type', contextType.value)
      }
      if (contextData.value && Object.keys(contextData.value).length > 0) {
        params.set('context_data', JSON.stringify(contextData.value))
      }

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
          } else if (data.type === 'search_start') {
            const last = messages.value[messages.value.length - 1]
            if (last?.role === 'assistant') {
              last.isSearching = true
              last.searchQuery = data.content
              last.searchSources = []
            }
          } else if (data.type === 'search_result') {
            const last = messages.value[messages.value.length - 1]
            if (last?.role === 'assistant') {
              try {
                const source = JSON.parse(data.content)
                if (!last.searchSources) last.searchSources = []
                last.searchSources.push(source)
              } catch {}
            }
          } else if (data.type === 'search_done') {
            const last = messages.value[messages.value.length - 1]
            if (last?.role === 'assistant') {
              last.isSearching = false
            }
          } else if (data.type === 'progress') {
            progress.value = data.content
          } else if (data.type === 'replace') {
            // 后端修正消息内容（如插入图片到段落间）
            const last = messages.value[messages.value.length - 1]
            if (last?.role === 'assistant') {
              last.content = data.content
            }
          } else if (data.type === 'thinking') {
            const last = messages.value[messages.value.length - 1]
            if (last?.role === 'assistant') {
              if (!last.thinkings) last.thinkings = []
              last.thinkings.push({ agent: data.agent || '辅导智能体', content: data.content })
            }
          } else if (data.type === 'thinking_start') {
            const last = messages.value[messages.value.length - 1]
            if (last?.role === 'assistant') {
              if (!last.thinkings) last.thinkings = []
              last.thinkings.push({ agent: data.agent || '辅导智能体', content: data.content || '' })
            }
          } else if (data.type === 'thinking_chunk') {
            const last = messages.value[messages.value.length - 1]
            if (last?.role === 'assistant' && last.thinkings?.length) {
              last.thinkings[last.thinkings.length - 1].content += data.content
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
        _refreshSessionList()
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

  async function deleteMessageAction(id: number) {
    try {
      const { deleteMessage } = await import('@/api/chat')
      await deleteMessage(id)
      messages.value = messages.value.filter(m => m.id !== id)
    } catch (e) {
      console.error('[TutorStore] 删除消息失败:', e)
    }
  }

  async function deleteMessagesAction(ids: number[]) {
    try {
      const { deleteMessages } = await import('@/api/chat')
      await deleteMessages(ids)
      messages.value = messages.value.filter(m => m.id === undefined || !ids.includes(m.id))
    } catch (e) {
      console.error('[TutorStore] 批量删除消息失败:', e)
    }
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
    setPageContext,
    loadSessions,
    loadSessionMessages,
    selectSession,
    newSession,
    sendMessage,
    closeConnection,
    stopGeneration,
    deleteMessage: deleteMessageAction,
    deleteMessages: deleteMessagesAction,
  }
})
