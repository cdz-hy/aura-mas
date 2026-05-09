<template>
  <div v-if="!plan" class="flex items-center justify-center h-64">
    <div class="text-center">
      <svg class="w-12 h-12 mx-auto text-navy-200 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" class="opacity-25" /><path d="M4 12a8 8 0 018-8" class="opacity-75" stroke-linecap="round" />
      </svg>
      <p class="mt-3 text-navy-400">加载中...</p>
    </div>
  </div>

  <div v-else class="flex gap-0 h-[calc(100vh-12rem)]">
    <!-- ==================== 左侧：模块列表 ==================== -->
    <div class="w-[320px] flex-shrink-0 flex flex-col card overflow-hidden animate-fade-in-up">
      <!-- Plan header -->
      <div class="px-4 py-4 border-b border-navy-100/50">
        <!-- 可编辑标题 -->
        <div class="flex items-center gap-2">
          <input
            v-if="editingTitle"
            v-model="editTitle"
            class="input-field text-sm py-1.5 flex-1"
            @keyup.enter="saveTitle"
            @keyup.escape="editingTitle = false"
            autofocus
          />
          <h2 v-else class="font-display text-base font-semibold text-navy-800 truncate flex-1">{{ plan.title }}</h2>
          <button
            v-if="!editingTitle"
            class="p-1 rounded text-navy-300 hover:text-navy-600 hover:bg-navy-50 transition-colors"
            @click="editTitle = plan.title; editingTitle = true"
            title="修改计划名称"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
          <button
            v-if="editingTitle"
            class="p-1 rounded text-emerald-500 hover:bg-emerald-50 transition-colors"
            @click="saveTitle"
            title="保存"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </button>
          <button
            v-if="editingTitle"
            class="p-1 rounded text-navy-300 hover:text-navy-600 hover:bg-navy-50 transition-colors"
            @click="editingTitle = false"
            title="取消"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div class="flex items-center gap-2 mt-1.5">
          <span class="text-xs px-2 py-0.5 rounded-full" :class="statusClass(plan.status)">
            {{ statusText(plan.status) }}
          </span>
          <span class="text-xs text-navy-400">{{ Math.round(plan.progress || 0) }}%</span>
        </div>
        <div class="mt-2 h-1.5 bg-navy-100 rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-navy-400 to-sage-500 rounded-full transition-all duration-500" :style="{ width: `${plan.progress || 0}%` }"></div>
        </div>
      </div>

      <!-- Module list -->
      <div class="flex-1 overflow-y-auto p-3 space-y-2">
        <div v-if="modules.length === 0" class="text-center py-8 text-navy-300 text-sm">
          <p>暂无学习模块</p>
          <p class="text-xs mt-1">在右侧对话中描述学习目标，AI 会自动规划</p>
        </div>
        <div
          v-for="(mod, i) in modules"
          :key="i"
          class="rounded-lg cursor-pointer transition-all duration-200 border"
          :class="selectedModule === i ? 'border-navy-300 bg-navy-50 shadow-sm' : 'border-transparent hover:bg-navy-50/50'"
          @click="selectedModule = i"
        >
          <div class="p-3">
            <div class="flex items-center gap-2.5">
              <span class="w-6 h-6 rounded-full text-xs flex items-center justify-center font-bold flex-shrink-0"
                :class="selectedModule === i ? 'bg-navy-600 text-white' : 'bg-navy-100 text-navy-500'">
                {{ i + 1 }}
              </span>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-navy-800 truncate">{{ mod.title }}</p>
                <p class="text-xs text-navy-400 mt-0.5">{{ mod.estimatedHours || 2 }}学时</p>
              </div>
            </div>
            <div class="flex flex-wrap gap-1 mt-2 ml-8">
              <span v-for="type in mod.resourceTypes" :key="type"
                class="text-[10px] px-1.5 py-0.5 rounded-full"
                :class="badgeClass(type)">
                {{ typeLabels[type] || type }}
              </span>
            </div>
          </div>

          <!-- 模块资源内容预览 -->
          <div v-if="selectedModule === i && mod.resources.length > 0" class="border-t border-navy-100/50 px-3 py-2 space-y-1.5">
            <div
              v-for="res in mod.resources"
              :key="res.id"
              class="flex items-center gap-2 p-1.5 rounded-md text-xs hover:bg-white transition-colors cursor-pointer"
              @click.stop="viewResource(res)"
            >
              <span class="w-2 h-2 rounded-full flex-shrink-0" :class="res.status === 2 ? 'bg-emerald-400' : 'bg-navy-200'"></span>
              <span class="text-navy-600 truncate flex-1">{{ res.moduleData?.title || typeLabels[res.moduleType] || res.moduleType }}</span>
              <span v-if="res.status === 2" class="text-emerald-500 text-[10px]">已生成</span>
              <span v-else class="text-navy-300 text-[10px]">待生成</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom action -->
      <div class="p-3 border-t border-navy-100/50">
        <button
          class="w-full text-xs px-3 py-2 rounded-lg bg-navy-50 text-navy-600 hover:bg-navy-100 transition-colors"
          @click="generateAllResources"
          :disabled="generating"
        >
          {{ generating ? generateProgress || '生成中...' : '生成全部资源' }}
        </button>
      </div>
    </div>

    <!-- ==================== 右侧：对话界面 ==================== -->
    <div class="flex-1 flex flex-col card overflow-hidden animate-fade-in-up ml-4" style="animation-delay: 0.1s">
      <!-- Chat header -->
      <div class="px-6 py-3 border-b border-navy-100/50 flex items-center justify-between">
        <div>
          <h3 class="font-display text-base font-semibold text-navy-800">AI 学习助手</h3>
          <p class="text-xs text-navy-400">描述学习目标，AI 会为你规划路径并生成资源</p>
        </div>
        <button
          v-if="chatStore.streaming"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
          @click="chatStore.stopGeneration()"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
          停止
        </button>
      </div>

      <!-- Messages -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
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
                @click="sendMessage(q)">
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

            <!-- 任务分解确认卡片 -->
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
                  @click="confirmBreakdown()">
                  确认，开始生成
                </button>
                <button class="px-4 py-2 rounded-lg bg-white text-navy-600 text-sm font-medium border border-navy-200 hover:bg-navy-50 transition-colors"
                  @click="showModifyInput = true">
                  补充说明
                </button>
              </div>
              <div v-if="showModifyInput && chatStore.awaitingConfirmation && i === chatStore.messages.length - 1" class="ml-2">
                <form @submit.prevent="submitModification" class="flex gap-2">
                  <input v-model="modifyText" type="text" class="input-field flex-1 text-sm" placeholder="输入补充说明..." autofocus />
                  <button type="submit" class="btn-primary px-4 text-sm" :disabled="!modifyText.trim()">发送</button>
                </form>
              </div>
            </div>

            <!-- 普通消息 -->
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

        <!-- Streaming -->
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
      </div>

      <!-- Input -->
      <div class="px-6 py-3 border-t border-navy-100/50 bg-white">
        <form @submit.prevent="sendMessage()" class="flex gap-3">
          <input
            v-model="inputText"
            type="text"
            class="input-field flex-1"
            :placeholder="chatStore.streaming ? 'AI回复中...' : chatStore.awaitingConfirmation ? '输入补充说明...' : '描述你想学习的内容...'"
            :disabled="chatStore.streaming"
          />
          <button type="submit" class="btn-primary px-5" :disabled="!inputText.trim() || chatStore.streaming">
            发送
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { getPlan, updatePlan } from '@/api/plan'
import { getPlanResources, updateResourceContent } from '@/api/resource'
import { issueTicket } from '@/api/auth'
import { createSSEConnection, cancelSSE } from '@/utils/sse'
import { parseMarkdown } from '@/utils/markdown'
import { useChatStore } from '@/stores/chat'
import type { LearningPlan, LearningResource } from '@/types/plan'

