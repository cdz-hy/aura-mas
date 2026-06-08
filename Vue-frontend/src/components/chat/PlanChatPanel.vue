<template>
  <div class="flex-1 flex-shrink-0 flex flex-col card overflow-hidden animate-fade-in-up min-w-[260px] md:min-w-[300px]" style="animation-delay: 0.1s">
    <!-- Header with mode toggle -->
    <div class="px-4 py-3 border-b border-navy-100/50">
      <div class="flex items-center justify-between gap-3">
        <!-- Mode Toggler (Merged Sliding Button) -->
        <button
          class="relative px-3.5 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-all duration-300 border shadow-sm select-none group flex-shrink-0"
          :class="mode === 'assistant' 
            ? 'bg-navy-50 hover:bg-navy-100 border-navy-200/80 text-navy-700' 
            : 'bg-purple-50 hover:bg-purple-100 border-purple-200/80 text-purple-700'"
          @click="switchMode(mode === 'assistant' ? 'tutor' : 'assistant')"
          title="切换工作模式"
        >
          <!-- Dynamic transition inside the button -->
          <transition name="mode-icon-fade" mode="out-in">
            <span :key="mode" class="flex items-center gap-1.5">
              <template v-if="mode === 'assistant'">
                <svg class="w-3.5 h-3.5 text-navy-600 animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
                </svg>
                <span>AI 学习助手</span>
              </template>
              <template v-else>
                <img :src="tutorGif" alt="" class="w-3.5 h-3.5 rounded flex-shrink-0" />
                <span>智能辅导</span>
              </template>
            </span>
          </transition>
          
          <!-- Swap arrows with hover rotation -->
          <svg class="w-3.5 h-3.5 opacity-40 group-hover:opacity-80 transition-all duration-500 transform group-hover:rotate-180 ml-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 17H4M4 17l4 4M4 17l4-4M4 7h16m0 0l-4-4m4 4l-4 4" />
          </svg>
        </button>

        <!-- Actions -->
        <div class="flex items-center gap-1.5 flex-shrink-0">
          <button
            class="p-2 rounded-lg transition-colors relative"
            :class="showSessionList ? 'bg-navy-100 text-navy-700' : 'bg-navy-50 text-navy-500 hover:bg-navy-100'"
            @click="showSessionList = !showSessionList"
            title="会话历史"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
            </svg>
            <span v-if="currentSessions.length" class="absolute -top-1 -right-1 bg-navy-600 text-white text-[9px] font-bold rounded-full w-4 h-4 flex items-center justify-center border border-white">
              {{ currentSessions.length }}
            </span>
          </button>
          <button
            class="p-2 rounded-lg bg-navy-50 text-navy-500 hover:bg-navy-100 transition-colors"
            @click="handleNewSession()"
            title="新建会话"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
          <button
            v-if="isStreaming"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
            @click="handleStop()"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            停止
          </button>
        </div>
      </div>

      <!-- Subtitle for tutor mode -->
      <div v-if="mode === 'tutor' && resourceTitle" class="mt-1.5 text-xs text-purple-500 truncate">
        当前模块: {{ resourceTitle }}
      </div>
    </div>

    <!-- Session list panel -->
    <transition name="slide-down">
      <div v-if="showSessionList" class="border-b border-navy-100/50 bg-navy-50/30 max-h-[240px] overflow-y-auto">
        <div v-if="currentSessionsLoading" class="p-4 text-center text-navy-400 text-sm">加载中...</div>
        <div v-else-if="currentSessions.length === 0" class="p-4 text-center text-navy-300 text-sm">暂无历史会话</div>
        <div v-else class="py-1">
          <div
            v-for="session in currentSessions"
            :key="session.sessionId"
            class="flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors group"
            :class="currentActiveSessionId === session.sessionId ? 'bg-navy-100/60' : 'hover:bg-white'"
            @click="handleSelectSession(session.sessionId)"
          >
            <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
              :class="currentActiveSessionId === session.sessionId ? (mode === 'tutor' ? 'bg-purple-600 text-white' : 'bg-navy-600 text-white') : 'bg-navy-100 text-navy-400'">
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm text-navy-700 truncate flex items-center gap-1.5">
                {{ session.title }}
              </p>
              <p class="text-[11px] text-navy-400 mt-0.5">{{ session.messageCount }} 条消息 · {{ formatTime(session.lastMessageAt) }}</p>
            </div>
            <button
              v-if="mode === 'assistant'"
              class="p-1.5 rounded-md text-navy-300 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 transition-all"
              @click.stop="handleDeleteSession(session.sessionId)"
              title="删除会话"
            >
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Messages area -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto px-6 py-4"
      @click="handleCitationClick"
      @mouseover="handleCitationMouseOver"
      @mouseout="handleCitationMouseOut"
    >
      <transition name="chat-fade" mode="out-in">
        <div :key="mode" class="space-y-4">
          <!-- ═══ Assistant mode messages ═══ -->
      <template v-if="mode === 'assistant'">
        <!-- Welcome -->
        <div v-if="chatStore.messages.length === 0" class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3 max-w-[80%]">
            <p class="text-navy-700">你好！请告诉我你想学习什么，我会为你规划学习路径并生成个性化资源。</p>
            <div class="mt-3 flex flex-wrap gap-2">
              <button v-for="q in quickQuestions" :key="q"
                class="text-xs px-3 py-1.5 rounded-full bg-white text-navy-600 border border-navy-200 hover:bg-navy-50 transition-colors"
                @click="handleSendAssistant(q)">
                {{ q }}
              </button>
            </div>
          </div>
        </div>

        <!-- Message list -->
        <div v-for="(msg, i) in chatStore.messages" :key="i" class="flex gap-3" :class="msg.role === 'user' ? 'justify-end' : ''">
          <template v-if="msg.role === 'assistant'">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
              <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
              </svg>
            </div>

            <!-- Task breakdown confirmation card -->
            <div v-if="msg.type === 'confirm' && msg.breakdown" class="max-w-[85%] space-y-3">
              <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3">
                <p class="text-navy-700 mb-3">{{ msg.content }}</p>
                <div v-if="msg.breakdown.modules" class="space-y-2">
                  <div v-for="(mod, j) in msg.breakdown.modules" :key="j" class="bg-white rounded-lg p-3 border border-navy-100">
                    <div class="flex items-center gap-2 mb-1">
                      <span class="w-6 h-6 rounded-full bg-navy-600 text-white text-xs flex items-center justify-center">{{ mod.module_id || j + 1 }}</span>
                      <span class="font-medium text-navy-800 text-sm">{{ mod.title }}</span>
                      <span v-if="mod.estimated_hours" class="text-xs text-navy-400 ml-auto">{{ mod.estimated_hours }}h</span>
                    </div>
                    <p v-if="mod.description" class="text-xs text-navy-500 ml-8">{{ mod.description }}</p>
                    <div v-if="mod.resources && mod.resources.length" class="flex flex-wrap gap-1 mt-1.5 ml-8">
                      <span v-for="r in mod.resources" :key="r.resource_type"
                        class="text-[10px] px-1.5 py-0.5 rounded-full"
                        :class="badgeClass(r.resource_type)">
                        {{ typeLabels[r.resource_type] || r.resource_type }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="chatStore.awaitingConfirmation && i === chatStore.messages.length - 1" class="flex gap-2 ml-2">
                <button class="px-4 py-2 rounded-lg bg-navy-600 text-white text-sm font-medium hover:bg-navy-700 transition-colors"
                  @click="$emit('confirmBreakdown')">
                  确认，开始生成
                </button>
                <button class="px-4 py-2 rounded-lg bg-white text-navy-600 text-sm font-medium border border-navy-200 hover:bg-navy-50 transition-colors"
                  @click="showModifyInput = true">
                  补充说明
                </button>
              </div>
              <div v-if="showModifyInput && chatStore.awaitingConfirmation && i === chatStore.messages.length - 1" class="ml-2">
                <form @submit.prevent="$emit('submitModification', modifyText); modifyText = ''; showModifyInput = false" class="flex gap-2">
                  <input v-model="modifyText" type="text" class="input-field flex-1 text-sm" placeholder="输入补充说明..." autofocus />
                  <button type="submit" class="btn-primary px-4 text-sm" :disabled="!modifyText.trim()">发送</button>
                </form>
              </div>
            </div>

            <!-- Resource generated card -->
            <div v-else-if="msg.type === 'resource_generated' && msg.resources?.length" class="max-w-[85%]">
              <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3">
                <p class="text-navy-700 mb-3">{{ msg.content }}</p>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="r in msg.resources" :key="r.id"
                    class="flex items-center gap-2 bg-white rounded-lg px-3 py-2 border border-navy-100 hover:border-navy-300 hover:shadow-sm transition-all cursor-pointer"
                    @click="$emit('openResource', r.id, r.type)"
                  >
                    <span class="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs"
                      :class="badgeClass(r.type)">
                      {{ typeLabels[r.type]?.[0] || r.type[0]?.toUpperCase() || 'R' }}
                    </span>
                    <span class="text-sm text-navy-700 font-medium">{{ r.title }}</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded-full" :class="badgeClass(r.type)">
                      {{ typeLabels[r.type] || r.type }}
                    </span>
                  </button>
                </div>
              </div>
            </div>

            <!-- Normal assistant message -->
            <div v-else class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3 max-w-[80%]">
              <div class="text-navy-700 leading-relaxed markdown-body" v-html="renderMd(msg.content)"></div>
            </div>
          </template>

          <template v-else>
            <div class="bg-navy-600 text-white rounded-2xl rounded-tr-sm px-5 py-3 max-w-[80%]">
              <p class="leading-relaxed">{{ msg.content }}</p>
            </div>
          </template>
        </div>

        <!-- Streaming indicator (assistant) -->
        <div v-if="chatStore.streaming" class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-white animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
            </svg>
          </div>
          <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3 max-w-[80%]">
            <div v-if="chatStore.streamBuffer" class="text-navy-700 leading-relaxed markdown-body" v-html="renderMd(chatStore.streamBuffer)"></div>
            <div v-else class="flex gap-1.5 py-1">
              <span class="w-2 h-2 rounded-full bg-navy-300 animate-bounce" style="animation-delay: 0s"></span>
              <span class="w-2 h-2 rounded-full bg-navy-300 animate-bounce" style="animation-delay: 0.15s"></span>
              <span class="w-2 h-2 rounded-full bg-navy-300 animate-bounce" style="animation-delay: 0.3s"></span>
            </div>
          </div>
        </div>

        <!-- Module context prompt -->
        <div v-if="moduleContextMessage && !chatStore.streaming" class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3 max-w-[80%]">
            <p class="text-navy-700">你正在查看「<span class="font-medium">{{ moduleContextMessage.title }}</span>」，如需为该模块生成补充资源，请点击：</p>
            <div class="mt-3 flex flex-wrap gap-2">
              <button
                v-for="opt in resourceOptions" :key="opt.type"
                class="text-xs px-3 py-1.5 rounded-full border transition-colors"
                :class="generatingType === opt.type ? 'bg-navy-600 text-white border-navy-600' : 'bg-white text-navy-600 border-navy-200 hover:bg-navy-50'"
                :disabled="!!generatingType"
                @click="$emit('generateResource', opt.type)">
                {{ opt.label }}
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- ═══ Tutor mode messages ═══ -->
      <template v-if="mode === 'tutor'">
        <!-- Empty state with follow-up -->
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

        <!-- Follow-up hint (after messages, separate from conversation) -->
        <div v-if="tutor.messages.value.length > 0 && !tutor.loading.value" class="tutor-followup-hint">
          <img :src="tutorGif" alt="" class="tutor-followup-avatar" />
          <div class="tutor-followup-bubble">{{ currentFollowUp }}</div>
        </div>
      </template>
        </div>
      </transition>
    </div>

    <!-- Input bar -->
    <div class="px-6 py-3 border-t border-navy-100/50 bg-white">
      <!-- Assistant input -->
      <form v-if="mode === 'assistant'" @submit.prevent="handleSendAssistant()" class="flex gap-3">
        <input
          v-model="assistantInput"
          type="text"
          class="input-field flex-1"
          :placeholder="chatStore.streaming ? 'AI回复中...' : chatStore.awaitingConfirmation ? '输入补充说明...' : '描述你想学习的内容...'"
          :disabled="chatStore.streaming"
        />
        <button type="submit" class="btn-primary px-5" :disabled="!assistantInput.trim() || chatStore.streaming">
          发送
        </button>
      </form>
      <!-- Tutor input -->
      <form v-else @submit.prevent="handleSendTutor()" class="flex gap-3">
        <input
          v-model="tutorInput"
          type="text"
          class="input-field flex-1"
          placeholder="输入你的问题..."
          :disabled="tutor.loading.value"
        />
        <button type="submit" class="btn-primary px-5" :disabled="!tutorInput.trim() || tutor.loading.value">
          发送
        </button>
      </form>
    </div>

    <!-- 引用悬浮预览卡片 -->
    <Teleport to="body">
      <transition name="fade">
        <div
          v-if="hoveredCitation"
          class="fixed z-50 p-3.5 rounded-xl border border-navy-100/50 bg-white/80 backdrop-blur-md shadow-[0_8px_30px_rgb(0,0,0,0.04)] max-w-xs text-left pointer-events-auto transition-all duration-150"
          :style="popoverStyle"
          @mouseenter="clearPopoverTimeout"
          @mouseleave="handleCitationMouseOut"
        >
          <div class="flex items-start gap-2.5">
            <div class="w-7 h-7 rounded-lg bg-navy-50 flex items-center justify-center flex-shrink-0 mt-0.5 text-navy-400">
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-xs font-semibold text-navy-800 line-clamp-2 leading-snug">
                {{ hoveredCitation.title }}
              </p>
              <p class="text-[10px] text-navy-400 font-mono tracking-tight mt-1.5 flex items-center gap-1">
                <svg class="w-3 h-3 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="2" y1="12" x2="22" y2="12" />
                  <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
                </svg>
                {{ hoveredCitation.domain }}
              </p>
              <div class="flex items-center justify-between mt-3 pt-2 border-t border-navy-100/30">
                <span class="text-[9px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-500 font-medium font-sans">
                  来源 [{{ hoveredCitation.id }}]
                </span>
                <a
                  :href="hoveredCitation.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-[10px] text-navy-500 hover:text-purple-600 flex items-center gap-1 font-medium transition-colors"
                >
                  查看原文
                  <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
                    <polyline points="15 3 21 3 21 9" />
                    <line x1="10" y1="14" x2="21" y2="3" />
                  </svg>
                </a>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import { parseMarkdown } from '@/utils/markdown'
import { useTutor, pickFollowUp } from '@/composables/useTutor'
import type { TutorContext } from '@/composables/useTutor'
import tutorGif from '@/image/智能辅导.gif'

const props = defineProps<{
  planId: string
  resourceId: number | null
  mode: 'assistant' | 'tutor'
}>()

const emit = defineEmits<{
  'update:mode': [mode: 'assistant' | 'tutor']
  confirmBreakdown: []
  submitModification: [text: string]
  generateResource: [type: string]
  openResource: [id: number, type: string]
  setModuleContext: [ctx: { title: string; description: string; moduleId: number; planId: number } | null]
}>()

const chatStore = useChatStore()
const authStore = useAuthStore()

// ─── Mode switching ───
function switchMode(newMode: 'assistant' | 'tutor') {
  emit('update:mode', newMode)
  showSessionList.value = false
}

// ─── Tutor context ───
const tutorContext = computed<TutorContext>(() => ({
  planId: Number(props.planId),
  resourceId: props.resourceId || 0,
}))

const tutor = useTutor(tutorContext)

// Track resource changes for follow-up updates
const currentFollowUp = ref('有什么不懂的地方吗，我可以帮你哦')

// Resource title for tutor subtitle
const resourceTitle = ref('')

function updateResourceTitle(title: string) {
  resourceTitle.value = title
}

// Detect resource type from resource ID for follow-up template selection
const currentResourceType = ref('')

function updateResourceType(type: string) {
  currentResourceType.value = type
}

// Update follow-up when entering tutor mode or changing resource
watch([() => props.mode, () => props.resourceId], ([mode]) => {
  if (mode !== 'tutor') return
  currentFollowUp.value = pickFollowUp(currentResourceType.value || undefined)
  nextTick(() => scrollBottom())
})

// ─── Shared state ───
const messagesContainer = ref<HTMLElement>()
const showSessionList = ref(false)
const assistantInput = ref('')
const tutorInput = ref('')
const showModifyInput = ref(false)
const modifyText = ref('')

const quickQuestions = [
  '我想学习 Python 基础',
  '帮我生成一些练习题',
  '这个知识点不太理解',
]

const resourceOptions = [
  { type: 'quiz', label: '测验' },
  { type: 'mindmap', label: '思维导图' },
  { type: 'code', label: '代码示例' },
  { type: 'summary', label: '总结' },
  { type: 'video', label: '教学视频' },
  { type: 'animation', label: '动画' },
  { type: 'podcast', label: '播客' },
]

const typeLabels: Record<string, string> = {
  document: '文档', text: '图文', mindmap: '导图', quiz: '题目', code: '代码', reading: '阅读', summary: '总结', video: '视频', image: '图片', diagram: '图表', animation: '动画', podcast: '播客',
}

const moduleContextMessage = computed(() => chatStore.selectedModuleContext ? { title: chatStore.selectedModuleContext.title } : null)
const generatingType = ref<string | null>(null)

// ─── Computed for current mode's sessions ───
const currentSessions = computed(() => {
  return props.mode === 'tutor' ? tutor.sessions.value : chatStore.sessions
})
const currentSessionsLoading = computed(() => {
  return props.mode === 'tutor' ? tutor.sessionsLoading.value : chatStore.sessionsLoading
})
const currentActiveSessionId = computed(() => {
  return props.mode === 'tutor' ? tutor.activeSessionId.value : chatStore.activeSessionId
})
const isStreaming = computed(() => {
  return props.mode === 'tutor' ? tutor.loading.value : chatStore.streaming
})

// ─── Actions ───
function handleSendAssistant(text?: string) {
  const msg = text || assistantInput.value.trim()
  if (!msg) return
  assistantInput.value = ''
  showModifyInput.value = false

  const ctx = chatStore.selectedModuleContext
  if (ctx) {
    const resourceType = detectResourceType(msg)
    if (resourceType) {
      chatStore.requestSupplementaryResource(props.planId, ctx, resourceType)
      return
    }
  }
  // 确认状态下，底部输入也走 confirmBreakdown 以携带 task_breakdown 上下文
  if (chatStore.awaitingConfirmation && chatStore.pendingTaskBreakdown) {
    chatStore.confirmBreakdown(props.planId, msg)
    return
  }
  chatStore.sendMessage(msg, props.planId)
}

function handleSendTutor() {
  const msg = tutorInput.value.trim()
  if (!msg) return
  tutorInput.value = ''
  tutor.send(msg)
  nextTick(() => scrollBottom())
}

function handleNewSession() {
  if (props.mode === 'tutor') {
    tutor.newSession()
    currentFollowUp.value = pickFollowUp()
  } else {
    chatStore.newSession()
    chatStore.loadSessions(props.planId)
  }
  showSessionList.value = false
}

async function handleSelectSession(sessionId: string) {
  if (props.mode === 'tutor') {
    await tutor.selectSession(sessionId)
  } else {
    await chatStore.selectSession(sessionId)
  }
  showSessionList.value = false
  nextTick(() => scrollBottom())
}

async function handleDeleteSession(sessionId: string) {
  await chatStore.deleteSession(sessionId)
}

function handleStop() {
  if (props.mode === 'tutor') {
    tutor.stopGeneration()
  } else {
    chatStore.stopGeneration(props.planId)
  }
}

// ─── Scroll ───
function scrollBottom() {
  if (messagesContainer.value) {
    const el = messagesContainer.value
    el.scrollTop = el.scrollHeight
    // Double-check after a short delay for images/transitions
    setTimeout(() => {
      if (el) el.scrollTop = el.scrollHeight
    }, 150)
    setTimeout(() => {
      if (el) el.scrollTop = el.scrollHeight
    }, 400)
  }
}

import { onMounted } from 'vue'

onMounted(() => {
  nextTick(() => scrollBottom())
})

// Auto-scroll on new messages
watch(() => {
  if (props.mode === 'tutor') return tutor.messages.value.length + (tutor.loading.value ? 1 : 0)
  return chatStore.messages.length + chatStore.streamBuffer.length
}, () => nextTick(() => scrollBottom()), { immediate: true })

// Load assistant sessions on mount and when planId changes
watch(() => props.planId, (planId) => {
  if (planId) {
    chatStore.resetForPlan(planId)
    chatStore.loadSessions(planId)
  }
}, { immediate: true })

// ─── Helpers ───
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

function badgeClass(type: string) {
  return { text: 'bg-blue-50 text-blue-500', document: 'bg-blue-50 text-blue-500', mindmap: 'bg-purple-50 text-purple-500', quiz: 'bg-amber-50 text-amber-500', code: 'bg-emerald-50 text-emerald-500', reading: 'bg-rose-50 text-rose-500', video: 'bg-red-50 text-red-500', summary: 'bg-sky-50 text-sky-500', image: 'bg-pink-50 text-pink-500', diagram: 'bg-indigo-50 text-indigo-500', animation: 'bg-orange-50 text-orange-500', podcast: 'bg-emerald-50 text-emerald-500' }[type] || 'bg-navy-50 text-navy-500'
}

function detectResourceType(msg: string): string | null {
  const lower = msg.toLowerCase()
  if (/测验|题目|练习|quiz|做题|出题/.test(lower)) return 'quiz'
  if (/思维导图|导图|mindmap|脑图/.test(lower)) return 'mindmap'
  if (/代码|code|示例代码|编程/.test(lower)) return 'code'
  if (/总结|摘要|summary|复习|要点/.test(lower)) return 'summary'
  if (/视频|video|教程|教学视频/.test(lower)) return 'video'
  if (/动画|animation|动效/.test(lower)) return 'animation'
  if (/播客|电台|podcast|博客|文章|blog|网页/.test(lower)) return 'podcast'
  return null
}

// Load tutor sessions when switching to tutor mode
watch(() => props.mode, (newMode) => {
  if (newMode === 'tutor') {
    tutor.loadSessions()
    nextTick(() => scrollBottom())
  }
})

// === 引用源（Citation）悬浮与点击交互 ===
const hoveredCitation = ref<{ id: string; title: string; url: string; domain: string } | null>(null)
const popoverX = ref(0)
const popoverY = ref(0)
const popoverPlacement = ref<'top' | 'bottom'>('top')
let popoverTimeout: ReturnType<typeof setTimeout> | null = null

const popoverStyle = computed(() => {
  return {
    left: `${popoverX.value}px`,
    top: `${popoverY.value}px`,
    transform: popoverPlacement.value === 'top' ? 'translate(-50%, -100%) translateY(-8px)' : 'translate(-50%, 8px)'
  }
})

function getDomainName(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

function handleCitationMouseOver(e: MouseEvent) {
  const target = (e.target as HTMLElement).closest('.citation-ref') as HTMLElement
  if (!target) return

  if (popoverTimeout) clearTimeout(popoverTimeout)

  const refId = target.getAttribute('data-ref') || ''
  const url = target.getAttribute('data-url') || ''
  const title = target.getAttribute('data-title') || `网页来源 [${refId}]`
  if (!url) return

  const rect = target.getBoundingClientRect()
  popoverX.value = rect.left + rect.width / 2
  
  if (rect.top < 150) {
    popoverPlacement.value = 'bottom'
    popoverY.value = rect.bottom
  } else {
    popoverPlacement.value = 'top'
    popoverY.value = rect.top
  }

  hoveredCitation.value = {
    id: refId,
    title,
    url,
    domain: getDomainName(url)
  }
}

function handleCitationMouseOut(e: MouseEvent) {
  if (popoverTimeout) clearTimeout(popoverTimeout)
  const target = (e.target as HTMLElement).closest('.citation-ref') as HTMLElement
  const related = e.relatedTarget as HTMLElement
  // 如果离开后进入的元素依然属于当前 citation-ref，则忽略，避免抖动
  if (target && related && target.contains(related)) {
    return
  }
  
  popoverTimeout = setTimeout(() => {
    hoveredCitation.value = null
  }, 250)
}

function clearPopoverTimeout() {
  if (popoverTimeout) clearTimeout(popoverTimeout)
}

function handleCitationClick(e: MouseEvent) {
  const target = (e.target as HTMLElement).closest('.citation-ref') as HTMLElement
  if (!target) return
  
  const url = target.getAttribute('data-url')
  if (url) {
    window.open(url, '_blank')
  }
}

// Expose for parent
defineExpose({ updateResourceTitle, updateResourceType, scrollBottom })
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

.chat-fade-enter-active,
.chat-fade-leave-active {
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.chat-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.chat-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Tutor message styles */
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
  cursor: pointer;
  transition: transform 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.tutor-md-content :deep(img:hover) {
  transform: scale(1.02);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease-out;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Mode Switcher Micro-animations */
.mode-icon-fade-enter-active,
.mode-icon-fade-leave-active {
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.mode-icon-fade-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.9);
}
.mode-icon-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.9);
}
</style>
