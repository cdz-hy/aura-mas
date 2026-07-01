<template>
  <aside
    class="flex flex-col border-r border-navy-100 bg-white transition-all duration-300"
    :class="uiStore.sidebarCollapsed ? 'w-[72px]' : 'w-[260px]'"
  >
    <!-- Logo area -->
    <div
      class="h-16 flex items-center px-5 border-b border-navy-100/50 cursor-pointer hover:bg-navy-50/50 transition-colors select-none"
      @click="uiStore.toggleSidebar()"
    >
      <div class="flex items-center gap-3 min-w-0">
        <img src="/aura-icon.svg" alt="AURA" class="w-9 h-9 flex-shrink-0" />
        <transition name="fade">
          <span v-if="!uiStore.sidebarCollapsed" class="font-display text-lg font-bold text-navy-800 whitespace-nowrap">
            智学
          </span>
        </transition>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 py-4 space-y-1 overflow-y-auto" :class="uiStore.sidebarCollapsed ? 'px-2' : 'px-3'">
      <template v-for="item in navMenus" :key="item.code">
        <!-- Section header with children -->
        <template v-if="item.type === 'section' && item.children?.length">
          <div class="pt-4 mt-4 border-t border-navy-100/50">
            <p v-if="!uiStore.sidebarCollapsed" class="px-4 pb-2 text-xs font-semibold text-navy-300 uppercase tracking-wider">
              {{ item.name }}
            </p>
            <router-link
              v-for="child in item.children"
              :key="child.code"
              :to="child.path || '/'"
              class="sidebar-link"
              :class="[
                { 'sidebar-link-active': isActive(child.path || '') },
                uiStore.sidebarCollapsed ? 'justify-center px-0' : '',
              ]"
            >
              <div class="w-5 h-5 flex-shrink-0" v-html="getIcon(child.icon)"></div>
              <span v-if="!uiStore.sidebarCollapsed" class="whitespace-nowrap">{{ child.name }}</span>
            </router-link>
          </div>
        </template>

        <!-- Regular menu item with path -->
        <router-link
          v-else-if="item.path"
          :to="item.path"
          class="sidebar-link group"
          :class="[
            { 'sidebar-link-active': isActive(item.path) },
            uiStore.sidebarCollapsed ? 'justify-center px-0' : '',
          ]"
        >
          <div class="w-5 h-5 flex-shrink-0" v-html="getIcon(item.icon)"></div>
          <transition name="fade">
            <span v-if="!uiStore.sidebarCollapsed" class="whitespace-nowrap">{{ item.name }}</span>
          </transition>
        </router-link>
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
            <p class="text-xs text-navy-400 truncate">{{ roleLabel }}</p>
          </div>
        </transition>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'
import type { MenuItem } from '@/types/menu'

const HIDDEN_SIDEBAR_CODES = new Set(['knowledge-tree'])

function filterSidebarMenus(items: MenuItem[]): MenuItem[] {
  return items
    .filter(item => !HIDDEN_SIDEBAR_CODES.has(item.code))
    .map(item => (
      item.children?.length
        ? { ...item, children: filterSidebarMenus(item.children) }
        : item
    ))
}

const route = useRoute()
const uiStore = useUiStore()
const authStore = useAuthStore()
const permissionStore = usePermissionStore()

const navMenus = computed(() => filterSidebarMenus(permissionStore.menus))

const roleLabel = computed(() => authStore.user?.role === 'admin' ? '管理员' : '学生')

function isActive(path: string) {
  return route.path === path
}

const iconMap: Record<string, string> = {
  dashboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  plan: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>',
  tree: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="5" r="3"/><circle cx="6" cy="19" r="3"/><circle cx="18" cy="19" r="3"/><path d="M12 8v4"/><path d="M12 12H6v4"/><path d="M12 12h6v4"/></svg>',
  notes: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
  profile: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  analytics: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
  admin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/></svg>',
  book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
  users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
  token: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2a10 10 0 1 0 10 10H12V2z"/><path d="M12 2a10 10 0 0 1 10 10"/><path d="M20.5 7H12"/><path d="M12 2v5"/></svg>',
  'knowledge-graph': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="2.5"/><circle cx="5" cy="5" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><line x1="7" y1="6.5" x2="10" y2="10.5"/><line x1="17" y1="6.5" x2="14" y2="10.5"/><line x1="7" y1="17.5" x2="10" y2="13.5"/><line x1="17" y1="17.5" x2="14" y2="13.5"/></svg>',
  log: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
  share: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="2.5"/><circle cx="5" cy="5" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><line x1="7" y1="6.5" x2="10" y2="10.5"/><line x1="17" y1="6.5" x2="14" y2="10.5"/><line x1="7" y1="17.5" x2="10" y2="13.5"/><line x1="17" y1="17.5" x2="14" y2="13.5"/></svg>',
}

function getIcon(code: string | null): string {
  return iconMap[code || ''] || iconMap.dashboard
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
