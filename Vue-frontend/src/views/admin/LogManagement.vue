<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6 flex-wrap gap-3">
      <h1 class="section-title">系统日志</h1>
      <div class="flex items-center gap-3 flex-wrap">
        <!-- View Toggle -->
        <div class="flex items-center bg-navy-100 rounded-lg p-0.5">
          <button
            class="px-3.5 py-1.5 text-sm rounded-md transition-all font-medium"
            :class="viewMode === 'chart' ? 'bg-white text-navy-800 shadow-sm' : 'text-navy-500 hover:text-navy-700'"
            @click="viewMode = 'chart'"
          >
            <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
            图表
          </button>
          <button
            class="px-3.5 py-1.5 text-sm rounded-md transition-all font-medium"
            :class="viewMode === 'list' ? 'bg-white text-navy-800 shadow-sm' : 'text-navy-500 hover:text-navy-700'"
            @click="switchToList"
          >
            <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
            列表
          </button>
        </div>

        <!-- Date Range -->
        <div class="flex items-center gap-2 bg-navy-50 rounded-lg px-3 py-2">
          <svg class="w-4 h-4 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <input v-model="dateRange.start" type="date" class="bg-transparent text-sm text-navy-700 outline-none" />
          <span class="text-navy-300">-</span>
          <input v-model="dateRange.end" type="date" class="bg-transparent text-sm text-navy-700 outline-none" />
        </div>

        <button class="btn-primary text-sm" @click="handleSearch" :disabled="loading">
          <svg v-if="loading" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
          <span v-else>查询</span>
        </button>

        <!-- Presets -->
        <div class="flex bg-navy-100/60 rounded-lg p-0.5 gap-0.5">
          <button v-for="preset in datePresets" :key="preset.label"
            class="px-3.5 py-1.5 text-xs rounded-md transition-all font-medium whitespace-nowrap"
            :class="activePreset === preset.label ? 'bg-navy-700 text-white shadow-sm' : 'text-navy-500 hover:text-navy-700 hover:bg-navy-50'"
            @click="applyPreset(preset)">
            {{ preset.label }}
          </button>
        </div>

        <!-- Refresh -->
        <button class="btn-ghost text-sm flex items-center gap-1.5" @click="refreshAll" :disabled="loading">
          <svg class="w-4 h-4" :class="{ 'animate-spin': loading }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
          刷新
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading && !statsData" class="flex items-center justify-center py-20">
      <svg class="w-8 h-8 animate-spin text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
    </div>

    <template v-else>
      <!-- ======================== CHART VIEW ======================== -->
      <template v-if="viewMode === 'chart'">
        <!-- Summary Cards -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
          <div v-for="(stat, i) in summaryStats" :key="stat.label"
            class="stat-card animate-fade-in-up rounded-2xl"
            :style="{ animationDelay: `${i * 0.08}s` }">
            <div class="flex items-center gap-3 mb-2">
              <div class="w-9 h-9 rounded-xl flex items-center justify-center" :class="stat.bgClass">
                <div class="w-5 h-5" :class="stat.iconClass" v-html="stat.icon"></div>
              </div>
              <span class="stat-label">{{ stat.label }}</span>
            </div>
            <span class="stat-value">{{ stat.value }}</span>
          </div>
        </div>

        <!-- Charts Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-5">
          <!-- Daily Trend -->
          <div class="card rounded-2xl p-6 lg:col-span-2">
            <h2 class="font-display text-base font-semibold text-navy-800 mb-4">每日日志趋势</h2>
            <div class="h-[280px]">
              <Bar v-if="dailyTrendData" :data="dailyTrendData" :options="stackedBarOptions" />
              <div v-else class="h-full flex items-center justify-center">
                <svg class="w-8 h-8 animate-spin text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
              </div>
            </div>
          </div>

          <!-- Module Distribution -->
          <div class="card rounded-2xl p-6">
            <h2 class="font-display text-base font-semibold text-navy-800 mb-4">模块分布</h2>
            <div class="h-[280px] flex items-center justify-center">
              <Doughnut v-if="moduleChartData" :data="moduleChartData" :options="doughnutOptions" />
              <div v-else class="flex items-center justify-center">
                <svg class="w-8 h-8 animate-spin text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
              </div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <!-- Hourly Distribution -->
          <div class="card rounded-2xl p-6">
            <h2 class="font-display text-base font-semibold text-navy-800 mb-4">小时分布（近7天）</h2>
            <div class="h-[240px]">
              <Bar v-if="hourlyData" :data="hourlyChartData" :options="hourlyBarOptions" />
              <div v-else class="h-full flex items-center justify-center">
                <svg class="w-8 h-8 animate-spin text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
              </div>
            </div>
          </div>

          <!-- Top Modules -->
          <div class="card rounded-2xl p-6">
            <h2 class="font-display text-base font-semibold text-navy-800 mb-4">模块操作排行</h2>
            <div class="h-[240px]">
              <Bar v-if="moduleRankData" :data="moduleRankData" :options="rankBarOptions" />
              <div v-else class="h-full flex items-center justify-center">
                <svg class="w-8 h-8 animate-spin text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- ======================== LIST VIEW ======================== -->
      <template v-else>
        <!-- Summary Cards -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
          <div v-for="(stat, i) in summaryStats" :key="stat.label"
            class="stat-card animate-fade-in-up rounded-2xl"
            :style="{ animationDelay: `${i * 0.08}s` }">
            <div class="flex items-center gap-3 mb-2">
              <div class="w-9 h-9 rounded-xl flex items-center justify-center" :class="stat.bgClass">
                <div class="w-5 h-5" :class="stat.iconClass" v-html="stat.icon"></div>
              </div>
              <span class="stat-label">{{ stat.label }}</span>
            </div>
            <span class="stat-value">{{ stat.value }}</span>
          </div>
        </div>

        <!-- Filter Bar -->
        <div class="card rounded-2xl p-4 mb-4">
          <div class="flex flex-wrap items-center gap-3">
            <!-- Keyword -->
            <div class="relative flex-1 min-w-[200px]">
              <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input v-model="filters.keyword" type="text" class="input-field pl-10" placeholder="搜索操作描述、类型、用户名..." @input="debouncedSearch" />
            </div>

            <!-- Module Dropdown -->
            <div class="custom-dropdown" v-click-outside="() => moduleDropdownOpen = false">
              <button class="dropdown-trigger" :class="{ 'has-value': filters.module }" @click="moduleDropdownOpen = !moduleDropdownOpen">
                <svg class="w-4 h-4 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
                <span>{{ moduleLabel }}</span>
                <svg class="w-4 h-4 text-navy-300 transition-transform" :class="{ 'rotate-180': moduleDropdownOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
              </button>
              <transition name="dropdown">
                <div v-if="moduleDropdownOpen" class="dropdown-menu">
                  <button v-for="opt in moduleOptions" :key="opt.value"
                    class="dropdown-item" :class="{ 'active': filters.module === opt.value }"
                    @click="filters.module = opt.value; moduleDropdownOpen = false; loadLogs(1)">
                    <span>{{ opt.label }}</span>
                    <svg v-if="filters.module === opt.value" class="w-4 h-4 ml-auto text-navy-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </button>
                </div>
              </transition>
            </div>

            <!-- Status Dropdown -->
            <div class="custom-dropdown" v-click-outside="() => statusDropdownOpen = false">
              <button class="dropdown-trigger" :class="{ 'has-value': filters.status !== null }" @click="statusDropdownOpen = !statusDropdownOpen">
                <svg class="w-4 h-4 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                <span>{{ statusLabel }}</span>
                <svg class="w-4 h-4 text-navy-300 transition-transform" :class="{ 'rotate-180': statusDropdownOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
              </button>
              <transition name="dropdown">
                <div v-if="statusDropdownOpen" class="dropdown-menu">
                  <button v-for="opt in statusOptions" :key="String(opt.value)"
                    class="dropdown-item" :class="{ 'active': filters.status === opt.value }"
                    @click="filters.status = opt.value; statusDropdownOpen = false; loadLogs(1)">
                    <span v-if="opt.color" class="w-2 h-2 rounded-full" :class="opt.color" />
                    <span>{{ opt.label }}</span>
                    <svg v-if="filters.status === opt.value" class="w-4 h-4 ml-auto text-navy-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </button>
                </div>
              </transition>
            </div>

            <button class="btn-ghost text-sm" @click="resetFilters">
              <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
              重置
            </button>
          </div>
        </div>

        <!-- Table -->
        <div class="card rounded-2xl overflow-hidden">
          <div v-if="tableLoading" class="p-12 text-center">
            <div class="inline-block w-8 h-8 border-2 border-navy-200 border-t-navy-600 rounded-full animate-spin" />
            <p class="text-sm text-navy-400 mt-3">加载中...</p>
          </div>

          <template v-else-if="logs.length > 0">
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead>
                  <tr class="border-b border-navy-100 bg-navy-50/50">
                    <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">ID</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">状态</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">模块</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">操作描述</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">操作者</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">IP</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">时间</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in logs" :key="row.id"
                    class="border-b border-navy-50 hover:bg-navy-50/30 transition-colors animate-row"
                    :style="{ animationDelay: `${idx * 30}ms` }">
                    <td class="px-5 py-3.5 text-sm text-navy-400 font-mono">{{ row.id }}</td>
                    <td class="px-5 py-3.5">
                      <span class="badge inline-flex items-center gap-1.5"
                        :class="row.status === 1 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'">
                        <span class="w-1.5 h-1.5 rounded-full" :class="row.status === 1 ? 'bg-emerald-500' : 'bg-red-500'" />
                        {{ row.status === 1 ? '成功' : '失败' }}
                      </span>
                    </td>
                    <td class="px-5 py-3.5">
                      <span class="badge" :class="moduleConfig(row.module)?.badgeClass || 'bg-navy-50 text-navy-600 border border-navy-200'">
                        {{ moduleConfig(row.module)?.label || row.module || '--' }}
                      </span>
                    </td>
                    <td class="px-5 py-3.5">
                      <p class="text-sm text-navy-700 max-w-xs truncate" :title="row.operation_desc">{{ row.operation_desc || row.operation_type }}</p>
                      <p v-if="row.status === 0 && row.error_msg" class="text-xs text-red-400 mt-0.5 max-w-xs truncate" :title="row.error_msg">{{ row.error_msg }}</p>
                    </td>
                    <td class="px-5 py-3.5 text-sm text-navy-600">{{ row.login_name || '系统' }}</td>
                    <td class="px-5 py-3.5 text-sm text-navy-400 font-mono text-xs">{{ row.user_ip || '--' }}</td>
                    <td class="px-5 py-3.5 text-sm text-navy-400">{{ formatTime(row.created_at) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Pagination -->
            <div class="px-5 py-4 border-t border-navy-100 flex items-center justify-between">
              <p class="text-sm text-navy-400">
                共 <span class="font-medium text-navy-600">{{ tableTotal }}</span> 条记录
              </p>
              <div class="flex items-center gap-1">
                <button class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
                  :class="tablePage > 1 ? 'text-navy-600 hover:bg-navy-50' : 'text-navy-300 cursor-not-allowed'"
                  :disabled="tablePage <= 1" @click="loadLogs(tablePage - 1)">上一页</button>
                <button v-for="p in visiblePages" :key="p"
                  class="w-9 h-9 rounded-lg text-sm font-medium transition-colors"
                  :class="p === tablePage ? 'bg-navy-600 text-white shadow-sm' : 'text-navy-600 hover:bg-navy-50'"
                  @click="loadLogs(p)">{{ p }}</button>
                <button class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
                  :class="tablePage < tableTotalPages ? 'text-navy-600 hover:bg-navy-50' : 'text-navy-300 cursor-not-allowed'"
                  :disabled="tablePage >= tableTotalPages" @click="loadLogs(tablePage + 1)">下一页</button>
              </div>
            </div>
          </template>

          <div v-else class="p-16 text-center">
            <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-navy-50 flex items-center justify-center">
              <svg class="w-8 h-8 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
            </div>
            <p class="text-navy-500 font-medium">暂无日志记录</p>
            <p class="text-sm text-navy-400 mt-1">当前筛选条件下没有日志数据</p>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import dayjs from 'dayjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend, Filler } from 'chart.js'
import { Bar, Doughnut } from 'vue-chartjs'
import { getLogPage, getLogStats, getLogTrend, getLogHourly } from '@/api/admin'
import type { AdminLogItem, AdminLogStats, AdminLogQuery, AdminLogTrendItem, AdminLogHourlyItem } from '@/api/admin'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend, Filler)

// Click-outside directive
const vClickOutside = {
  mounted(el: HTMLElement, binding: any) {
    el._clickOutside = (e: MouseEvent) => { if (!el.contains(e.target as Node)) binding.value(e) }
    document.addEventListener('click', el._clickOutside)
  },
  unmounted(el: HTMLElement) { document.removeEventListener('click', el._clickOutside) },
}

// ======================== State ========================
const loading = ref(false)
const viewMode = ref<'chart' | 'list'>('chart')
const activePreset = ref('近7天')
const statsData = ref<AdminLogStats | null>(null)
const trendData = ref<AdminLogTrendItem[] | null>(null)
const hourlyData = ref<AdminLogHourlyItem[] | null>(null)

const dateRange = ref({
  start: dayjs().subtract(6, 'day').format('YYYY-MM-DD'),
  end: dayjs().format('YYYY-MM-DD'),
})

const datePresets = [
  { label: '今天', days: 0 },
  { label: '近7天', days: 6 },
  { label: '近30天', days: 29 },
  { label: '全部', days: -1 },
]

// Table state
const logs = ref<AdminLogItem[]>([])
const tableTotal = ref(0)
const tablePage = ref(1)
const tableSize = ref(20)
const tableLoading = ref(false)

// Filters
const filters = ref<AdminLogQuery>({ keyword: '', module: '', status: null })
const moduleDropdownOpen = ref(false)
const statusDropdownOpen = ref(false)

// ======================== Module Config ========================
interface ModuleConfigItem { label: string; badgeClass: string }
const moduleMap: Record<string, ModuleConfigItem> = {
  Auth: { label: '认证', badgeClass: 'bg-rose-50 text-rose-700 border border-rose-200' },
  UserAdmin: { label: '用户管理', badgeClass: 'bg-blue-50 text-blue-700 border border-blue-200' },
  User: { label: '用户', badgeClass: 'bg-sky-50 text-sky-700 border border-sky-200' },
  KB: { label: '知识库', badgeClass: 'bg-amber-50 text-amber-700 border border-amber-200' },
  Plan: { label: '计划', badgeClass: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
  KG: { label: '知识图谱', badgeClass: 'bg-indigo-50 text-indigo-700 border border-indigo-200' },
  Note: { label: '笔记', badgeClass: 'bg-teal-50 text-teal-700 border border-teal-200' },
  Resource: { label: '资源', badgeClass: 'bg-orange-50 text-orange-700 border border-orange-200' },
  Flashcard: { label: '闪卡', badgeClass: 'bg-pink-50 text-pink-700 border border-pink-200' },
  File: { label: '文件', badgeClass: 'bg-gray-50 text-gray-700 border border-gray-200' },
  Ticket: { label: '票据', badgeClass: 'bg-violet-50 text-violet-700 border border-violet-200' },
  Dialogue: { label: '对话', badgeClass: 'bg-cyan-50 text-cyan-700 border border-cyan-200' },
}
function moduleConfig(module: string | null): ModuleConfigItem | null {
  if (!module) return null
  return moduleMap[module] || { label: module, badgeClass: 'bg-navy-50 text-navy-600 border border-navy-200' }
}

// ======================== Filter Options ========================
const moduleOptions = computed(() => {
  const dist = statsData.value?.moduleDistribution || []
  return [
    { value: '', label: '全部模块' },
    ...dist.map(d => ({ value: d.module, label: moduleConfig(d.module)?.label || d.module })),
  ]
})
const statusOptions = [
  { value: null, label: '全部状态', color: '' },
  { value: 1, label: '成功', color: 'bg-emerald-500' },
  { value: 0, label: '失败', color: 'bg-red-500' },
]
const moduleLabel = computed(() => moduleOptions.value.find(o => o.value === filters.value.module)?.label || '全部模块')
const statusLabel = computed(() => statusOptions.find(o => o.value === filters.value.status)?.label || '全部状态')

function resetFilters() {
  filters.value = { keyword: '', module: '', status: null }
  loadLogs(1)
}

// ======================== Summary Stats ========================
const summaryStats = computed(() => {
  const s = statsData.value
  return [
    { label: '日志总数', value: s?.total ?? '--', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>', bgClass: 'bg-blue-50', iconClass: 'text-blue-500' },
    { label: '今日新增', value: s?.todayCount ?? '--', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>', bgClass: 'bg-emerald-50', iconClass: 'text-emerald-500' },
    { label: '失败操作', value: s?.failCount ?? '--', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>', bgClass: 'bg-red-50', iconClass: 'text-red-500' },
    { label: '涉及模块', value: s?.moduleDistribution?.length ?? '--', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>', bgClass: 'bg-purple-50', iconClass: 'text-purple-500' },
  ]
})

// ======================== Charts ========================
const chartColors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#f97316', '#6366f1', '#14b8a6', '#64748b', '#a855f7']

const dailyTrendData = computed(() => {
  if (!trendData.value) return null
  return {
    labels: trendData.value.map(d => dayjs(d.date).format('MM/DD')),
    datasets: [
      { label: '成功', data: trendData.value.map(d => d.successCount), backgroundColor: 'rgba(16,185,129,0.7)', borderRadius: 4 },
      { label: '失败', data: trendData.value.map(d => d.failCount), backgroundColor: 'rgba(239,68,68,0.7)', borderRadius: 4 },
    ],
  }
})

const stackedBarOptions = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { position: 'top' as const, labels: { usePointStyle: true, padding: 16, font: { size: 12 } } }, tooltip: { callbacks: { label: (ctx: any) => `${ctx.dataset.label}: ${ctx.parsed.y} 次` } } },
  scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: 'rgba(0,0,0,0.04)' } } },
}

const moduleChartData = computed(() => {
  if (!statsData.value?.moduleDistribution?.length) return null
  const dist = statsData.value.moduleDistribution
  return {
    labels: dist.map(d => moduleConfig(d.module)?.label || d.module),
    datasets: [{ data: dist.map(d => d.count), backgroundColor: chartColors.slice(0, dist.length), borderWidth: 2, borderColor: '#fff' }],
  }
})

const doughnutOptions = {
  responsive: true, maintainAspectRatio: false, cutout: '55%',
  plugins: { legend: { position: 'bottom' as const, labels: { padding: 12, usePointStyle: true, font: { size: 11 } } }, tooltip: { callbacks: { label: (ctx: any) => { const t = ctx.dataset.data.reduce((a: number, b: number) => a + b, 0); return `${ctx.label}: ${ctx.parsed} 次 (${t > 0 ? ((ctx.parsed / t) * 100).toFixed(1) : 0}%)` } } } },
}

const hourlyChartData = computed(() => {
  if (!hourlyData.value) return null
  return {
    labels: hourlyData.value.map(d => `${String(d.hour).padStart(2, '0')}:00`),
    datasets: [
      { label: '成功', data: hourlyData.value.map(d => d.successCount), backgroundColor: 'rgba(16,185,129,0.6)', borderRadius: 3, maxBarThickness: 16 },
      { label: '失败', data: hourlyData.value.map(d => d.failCount), backgroundColor: 'rgba(239,68,68,0.6)', borderRadius: 3, maxBarThickness: 16 },
    ],
  }
})

const hourlyBarOptions = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { position: 'top' as const, labels: { usePointStyle: true, padding: 12, font: { size: 11 } } } },
  scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: 'rgba(0,0,0,0.04)' } } },
}

