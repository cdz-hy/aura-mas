<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="px-4 py-3 border-b border-purple-100/50 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <img :src="tutorGif" alt="" class="w-6 h-6 rounded-lg object-cover" />
        <span class="text-sm font-semibold text-purple-700">智能辅导</span>
      </div>
      <div class="flex items-center gap-1.5">
        <button
          class="p-2 rounded-lg transition-colors relative"
          :class="showSessionList ? 'bg-purple-100 text-purple-700' : 'bg-purple-50 text-purple-500 hover:bg-purple-100'"
          @click="showSessionList = !showSessionList"
          title="会话历史"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
          </svg>
          <span v-if="tutor.sessions.value.length" class="absolute -top-1 -right-1 bg-purple-600 text-white text-[9px] font-bold rounded-full w-4 h-4 flex items-center justify-center border border-white">
            {{ tutor.sessions.value.length }}
          </span>
        </button>
        <button
          class="p-2 rounded-lg bg-purple-50 text-purple-500 hover:bg-purple-100 transition-colors"
          @click="handleNewSession()"
          title="新建会话"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
        <button
          v-if="tutor.loading.value"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
          @click="tutor.stopGeneration()"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
          停止
        </button>
        <button
          class="p-2 rounded-lg bg-purple-50 text-purple-500 hover:bg-purple-100 transition-colors"
          @click="uiStore.toggleTutorPanel()"
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
      <div v-if="showSessionList" class="border-b border-purple-100/50 bg-purple-50/30 max-h-[240px] overflow-y-auto">
        <div v-if="tutor.sessionsLoading.value" class="p-4 text-center text-purple-400 text-sm">加载中...</div>
        <div v-else-if="tutor.sessions.value.length === 0" class="p-4 text-center text-purple-300 text-sm">暂无历史会话</div>
        <div v-else class="py-1">
          <div
            v-for="session in tutor.sessions.value"
            :key="session.sessionId"
            class="flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors"
            :class="tutor.activeSessionId.value === session.sessionId ? 'bg-purple-100/60' : 'hover:bg-white'"
            @click="handleSelectSession(session.sessionId)"
          >
            <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
              :class="tutor.activeSessionId.value === session.sessionId ? 'bg-purple-600 text-white' : 'bg-purple-100 text-purple-400'">
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm text-purple-700 truncate">{{ session.title }}</p>
              <p class="text-[11px] text-purple-400 mt-0.5">{{ session.messageCount }} 条消息 · {{ formatTime(session.lastMessageAt) }}</p>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- Messages area -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto px-4 py-4">
      <!-- Empty state -->
      <div v-if="tutor.messages.value.length === 0" class="tutor-empty">
        <img :src="tutorGif" alt="" class="tutor-empty-gif" />
        <div class="tutor-empty-bubble">{{ currentFollowUp }}</div>
      </div>

      <!-- Message list -->
      <div v-for="(msg, i) in tutor.messages.value" :key="i" class="tutor-msg-row" :class="msg.role">
        <div v-if="msg.role === 'assistant'" class="tutor-avatar">
          <img :src="tutorGif" alt="" />
        </div>
        <div class="tutor-bubble" :class="msg.role">
          <template v-if="msg.role === 'assistant'">
            <span v-if="!msg.content && tutor.loading.value && i === tutor.messages.value.length - 1" class="tutor-typing">
              <span></span><span></span><span></span>
            </span>
            <div v-else class="tutor-md-content" v-html="renderMd(msg.content)"></div>
          </template>
          <template v-else>{{ msg.content }}</template>
        </div>
      </div>

      <!-- Progress indicator -->
      <div v-if="tutor.loading.value && tutor.progress.value" class="tutor-progress-bar">
        <div class="tutor-progress-spinner"></div>
        <span>{{ tutor.progress.value }}</span>
      </div>

      <!-- Follow-up hint -->
      <div v-if="tutor.messages.value.length > 0 && !tutor.loading.value" class="tutor-followup-hint">
        <img :src="tutorGif" alt="" class="tutor-followup-avatar" />
        <div class="tutor-followup-bubble">{{ currentFollowUp }}</div>
      </div>
    </div>

    <!-- Input bar -->
    <div class="px-4 py-3 border-t border-purple-100/50 bg-white">
      <form @submit.prevent="handleSend()" class="flex gap-2">
        <input
          v-model="inputText"
          type="text"
          class="flex-1 px-4 py-2 text-sm border border-purple-200 rounded-xl outline-none focus:border-purple-400 transition-colors"
          placeholder="输入你的问题..."
          :disabled="tutor.loading.value"
        />
        <button
          type="submit"
          class="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-xl hover:bg-purple-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="!inputText.trim() || tutor.loading.value"
        >
          发送
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTutor, pickFollowUp } from '@/composables/useTutor'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { getCurrentProfile } from '@/api/user'
import { getDashboardStats } from '@/api/stats'
import { getKnowledgeMastery, getWeekComparison } from '@/api/analytics'
import { parseMarkdown } from '@/utils/markdown'
import { felderAxisLabel } from '@/types/profile'
import type { StudentProfile } from '@/types/profile'
import tutorGif from '@/image/智能辅导.gif'

