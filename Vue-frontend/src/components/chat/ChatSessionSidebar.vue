<template>
  <div class="w-[260px] flex-shrink-0 border-r border-navy-100 bg-navy-50/30 flex flex-col h-full">
    <!-- New conversation button -->
    <div class="p-3">
      <button
        class="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200"
        :class="'bg-navy-600 text-white hover:bg-navy-700 shadow-sm'"
        @click="$emit('newSession')"
      >
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        新对话
      </button>
    </div>

    <!-- Session list -->
    <div class="flex-1 overflow-y-auto px-2 pb-3 space-y-0.5">
      <div v-if="loading" class="flex items-center justify-center py-8">
        <svg class="w-5 h-5 text-navy-300 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" class="opacity-25" /><path d="M4 12a8 8 0 018-8" class="opacity-75" stroke-linecap="round" />
        </svg>
      </div>

      <div v-else-if="sessions.length === 0" class="text-center py-8">
        <svg class="w-10 h-10 mx-auto mb-2 text-navy-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        <p class="text-xs text-navy-400">暂无会话记录</p>
      </div>

      <div
        v-for="session in sessions"
        :key="session.sessionId"
        class="group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-150 relative"
        :class="activeSessionId === session.sessionId
          ? 'bg-navy-100 text-navy-800'
          : 'text-navy-600 hover:bg-navy-50 hover:text-navy-700'"
        @click="$emit('select', session.sessionId)"
      >
        <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        <div class="flex-1 min-w-0">
          <p class="text-sm truncate">{{ session.title || '新对话' }}</p>
          <p class="text-[10px] text-navy-400 mt-0.5">{{ formatTime(session.lastMessageAt) }}</p>
        </div>
        <!-- Delete button -->
        <button
          class="opacity-0 group-hover:opacity-100 absolute right-2 p-1 rounded transition-opacity hover:bg-red-100 hover:text-red-500"
          @click.stop="confirmDelete(session)"
          title="删除会话"
        >
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ChatSession } from '@/types/chat'

defineProps<{
  sessions: ChatSession[]
  activeSessionId: string
  loading?: boolean
}>()

const emit = defineEmits<{
  newSession: []
  select: [sessionId: string]
  delete: [sessionId: string]
}>()

function formatTime(time: string) {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } else if (diffDays === 1) {
    return '昨天'
  } else if (diffDays < 7) {
    return `${diffDays}天前`
  } else {
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }
}

function confirmDelete(session: ChatSession) {
  if (confirm(`确定删除会话"${session.title}"？此操作不可撤销。`)) {
    emit('delete', session.sessionId)
  }
}
</script>
