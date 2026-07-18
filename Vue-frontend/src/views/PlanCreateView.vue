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

    <!-- Main content -->
    <div class="flex-1 flex gap-4 ml-4">
      <!-- Chat panel -->
      <div class="flex-1 flex flex-col card overflow-hidden animate-fade-in-up">
        <!-- Chat header -->
        <div class="px-6 py-4 border-b border-navy-100/50 flex items-center justify-between">
          <div>
            <h2 class="font-display text-lg font-semibold text-navy-800">创建学习计划</h2>
            <p class="text-sm text-navy-400 mt-0.5">告诉我你想学什么，我会为你量身定制</p>
          </div>
          <!-- Stop button -->
          <button
            v-if="store.streaming"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
            @click="store.stopGeneration()"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            停止生成
          </button>
        </div>

        <!-- Messages -->
        <div ref="messagesContainer" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          <!-- Welcome message -->
          <div v-if="store.messages.length === 0" class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
              <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3 max-w-[80%]">
              <p class="text-navy-700 leading-relaxed">
                你好！我是你的AI学习助手。请告诉我：
              </p>
              <ul class="mt-2 space-y-1 text-sm text-navy-600">
                <li>• 你想学习什么课程或技能？</li>
                <li>• 你目前的基础如何？</li>
                <li>• 你的学习目标是什么？</li>
              </ul>
            </div>
          </div>

          <!-- Message list -->
          <div v-for="(msg, i) in store.messages" :key="i" class="flex gap-3" :class="msg.role === 'user' ? 'justify-end' : ''">
            <template v-if="msg.role === 'assistant'">
              <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
                <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3 max-w-[80%]">
                <div class="text-navy-700 leading-relaxed markdown-body" v-html="renderMd(msg.content)"></div>
              </div>
            </template>
            <template v-else>
              <div class="bg-navy-600 text-white rounded-2xl rounded-tr-sm px-5 py-3 max-w-[80%]">
                <p class="leading-relaxed">{{ msg.content }}</p>
              </div>
            </template>
          </div>

          <!-- Typing indicator -->
          <div v-if="store.streaming" class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-navy-500 to-navy-700 flex items-center justify-center flex-shrink-0">
              <svg class="w-4 h-4 text-white animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <div class="bg-navy-50 rounded-2xl rounded-tl-sm px-5 py-3">
              <div v-if="store.streamBuffer" class="text-navy-700 leading-relaxed markdown-body" v-html="renderMd(store.streamBuffer)"></div>
              <div v-else class="flex gap-1.5 py-1">
                <span class="w-2 h-2 rounded-full bg-navy-300 animate-bounce" style="animation-delay: 0s"></span>
                <span class="w-2 h-2 rounded-full bg-navy-300 animate-bounce" style="animation-delay: 0.15s"></span>
                <span class="w-2 h-2 rounded-full bg-navy-300 animate-bounce" style="animation-delay: 0.3s"></span>
              </div>
            </div>
          </div>

          <!-- Progress log -->
          <div v-if="store.progressLogs.length > 0" class="flex items-start gap-3">
            <div class="w-8"></div>
            <div class="space-y-1">
              <p v-for="(log, i) in store.progressLogs" :key="i" class="text-xs text-navy-300 flex items-center gap-1.5">
                <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                {{ log }}
              </p>
            </div>
          </div>
        </div>

        <!-- Input area -->
        <div class="px-6 py-4 border-t border-navy-100/50 bg-white">
          <form @submit.prevent="sendMessage" class="flex gap-3 items-end">
            <AutoGrowTextarea
              v-model="inputText"
              :placeholder="store.streaming ? 'AI正在回复中...' : '描述你想学习的内容...'"
              :disabled="store.streaming"
            />
            <button type="submit" class="btn-primary px-6" :disabled="!inputText.trim() || store.streaming">
              发送
            </button>
          </form>
        </div>
      </div>

      <!-- Right: Profile + Plan preview -->
      <div class="w-[380px] flex-shrink-0 space-y-5 animate-fade-in-up" style="animation-delay: 0.15s">
        <!-- Profile radar -->
        <div class="card p-5">
          <h3 class="font-display text-base font-semibold text-navy-800 mb-4">学习画像</h3>
          <div class="aspect-square flex items-center justify-center">
            <ProfileRadar :dimensions="store.profileDimensions" />
          </div>
          <div class="mt-4 grid grid-cols-2 gap-2">
            <div v-for="(val, key) in store.profileDimensions" :key="key" class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full" :class="val !== undefined ? 'bg-sage-400' : 'bg-navy-100'"></div>
              <span class="text-xs" :class="val !== undefined ? 'text-navy-600' : 'text-navy-300'">
                {{ dimensionLabels[key] || key }}
              </span>
            </div>
          </div>
        </div>

        <!-- Plan preview -->
        <div v-if="store.generatedPlan" class="card p-5">
          <h3 class="font-display text-base font-semibold text-navy-800 mb-3">生成的学习计划</h3>
          <p class="text-sm font-medium text-navy-700 mb-3">{{ store.generatedPlan.title }}</p>
          <div class="space-y-2">
            <div v-for="(mod, i) in store.generatedPlan.modules" :key="i" class="flex items-center gap-3 p-2.5 rounded-lg bg-navy-50/50">
              <span class="w-6 h-6 rounded-full bg-navy-200 text-navy-600 text-xs flex items-center justify-center font-bold">{{ i + 1 }}</span>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-navy-700 truncate">{{ mod.title }}</p>
              </div>
              <div class="flex gap-1">
                <span v-for="type in mod.resourceTypes" :key="type" class="text-[10px] px-1.5 py-0.5 rounded" :class="typeBadgeClass(type)">
                  {{ typeLabels[type] }}
                </span>
              </div>
            </div>
          </div>
          <router-link v-if="store.generatedPlan.id" :to="`/plan/${store.generatedPlan.id}`" class="btn-primary w-full mt-4 text-sm">
            进入学习计划
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import { parseMarkdown } from '@/utils/markdown'
import { usePlanCreateStore } from '@/stores/planCreate'
import ProfileRadar from '@/components/profile/ProfileRadar.vue'
import ChatSessionSidebar from '@/components/chat/ChatSessionSidebar.vue'
import AutoGrowTextarea from '@/components/common/AutoGrowTextarea.vue'

