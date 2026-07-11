<template>
  <div class="plan-advisor-chat" :style="positionStyle">
    <!-- 触发按钮 -->
    <button
      v-if="!isOpen"
      class="advisor-trigger"
      @click="openChat"
      :class="{ 'has-notification': hasNotification }"
    >
      <img src="/学习顾问.png" alt="AI学习顾问" class="w-full h-full rounded-full object-cover" />
      <span v-if="hasNotification" class="notification-dot"></span>
    </button>

    <!-- 对话面板 -->
    <transition name="advisor-slide">
      <div v-if="isOpen" class="advisor-panel" :style="{ transform: `translate(${panelOffset.x}px, ${panelOffset.y}px)` }">
        <!-- 头部（可拖动） -->
        <div
          class="advisor-header cursor-move select-none"
          @mousedown="startDrag"
          @touchstart.prevent="startDragTouch"
        >
          <div class="flex items-center gap-2">
            <img src="/学习顾问.png" alt="AI学习顾问" class="w-8 h-8 rounded-full object-cover" />
            <div>
              <h3 class="font-semibold text-navy-800 text-sm">AI 学习顾问</h3>
              <p class="text-xs text-navy-400">{{ isListening ? '正在聆听...' : '随时为你服务' }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <!-- 关闭按钮 -->
            <button
              class="p-1.5 rounded-lg text-navy-400 hover:text-navy-600 hover:bg-navy-100 transition-colors"
              @click="closeChat"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 消息列表 -->
        <div ref="messagesContainer" class="advisor-messages">
          <!-- 欢迎消息 -->
          <div v-if="messages.length === 0" class="message assistant">
            <div class="message-content">
              <p class="text-sm text-navy-700 leading-relaxed">
                你好！我是你的 AI 学习顾问。我可以：
              </p>
              <ul class="mt-2 space-y-1 text-xs text-navy-600">
                <li>• 分析你的学习情况，提供个性化建议</li>
                <li>• 根据你的进度推荐合适的学习计划</li>
                <li>• 解答学习中的疑问</li>
              </ul>
              <p class="mt-3 text-xs text-navy-400">点击麦克风按钮或输入文字开始对话</p>
            </div>
          </div>

          <!-- 消息列表 -->
          <div
            v-for="(msg, i) in messages"
            :key="i"
            class="message"
            :class="msg.role"
          >
            <div class="message-content">
              <!-- 计划建议卡片 -->
              <div v-if="msg.type === 'plan_suggestion'" class="plan-suggestion">
                <div class="flex items-center gap-2 mb-2">
                  <svg class="w-4 h-4 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
                  </svg>
                  <span class="text-sm font-medium text-emerald-700">为你推荐的学习计划</span>
                </div>
                <p class="text-sm text-navy-700 mb-3">{{ msg.suggestion.title }}</p>
                <div class="space-y-1 mb-3">
                  <div v-for="(mod, idx) in msg.suggestion.modules.slice(0, 3)" :key="idx" class="text-xs text-navy-500">
                    {{ idx + 1 }}. {{ mod.title }}
                  </div>
                  <p v-if="msg.suggestion.modules.length > 3" class="text-xs text-navy-400">
                    ...共 {{ msg.suggestion.modules.length }} 个模块
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

              <!-- 消息内容 -->
              <div v-else>
                <div class="text-sm text-navy-700 leading-relaxed markdown-body" v-html="renderMd(msg.content)"></div>
              </div>
            </div>
          </div>

          <!-- 加载指示器 -->
          <div v-if="loading" class="message assistant">
            <div class="message-content">
              <div class="flex gap-1.5 py-1">
                <span class="w-2 h-2 rounded-full bg-emerald-300 animate-bounce" style="animation-delay: 0s"></span>
                <span class="w-2 h-2 rounded-full bg-emerald-300 animate-bounce" style="animation-delay: 0.15s"></span>
                <span class="w-2 h-2 rounded-full bg-emerald-300 animate-bounce" style="animation-delay: 0.3s"></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="advisor-input">
          <!-- 语音输入按钮 -->
          <button
            class="voice-btn"
            :class="{ 'is-listening': isListening }"
            @mousedown="startListening"
            @mouseup="stopListening"
            @touchstart.prevent="startListening"
            @touchend.prevent="stopListening"
            :disabled="loading"
          >
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          </button>

          <!-- 文字输入 -->
          <input
            v-model="inputText"
            class="text-input"
            placeholder="输入你的问题..."
            @keyup.enter="sendMessage"
            :disabled="loading"
          />

          <!-- 发送按钮 -->
          <button
            class="send-btn"
            @click="sendMessage"
            :disabled="!inputText.trim() || loading"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { parseMarkdown } from '@/utils/markdown'
import { getDashboardStats, getStudyHeatmap } from '@/api/stats'
import { getDueFlashcardCount } from '@/api/flashcard'
import { getPlans } from '@/api/plan'
import { getDialogueHistoryByIntent } from '@/api/chat'
import { PYTHON_AI_BASE } from '@/api/request'
import { issueTicket } from '@/api/auth'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  type?: 'text' | 'plan_suggestion'
  suggestion?: any
}

