<template>
  <aside class="flex h-full w-full flex-shrink-0 flex-col rounded-lg border border-navy-100 bg-white shadow-paper xl:w-[360px]">
    <div class="border-b border-navy-100 px-4 py-3">
      <p class="truncate text-sm font-semibold text-navy-800" :title="selectedNode?.title || ''">
        {{ selectedNode?.title || '选择节点' }}
      </p>
      <p class="mt-1 h-4 truncate text-xs text-navy-400" :title="selectedNode?.summary || ''">
        {{ selectedNode?.summary || '查看节点对话与生成结果' }}
      </p>
    </div>

    <div class="border-b border-navy-100 p-3">
      <div class="grid grid-cols-2 gap-2">
        <button class="quick-button" :disabled="disabled" title="按学习顺序拆分" @click="subdivide">
          按学习顺序拆分
        </button>
        <button class="quick-button" :disabled="disabled" title="第一性原理" @click="firstPrinciples">
          第一性原理
        </button>
        <button class="quick-button" disabled title="后续任务开放">
          生成测验
        </button>
        <button class="quick-button" disabled title="后续任务开放">
          生成闪卡
        </button>
      </div>
    </div>

    <div ref="messageListRef" class="flex-1 space-y-3 overflow-y-auto p-4">
      <div v-if="!selectedNode" class="pt-16 text-center text-sm text-navy-300">
        请选择一个节点
      </div>
      <div v-else-if="messages.length === 0 && !streamingText" class="pt-16 text-center text-sm text-navy-300">
        暂无对话
      </div>
      <div
        v-for="message in messages"
        :key="message.id"
        class="message"
        :class="message.role === 'user' ? 'ml-8 bg-navy-600 text-white' : 'mr-8 bg-navy-50 text-navy-700'"
      >
        <p class="whitespace-pre-wrap break-words text-sm leading-6">{{ message.content }}</p>
      </div>
      <div v-if="streamingText" class="message mr-8 border border-sage-100 bg-sage-50 text-navy-700">
        <p class="whitespace-pre-wrap break-words text-sm leading-6">{{ streamingText }}</p>
      </div>
    </div>

    <form class="border-t border-navy-100 p-3" @submit.prevent="submit">
      <textarea
        v-model="composer"
        class="h-20 w-full resize-none rounded-lg border border-navy-200 px-3 py-2 text-sm text-navy-700 outline-none transition-colors placeholder:text-navy-300 focus:border-navy-400 focus:ring-2 focus:ring-navy-100"
        placeholder="询问这个节点..."
        :disabled="disabled"
        @keydown.enter.exact.prevent="submit"
      />
      <div class="mt-2 flex items-center justify-between gap-2">
        <p class="truncate text-xs text-red-500">{{ error }}</p>
        <div class="flex items-center gap-2">
          <button
            v-if="canStopStream"
            type="button"
            class="h-8 rounded-lg px-3 text-xs font-semibold text-navy-500 hover:bg-navy-50"
            @click="store.stopStream"
          >
            停止
          </button>
          <button class="btn-primary h-8 px-4 py-0 text-sm" :disabled="disabled || !composer.trim()">
            发送
          </button>
        </div>
      </div>
    </form>
  </aside>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useKnowledgeTreeStore } from '@/stores/knowledgeTree'
import type { KnowledgeNode } from '@/types/knowledgeTree'

const props = defineProps<{
  selectedNode: KnowledgeNode | null
}>()

const store = useKnowledgeTreeStore()
const composer = ref('')
const messageListRef = ref<HTMLElement | null>(null)

const messages = computed(() => {
  const nodeId = props.selectedNode?.id
  return nodeId ? store.messagesByNode[nodeId] || [] : []
})

const streamingText = computed(() => (
  props.selectedNode?.id && store.streamingNodeId === props.selectedNode.id
    ? store.streamingText
    : ''
))
const canStopStream = computed(() => Boolean(store.streamingNodeId))
const disabled = computed(() => !props.selectedNode || store.loading)
const error = computed(() => store.error)

watch([messages, streamingText], () => {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}, { deep: true })

async function submit() {
  const text = composer.value.trim()
  if (!text || disabled.value) return
  composer.value = ''
  await store.sendMessage(text)
}

async function subdivide() {
  if (disabled.value) return
  await store.subdivideCurrent('按学习顺序拆分')
}

async function firstPrinciples() {
  if (disabled.value) return
  await store.firstPrinciplesCurrent()
}
</script>

<style scoped>
.quick-button {
  height: 34px;
  min-width: 0;
  overflow: hidden;
  border-radius: 8px;
  background: rgb(248 250 252);
  padding: 0 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 600;
  color: rgb(71 85 105);
  transition: background-color 0.18s ease, color 0.18s ease;
}

.quick-button:hover:not(:disabled) {
  background: rgb(226 232 240);
  color: rgb(30 41 59);
}

.quick-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.message {
  border-radius: 8px;
  padding: 10px 12px;
}
</style>