const moduleRankData = computed(() => {
  if (!statsData.value?.moduleDistribution?.length) return null
  const dist = [...statsData.value.moduleDistribution].sort((a, b) => b.count - a.count).slice(0, 8)
  return {
    labels: dist.map(d => moduleConfig(d.module)?.label || d.module),
    datasets: [{ label: '操作次数', data: dist.map(d => d.count), backgroundColor: dist.map((_, i) => chartColors[i % chartColors.length]), borderRadius: 4 }],
  }
})

const rankBarOptions = {
  responsive: true, maintainAspectRatio: false, indexAxis: 'y' as const,
  plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx: any) => `操作次数: ${ctx.parsed.x}` } } },
  scales: { x: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: 'rgba(0,0,0,0.04)' } }, y: { grid: { display: false } } },
}

// ======================== Debounce ========================
let debounceTimer: ReturnType<typeof setTimeout> | null = null
function debouncedSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => loadLogs(1), 400)
}

// ======================== Date Presets ========================
let skipPresetClear = false
function applyPreset(preset: { label: string; days: number }) {
  skipPresetClear = true
  activePreset.value = preset.label
  if (preset.days === -1) { dateRange.value.start = ''; dateRange.value.end = '' }
  else if (preset.days === 0) { dateRange.value.start = dayjs().format('YYYY-MM-DD'); dateRange.value.end = dayjs().format('YYYY-MM-DD') }
  else { dateRange.value.start = dayjs().subtract(preset.days, 'day').format('YYYY-MM-DD'); dateRange.value.end = dayjs().format('YYYY-MM-DD') }
  handleSearch()
}

