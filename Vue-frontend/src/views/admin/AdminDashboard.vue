<template>
  <div>
    <!-- Welcome header -->
    <div class="mb-8">
      <h1 class="section-title">
        {{ greeting }}，{{ authStore.user?.nickname || '管理员' }}
      </h1>
      <p class="mt-1 text-navy-400">系统运行概览与操作日志</p>
    </div>

    <!-- Stats cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
      <div
        v-for="(stat, i) in stats"
        :key="stat.label"
        class="stat-card animate-fade-in-up relative overflow-hidden group cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300 bg-white"
        :style="{ animationDelay: `${i * 0.08}s` }"
      >
        <div class="absolute -right-6 -bottom-6 w-32 h-32 opacity-[0.04] transition-transform duration-700 group-hover:scale-110 group-hover:-rotate-12 pointer-events-none" :class="stat.iconClass" v-html="stat.icon"></div>
        <div class="absolute -left-10 -top-10 w-24 h-24 rounded-full opacity-30 blur-2xl transition-all duration-700 group-hover:scale-150 pointer-events-none" :class="stat.decorationClass"></div>

        <div class="relative z-10 flex items-center justify-between">
          <span class="stat-label group-hover:text-navy-600 transition-colors">{{ stat.label }}</span>
          <div class="w-10 h-10 rounded-xl flex items-center justify-center shadow-sm transition-transform duration-500 group-hover:scale-110 group-hover:rotate-3" :class="stat.bgClass">
            <div class="w-5 h-5" :class="stat.iconClass" v-html="stat.icon"></div>
          </div>
        </div>

        <div class="relative z-10 mt-1 flex flex-col">
          <span class="stat-value group-hover:text-navy-900 transition-colors">{{ stat.value }}</span>
          <div class="mt-2 h-1 w-12 rounded-full opacity-60 transition-all duration-500 group-hover:w-16" :class="stat.lineClass"></div>
        </div>
      </div>
    </div>

    <!-- Main content grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- System logs -->
      <div class="lg:col-span-2 card p-6 animate-fade-in-up" style="animation-delay: 0.35s">
        <div class="flex items-center justify-between mb-5">
          <h2 class="font-display text-lg font-semibold text-navy-800">最近操作日志</h2>
          <span class="text-xs text-navy-400">最近 15 条</span>
        </div>

        <div v-if="logs.length === 0" class="text-center py-12">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-navy-50 flex items-center justify-center">
            <svg class="w-8 h-8 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          <p class="text-navy-400">暂无操作日志</p>
        </div>

        <div v-else class="space-y-1 max-h-[520px] overflow-y-auto custom-scrollbar">
          <div
            v-for="log in logs"
            :key="log.id"
            class="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-navy-50/60 transition-colors group"
          >
            <!-- Status dot -->
            <div class="w-2 h-2 rounded-full flex-shrink-0" :class="log.status === 1 ? 'bg-emerald-400' : 'bg-red-400'"></div>

            <!-- Icon by module -->
            <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" :class="moduleConfig(log.module)?.bgClass || 'bg-navy-50'">
              <div class="w-4 h-4" :class="moduleConfig(log.module)?.iconClass || 'text-navy-400'" v-html="moduleConfig(log.module)?.icon || defaultIcon"></div>
            </div>

            <!-- Content -->
            <div class="flex-1 min-w-0">
              <p class="text-sm text-navy-700 truncate">{{ log.operation_desc || log.operation_type }}</p>
              <div class="flex items-center gap-2 mt-0.5">
                <span class="text-xs text-navy-400">{{ log.login_name || '系统' }}</span>
                <span v-if="log.user_ip" class="text-xs text-navy-300">{{ log.user_ip }}</span>
              </div>
            </div>

            <!-- Module badge -->
            <span class="text-[10px] px-2 py-0.5 rounded-full font-medium flex-shrink-0" :class="moduleConfig(log.module)?.badgeClass || 'bg-navy-50 text-navy-500'">
              {{ moduleConfig(log.module)?.label || log.module }}
            </span>

            <!-- Time -->
            <span class="text-xs text-navy-300 flex-shrink-0 w-16 text-right">{{ formatTime(log.created_at) }}</span>
          </div>
        </div>
      </div>

      <!-- Right sidebar -->
      <div class="space-y-6 animate-fade-in-up" style="animation-delay: 0.45s">
        <!-- Quick stats -->
        <div class="card p-6">
          <h2 class="font-display text-lg font-semibold text-navy-800 mb-5">平台概览</h2>
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-sm text-navy-500">活跃用户</span>
              <span class="text-sm font-semibold text-navy-800">{{ data?.activeUsers ?? '--' }} / {{ data?.totalUsers ?? '--' }}</span>
            </div>
            <div class="flex-1 h-1.5 bg-navy-50 rounded-full overflow-hidden">
              <div class="h-full bg-gradient-to-r from-emerald-400 to-emerald-500 rounded-full transition-all duration-700" :style="{ width: activeUserPercent + '%' }"></div>
            </div>

            <div class="flex items-center justify-between pt-2">
              <span class="text-sm text-navy-500">进行中计划</span>
              <span class="text-sm font-semibold text-navy-800">{{ data?.activePlans ?? '--' }} / {{ data?.totalPlans ?? '--' }}</span>
            </div>
            <div class="flex-1 h-1.5 bg-navy-50 rounded-full overflow-hidden">
              <div class="h-full bg-gradient-to-r from-blue-400 to-blue-500 rounded-full transition-all duration-700" :style="{ width: activePlanPercent + '%' }"></div>
            </div>

            <div class="flex items-center justify-between pt-2">
              <span class="text-sm text-navy-500">今日 Token 消耗</span>
              <span class="text-sm font-semibold text-navy-800">{{ formatTokens(data?.todayTokens) }}</span>
            </div>
          </div>
        </div>

        <!-- Legend -->
        <div class="card p-6">
          <h2 class="font-display text-lg font-semibold text-navy-800 mb-4">日志状态说明</h2>
          <div class="space-y-3">
            <div class="flex items-center gap-3">
              <div class="w-2.5 h-2.5 rounded-full bg-emerald-400"></div>
              <span class="text-sm text-navy-600">操作成功</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="w-2.5 h-2.5 rounded-full bg-red-400"></div>
              <span class="text-sm text-navy-600">操作失败</span>
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-navy-100/50">
            <p class="text-xs text-navy-400">日志通过 AOP 切面自动记录，覆盖认证、用户管理、知识库、学习计划等核心操作。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getDashboardStats, getDashboardLogs } from '@/api/admin'