const route = useRoute()
const planId = Number(route.params.id)
const planIdStr = String(planId)
const chatStore = useChatStore()

const plan = ref<LearningPlan | null>(null)
const resources = ref<LearningResource[]>([])
const selectedModule = ref(0)
const generating = ref(false)
const generateProgress = ref('')
const messagesContainer = ref<HTMLElement>()
const inputText = ref('')
const showModifyInput = ref(false)
const modifyText = ref('')

// 标题编辑
const editingTitle = ref(false)
const editTitle = ref('')

const quickQuestions = [
  '我想学习 Python 基础',
  '帮我生成一些练习题',
  '这个知识点不太理解',
]

const typeLabels: Record<string, string> = {
  document: '文档', mindmap: '导图', quiz: '题目', code: '代码', reading: '阅读',
}

// Build modules from resources
const modules = computed(() => {
  const moduleMap = new Map<number, { order: number; title: string; estimatedHours: number; resourceTypes: string[]; resources: LearningResource[] }>()
  resources.value.forEach(r => {
    if (!moduleMap.has(r.moduleOrder)) {
      moduleMap.set(r.moduleOrder, {
        order: r.moduleOrder,
        title: r.moduleData?.module_title || `模块 ${r.moduleOrder}`,
        estimatedHours: r.moduleData?.estimated_hours || 2,
        resourceTypes: [],
        resources: [],
      })
    }
    const mod = moduleMap.get(r.moduleOrder)!
    if (!mod.resourceTypes.includes(r.moduleType)) {
      mod.resourceTypes.push(r.moduleType)
    }
    mod.resources.push(r)
  })
  return Array.from(moduleMap.values()).sort((a, b) => a.order - b.order)
})

