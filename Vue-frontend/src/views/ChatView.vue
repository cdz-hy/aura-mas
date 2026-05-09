<template>
  <div class="flex gap-0 h-[calc(100vh-12rem)]">
    <!-- Session sidebar -->
    <ChatSessionSidebar
      :sessions="store.sessions"
      :active-session-id="store.activeSessionId"
      :loading="store.sessionsLoading"
      @new-session="store.newSession()"
      @select="store.selectSession($event)"
      @delete="store.deleteSession($event)"
    />

    <!-- Chat panel -->
    <div class="flex-1 flex flex-col card overflow-hidden animate-fade-in-up ml-4">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-navy-100/50 flex items-center justify-between">
        <div>
          <h2 class="font-display text-lg font-semibold text-navy-800">AI 学习助手</h2>
          <p class="text-sm text-navy-400">围绕学习计划提问，获取个性化解答</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="store.streaming"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
            @click="store.stopGeneration()"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            停止生成
          </button>
          <router-link v-if="planId" :to="`/plan/${planId}`" class="btn-ghost text-sm">
            返回计划
          </router-link>
        </div>
      </div>

      <!-- Messages -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        <div v-for="(msg, i) in store.messages" :key="i" class="flex gap-3" :class="msg.role === 'user' ? 'justify-end' : ''">
          <!-- AI 消息 -->
          <template v-if="msg.role === 'assistant'">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
              <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
              </svg>
            </div>

            <!-- 任务分解确认卡片 -->
            <div v-if="msg.type === 'confirm' && msg.breakdown" class="max-w-[85%] space-y-3">
              <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3">
                <p class="text-navy-700 mb-3">{{ msg.content }}</p>
                <!-- 模块列表 -->
                <div v-if="msg.breakdown.modules" class="space-y-2">
                  <div
                    v-for="(mod, j) in msg.breakdown.modules"
                    :key="j"
                    class="bg-white rounded-lg p-3 border border-navy-100"
                  >
                    <div class="flex items-center gap-2 mb-1">
                      <span class="w-6 h-6 rounded-full bg-navy-600 text-white text-xs flex items-center justify-center">{{ mod.module_id || j + 1 }}</span>
                      <span class="font-medium text-navy-800">{{ mod.title }}</span>
                      <span v-if="mod.estimated_hours" class="text-xs text-navy-400 ml-auto">{{ mod.estimated_hours }}h</span>
                    </div>
                    <p v-if="mod.description" class="text-sm text-navy-500 ml-8">{{ mod.description }}</p>
                    <div v-if="mod.resources?.length" class="ml-8 mt-1 flex flex-wrap gap-1">
                      <span
                        v-for="r in mod.resources"
                        :key="r.resource_type"
                        class="text-xs px-2 py-0.5 rounded-full bg-navy-100 text-navy-600"
                      >
                        {{ resourceTypeLabel(r.resource_type) }}
                      </span>
                    </div>
                  </div>
                </div>
                <!-- 预估信息 -->
                <div v-if="msg.breakdown.total_estimated_hours" class="text-sm text-navy-500 mt-2">
                  预估总时长: {{ msg.breakdown.total_estimated_hours }} 小时
                </div>
              </div>
              <!-- 确认按钮 - 仅在等待确认时显示 -->
              <div v-if="store.awaitingConfirmation && i === store.messages.length - 1" class="flex gap-2 ml-2">
                <button
                  class="px-4 py-2 rounded-lg bg-navy-600 text-white text-sm font-medium hover:bg-navy-700 transition-colors"
                  @click="confirmBreakdown()"
                >
                  确认，开始生成
                </button>
                <button
                  class="px-4 py-2 rounded-lg bg-white text-navy-600 text-sm font-medium border border-navy-200 hover:bg-navy-50 transition-colors"
                  @click="showModifyInput = true"
                >
                  补充说明
                </button>
              </div>
              <!-- 补充说明输入框 -->
              <div v-if="showModifyInput && store.awaitingConfirmation && i === store.messages.length - 1" class="ml-2">
                <form @submit.prevent="submitModification" class="flex gap-2">
                  <input
                    v-model="modifyText"
                    type="text"
                    class="input-field flex-1 text-sm"
                    placeholder="输入补充说明或修改意见..."
                    autofocus
                  />
                  <button type="submit" class="btn-primary px-4 text-sm" :disabled="!modifyText.trim()">发送</button>
                </form>
              </div>
            </div>

            <!-- 普通消息 -->
            <div v-else class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3 max-w-[80%]">
              <div class="text-navy-700 leading-relaxed markdown-body" v-html="renderMd(msg.content)"></div>
            </div>
          </template>

          <!-- 用户消息 -->
          <template v-else>
            <div class="bg-navy-600 text-white rounded-2xl rounded-tr-sm px-5 py-3 max-w-[80%]">
              <p class="leading-relaxed">{{ msg.content }}</p>
            </div>
          </template>
        </div>

        <!-- Streaming -->
        <div v-if="store.streaming" class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-white animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
            </svg>
          </div>
          <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3 max-w-[80%]">
            <div v-if="store.streamBuffer" class="text-navy-700 leading-relaxed markdown-body" v-html="renderMd(store.streamBuffer)"></div>
            <div v-else class="flex gap-1.5 py-1">
              <span class="w-2 h-2 rounded-full bg-navy-300 animate-bounce" style="animation-delay: 0s"></span>
              <span class="w-2 h-2 rounded-full bg-navy-300 animate-bounce" style="animation-delay: 0.15s"></span>
              <span class="w-2 h-2 rounded-full bg-navy-300 animate-bounce" style="animation-delay: 0.3s"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="px-6 py-4 border-t border-navy-100/50 bg-white">
        <form @submit.prevent="sendMessage" class="flex gap-3">
          <input
            v-model="inputText"
            type="text"
            class="input-field flex-1"
            :placeholder="store.streaming ? 'AI回复中...' : store.awaitingConfirmation ? '输入补充说明或直接发送确认...' : '输入你的问题...'"
            :disabled="store.streaming"
          />
          <button type="submit" class="btn-primary px-6" :disabled="!inputText.trim() || store.streaming">
            发送
          </button>
        </form>
        <div class="mt-2 flex flex-wrap gap-2">
          <button
            v-for="q in quickQuestions"
            :key="q"
            class="text-xs px-3 py-1.5 rounded-full bg-navy-50 text-navy-500 hover:bg-navy-100 transition-colors"
            @click="sendMessageDirect(q)"
          >
            {{ q }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { parseMarkdown } from '@/utils/markdown'
import { useChatStore } from '@/stores/chat'
import ChatSessionSidebar from '@/components/chat/ChatSessionSidebar.vue'

const route = useRoute()
const planId = route.params.id as string
const store = useChatStore()

const messagesContainer = ref<HTMLElement>()
const inputText = ref('')
const showModifyInput = ref(false)
const modifyText = ref('')

const quickQuestions = [
  '这个知识点我不太理解，能详细解释一下吗？',
  '给我出几道练习题',
  '能给我一些代码示例吗？',
  '这个主题有什么拓展阅读推荐？',
]

const resourceTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    document: '文档', mindmap: '思维导图', quiz: '练习题',
    code: '代码', video: '视频', reading: '阅读',
  }
  return labels[type] || type
}

function renderMd(text: string) {
  return parseMarkdown(text)
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(() => store.messages.length + store.streamBuffer.length, scrollToBottom)

function sendMessage() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  showModifyInput.value = false
  store.sendMessage(text, planId)
}

function sendMessageDirect(text: string) {
  store.sendMessage(text, planId)
}

function confirmBreakdown() {
  showModifyInput.value = false
  store.confirmBreakdown(planId)
}

function submitModification() {
  const text = modifyText.value.trim()
  if (!text) return
  modifyText.value = ''
  showModifyInput.value = false
  store.confirmBreakdown(planId, text)
}

onMounted(() => {
  store.loadSessions(planId)
  if (!store.activeSessionId) {
    store.newSession()
  }
})
</script>