const router = useRouter()

// Markdown 渲染
function renderMd(text: string) {
  return parseMarkdown(text)
}

// 状态
const isOpen = ref(false)
const messages = ref<Message[]>([])
const inputText = ref('')
const loading = ref(false)
const hasNotification = ref(false)

// 语音状态
const isListening = ref(false)
const mediaRecorder = ref<MediaRecorder | null>(null)
const audioChunks = ref<Blob[]>([])

// 拖动状态
const position = ref({ x: 24, y: 24 })
const panelOffset = ref({ x: 0, y: 0 })
const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })

// 计算位置样式
const positionStyle = computed(() => ({
  right: position.value.x + 'px',
  top: position.value.y + 'px'
}))

// 引用
const messagesContainer = ref<HTMLElement | null>(null)

// 打开对话
async function openChat() {
  isOpen.value = true
  hasNotification.value = false

  // 检查是否有检测到的变化
  const changeReason = localStorage.getItem('advisor_change_reason')

  if (messages.value.length === 0) {
    // 没有历史对话，加载历史或主动问候
    await loadHistory()
  } else if (changeReason) {
    // 有历史对话且检测到新变化，主动发起分析
    await proactiveGreeting()
  }
}

// 加载历史对话
async function loadHistory() {
  try {
    const res = await getDialogueHistoryByIntent('plan_advisor', 20)
    const history = res.data || []
    if (history.length > 0) {
      // 反转顺序，让最新的消息在最下面
      const reversedHistory = [...history].reverse()
      for (const item of reversedHistory) {
        const role = item.dialogueType === 'USER' ? 'user' : 'assistant'
        messages.value.push({
          id: item.id?.toString() || Date.now().toString(),
          role: role as 'user' | 'assistant',
          content: item.conversationText || '',
          type: 'text'
        })
      }
      scrollToBottom()
    } else {
      // 没有历史对话，主动问候
      await proactiveGreeting()
    }
  } catch (e) {
    console.error('Load history failed:', e)
    // 加载失败，主动问候
    await proactiveGreeting()
  }
}

// 关闭对话
function closeChat() {
  isOpen.value = false
}

// 拖动功能
function startDrag(e: MouseEvent) {
  isDragging.value = true
  dragStart.value = { x: e.clientX - panelOffset.value.x, y: e.clientY - panelOffset.value.y }
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

function startDragTouch(e: TouchEvent) {
  isDragging.value = true
  const touch = e.touches[0]
  dragStart.value = { x: touch.clientX - panelOffset.value.x, y: touch.clientY - panelOffset.value.y }
  document.addEventListener('touchmove', onDragTouch)
  document.addEventListener('touchend', stopDrag)
}

function onDrag(e: MouseEvent) {
  if (!isDragging.value) return
  panelOffset.value = {
    x: e.clientX - dragStart.value.x,
    y: e.clientY - dragStart.value.y
  }
}

function onDragTouch(e: TouchEvent) {
  if (!isDragging.value) return
  const touch = e.touches[0]
  panelOffset.value = {
    x: touch.clientX - dragStart.value.x,
    y: touch.clientY - dragStart.value.y
  }
}

function stopDrag() {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDragTouch)
  document.removeEventListener('touchend', stopDrag)
}