const uiStore = useUiStore()
const route = useRoute()
const authStore = useAuthStore()

// Tutor context: general Q&A mode (no plan/resource binding)
const tutorContext = computed(() => ({ planId: 0, resourceId: 0 }))
const tutor = useTutor(tutorContext)

// ─── 上下文感知：根据路由收集页面数据 ───

// 缓存画像数据，避免重复请求
let cachedProfile: StudentProfile | null = null

async function fetchProfileContext(): Promise<{ type: string; data: Record<string, any> }> {
  try {
    if (!cachedProfile) {
      const res = await getCurrentProfile()
      cachedProfile = res.data
    }
    const p = cachedProfile
    // learningBehavior 可能是 JSON 字符串（Java 后端），需要先解析
    const rawB = p?.learningBehavior
    let b: Record<string, any> | null = null
    if (typeof rawB === 'string') {
      try { b = JSON.parse(rawB) } catch { b = null }
    } else if (rawB && typeof rawB === 'object') {
      b = rawB as Record<string, any>
    }
    const user = authStore.user

    const data: Record<string, any> = {
      页面: '我的画像（学习者画像）',
      用户昵称: user?.nickname || user?.loginName || '',
    }
    if (b) {
      data['视觉-言语维度'] = felderAxisLabel('visual_vs_verbal', b.visual_vs_verbal ?? 0) + ` (${(b.visual_vs_verbal ?? 0).toFixed(2)})`
      data['感知-直觉维度'] = felderAxisLabel('sensing_vs_intuitive', b.sensing_vs_intuitive ?? 0) + ` (${(b.sensing_vs_intuitive ?? 0).toFixed(2)})`
      data['活跃-沉思维度'] = felderAxisLabel('active_vs_reflective', b.active_vs_reflective ?? 0) + ` (${(b.active_vs_reflective ?? 0).toFixed(2)})`
      data['循序-全局维度'] = felderAxisLabel('sequential_vs_global', b.sequential_vs_global ?? 0) + ` (${(b.sequential_vs_global ?? 0).toFixed(2)})`
      if (b.knowledge_base?.length) data['已掌握知识'] = b.knowledge_base.join('、')
      if (b.weak_areas?.length) data['薄弱领域'] = b.weak_areas.join('、')
      if (b.interest_tags?.length) data['兴趣标签'] = b.interest_tags.join('、')
      if (b.preferred_resource_types?.length) data['偏好资源类型'] = b.preferred_resource_types.join('、')
      if (b.goal_orientation) data['目标导向'] = b.goal_orientation
    }
    return { type: 'profile', data }
  } catch {
    return { type: 'profile', data: { 页面: '我的画像', 备注: '画像数据加载失败' } }
  }
}

// 缓存 Dashboard 和 Analytics 数据
let cachedDashboard: any = null
let cachedAnalytics: any = null

async function fetchDashboardContext(): Promise<{ type: string; data: Record<string, any> }> {
  try {
    if (!cachedDashboard) {
      const res = await getDashboardStats()
      cachedDashboard = res.data
    }
    const d = cachedDashboard
    const data: Record<string, any> = {
      页面: '学习概览（仪表盘）',
      总计划数: d.totalPlans,
      进行中计划: d.activePlans,
      已完成计划: d.completedPlans,
      总学习时长: `${d.totalStudyHours}小时`,
      测验正确率: `${(d.quizAccuracy * 100).toFixed(1)}%`,
      总笔记数: d.totalNotes,
      总测验数: d.totalQuizzes,
    }
    return { type: 'dashboard', data }
  } catch {
    return { type: 'dashboard', data: { 页面: '学习概览（仪表盘）' } }
  }
}