const store = usePlanCreateStore()
const messagesContainer = ref<HTMLElement>()
const inputText = ref('')

const dimensionLabels: Record<string, string> = {
  sensing_vs_intuitive: '感知-直觉',
  visual_vs_verbal: '视觉-言语',
  active_vs_reflective: '活跃-沉思',
  sequential_vs_global: '循序-全局',
  knowledge_base: '知识基础',
  interest_tags: '兴趣标签',
  goal_orientation: '目标导向',
  weak_areas: '薄弱环节',
  preferred_resource_types: '偏好资源',
}

const typeLabels: Record<string, string> = { document: '文档', mindmap: '导图', quiz: '题目', code: '代码', reading: '阅读' }
function typeBadgeClass(type: string) {
  return { document: 'badge-doc', mindmap: 'badge-mindmap', quiz: 'badge-quiz', code: 'badge-code', reading: 'badge-reading' }[type] || 'badge-doc'
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

// Auto-scroll on new messages/streaming
watch(() => store.messages.length + store.streamBuffer.length + store.progressLogs.length, scrollToBottom)

function sendMessage() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  store.sendMessage(text)
}

onMounted(async () => {
  await store.loadSessions()
  if (!store.activeSessionId) {
    store.newSession()
  } else if (store.messages.length === 0) {
    // 刷新后恢复：有持久化的会话 ID 但消息丢失，重新加载
    await store.selectSession(store.activeSessionId)
  }
})
</script>
