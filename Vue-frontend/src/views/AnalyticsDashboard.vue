<template>
  <div class="space-y-6 animate-fade-in-up">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="section-title">学习分析</h1>
        <p class="text-sm text-navy-400 mt-1">汇总你的学习进度、答题表现和知识掌握情况</p>
      </div>
      <button class="btn-secondary text-sm" :disabled="loading" @click="loadAnalytics">
        {{ loading ? '刷新中...' : '刷新数据' }}
      </button>
    </div>

    <div v-if="loading" class="flex items-center justify-center h-40">
      <svg class="w-8 h-8 text-navy-300 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" class="opacity-25" />
        <path d="M4 12a8 8 0 018-8" class="opacity-75" stroke-linecap="round" />
      </svg>
    </div>

    <template v-else>
      <div v-if="loadError" class="card p-5 border-red-100 bg-red-50/60">
        <p class="text-sm font-medium text-red-600">学习分析加载失败</p>
        <p class="text-sm text-red-500 mt-1">{{ loadError }}</p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div v-for="stat in overviewStats" :key="stat.label" class="stat-card">
          <span class="stat-label">{{ stat.label }}</span>
          <span class="stat-value">{{ stat.value }}</span>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <section class="lg:col-span-2 card p-6">
          <div class="flex items-center justify-between mb-5">
            <h2 class="font-display text-lg font-semibold text-navy-800">答题趋势</h2>
            <span class="text-xs px-2.5 py-1 rounded-full bg-sage-100 text-sage-700">
              {{ trendLabel }}
            </span>
          </div>
          <div v-if="dailyAccuracy.length" class="flex items-end gap-2 h-44">
            <div
              v-for="day in dailyAccuracy"
              :key="day.date"
              class="flex-1 min-w-0 flex flex-col items-center justify-end gap-2"
              :title="`${day.date}: ${day.accuracy || 0}%`"
            >
              <div class="w-full rounded-t-md bg-gradient-to-t from-navy-500 to-sage-400 transition-all" :style="{ height: `${Math.max(4, day.accuracy || 0)}%` }"></div>
              <span class="text-[10px] text-navy-300 truncate w-full text-center">{{ shortDate(day.date) }}</span>
            </div>
          </div>
          <p v-else class="text-sm text-navy-300 text-center py-16">暂无答题趋势数据</p>
        </section>

        <section class="card p-6">
          <h2 class="font-display text-lg font-semibold text-navy-800 mb-5">知识掌握</h2>
          <div class="space-y-5">
            <div>
              <p class="text-sm font-medium text-navy-600 mb-2">已掌握</p>
              <div class="flex flex-wrap gap-2">
                <span v-for="item in mastered" :key="item" class="px-2.5 py-1 rounded-full bg-sage-100 text-sage-700 text-xs">{{ item }}</span>
                <span v-if="!mastered.length" class="text-sm text-navy-300">暂无数据</span>
              </div>
            </div>
            <div>
              <p class="text-sm font-medium text-navy-600 mb-2">薄弱点</p>
              <div class="flex flex-wrap gap-2">
                <span v-for="item in weakAreas" :key="item" class="px-2.5 py-1 rounded-full bg-amber-100 text-amber-700 text-xs">{{ item }}</span>
                <span v-if="!weakAreas.length" class="text-sm text-navy-300">暂无数据</span>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section class="card p-6">
          <h2 class="font-display text-lg font-semibold text-navy-800 mb-5">按题型表现</h2>
          <div v-if="questionTypes.length" class="space-y-4">
            <div v-for="item in questionTypes" :key="item.type">
              <div class="flex justify-between text-sm mb-1.5">
                <span class="font-medium text-navy-700">{{ item.type }}</span>
                <span class="text-navy-400">{{ item.correct }}/{{ item.total }} · {{ item.accuracy }}%</span>
              </div>
              <div class="h-2 bg-navy-100 rounded-full overflow-hidden">
                <div class="h-full bg-navy-500 rounded-full" :style="{ width: `${Math.min(100, item.accuracy || 0)}%` }"></div>
              </div>
            </div>
          </div>
          <p v-else class="text-sm text-navy-300 text-center py-10">暂无题型数据</p>
        </section>

        <section class="card p-6">
          <h2 class="font-display text-lg font-semibold text-navy-800 mb-5">按难度表现</h2>
          <div v-if="difficulties.length" class="space-y-4">
            <div v-for="item in difficulties" :key="item.difficulty">
              <div class="flex justify-between text-sm mb-1.5">
                <span class="font-medium text-navy-700">难度 {{ item.difficulty }}</span>
                <span class="text-navy-400">{{ item.correct }}/{{ item.total }} · {{ item.accuracy }}%</span>
              </div>
              <div class="h-2 bg-navy-100 rounded-full overflow-hidden">
                <div class="h-full bg-sage-500 rounded-full" :style="{ width: `${Math.min(100, item.accuracy || 0)}%` }"></div>
              </div>
            </div>
          </div>
          <p v-else class="text-sm text-navy-300 text-center py-10">暂无难度数据</p>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getAnalyticsData, type AnalyticsData } from '@/api/stats'

const loading = ref(true)
const loadError = ref('')
const analytics = ref<AnalyticsData | null>(null)

const overview = computed(() => analytics.value?.overview ?? {})
const quizAnalysis = computed(() => analytics.value?.quizAnalysis ?? {})
const knowledgeMastery = computed(() => analytics.value?.knowledgeMastery ?? {})

const overviewStats = computed(() => [
  { label: '学习计划', value: overview.value.totalPlans ?? 0 },
  { label: '学习资源', value: overview.value.totalResources ?? 0 },
  { label: '学习时长', value: `${overview.value.totalStudyHours ?? 0}h` },
  { label: '答题正确率', value: `${overview.value.quizAccuracy ?? 0}%` },
])

const questionTypes = computed(() => quizAnalysis.value.byQuestionType ?? [])
const difficulties = computed(() => quizAnalysis.value.byDifficulty ?? [])
const dailyAccuracy = computed(() => (quizAnalysis.value.dailyAccuracy ?? []).slice(-14))
const mastered = computed(() => knowledgeMastery.value.mastered ?? [])
const weakAreas = computed(() => knowledgeMastery.value.weakAreas ?? [])

const trendLabel = computed(() => {
  const trend = quizAnalysis.value.trend
  if (!trend?.direction) return '趋势稳定'
  const change = trend.changePercent ?? 0
  if (trend.direction === 'up') return `提升 ${change}%`
  if (trend.direction === 'down') return `下降 ${change}%`
  return '趋势稳定'
})

function shortDate(date: string) {
  if (!date) return ''
  return date.slice(5).replace('-', '/')
}

async function loadAnalytics() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await getAnalyticsData()
    analytics.value = res.data || {}
  } catch (error: any) {
    loadError.value = error?.message || '无法获取学习分析数据'
    analytics.value = {}
  } finally {
    loading.value = false
  }
}

onMounted(loadAnalytics)
</script>