async function fetchAnalyticsContext(): Promise<{ type: string; data: Record<string, any> }> {
  try {
    if (!cachedAnalytics) {
      const [masteryRes, weekRes] = await Promise.all([
        getKnowledgeMastery(),
        getWeekComparison(),
      ])
      cachedAnalytics = { mastery: masteryRes.data, week: weekRes.data }
    }
    const { mastery, week } = cachedAnalytics
    const data: Record<string, any> = { 页面: '学习分析' }
    if (mastery) {
      if (mastery.mastered?.length) data['已掌握知识'] = mastery.mastered.join('、')
      if (mastery.weakAreas?.length) data['薄弱知识点'] = mastery.weakAreas.join('、')
      if (mastery.interests?.length) data['兴趣方向'] = mastery.interests.join('、')
      if (mastery.performance) {
        data['学习速度'] = mastery.performance.learningSpeed
        data['参与度'] = mastery.performance.engagement
        data['测验正确率'] = `${(mastery.performance.quizAccuracy * 100).toFixed(1)}%`
      }
    }
    if (week) {
      data['本周学习时长'] = `${week.studyMinutes?.thisWeek || 0}分钟`
      data['周环比变化'] = `${week.studyMinutes?.change > 0 ? '+' : ''}${week.studyMinutes?.change || 0}%`
    }
    return { type: 'analytics', data }
  } catch {
    return { type: 'analytics', data: { 页面: '学习分析' } }
  }
}

async function gatherContext(): Promise<{ type: string; data: Record<string, any> }> {
  const path = route.path
  if (path === '/dashboard') return fetchDashboardContext()
  if (path === '/analytics') return fetchAnalyticsContext()
  if (path === '/notes' || path.startsWith('/notes/')) return { type: 'notes', data: { 页面: '我的笔记' } }
  if (path === '/settings') return { type: 'settings', data: { 页面: '个人设置' } }
  return { type: '', data: {} }
}

// 路由变化时更新上下文
watch(() => route.path, async (path) => {
  if (path === '/profile') {
    const ctx = await fetchProfileContext()
    tutor.setPageContext(ctx.type, ctx.data)
  } else {
    const ctx = await gatherContext()
    tutor.setPageContext(ctx.type, ctx.data)
  }
}, { immediate: true })

const messagesContainer = ref<HTMLElement>()
const inputText = ref('')
const showSessionList = ref(false)
const currentFollowUp = ref('有什么不懂的地方吗，我可以帮你哦')

// Update follow-up hints periodically
watch(() => tutor.messages.value.length, () => {
  if (tutor.messages.value.length > 0 && !tutor.loading.value) {
    currentFollowUp.value = pickFollowUp()
  }
})

function handleSend() {
  const msg = inputText.value.trim()
  if (!msg) return
  inputText.value = ''
  tutor.send(msg)
  nextTick(() => scrollBottom())
}

function handleNewSession() {
  tutor.newSession()
  currentFollowUp.value = pickFollowUp()
  showSessionList.value = false
}

async function handleSelectSession(sessionId: string) {
  await tutor.selectSession(sessionId)
  showSessionList.value = false
  nextTick(() => scrollBottom())
}

function scrollBottom() {
  if (messagesContainer.value) {
    const el = messagesContainer.value
    el.scrollTop = el.scrollHeight
    setTimeout(() => { if (el) el.scrollTop = el.scrollHeight }, 150)
    setTimeout(() => { if (el) el.scrollTop = el.scrollHeight }, 400)
  }
}

function renderMd(text: string) {
  return parseMarkdown(text || '')
}

function formatTime(time?: string) {
  if (!time) return ''
  const d = new Date(time)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 7) return `${diffDay}天前`
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// Auto-scroll on new messages
watch(() => tutor.messages.value.length + (tutor.loading.value ? 1 : 0), () => {
  nextTick(() => scrollBottom())
})
</script>

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  max-height: 0;
}
.slide-down-enter-to,
.slide-down-leave-from {
  max-height: 240px;
}

