<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6 flex-wrap gap-3">
      <h1 class="section-title">学习分析仪表盘</h1>
      <div class="flex items-center gap-3">
        <!-- Time Range -->
        <div class="flex bg-navy-100/60 rounded-lg p-0.5 gap-0.5">
          <button v-for="preset in timePresets" :key="preset.label"
            class="px-3.5 py-1.5 text-xs rounded-md transition-all font-medium whitespace-nowrap"
            :class="activePreset === preset.label ? 'bg-navy-700 text-white shadow-sm' : 'text-navy-500 hover:text-navy-700 hover:bg-navy-50'"
            @click="applyPreset(preset)">
            {{ preset.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <svg class="w-8 h-8 animate-spin text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 11-6.219-8.56" />
      </svg>
    </div>

    <template v-else-if="analyticsData">
      <!-- Summary Cards -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
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
          <span v-if="stat.sub" class="text-xs text-navy-400 mt-1">{{ stat.sub }}</span>
        </div>
      </div>

      <!-- Week Comparison -->
      <WeekComparison :week-data="analyticsData.weekComparison" class="mb-6" />

      <!-- Tabs -->
      <div class="flex items-center gap-1 mb-6 border-b border-navy-100 pb-px overflow-x-auto">
        <button v-for="tab in tabs" :key="tab.key"
          class="px-4 py-2.5 text-sm font-medium transition-all whitespace-nowrap border-b-2 -mb-px"
          :class="activeTab === tab.key
            ? 'text-navy-800 border-navy-800'
            : 'text-navy-400 border-transparent hover:text-navy-600 hover:border-navy-200'"
          @click="activeTab = tab.key">
          {{ tab.label }}
        </button>
      </div>

      <!-- Tab Content -->
      <div :key="activeTab" class="animate-fade-in-up">
        <component :is="currentTabComponent" :data="analyticsData" />
      </div>
    </template>

    <!-- Empty State -->
    <div v-else class="flex flex-col items-center justify-center py-20">
      <div class="w-16 h-16 rounded-2xl bg-navy-50 flex items-center justify-center mb-4">
        <svg class="w-8 h-8 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
      </div>
      <p class="text-navy-500 font-medium">暂无分析数据</p>
      <p class="text-sm text-navy-400 mt-1">开始学习后，这里将展示你的学习分析</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import { getAnalyticsData, type AnalyticsData } from '@/api/analytics'
import { tracker } from '@/utils/tracker'
import WeekComparison from '@/components/analytics/WeekComparison.vue'

// Async tab components
const TabOverview = defineAsyncComponent(() => import('@/components/analytics/TabOverview.vue'))
const TabAI = defineAsyncComponent(() => import('@/components/analytics/TabAI.vue'))
const TabReview = defineAsyncComponent(() => import('@/components/analytics/TabReview.vue'))

const loading = ref(false)
const analyticsData = ref<AnalyticsData | null>(null)
const activeTab = ref('overview')
const activePreset = ref('全部')

const timePresets = [
  { label: '近7天', days: 7 },
  { label: '近30天', days: 30 },
  { label: '全部', days: 365 },
]

function applyPreset(preset: { label: string; days: number }) {
  activePreset.value = preset.label
  fetchData(preset.days)
}

const tabs = [
  { key: 'overview', label: '学习概览' },
  { key: 'ai', label: '对话分布' },
  { key: 'review', label: '复习助手' },
]

const tabComponentMap: Record<string, any> = {
  overview: TabOverview,
  ai: TabAI,
  review: TabReview,
}

const currentTabComponent = computed(() => tabComponentMap[activeTab.value])

const summaryStats = computed(() => {
  const data = analyticsData.value
  if (!data) return []

  const overview = data.overview || {}
  const quiz = data.quizAnalysis || {}
  const heatmap = data.heatmap || {}
  const flashcard = data.flashcardStats || {}

  return [
    {
      label: '今日学习',
      value: formatDuration(overview.todayDurationSeconds || 0),
      sub: `累计 ${formatHours(overview.totalDurationSeconds || 0)}`,
      bgClass: 'bg-blue-50',
      iconClass: 'text-blue-500',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
    },
    {
      label: '答题正确率',
      value: `${overview.quizAccuracy || 0}%`,
      sub: quiz.recentTrend?.direction === 'up' ? `↑ ${quiz.recentTrend.changePercent}%` :
        quiz.recentTrend?.direction === 'down' ? `↓ ${Math.abs(quiz.recentTrend.changePercent)}%` : '持平',
      bgClass: 'bg-emerald-50',
      iconClass: 'text-emerald-500',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    },
    {
      label: '学习连续',
      value: `${heatmap.currentStreak || 0}天`,
      sub: `最长 ${heatmap.longestStreak || 0} 天`,
      bgClass: 'bg-amber-50',
      iconClass: 'text-amber-500',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
    },
    {
      label: '闪卡待复习',
      value: `${flashcard.dueToday || 0}张`,
      sub: `共 ${flashcard.totalCards || 0} 张`,
      bgClass: 'bg-purple-50',
      iconClass: 'text-purple-500',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
    },
    {
      label: '资源完成率',
      value: `${overview.resourceCompletionRate || 0}%`,
      sub: `${overview.completedResources || 0} / ${overview.totalResources || 0} 个`,
      bgClass: 'bg-rose-50',
      iconClass: 'text-rose-500',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    },
  ]
})

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return mins > 0 ? `${hours}小时${mins}分` : `${hours}小时`
}

function formatHours(seconds: number): string {
  return `${(seconds / 3600).toFixed(1)}小时`
}

async function fetchData(days?: number) {
  loading.value = true
  try {
    const res = await getAnalyticsData(days)
    analyticsData.value = res.data || res
  } catch (e) {
    console.error('Failed to fetch analytics data:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()

  // 追踪页面浏览
  tracker.trackPageView({ page: 'analytics' })
})
</script>