import type { AdminDashboardStats, AdminLogItem } from '@/api/admin'
import dayjs from 'dayjs'

const authStore = useAuthStore()
const data = ref<AdminDashboardStats | null>(null)
const logs = ref<AdminLogItem[]>([])

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const stats = computed(() => [
  {
    label: '用户总数',
    value: data.value?.totalUsers ?? '--',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    bgClass: 'bg-blue-50',
    iconClass: 'text-blue-500',
    decorationClass: 'bg-blue-200',
    lineClass: 'bg-blue-300',
  },
  {
    label: '进行中计划',
    value: data.value?.activePlans ?? '--',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
    bgClass: 'bg-emerald-50',
    iconClass: 'text-emerald-500',
    decorationClass: 'bg-emerald-200',
    lineClass: 'bg-emerald-300',
  },
  {
    label: '知识库文档',
    value: data.value?.totalKBDocs ?? '--',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    bgClass: 'bg-amber-50',
    iconClass: 'text-amber-500',
    decorationClass: 'bg-amber-200',
    lineClass: 'bg-amber-300',
  },
  {
    label: '今日 AI 调用',
    value: data.value?.todayAICalls ?? '--',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    bgClass: 'bg-purple-50',
    iconClass: 'text-purple-500',
    decorationClass: 'bg-purple-200',
    lineClass: 'bg-purple-300',
  },
])

