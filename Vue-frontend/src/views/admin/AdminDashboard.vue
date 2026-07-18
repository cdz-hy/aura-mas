<template>
  <div>
    <!-- Welcome header -->
    <div class="mb-8">
      <h1 class="section-title">
        {{ greeting }}，{{ authStore.user?.nickname || '管理员' }}
      </h1>
      <p class="mt-1 text-navy-400 h-6">系统运行概览与数据监控</p>
    </div>

    <!-- Stats cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
      <div v-for="(stat, i) in stats" :key="stat.label" class="stat-card animate-fade-in-up relative overflow-hidden group cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300 bg-white" :style="{ animationDelay: `${i * 0.08}s` }">
        <!-- Background decorative icon -->
        <div class="absolute -right-6 -bottom-6 w-32 h-32 opacity-[0.04] transition-transform duration-700 group-hover:scale-110 group-hover:-rotate-12 pointer-events-none" :class="stat.iconClass" v-html="stat.icon"></div>

        <!-- Background decorative gradient blob -->
        <div class="absolute -left-10 -top-10 w-24 h-24 rounded-full opacity-30 blur-2xl transition-all duration-700 group-hover:scale-150 pointer-events-none" :class="stat.decorationClass"></div>

        <div class="relative z-10 flex items-center justify-between">
          <span class="stat-label group-hover:text-navy-600 transition-colors">{{ stat.label }}</span>
          <div class="w-10 h-10 rounded-xl flex items-center justify-center shadow-sm transition-transform duration-500 group-hover:scale-110 group-hover:rotate-3" :class="stat.bgClass">
            <div class="w-5 h-5" :class="stat.iconClass" v-html="stat.icon"></div>
          </div>
        </div>

        <div class="relative z-10 mt-1 flex flex-col">
          <span class="stat-value group-hover:text-navy-900 transition-colors">{{ stat.value }}</span>
          <span v-if="stat.sub" class="text-xs text-navy-400 mt-1">{{ stat.sub }}</span>
          <div class="mt-2 h-1 w-12 rounded-full opacity-60 transition-all duration-500 group-hover:w-16" :class="stat.lineClass"></div>
        </div>
      </div>
    </div>

    <!-- Charts row -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
      <!-- Trend chart -->
      <div class="lg:col-span-2 card p-6 animate-fade-in-up" style="animation-delay: 0.35s">
        <div class="flex items-center justify-between mb-5">
          <h2 class="font-display text-lg font-semibold text-navy-800">近7天操作日志趋势</h2>
          <router-link to="/admin/logs" class="text-xs text-navy-400 hover:text-navy-600 transition-colors">查看全部 →</router-link>
        </div>
        <div class="h-[260px]">
          <Bar v-if="trendData" :data="trendChartData" :options="trendChartOptions" />
          <div v-else class="h-full flex items-center justify-center">
            <svg class="w-8 h-8 animate-spin text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
          </div>
        </div>
      </div>

      <!-- Module distribution -->
      <div class="card p-6 animate-fade-in-up" style="animation-delay: 0.45s">
        <h2 class="font-display text-lg font-semibold text-navy-800 mb-5">操作模块分布</h2>
        <div class="h-[260px] flex items-center justify-center">
          <Doughnut v-if="moduleChartData" :data="moduleChartData" :options="doughnutOptions" />
          <div v-else class="flex items-center justify-center">
            <svg class="w-8 h-8 animate-spin text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom row -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Recent logs -->
      <div class="lg:col-span-2 card p-6 animate-fade-in-up" style="animation-delay: 0.55s">
        <div class="flex items-center justify-between mb-5">
          <h2 class="font-display text-lg font-semibold text-navy-800">最近操作记录</h2>
          <router-link to="/admin/logs" class="text-xs text-navy-400 hover:text-navy-600 transition-colors">查看全部 →</router-link>
        </div>

        <div v-if="logs.length === 0" class="text-center py-12">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-navy-50 flex items-center justify-center">
            <svg class="w-8 h-8 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
            </svg>
          </div>
          <p class="text-navy-400">暂无操作日志</p>
        </div>

        <div v-else class="space-y-1 max-h-[400px] overflow-y-auto custom-scrollbar">
          <div
            v-for="log in logs.slice(0, 10)"
            :key="log.id"
            class="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-navy-50/60 transition-colors group"
          >
            <div class="w-2 h-2 rounded-full flex-shrink-0" :class="log.status === 1 ? 'bg-emerald-400' : 'bg-red-400'"></div>
            <div class="flex-1 min-w-0">
              <p class="text-sm text-navy-700 truncate">{{ log.operation_desc || log.operation_type }}</p>
              <div class="flex items-center gap-2 mt-0.5">
                <span class="text-xs text-navy-400">{{ log.login_name || '系统' }}</span>
              </div>
            </div>
            <span class="text-[10px] px-2 py-0.5 rounded-full font-medium flex-shrink-0" :class="moduleConfig(log.module)?.badgeClass || 'bg-navy-50 text-navy-500'">
              {{ moduleConfig(log.module)?.label || log.module }}
            </span>
            <span class="text-xs text-navy-300 flex-shrink-0 w-12 text-right">{{ formatTime(log.created_at) }}</span>
          </div>
        </div>
      </div>

      <!-- Right sidebar -->
      <div class="space-y-6 animate-fade-in-up" style="animation-delay: 0.65s">
        <!-- Platform overview -->
        <div class="card p-6">
          <h2 class="font-display text-lg font-semibold text-navy-800 mb-5">平台概览</h2>
          <div class="space-y-4">
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <span class="text-sm text-navy-500">活跃用户</span>
                <span class="text-sm font-semibold text-navy-800">{{ data?.activeUsers ?? '--' }} / {{ data?.totalUsers ?? '--' }}</span>
              </div>
              <div class="flex-1 h-1.5 bg-navy-50 rounded-full overflow-hidden">
                <div class="h-full bg-gradient-to-r from-emerald-400 to-emerald-500 rounded-full transition-all duration-700" :style="{ width: activeUserPercent + '%' }"></div>
              </div>
            </div>
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <span class="text-sm text-navy-500">进行中计划</span>
                <span class="text-sm font-semibold text-navy-800">{{ data?.activePlans ?? '--' }} / {{ data?.totalPlans ?? '--' }}</span>
              </div>
              <div class="flex-1 h-1.5 bg-navy-50 rounded-full overflow-hidden">
                <div class="h-full bg-gradient-to-r from-blue-400 to-blue-500 rounded-full transition-all duration-700" :style="{ width: activePlanPercent + '%' }"></div>
              </div>
            </div>
            <div class="pt-2 border-t border-navy-100/50">
              <div class="flex items-center justify-between">
                <span class="text-sm text-navy-500">今日 Token 消耗</span>
                <span class="text-sm font-semibold text-navy-800">{{ formatTokens(data?.todayTokens) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick nav -->
        <div class="card p-6">
          <h2 class="font-display text-lg font-semibold text-navy-800 mb-4">快捷导航</h2>
          <div class="space-y-2">
            <router-link
              v-for="nav in quickNavs"
              :key="nav.path"
              :to="nav.path"
              class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-navy-600 hover:bg-navy-50 hover:text-navy-800 transition-all"
            >
              <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" :class="nav.bgClass">
                <div class="w-4 h-4" :class="nav.iconClass" v-html="nav.icon"></div>
              </div>
              <span class="flex-1">{{ nav.label }}</span>
              <svg class="w-4 h-4 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getDashboardStats, getDashboardLogs, getLogStats, getLogTrend } from '@/api/admin'
import type { AdminDashboardStats, AdminLogItem, AdminLogStats, AdminLogTrendItem } from '@/api/admin'
import dayjs from 'dayjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend } from 'chart.js'
import { Bar, Doughnut } from 'vue-chartjs'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend)

const authStore = useAuthStore()
const data = ref<AdminDashboardStats | null>(null)
const logs = ref<AdminLogItem[]>([])
const logStats = ref<AdminLogStats | null>(null)
const trendData = ref<AdminLogTrendItem[] | null>(null)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

// ======================== Stats ========================
const stats = computed(() => [
  {
    label: '用户总数',
    value: data.value?.totalUsers ?? '--',
    sub: data.value ? `${data.value.activeUsers} 活跃` : undefined,
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    bgClass: 'bg-blue-50', iconClass: 'text-blue-500', decorationClass: 'bg-blue-200', lineClass: 'bg-blue-300',
  },
  {
    label: '进行中计划',
    value: data.value?.activePlans ?? '--',
    sub: data.value ? `共 ${data.value.totalPlans} 个` : undefined,
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
    bgClass: 'bg-emerald-50', iconClass: 'text-emerald-500', decorationClass: 'bg-emerald-200', lineClass: 'bg-emerald-300',
  },
  {
    label: '知识库文档',
    value: data.value?.totalKBDocs ?? '--',
    sub: '已入库',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    bgClass: 'bg-amber-50', iconClass: 'text-amber-500', decorationClass: 'bg-amber-200', lineClass: 'bg-amber-300',
  },
  {
    label: '今日 AI 调用',
    value: data.value?.todayAICalls ?? '--',
    sub: data.value ? `${formatTokens(data.value.todayTokens)} Token` : undefined,
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    bgClass: 'bg-purple-50', iconClass: 'text-purple-500', decorationClass: 'bg-purple-200', lineClass: 'bg-purple-300',
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

// ======================== Charts ========================
const trendChartData = computed(() => {
  if (!trendData.value) return null
  return {
    labels: trendData.value.map(d => dayjs(d.date).format('MM/DD')),
    datasets: [
      {
        label: '成功',
        data: trendData.value.map(d => d.successCount),
        backgroundColor: 'rgba(16, 185, 129, 0.75)',
        borderRadius: 4,
        barPercentage: 0.7,
      },
      {
        label: '失败',
        data: trendData.value.map(d => d.failCount),
        backgroundColor: 'rgba(239, 68, 68, 0.75)',
        borderRadius: 4,
        barPercentage: 0.7,
      },
    ],
  }
})

const trendChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' as const, labels: { usePointStyle: true, padding: 16, font: { size: 12 } } },
    tooltip: { callbacks: { label: (ctx: any) => `${ctx.dataset.label}: ${ctx.parsed.y} 次` } },
  },
  scales: {
    x: { stacked: true, grid: { display: false } },
    y: { stacked: true, beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: 'rgba(0,0,0,0.04)' } },
  },
}

const chartColors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#f97316', '#6366f1', '#14b8a6']

const moduleChartData = computed(() => {
  if (!logStats.value?.moduleDistribution?.length) return null
  const dist = logStats.value.moduleDistribution
  return {
    labels: dist.map(d => moduleConfig(d.module)?.label || d.module),
    datasets: [{
      data: dist.map(d => d.count),
      backgroundColor: chartColors.slice(0, dist.length),
      borderWidth: 2,
      borderColor: '#fff',
    }],
  }
})

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '55%',
  plugins: {
    legend: { position: 'bottom' as const, labels: { padding: 12, usePointStyle: true, font: { size: 11 } } },
    tooltip: {
      callbacks: {
        label: (ctx: any) => {
          const total = ctx.dataset.data.reduce((a: number, b: number) => a + b, 0)
          const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0
          return `${ctx.label}: ${ctx.parsed} 次 (${pct}%)`
        },
      },
    },
  },
}