function handleSearch() {
  loadStats()
  if (viewMode.value === 'list') loadLogs(1)
}

function switchToList() {
  viewMode.value = 'list'
  if (logs.value.length === 0) loadLogs(1)
}

function refreshAll() {
  loadStats()
  if (viewMode.value === 'list') loadLogs(tablePage.value)
}

watch(dateRange, () => {
  if (skipPresetClear) { skipPresetClear = false; return }
  activePreset.value = ''
}, { deep: true })

// ======================== Fetch ========================
async function loadStats() {
  loading.value = true
  try {
    const [statsRes, trendRes, hourlyRes] = await Promise.all([
      getLogStats().catch(() => null),
      getLogTrend().catch(() => null),
      getLogHourly().catch(() => null),
    ])
    if (statsRes) statsData.value = statsRes.data
    if (trendRes) trendData.value = trendRes.data
    if (hourlyRes) hourlyData.value = hourlyRes.data
  } finally {
    loading.value = false
  }
}

async function loadLogs(page: number) {
  if (page < 1 || (tableTotalPages.value > 1 && page > tableTotalPages.value)) return
  tableLoading.value = true
  tablePage.value = page
  try {
    const params: AdminLogQuery = {
      page, size: tableSize.value,
      module: filters.value.module || undefined,
      status: filters.value.status ?? undefined,
      keyword: filters.value.keyword || undefined,
      startDate: dateRange.value.start ? dateRange.value.start + ' 00:00:00' : undefined,
      endDate: dateRange.value.end ? dateRange.value.end + ' 23:59:59' : undefined,
    }
    const res = await getLogPage(params) as any
    const d = res?.data ?? res
    logs.value = d?.records ?? []
    tableTotal.value = d?.total ?? 0
  } catch (e) {
    console.error('加载日志失败:', e)
    logs.value = []
    tableTotal.value = 0
  } finally {
    tableLoading.value = false
  }
}