// 检测学习变化并主动提示
async function checkLearningChanges() {
  try {
    // 使用独立 key，避免与 AdvisorSuggestionCloud 竞态
    const lastCheckKey = 'advisor_chat_last_check'
    const lastCheckStr = localStorage.getItem(lastCheckKey)
    const lastCheck = lastCheckStr ? JSON.parse(lastCheckStr) : null

    // 获取当前学习数据
    const [statsRes, plansRes, heatmapRes] = await Promise.all([
      getDashboardStats().catch(() => ({ data: null })),
      getPlans({ page: 1, size: 10 }).catch(() => ({ data: { records: [] } })),
      getStudyHeatmap(30).catch(() => ({ data: null }))
    ])

    const stats = statsRes.data
    const plans = plansRes.data?.records || []
    const streakDays = heatmapRes.data?.currentStreak || 0

    console.log('[AdvisorChat] checkLearningChanges', {
      lastCheck,
      currentPlanCount: plans.length,
      streakDays,
      quizAccuracy: stats?.quizAccuracy,
      completedResources: stats?.completedResources,
    })

    const changes: string[] = []

    if (lastCheck) {
      // 1. 学习时长变化（增加超过 30 分钟）
      const lastMinutes = Math.floor((lastCheck.todayDurationSeconds || 0) / 60)
      const currentMinutes = Math.floor((stats?.todayDurationSeconds || 0) / 60)
      if (currentMinutes - lastMinutes > 30) {
        changes.push(`今日学习时长增加了 ${currentMinutes - lastMinutes} 分钟`)
      }

      // 2. 计划数量变化
      const lastPlanCount = lastCheck.planCount || 0
      const currentPlanCount = plans.length
      if (currentPlanCount > lastPlanCount) {
        changes.push(`新增了 ${currentPlanCount - lastPlanCount} 个学习计划`)
      } else if (currentPlanCount < lastPlanCount) {
        changes.push(`学习计划减少了 ${lastPlanCount - currentPlanCount} 个`)
      }

      // 3. 答题正确率变化（波动超过 5%）
      const lastAccuracy = lastCheck.quizAccuracy || 0
      const currentAccuracy = stats?.quizAccuracy || 0
      if (lastAccuracy > 0 && Math.abs(currentAccuracy - lastAccuracy) > 5) {
        const direction = currentAccuracy > lastAccuracy ? '提升' : '下降'
        changes.push(`答题正确率${direction}了 ${Math.abs(currentAccuracy - lastAccuracy).toFixed(1)}%`)
      }

      // 4. 连续学习天数变化
      const lastStreak = lastCheck.streakDays || 0
      if (streakDays > lastStreak && streakDays >= 3) {
        changes.push(`连续学习天数达到 ${streakDays} 天`)
      } else if (lastStreak >= 3 && streakDays === 0) {
        changes.push('连续学习中断了')
      }

      // 5. 完成资源数变化
      const lastCompleted = lastCheck.completedResources || 0
      const currentCompleted = stats?.completedResources || 0
      if (currentCompleted > lastCompleted) {
        changes.push(`新完成了 ${currentCompleted - lastCompleted} 个学习资源`)
      }

      // 6. 总学习时长里程碑（每 10 小时一个节点）
      const lastHours = lastCheck.totalStudyHours || 0
      const currentHours = stats?.totalStudyHours || 0
      if (currentHours > lastHours && Math.floor(currentHours / 10) > Math.floor(lastHours / 10)) {
        changes.push(`累计学习时长突破 ${Math.floor(currentHours / 10) * 10} 小时`)
      }
    } else {
      // 首次检查
      if (plans.length > 0) {
        changes.push('首次分析学习情况')
      }
    }

    // 保存当前数据
    localStorage.setItem(lastCheckKey, JSON.stringify({
      todayDurationSeconds: stats?.todayDurationSeconds || 0,
      totalStudyHours: stats?.totalStudyHours || 0,
      quizAccuracy: stats?.quizAccuracy || 0,
      streakDays: streakDays,
      completedResources: stats?.completedResources || 0,
      planCount: plans.length,
      timestamp: Date.now()
    }))

    // 如果有变化，显示通知
    if (changes.length > 0) {
      hasNotification.value = true
      localStorage.setItem('advisor_change_reason', changes.join('；'))
    }

    return changes.length > 0
  } catch (e) {
    console.error('Check learning changes failed:', e)
    return false
  }
}

