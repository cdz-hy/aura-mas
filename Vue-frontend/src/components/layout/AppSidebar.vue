<template>
  <aside
    class="flex flex-col border-r border-navy-100 bg-white transition-all duration-300"
    :class="uiStore.sidebarCollapsed ? 'w-[72px]' : 'w-[260px]'"
  >
    <!-- Logo area -->
    <div
      class="h-16 flex items-center px-5 border-b border-navy-100/50 cursor-pointer hover:bg-navy-50/50 transition-colors"
      @click="uiStore.toggleSidebar()"
    >
      <div class="flex items-center gap-3 min-w-0">
        <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-navy-600 to-navy-800 flex items-center justify-center flex-shrink-0 shadow-sm">
          <svg class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <transition name="fade">
          <span v-if="!uiStore.sidebarCollapsed" class="font-display text-lg font-bold text-navy-800 whitespace-nowrap">
            智学
          </span>
        </transition>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 py-4 space-y-1 overflow-y-auto" :class="uiStore.sidebarCollapsed ? 'px-2' : 'px-3'">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="sidebar-link group"
        :class="[
          { 'sidebar-link-active': isActive(item.path) },
          uiStore.sidebarCollapsed ? 'justify-center px-0' : '',
        ]"
      >
        <div class="w-5 h-5 flex-shrink-0" v-html="item.icon"></div>
        <transition name="fade">
          <span v-if="!uiStore.sidebarCollapsed" class="whitespace-nowrap">{{ item.label }}</span>
        </transition>
      </router-link>

      <!-- Admin section -->
      <template v-if="authStore.isAdmin">
        <div class="pt-4 mt-4 border-t border-navy-100/50">
          <p v-if="!uiStore.sidebarCollapsed" class="px-4 pb-2 text-xs font-semibold text-navy-300 uppercase tracking-wider">
            管理
          </p>
          <router-link
            v-for="item in adminNavItems"
            :key="item.path"
            :to="item.path"
            class="sidebar-link"
            :class="[
              { 'sidebar-link-active': isActive(item.path) },
              uiStore.sidebarCollapsed ? 'justify-center px-0' : '',
            ]"
          >
            <div class="w-5 h-5 flex-shrink-0" v-html="item.icon"></div>
            <span v-if="!uiStore.sidebarCollapsed" class="whitespace-nowrap">{{ item.label }}</span>
          </router-link>
        </div>
      </template>
    </nav>

    <!-- User info -->
    <div class="p-3 border-t border-navy-100/50">
      <div
        class="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-navy-50 transition-colors cursor-pointer"
        :class="uiStore.sidebarCollapsed ? 'justify-center' : ''"
        @click="$router.push('/settings')"
      >
        <div class="w-8 h-8 rounded-full overflow-hidden flex-shrink-0">
          <img
            v-if="authStore.user?.avatarUrl"
            :src="authStore.user.avatarUrl"
            alt="头像"
            class="w-full h-full object-cover"
          />
          <div
            v-else
            class="w-full h-full bg-gradient-to-br from-sage-400 to-sage-600 flex items-center justify-center text-white text-sm font-bold"
          >
            {{ authStore.user?.nickname?.[0] || 'U' }}
          </div>
        </div>
        <transition name="fade">
          <div v-if="!uiStore.sidebarCollapsed" class="overflow-hidden">
            <p class="text-sm font-medium text-navy-800 truncate">{{ authStore.user?.nickname || '用户' }}</p>
            <p class="text-xs text-navy-400 truncate">{{ authStore.user?.role === 'admin' ? '管理员' : '学生' }}</p>
          </div>
        </transition>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const uiStore = useUiStore()
const authStore = useAuthStore()

function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}

const navItems = [
  {
    path: '/dashboard',
    label: '学习概览',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  },
  {
    path: '/plan/create',
    label: '学习计划',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>',
  },
  {
    path: '/notes',
    label: '我的笔记',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
  },
  {
    path: '/profile',
    label: '我的画像',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  },
]

const adminNavItems = [
  {
    path: '/admin',
    label: '管理概览',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/></svg>',
  },
  {
    path: '/admin/kb',
    label: '知识库管理',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
  },
  {
    path: '/admin/users',
    label: '用户管理',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
  },
]
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
