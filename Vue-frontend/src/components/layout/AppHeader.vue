<template>
  <header class="h-16 border-b border-navy-100/50 bg-white/80 backdrop-blur-sm flex items-center justify-between px-6 flex-shrink-0">
    <!-- Left: collapse toggle + breadcrumb -->
    <div class="flex items-center gap-4">
      <button
        class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-400 hover:bg-navy-50 hover:text-navy-600 transition-colors"
        @click="uiStore.toggleSidebar()"
      >
        <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      <nav class="flex items-center gap-2 text-sm">
        <span class="text-navy-300">智学</span>
        <svg v-if="breadcrumb" class="w-4 h-4 text-navy-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
        <span v-if="breadcrumb" class="text-navy-600 font-medium">{{ breadcrumb }}</span>
      </nav>
    </div>

    <!-- Right: notes toggle + user actions -->
    <div class="flex items-center gap-3">
      <button
        class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all duration-200"
        :class="uiStore.notesPanelOpen ? 'bg-navy-100 text-navy-700' : 'text-navy-400 hover:bg-navy-50 hover:text-navy-600'"
        @click="uiStore.toggleNotesPanel()"
      >
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        笔记
      </button>

      <div class="w-px h-6 bg-navy-100"></div>

      <button
        class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-navy-400 hover:bg-red-50 hover:text-red-600 transition-colors"
        @click="handleLogout"
      >
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
          <polyline points="16 17 21 12 16 7"/>
          <line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
        退出
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const uiStore = useUiStore()
const authStore = useAuthStore()

const breadcrumbMap: Record<string, string> = {
  '/dashboard': '学习概览',
  '/plan/create': '学习计划',
  '/notes': '我的笔记',
  '/profile': '我的画像',
  '/admin': '管理概览',
  '/admin/kb': '知识库管理',
  '/admin/users': '用户管理',
}

const breadcrumb = computed(() => {
  const path = route.path
  if (breadcrumbMap[path]) return breadcrumbMap[path]
  if (path.startsWith('/plan/')) return '学习计划详情'
  return ''
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>