.tutor-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 24px 12px;
}
.tutor-empty-gif {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  object-fit: cover;
  box-shadow: 0 4px 16px rgba(139, 92, 246, 0.1);
}
.tutor-empty-bubble {
  background: rgba(245, 243, 255, 0.8);
  backdrop-filter: blur(8px);
  color: #5b21b6;
  padding: 12px 16px;
  border-radius: 14px 14px 14px 4px;
  font-size: 13.5px;
  line-height: 1.8;
  max-width: 88%;
  border: 1px solid rgba(139, 92, 246, 0.08);
}

.tutor-followup-hint {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding-top: 8px;
  opacity: 0.85;
}
.tutor-followup-avatar {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  object-fit: cover;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(139, 92, 246, 0.1);
}
.tutor-followup-bubble {
  background: rgba(245, 243, 255, 0.6);
  color: #7c3aed;
  padding: 8px 14px;
  border-radius: 4px 16px 16px 16px;
  font-size: 13px;
  line-height: 1.7;
  max-width: 82%;
  border: 1px dashed rgba(139, 92, 246, 0.15);
}

.tutor-msg-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  margin-bottom: 12px;
}
.tutor-msg-row.user { justify-content: flex-end; }

.tutor-avatar {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(139, 92, 246, 0.1);
}
.tutor-avatar img { width: 100%; height: 100%; object-fit: cover; }

.tutor-bubble {
  max-width: 82%;
  padding: 10px 14px;
  font-size: 13.5px;
  line-height: 1.8;
  word-break: break-word;
}
.tutor-bubble.assistant {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(6px);
  color: #334155;
  border-radius: 4px 16px 16px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(139, 92, 246, 0.06);
}
.tutor-bubble.user {
  background: linear-gradient(135deg, #a78bfa, #8b5cf6);
  color: white;
  border-radius: 16px 4px 16px 16px;
  box-shadow: 0 3px 12px rgba(139, 92, 246, 0.2);
}

.tutor-typing {
  display: inline-flex;
  gap: 6px;
  padding: 8px 0;
}
.tutor-typing span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: linear-gradient(135deg, #c4b5fd, #a78bfa);
  animation: tutor-bounce 1.4s infinite ease-in-out;
}
.tutor-typing span:nth-child(1) { animation-delay: -0.32s; }
.tutor-typing span:nth-child(2) { animation-delay: -0.16s; }
@keyframes tutor-bounce {
  0%, 80%, 100% { transform: scale(0); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

.tutor-progress-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  margin: 4px 0;
  background: linear-gradient(135deg, rgba(245, 243, 255, 0.9), rgba(237, 233, 254, 0.7));
  border-radius: 12px;
  font-size: 13px;
  color: #7c3aed;
  border: 1px solid rgba(139, 92, 246, 0.1);
  animation: progress-fade-in 0.3s ease;
}
@keyframes progress-fade-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.tutor-progress-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(139, 92, 246, 0.2);
  border-top-color: #8b5cf6;
  border-radius: 50%;
  animation: tutor-spin 0.8s linear infinite;
  flex-shrink: 0;
}
@keyframes tutor-spin {
  to { transform: rotate(360deg); }
}

/* Tutor markdown content */
.tutor-md-content :deep(p) { margin: 0 0 10px 0; }
.tutor-md-content :deep(p:last-child) { margin-bottom: 0; }
.tutor-md-content :deep(strong) { font-weight: 600; color: #1e293b; }
.tutor-md-content :deep(code) {
  background: linear-gradient(135deg, #f5f3ff, #ede9fe);
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 12px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: #7c3aed;
}
.tutor-md-content :deep(pre) {
  background: linear-gradient(135deg, #1e1b4b, #2e1065);
  color: #e0e7ff;
  padding: 14px;
  border-radius: 14px;
  overflow-x: auto;
  margin: 10px 0;
  font-size: 12px;
  line-height: 1.7;
}
.tutor-md-content :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
  font-size: inherit;
}
.tutor-md-content :deep(ul), .tutor-md-content :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}
.tutor-md-content :deep(li) { margin: 4px 0; line-height: 1.7; }
.tutor-md-content :deep(blockquote) {
  border-left: 3px solid #a78bfa;
  padding-left: 14px;
  margin: 10px 0;
  color: #64748b;
  font-style: italic;
}
.tutor-md-content :deep(img) {
  max-width: 100%;
  border-radius: 10px;
  margin: 10px 0;
}
</style>