const activeUserPercent = computed(() => {
  if (!data.value || data.value.totalUsers === 0) return 0
  return Math.round((data.value.activeUsers / data.value.totalUsers) * 100)
})

const activePlanPercent = computed(() => {
  if (!data.value || data.value.totalPlans === 0) return 0
  return Math.round((data.value.activePlans / data.value.totalPlans) * 100)
})

const defaultIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>'

interface ModuleConfigItem {
  label: string
  icon: string
  bgClass: string
  iconClass: string
  badgeClass: string
}

const moduleMap: Record<string, ModuleConfigItem> = {
  Auth: {
    label: '认证',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    bgClass: 'bg-rose-50',
    iconClass: 'text-rose-500',
    badgeClass: 'bg-rose-50 text-rose-600',
  },
  UserAdmin: {
    label: '用户管理',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    bgClass: 'bg-blue-50',
    iconClass: 'text-blue-500',
    badgeClass: 'bg-blue-50 text-blue-600',
  },
  User: {
    label: '用户',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    bgClass: 'bg-sky-50',
    iconClass: 'text-sky-500',
    badgeClass: 'bg-sky-50 text-sky-600',
  },
  KB: {
    label: '知识库',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    bgClass: 'bg-amber-50',
    iconClass: 'text-amber-500',
    badgeClass: 'bg-amber-50 text-amber-600',
  },
  Plan: {
    label: '计划',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
    bgClass: 'bg-emerald-50',
    iconClass: 'text-emerald-500',
    badgeClass: 'bg-emerald-50 text-emerald-600',
  },
  KG: {
    label: '知识图谱',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    bgClass: 'bg-indigo-50',
    iconClass: 'text-indigo-500',
    badgeClass: 'bg-indigo-50 text-indigo-600',
  },
  Note: {
    label: '笔记',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',
    bgClass: 'bg-teal-50',
    iconClass: 'text-teal-500',
    badgeClass: 'bg-teal-50 text-teal-600',
  },
  Resource: {
    label: '资源',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    bgClass: 'bg-orange-50',
    iconClass: 'text-orange-500',
    badgeClass: 'bg-orange-50 text-orange-600',
  },
  Flashcard: {
    label: '闪卡',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
    bgClass: 'bg-pink-50',
    iconClass: 'text-pink-500',
    badgeClass: 'bg-pink-50 text-pink-600',
  },
  File: {
    label: '文件',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',
    bgClass: 'bg-gray-50',
    iconClass: 'text-gray-500',
    badgeClass: 'bg-gray-50 text-gray-600',
  },
  Ticket: {
    label: '票据',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>',
    bgClass: 'bg-violet-50',
    iconClass: 'text-violet-500',
    badgeClass: 'bg-violet-50 text-violet-600',
  },
  Dialogue: {
    label: '对话',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    bgClass: 'bg-cyan-50',
    iconClass: 'text-cyan-500',
    badgeClass: 'bg-cyan-50 text-cyan-600',
  },
}

function moduleConfig(module: string | null): ModuleConfigItem | null {
  if (!module) return null
  return moduleMap[module] || null
}

function formatTime(date: string | null): string {
  if (!date) return ''
  return dayjs(date).format('HH:mm')
}

function formatTokens(tokens: number | undefined): string {
  if (tokens == null) return '--'
  if (tokens >= 1_000_000) return (tokens / 1_000_000).toFixed(1) + 'M'
  if (tokens >= 1_000) return (tokens / 1_000).toFixed(1) + 'K'
  return tokens.toString()
}

async function loadDashboard() {
  try {
    const [statsRes, logsRes] = await Promise.all([
      getDashboardStats().catch(() => null),
      getDashboardLogs().catch(() => null),
    ])
    if (statsRes) data.value = statsRes.data
    if (logsRes) logs.value = logsRes.data
  } catch {
    // silent
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: var(--color-navy-200, #e2e8f0);
  border-radius: 20px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: var(--color-navy-300, #cbd5e1);
}
</style>
