<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="px-4 py-3 border-b border-emerald-100/50 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <img src="/学习顾问.png" alt="" class="w-6 h-6 rounded-lg object-cover" />
        <span class="text-sm font-semibold text-emerald-700">AI 学习顾问</span>
      </div>
      <div class="flex items-center gap-1.5">
        <button
          class="p-2 rounded-lg transition-colors relative"
          :class="showSessionList ? 'bg-emerald-100 text-emerald-700' : 'bg-emerald-50 text-emerald-500 hover:bg-emerald-100'"
          @click="showSessionList = !showSessionList"
          title="会话历史"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
          </svg>
          <span v-if="sessions.length" class="absolute -top-1 -right-1 bg-emerald-600 text-white text-[9px] font-bold rounded-full w-4 h-4 flex items-center justify-center border border-white">
            {{ sessions.length }}
          </span>
        </button>
        <button
          class="p-2 rounded-lg bg-emerald-50 text-emerald-500 hover:bg-emerald-100 transition-colors"
          @click="handleNewSession()"
          title="新建会话"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
        <button
          v-if="loading"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
          @click="stopGeneration()"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
          停止
        </button>
        <button
          v-if="isSidebar"
          class="p-2 rounded-lg bg-emerald-50 text-emerald-500 hover:bg-emerald-100 transition-colors"
          @click="$emit('close')"
          title="关闭"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Session list panel -->
    <transition name="slide-down">
      <div v-if="showSessionList" class="border-b border-emerald-100/50 bg-emerald-50/30 max-h-[240px] overflow-y-auto">
        <div v-if="sessionsLoading" class="p-4 text-center text-emerald-400 text-sm">加载中...</div>
        <div v-else-if="sessions.length === 0" class="p-4 text-center text-emerald-300 text-sm">暂无历史会话</div>
        <div v-else class="py-1">
          <div
            v-for="session in sessions"
            :key="session.sessionId"
            class="flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors"
            :class="activeSessionId === session.sessionId ? 'bg-emerald-100/60' : 'hover:bg-white'"
            @click="handleSelectSession(session.sessionId)"
          >
            <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
              :class="activeSessionId === session.sessionId ? 'bg-emerald-600 text-white' : 'bg-emerald-100 text-emerald-400'">
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm text-emerald-700 truncate">{{ session.title }}</p>
              <p class="text-[11px] text-emerald-400 mt-0.5">{{ session.messageCount }} 条消息 · {{ formatTime(session.lastMessageAt) }}</p>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- Messages area -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto px-4 py-4">
      <!-- Empty state -->
      <div v-if="messages.length === 0" class="tutor-empty">
        <img src="/学习顾问.png" alt="" class="tutor-empty-gif" />
        <div class="tutor-empty-bubble">你好！我是你的 AI 学习顾问，有什么可以帮你的吗？</div>
      </div>

      <!-- Message list -->
      <div v-for="(msg, i) in messages" :key="i" class="tutor-msg-row group" :class="msg.role">
        <div v-if="msg.role === 'assistant'" class="tutor-avatar">
          <img src="/学习顾问.png" alt="" />
        </div>
        <div class="tutor-bubble" :class="msg.role">
          <template v-if="msg.role === 'assistant'">
            <!-- Thinking process -->
            <ThinkingProcess
              v-if="msg.thinkings && msg.thinkings.length > 0"
              :thinkings="msg.thinkings"
              :isStreaming="loading && i === messages.length - 1"
            />
            <!-- Plan suggestion card -->
            <div v-if="msg.type === 'plan_suggestion'" class="plan-suggestion-card">
              <div class="flex items-center gap-2 mb-2">
                <svg class="w-4 h-4 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
                </svg>
                <span class="text-sm font-medium text-emerald-700">为你推荐的学习计划</span>
              </div>
              <p class="text-sm text-navy-700 mb-3">{{ msg.suggestion?.title }}</p>
              <div class="space-y-1 mb-3">
                <div v-for="(mod, idx) in (msg.suggestion?.modules || []).slice(0, 3)" :key="idx" class="text-xs text-navy-500">
                  {{ idx + 1 }}. {{ mod.title }}
                </div>
                <p v-if="(msg.suggestion?.modules || []).length > 3" class="text-xs text-navy-400">
                  ...共 {{ msg.suggestion?.modules?.length }} 个模块
                </p>
              </div>
              <div class="flex gap-2">
                <button
                  class="flex-1 px-3 py-1.5 bg-emerald-600 text-white text-xs rounded-lg hover:bg-emerald-700 transition-colors"
                  @click="acceptPlanSuggestion(msg.suggestion)"
                >
                  接受建议
                </button>
                <button
                  class="flex-1 px-3 py-1.5 bg-navy-100 text-navy-600 text-xs rounded-lg hover:bg-navy-200 transition-colors"
                  @click="rejectPlanSuggestion(msg.id)"
                >
                  暂不需要
                </button>
              </div>
            </div>
            <!-- Normal message -->
            <div v-else class="tutor-md-content" v-html="renderMd(msg.content)"></div>
          </template>
          <template v-else>{{ msg.content }}</template>
        </div>
      </div>

      <!-- Loading indicator -->
      <div v-if="loading" class="tutor-msg-row assistant">
        <div class="tutor-avatar">
          <img src="/学习顾问.png" alt="" />
        </div>
        <div class="tutor-bubble assistant">
          <span class="tutor-typing">
            <span></span><span></span><span></span>
          </span>
        </div>
      </div>
    </div>

    <!-- Input bar -->
    <div class="px-4 py-3 border-t border-emerald-100/50 bg-white">
      <div class="flex gap-2 items-end">
        <textarea
          ref="inputRef"
          v-model="inputText"
          class="flex-1 resize-none rounded-xl border border-emerald-200 px-3 py-2 text-sm focus:outline-none focus:border-emerald-400 max-h-32"
          placeholder="输入你的问题..."
          rows="1"
          @input="autoResize"
          @keydown.enter.exact.prevent="sendMessage"
          :disabled="loading"
        />
        <button
          class="p-2 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 transition-colors disabled:opacity-50"
          @click="sendMessage"
          :disabled="!inputText.trim() || loading"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { parseMarkdown } from '@/utils/markdown'