const tableTotalPages = computed(() => Math.max(1, Math.ceil(tableTotal.value / tableSize.value)))
const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, tablePage.value - 2)
  const end = Math.min(tableTotalPages.value, tablePage.value + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

// ======================== Helpers ========================
function formatTime(t: string | null | undefined): string {
  if (!t) return '--'
  return dayjs(t).format('MM-DD HH:mm:ss')
}

// ======================== Init ========================
onMounted(() => {
  loadStats()
  loadLogs(1)
})
</script>

<style scoped>
.animate-row {
  animation: fadeInRow 0.35s ease-out forwards;
  opacity: 0;
}
@keyframes fadeInRow {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Custom Dropdown */
.custom-dropdown { position: relative; }
.dropdown-trigger {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px; min-width: 130px;
  background: white; border: 1.5px dashed #c8d6e0; border-radius: 10px;
  font-size: 0.875rem; color: #64748b; cursor: pointer; transition: all 0.2s ease; font-family: inherit;
}
.dropdown-trigger:hover { border-color: #94a3b8; background: #f8fafc; }
.dropdown-trigger.has-value { color: #1e293b; border-color: #94a3b8; border-style: solid; }
.dropdown-menu {
  position: absolute; top: calc(100% + 6px); left: 0; min-width: 100%;
  background: white; border: 1.5px solid #e2e8f0; border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04);
  padding: 4px; z-index: 50; overflow: hidden;
}
.dropdown-item {
  display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 12px;
  border-radius: 8px; font-size: 0.875rem; color: #475569; background: transparent;
  border: none; cursor: pointer; transition: all 0.15s ease; text-align: left; font-family: inherit;
}
.dropdown-item:hover { background: #f1f5f9; color: #1e293b; }
.dropdown-item.active { background: #f1f5f9; color: #1e293b; font-weight: 500; }
.dropdown-enter-active { transition: all 0.2s ease-out; }
.dropdown-leave-active { transition: all 0.15s ease-in; }
.dropdown-enter-from { opacity: 0; transform: translateY(-6px) scale(0.98); }
.dropdown-leave-to { opacity: 0; transform: translateY(-4px) scale(0.98); }
</style>