// 主动问候 - 根据学习情况主动提问和建议
async function proactiveGreeting() {
  try {
    // 获取学习数据
    const [statsRes, flashcardRes, plansRes] = await Promise.all([
      getDashboardStats().catch(() => ({ data: null })),
      getDueFlashcardCount().catch(() => ({ data: 0 })),
      getPlans({ page: 1, size: 10 }).catch(() => ({ data: { records: [] } }))
    ])

    const rawStats = statsRes.data
    const dueCount = flashcardRes.data || 0
    const plans = plansRes.data?.records || []

    // 转换字段名，与后端 _format_stats 对齐
    const stats = rawStats ? {
      todayStudyMinutes: Math.floor((rawStats.todayDurationSeconds || 0) / 60),
      totalStudyMinutes: Math.floor((rawStats.totalDurationSeconds || 0) / 60),
      totalStudyHours: rawStats.totalStudyHours || 0,
      streakDays: 0, // 由后端从 heatmap 获取
      quizAccuracy: rawStats.quizAccuracy || 0,
      completedModules: rawStats.completedResources || 0,
      totalModules: rawStats.totalResources || 0,
      dueFlashcards: dueCount,
    } : null

    // 获取变化原因
    const changeReason = localStorage.getItem('advisor_change_reason') || ''

    // 调用后端 AI 顾问 API 获取主动建议
    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket

    const userMessage = changeReason
      ? `[系统自动触发] 检测到学生学习情况变化：${changeReason}。请主动分析学生的学习情况，根据学习计划和资源内容，主动提出问题或建议。`
      : '[系统自动触发] 请主动分析学生的学习情况，根据学习计划和资源内容，主动提出问题或建议。'

    const response = await fetch(`${PYTHON_AI_BASE}/api/ai/plan-advisor/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ticket}`
      },
      body: JSON.stringify({
        stats: stats,
        plans: plans,
        userMessage: userMessage
      })
    })

    if (response.ok) {
      const data = await response.json()
      if (data.type === 'plan_suggestion' && data.suggestion) {
        addMessage('assistant', data.message, 'plan_suggestion', data.suggestion)
      } else {
        addMessage('assistant', data.message || '你好！有什么我可以帮你的吗？')
      }
    } else {
      addMessage('assistant', '你好！有什么我可以帮你的吗？')
    }

    // 清除变化原因
    localStorage.removeItem('advisor_change_reason')
  } catch (e) {
    console.error('Proactive greeting failed:', e)
    addMessage('assistant', '你好！有什么我可以帮你的吗？')
  }
}

// 添加消息
function addMessage(role: 'user' | 'assistant', content: string, type: string = 'text', suggestion?: any) {
  messages.value.push({
    id: Date.now().toString(),
    role,
    content,
    type: type as any,
    suggestion
  })
  scrollToBottom()
}

// 发送消息
async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  addMessage('user', text)
  inputText.value = ''
  loading.value = true

  try {
    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket

    // 获取学习数据上下文
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

    const context = {
      stats: stats,
      plans: plansRes.data?.records || [],
      userMessage: text
    }

    // 调用 AI 顾问 API
    const response = await fetch(`${PYTHON_AI_BASE}/api/ai/plan-advisor/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ticket}`
      },
      body: JSON.stringify(context)
    })

    if (!response.ok) {
      throw new Error('请求失败')
    }

    const data = await response.json()

    // 处理响应
    if (data.type === 'plan_suggestion') {
      addMessage('assistant', data.message, 'plan_suggestion', data.suggestion)
    } else {
      addMessage('assistant', data.message)
    }
  } catch (e) {
    console.error('Send message failed:', e)
    addMessage('assistant', '抱歉，处理你的请求时出现了问题。请稍后再试。')
  } finally {
    loading.value = false
  }
}