import { getDashboardStats } from '@/api/stats'
import { getDueFlashcardCount } from '@/api/flashcard'
import { getPlans } from '@/api/plan'
import { getDialogueHistoryByIntent, getSessionMessages, getSessions } from '@/api/chat'
import { issueTicket } from '@/api/auth'
import { PYTHON_AI_BASE } from '@/api/request'
import ThinkingProcess from '@/components/chat/ThinkingProcess.vue'

// Props & Emits
const props = defineProps<{
  isSidebar?: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const router = useRouter()

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  type?: 'text' | 'plan_suggestion'
  suggestion?: any
  thinkings?: Array<{ agent: string; content: string }>
}

interface Session {
  sessionId: string
  title: string
  messageCount: number
  lastMessageAt: string
}

// State
const messages = ref<Message[]>([])
const inputText = ref('')
const loading = ref(false)
const showSessionList = ref(false)
const sessions = ref<Session[]>([])
const sessionsLoading = ref(false)
const activeSessionId = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)

// Markdown rendering
function renderMd(text: string) {
  return parseMarkdown(text)
}

// Auto resize textarea
function autoResize() {
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
    inputRef.value.style.height = Math.min(inputRef.value.scrollHeight, 128) + 'px'
  }
}

// Format time
function formatTime(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

// Scroll to bottom
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Add message
function addMessage(
  role: 'user' | 'assistant',
  content: string,
  type: string = 'text',
  suggestion?: any,
  thinkings?: Array<{ agent: string; content: string }>
) {
  messages.value.push({
    id: Date.now().toString(),
    role,
    content,
    type: type as any,
    suggestion,
    thinkings: thinkings || []
  })
  scrollToBottom()
}

// Send message
async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  addMessage('user', text)
  inputText.value = ''
  loading.value = true

  // Add empty assistant message for streaming
  const assistantMsgIndex = messages.value.length
  addMessage('assistant', '')

  try {
    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket

    // Get learning data context
    const [statsRes, plansRes, flashcardRes] = await Promise.all([
      getDashboardStats().catch(() => ({ data: null })),
      getPlans({ page: 1, size: 10 }).catch(() => ({ data: { records: [] } })),
      getDueFlashcardCount().catch(() => ({ data: 0 }))
    ])

    const rawStats = statsRes.data
    const dueCount = flashcardRes.data || 0
    const stats = rawStats ? {
      todayStudyMinutes: Math.floor((rawStats.todayDurationSeconds || 0) / 60),
      totalStudyMinutes: Math.floor((rawStats.totalDurationSeconds || 0) / 60),
      totalStudyHours: rawStats.totalStudyHours || 0,
      quizAccuracy: rawStats.quizAccuracy || 0,
      completedModules: rawStats.completedResources || 0,
      totalModules: rawStats.totalResources || 0,
      dueFlashcards: dueCount,
    } : null

    const plans = plansRes.data?.records || []

    // 确保有会话 ID
    if (!activeSessionId.value) {
      const userId = JSON.parse(atob(localStorage.getItem('token')?.split('.')[1] || '{}')).sub || 0
      activeSessionId.value = `advisor-${userId}-${Date.now()}`
    }

    // Build SSE URL
    const params = new URLSearchParams({
      ticket,
      user_message: text,
      session_id: activeSessionId.value,
      stats: JSON.stringify(stats || {}),
      plans: JSON.stringify(plans),
    })

    const url = `${PYTHON_AI_BASE}/api/ai/plan-advisor/chat?${params}`
    const source = new EventSource(url)

    // Track thinking steps
    const thinkings: Array<{ agent: string; content: string }> = []

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        switch (data.type) {
          case 'thinking_start':
            // Add new thinking step
            thinkings.push({ agent: data.agent || 'AI学习顾问', content: data.content || '' })
            if (messages.value[assistantMsgIndex]) {
              messages.value[assistantMsgIndex].thinkings = [...thinkings]
            }
            break

          case 'thinking_chunk':
            // Append to last thinking step
            if (thinkings.length > 0) {
              thinkings[thinkings.length - 1].content += data.content
              if (messages.value[assistantMsgIndex]) {
                messages.value[assistantMsgIndex].thinkings = [...thinkings]
              }
            }
            break

          case 'thinking':
            // Add thinking step (complete)
            thinkings.push({ agent: data.agent || 'AI学习顾问', content: data.content })
            if (messages.value[assistantMsgIndex]) {
              messages.value[assistantMsgIndex].thinkings = [...thinkings]
            }
            break

          case 'progress':
            // Update progress
            if (messages.value[assistantMsgIndex]) {
              messages.value[assistantMsgIndex].content += `\n\n[${data.content}]`
            }
            break

          case 'chunk':
            // Append streaming text
            if (messages.value[assistantMsgIndex]) {
              // Remove progress indicators and append content
              let content = messages.value[assistantMsgIndex].content
              content = content.replace(/\[.*?\]\s*$/g, '') // Remove progress markers
              messages.value[assistantMsgIndex].content = content + data.content
            }
            scrollToBottom()
            break

          case 'plan_suggestion':
            // Handle plan suggestion
            if (messages.value[assistantMsgIndex]) {
              messages.value[assistantMsgIndex].type = 'plan_suggestion'
              messages.value[assistantMsgIndex].suggestion = data.suggestion
            }
            break

          case 'done':
            // Stream complete
            source.close()
            loading.value = false
            // 刷新会话列表
            loadSessions()
            break

          case 'error':
            source.close()
            if (messages.value[assistantMsgIndex]) {
              messages.value[assistantMsgIndex].content = data.content || '抱歉，处理请求时出现了问题。'
            }
            loading.value = false
            break
        }
      } catch (e) {
        console.error('Parse SSE data failed:', e)
      }
    }

    source.onerror = () => {
      source.close()
      if (messages.value[assistantMsgIndex] && !messages.value[assistantMsgIndex].content) {
        messages.value[assistantMsgIndex].content = '抱歉，连接出现问题。请稍后再试。'
      }
      loading.value = false
    }
  } catch (e) {
    console.error('Send message failed:', e)
    if (messages.value[assistantMsgIndex]) {
      messages.value[assistantMsgIndex].content = '抱歉，处理你的请求时出现了问题。请稍后再试。'
    }
    loading.value = false
  }
}