// ======================== Quick Nav ========================
const quickNavs = [
  { label: '用户管理', path: '/admin/users', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>', bgClass: 'bg-blue-50', iconClass: 'text-blue-500' },
  { label: '知识库', path: '/admin/kb', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>', bgClass: 'bg-amber-50', iconClass: 'text-amber-500' },
  { label: '调用分析', path: '/admin/token', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>', bgClass: 'bg-purple-50', iconClass: 'text-purple-500' },
  { label: '系统日志', path: '/admin/logs', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>', bgClass: 'bg-rose-50', iconClass: 'text-rose-500' },
]

// ======================== Module Config ========================
interface ModuleConfigItem { label: string; badgeClass: string }
const moduleMap: Record<string, ModuleConfigItem> = {
  Auth: { label: '认证', badgeClass: 'bg-rose-50 text-rose-600' },
  UserAdmin: { label: '用户管理', badgeClass: 'bg-blue-50 text-blue-600' },
  User: { label: '用户', badgeClass: 'bg-sky-50 text-sky-600' },
  KB: { label: '知识库', badgeClass: 'bg-amber-50 text-amber-600' },
  Plan: { label: '计划', badgeClass: 'bg-emerald-50 text-emerald-600' },
  KG: { label: '知识图谱', badgeClass: 'bg-indigo-50 text-indigo-600' },
  Note: { label: '笔记', badgeClass: 'bg-teal-50 text-teal-600' },
  Resource: { label: '资源', badgeClass: 'bg-orange-50 text-orange-600' },
  Flashcard: { label: '闪卡', badgeClass: 'bg-pink-50 text-pink-600' },
  File: { label: '文件', badgeClass: 'bg-gray-50 text-gray-600' },
  Ticket: { label: '票据', badgeClass: 'bg-violet-50 text-violet-600' },
  Dialogue: { label: '对话', badgeClass: 'bg-cyan-50 text-cyan-600' },
}
function moduleConfig(module: string | null): ModuleConfigItem | null {
  if (!module) return null
  return moduleMap[module] || { label: module, badgeClass: 'bg-navy-50 text-navy-500' }
}

// ======================== Helpers ========================
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

// ======================== Load ========================
async function loadDashboard() {
  const [statsRes, logsRes, logStatsRes, trendRes] = await Promise.all([
    getDashboardStats().catch(() => null),
    getDashboardLogs().catch(() => null),
    getLogStats().catch(() => null),
    getLogTrend().catch(() => null),
  ])
  if (statsRes) data.value = statsRes.data
  if (logsRes) logs.value = logsRes.data
  if (logStatsRes) logStats.value = logStatsRes.data
  if (trendRes) trendData.value = trendRes.data
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