function renderMd(text: string) { return parseMarkdown(text) }

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(() => chatStore.messages.length + chatStore.streamBuffer.length, scrollToBottom)

function sendMessage(text?: string) {
  const msg = text || inputText.value.trim()
  if (!msg) return
  inputText.value = ''
  showModifyInput.value = false
  chatStore.sendMessage(msg, planIdStr)
}

function confirmBreakdown() {
  showModifyInput.value = false
  chatStore.confirmBreakdown(planIdStr)
}

function submitModification() {
  const text = modifyText.value.trim()
  if (!text) return
  modifyText.value = ''
  showModifyInput.value = false
  chatStore.confirmBreakdown(planIdStr, text)
}

// 保存计划标题
async function saveTitle() {
  const title = editTitle.value.trim()
  if (!title || !plan.value) return
  editingTitle.value = false
  if (title === plan.value.title) return
  try {
    await updatePlan(planId, { title })
    plan.value.title = title
  } catch (e) {
    console.error('Failed to update plan title:', e)
  }
}

// 查看资源详情（展开模块内容）
function viewResource(res: LearningResource) {
  if (res.status !== 2 || !res.moduleData) return
  // 将资源内容作为消息显示在对话中
  const content = res.moduleData
  if (content.content) {
    chatStore.messages.push({
      role: 'assistant',
      content: `**${content.title || typeLabels[res.moduleType]}**\n\n${content.content}`,
    })
  }
}

// Status helpers
function statusText(s: number) { return ['待规划', '生成中', '待确认', '学习中', '已完成'][s] || '未知' }
function statusClass(s: number) {
  return ['bg-gray-100 text-gray-600', 'bg-blue-100 text-blue-600', 'bg-amber-100 text-amber-600', 'bg-emerald-100 text-emerald-600', 'bg-sage-100 text-sage-700'][s] || 'bg-gray-100 text-gray-600'
}
function badgeClass(type: string) {
  return { document: 'bg-blue-50 text-blue-500', mindmap: 'bg-purple-50 text-purple-500', quiz: 'bg-amber-50 text-amber-500', code: 'bg-emerald-50 text-emerald-500', reading: 'bg-rose-50 text-rose-500' }[type] || 'bg-navy-50 text-navy-500'
}

// Generate all resources
async function generateAllResources() {
  generating.value = true
  generateProgress.value = ''
  try {
    const pending = resources.value.filter(r => r.status !== 2 || !r.moduleData || Object.keys(r.moduleData).length === 0)
    if (pending.length === 0) {
      generateProgress.value = '所有资源已生成'
      generating.value = false
      return
    }
    let completed = 0
    for (const resource of pending) {
      generateProgress.value = `[${completed + 1}/${pending.length}] 生成中...`
      const ticketRes = await issueTicket()
      const content = await generateSingleResource(ticketRes.data.ticket, resource)
      if (content) {
        await updateResourceContent(resource.id, content, 2)
        resource.moduleData = content
        resource.status = 2
      }
      completed++
    }
    generateProgress.value = `全部 ${pending.length} 个资源生成完毕！`
  } catch (e: any) {
    generateProgress.value = `生成失败: ${e.message}`
  } finally {
    generating.value = false
  }
}

function generateSingleResource(ticket: string, resource: LearningResource): Promise<Record<string, any> | null> {
  return new Promise((resolve) => {
    let resolved = false
    const sse = createSSEConnection('/api/ai/resource/generate', ticket, {
      plan_id: String(resource.planId), module_id: String(resource.moduleOrder), type: resource.moduleType,
      title: resource.moduleData?.module_title || '',
      description: resource.moduleData?.module_description || '',
    }, {
      onResource(data) { if (!resolved) { resolved = true; resolve(data) } },
      onDone() { if (!resolved) { resolved = true; resolve(null) } },
      onError() { if (!resolved) { resolved = true; resolve(null) } },
    })
    setTimeout(() => { if (!resolved) { resolved = true; cancelSSE(sse); resolve(null) } }, 300000)
  })
}

function parseModuleData(res: LearningResource[]) {
  res.forEach(r => {
    if (typeof r.moduleData === 'string') {
      try { r.moduleData = JSON.parse(r.moduleData) } catch { r.moduleData = {} }
    }
  })
}

onMounted(async () => {
  // 重置对话状态，防止残留其他计划的消息
  chatStore.resetForPlan(planIdStr)

  try {
    const [planRes, resourcesRes] = await Promise.all([
      getPlan(planId),
      getPlanResources(planId),
    ])
    plan.value = planRes.data
    resources.value = resourcesRes.data || []
    parseModuleData(resources.value)
  } catch (e) {
    console.error('[PlanDetail] 加载失败:', e)
  }

  // 加载该计划的会话并自动创建新会话
  await chatStore.loadSessions(planIdStr)
  chatStore.newSession()
})
</script>