// Stop generation
function stopGeneration() {
  loading.value = false
}

// Load history
async function loadHistory() {
  if (!activeSessionId.value) return

  try {
    const res = await getSessionMessages(activeSessionId.value, 50)
    const history = res.data || []

    if (history.length > 0) {
      // 数据库返回的是按 id 升序排列（最早的在前），直接使用即可
      for (const item of history) {
        const role = item.dialogueType === 'USER' ? 'user' : 'assistant'

        // 解析思考过程
        let thinkings: Array<{ agent: string; content: string }> = []
        if (item.conversationContext) {
          try {
            const ctx = JSON.parse(item.conversationContext)
            if (ctx.thinkings) {
              thinkings = ctx.thinkings
            }
          } catch (e) {
            // 解析失败，忽略
          }
        }

        messages.value.push({
          id: item.id?.toString() || Date.now().toString(),
          role: role as 'user' | 'assistant',
          content: item.conversationText || '',
          type: 'text',
          thinkings: thinkings
        })
      }
      scrollToBottom()
    }
  } catch (e) {
    console.error('Load history failed:', e)
  }
}

// New session
function handleNewSession() {
  messages.value = []
  activeSessionId.value = ''
  // 生成新的会话 ID
  const userId = JSON.parse(atob(localStorage.getItem('token')?.split('.')[1] || '{}')).sub || 0
  activeSessionId.value = `advisor-${userId}-${Date.now()}`
  loadSessions()
}