// 接受计划建议
async function acceptPlanSuggestion(suggestion: any) {
  try {
    loading.value = true
    addMessage('user', `接受建议：${suggestion.title}`)

    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket

    // 调用创建计划 API
    const response = await fetch(`${PYTHON_AI_BASE}/api/ai/plan-advisor/create-plan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ticket}`
      },
      body: JSON.stringify({
        title: suggestion.title,
        description: suggestion.description || '',
        modules: suggestion.modules || []
      })
    })

    if (!response.ok) {
      throw new Error('创建计划失败')
    }

    const data = await response.json()

    if (data.success) {
      addMessage('assistant', `✅ ${data.message}\n\n正在跳转到新计划...`)
      // 通知学习顾问
      localStorage.setItem('advisor_plan_created', `通过顾问建议创建了学习计划「${suggestion.title}」`)

      // 延迟后跳转到新计划
      setTimeout(() => {
        router.push(`/plan/${data.planId}`)
        closeChat()
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

// 拒绝计划建议
function rejectPlanSuggestion(messageId: string) {
  const idx = messages.value.findIndex(m => m.id === messageId)
  if (idx !== -1) {
    messages.value[idx].content = '好的，暂时不需要新计划。如果你改变主意，随时告诉我！'
    messages.value[idx].type = 'text'
    messages.value[idx].suggestion = undefined
  }
}

// 语音识别
function startListening() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert('你的浏览器不支持语音识别功能')
    return
  }

  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  const recognition = new SpeechRecognition()

  recognition.lang = 'zh-CN'
  recognition.interimResults = false
  recognition.maxAlternatives = 1

  recognition.onresult = (event: any) => {
    const transcript = event.results[0][0].transcript
    inputText.value = transcript
    isListening.value = false
    // 自动发送
    sendMessage()
  }

  recognition.onerror = (event: any) => {
    console.error('Speech recognition error:', event.error)
    isListening.value = false
  }

  recognition.onend = () => {
    isListening.value = false
  }

  isListening.value = true
  recognition.start()
}

function stopListening() {
  isListening.value = false
}

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 暴露方法给父组件
defineExpose({
  openChat
})

// 生命周期
onMounted(() => {
  // 检查是否有计划创建信号（由 PlanCreateView 写入）
  const planCreated = localStorage.getItem('advisor_plan_created')
  console.log('[AdvisorChat] onMounted 检查信号:', planCreated)
  if (planCreated) {
    hasNotification.value = true
    localStorage.setItem('advisor_change_reason', planCreated)
    console.log('[AdvisorChat] 检测到计划创建信号，已设通知')
  }

  // 页面加载后检测学习变化（延迟 4 秒，避免与 AdvisorSuggestionCloud 同时请求）
  setTimeout(() => {
    checkLearningChanges()
  }, 4000)
})
</script>

<style scoped>
.plan-advisor-chat {
  position: fixed;
  right: 24px;
  top: 24px;
  z-index: 100;
}

.advisor-trigger {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  position: relative;
  padding: 0;
  border: none;
  cursor: pointer;
}

.advisor-trigger:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 25px rgba(0, 0, 0, 0.2);
}

.advisor-trigger.has-notification {
  animation: pulse 2s infinite;
}

.notification-dot {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 12px;
  height: 12px;
  background: #ef4444;
  border-radius: 50%;
  border: 2px solid white;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3);
  }
  50% {
    box-shadow: 0 4px 30px rgba(16, 185, 129, 0.5);
  }
}

.advisor-panel {
  position: absolute;
  top: 70px;
  right: 0;
  width: 380px;
  max-height: 500px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.advisor-header {
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, #f0fdf4, #ecfdf5);
}

.advisor-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  max-height: 350px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  display: flex;
  flex-direction: column;
}

.message.user {
  align-items: flex-end;
}

.message.assistant {
  align-items: flex-start;
}

.message-content {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
}

.message.user .message-content {
  background: #f0fdf4;
  color: #166534;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  background: #f9fafb;
  color: #374151;
  border-bottom-left-radius: 4px;
}

.plan-suggestion {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 12px;
  padding: 12px;
}

.advisor-input {
  padding: 12px 16px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 8px;
  background: white;
}

.voice-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #f3f4f6;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.voice-btn:hover {
  background: #e5e7eb;
  color: #374151;
}

.voice-btn.is-listening {
  background: #fee2e2;
  color: #ef4444;
  animation: pulse-red 1s infinite;
}

@keyframes pulse-red {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(239, 68, 68, 0);
  }
}

.text-input {
  flex: 1;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.text-input:focus {
  border-color: #10b981;
}

.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #10b981;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: #059669;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 动画 */
.advisor-slide-enter-active {
  transition: all 0.3s ease-out;
}

.advisor-slide-leave-active {
  transition: all 0.2s ease-in;
}

.advisor-slide-enter-from,
.advisor-slide-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

/* Markdown 样式 */
.markdown-body :deep(p) {
  margin-bottom: 0.5em;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(strong) {
  font-weight: 600;
  color: #1f2937;
}

.markdown-body :deep(em) {
  font-style: italic;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.markdown-body :deep(li) {
  margin-bottom: 0.25em;
}

.markdown-body :deep(code) {
  background: #f3f4f6;
  padding: 0.15em 0.4em;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: 'Fira Code', 'Consolas', monospace;
}

.markdown-body :deep(pre) {
  background: #f3f4f6;
  padding: 0.75em;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0.5em 0;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid #10b981;
  padding-left: 0.75em;
  margin: 0.5em 0;
  color: #6b7280;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  font-weight: 600;
  margin: 0.75em 0 0.5em;
}

.markdown-body :deep(h1) {
  font-size: 1.25em;
}

.markdown-body :deep(h2) {
  font-size: 1.125em;
}

.markdown-body :deep(h3) {
  font-size: 1em;
}

.markdown-body :deep(a) {
  color: #10b981;
  text-decoration: underline;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 0.75em 0;
}
</style>