// Select session
async function handleSelectSession(sessionId: string) {
  activeSessionId.value = sessionId
  showSessionList.value = false
  // 加载会话消息
  messages.value = []
  await loadHistory()
}

// Load sessions
async function loadSessions() {
  sessionsLoading.value = true
  try {
    const res = await getSessions('plan_advisor')
    const sessionList = res.data || []

    // 过滤 plan_advisor 类型的会话
    sessions.value = sessionList
      .filter((s: any) => s.sessionId?.startsWith('advisor-'))
      .map((s: any) => ({
        sessionId: s.sessionId,
        title: s.title || '新对话',
        messageCount: s.messageCount || 0,
        lastMessageAt: s.lastMessageAt || ''
      }))
      .sort((a: any, b: any) => b.lastMessageAt.localeCompare(a.lastMessageAt))

  } catch (e) {
    console.error('Load sessions failed:', e)
  } finally {
    sessionsLoading.value = false
  }
}

// Accept plan suggestion
async function acceptPlanSuggestion(suggestion: any) {
  if (!suggestion) return

  try {
    loading.value = true
    addMessage('user', `接受建议：${suggestion.title}`)

    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket

    const response = await fetch(`${PYTHON_AI_BASE}/api/ai/plan-advisor/create-plan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ticket}`
      },
      body: JSON.stringify({
        title: suggestion.title,
        description: suggestion.description || '',
        modules: suggestion.modules || [],
        session_id: activeSessionId.value
      })
    })

    if (!response.ok) {
      throw new Error('创建计划失败')
    }

    const data = await response.json()

    if (data.success) {
      addMessage('assistant', `✅ ${data.message}`)

      // Trigger resource generation for each resource
      if (data.resourceIds && data.resourceIds.length > 0) {
        for (let i = 0; i < data.resourceIds.length; i++) {
          const resourceId = data.resourceIds[i]
          const module = (suggestion.modules || [])[i] || { title: suggestion.title, description: '' }

          try {
            const userMessage = `请为「${module.title}」生成学习资源。学习目标：${module.description || suggestion.title}`
            await fetch(`${PYTHON_AI_BASE}/api/ai/resource/generate?ticket=${ticket}&plan_id=${data.planId}&module_id=${resourceId}&type=text&title=${encodeURIComponent(module.title)}&description=${encodeURIComponent(module.description || '')}&user_message=${encodeURIComponent(userMessage)}`, {
              method: 'GET',
              headers: { 'Authorization': `Bearer ${ticket}` }
            })
          } catch (e) {
            console.error(`Generate resource ${resourceId} failed:`, e)
          }
        }
      }

      // Navigate to new plan
      setTimeout(() => {
        router.push(`/plan/${data.planId}`)
        if (props.isSidebar) {
          emit('close')
        }
      }, 1500)
    } else {
      addMessage('assistant', '抱歉，创建计划失败，请稍后再试。')
    }
  } catch (e) {
    console.error('Accept plan suggestion failed:', e)
    addMessage('assistant', '抱歉，创建计划时出现了问题。请稍后再试。')
  } finally {
    loading.value = false
  }
}

// Reject plan suggestion
function rejectPlanSuggestion(messageId: string) {
  const idx = messages.value.findIndex(m => m.id === messageId)
  if (idx !== -1) {
    messages.value[idx].content = '好的，暂时不需要新计划。如果你改变主意，随时告诉我！'
    messages.value[idx].type = 'text'
    messages.value[idx].suggestion = undefined
  }
}

// Lifecycle
onMounted(async () => {
  await loadSessions()
  await loadHistory()
})
</script>

<style scoped>
/* Tutor message styles */
.tutor-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  gap: 16px;
}

.tutor-empty-gif {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  object-fit: cover;
}

.tutor-empty-bubble {
  background: #f0fdf4;
  border-radius: 16px;
  border-top-left-radius: 4px;
  padding: 12px 16px;
  font-size: 14px;
  color: #374151;
  max-width: 240px;
  text-align: center;
}

.tutor-msg-row {
  display: flex;
  margin-bottom: 16px;
  align-items: flex-start;
}

.tutor-msg-row.user {
  flex-direction: row-reverse;
}

.tutor-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  margin-right: 8px;
}

.tutor-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.tutor-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
}

.tutor-bubble.user {
  background: #10b981;
  color: white;
  border-top-right-radius: 4px;
}

.tutor-bubble.assistant {
  background: #f9fafb;
  color: #374151;
  border-top-left-radius: 4px;
}

.tutor-typing {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.tutor-typing span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9ca3af;
  animation: typing 1.4s infinite;
}

.tutor-typing span:nth-child(2) {
  animation-delay: 0.2s;
}

.tutor-typing span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 100% {
    opacity: 0.4;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

.tutor-md-content {
  line-height: 1.6;
}

.tutor-md-content :deep(p) {
  margin-bottom: 0.5em;
}

.tutor-md-content :deep(p:last-child) {
  margin-bottom: 0;
}

.tutor-md-content :deep(strong) {
  font-weight: 600;
  color: #1f2937;
}

.tutor-md-content :deep(ul),
.tutor-md-content :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.tutor-md-content :deep(li) {
  margin-bottom: 0.25em;
}

.tutor-md-content :deep(code) {
  background: #f3f4f6;
  padding: 0.15em 0.4em;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: 'Fira Code', 'Consolas', monospace;
}

.tutor-md-content :deep(pre) {
  background: #f3f4f6;
  padding: 0.75em;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0.5em 0;
}

.tutor-md-content :deep(pre code) {
  background: none;
  padding: 0;
}

/* Plan suggestion card */
.plan-suggestion-card {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 12px;
  padding: 12px;
}

/* Slide down animation */
.slide-down-enter-active {
  transition: all 0.2s ease-out;
}

.slide-down-leave-active {
  transition: all 0.15s ease-in;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  max-height: 0;
}

/* Progress bar */
.tutor-progress-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  color: #6b7280;
  font-size: 12px;
}

.tutor-progress-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #e5e7eb;
  border-top-color: #10b981;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
