<template>
  <div class="space-y-6">
    <!-- 智能建议卡片 -->
    <div class="card rounded-2xl p-6 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-100">
      <div class="flex items-start justify-between">
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center">
              <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h3 class="font-semibold text-emerald-800">智能复习建议</h3>
          </div>
          <p class="text-sm text-emerald-700 leading-relaxed">{{ smartAdvice }}</p>
        </div>
        <button
          v-if="flashcardData?.dueToday && flashcardData.dueToday > 0"
          class="flex-shrink-0 ml-4 px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-xl hover:bg-emerald-700 transition-colors flex items-center gap-2"
          @click="startReview"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          开始复习
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="card rounded-2xl p-4 text-center hover:shadow-lg transition-shadow">
        <div class="w-10 h-10 rounded-full bg-navy-50 flex items-center justify-center mx-auto mb-2">
          <svg class="w-5 h-5 text-navy-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
          </svg>
        </div>
        <p class="text-2xl font-bold text-navy-800">{{ flashcardData?.totalCards || 0 }}</p>
        <p class="text-xs text-navy-400 mt-1">总闪卡数</p>
      </div>
      <div class="card rounded-2xl p-4 text-center hover:shadow-lg transition-shadow">
        <div class="w-10 h-10 rounded-full bg-rose-50 flex items-center justify-center mx-auto mb-2">
          <svg class="w-5 h-5 text-rose-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
          </svg>
        </div>
        <p class="text-2xl font-bold text-rose-500">{{ flashcardData?.dueToday || 0 }}</p>
        <p class="text-xs text-navy-400 mt-1">待复习</p>
      </div>
      <div class="card rounded-2xl p-4 text-center hover:shadow-lg transition-shadow">
        <div class="w-10 h-10 rounded-full bg-amber-50 flex items-center justify-center mx-auto mb-2">
          <svg class="w-5 h-5 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <p class="text-2xl font-bold text-amber-500">{{ flashcardData?.learning || 0 }}</p>
        <p class="text-xs text-navy-400 mt-1">学习中</p>
      </div>
      <div class="card rounded-2xl p-4 text-center hover:shadow-lg transition-shadow">
        <div class="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center mx-auto mb-2">
          <svg class="w-5 h-5 text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        <p class="text-2xl font-bold text-emerald-500">{{ flashcardData?.mastered || 0 }}</p>
        <p class="text-xs text-navy-400 mt-1">已掌握</p>
      </div>
      <div class="card rounded-2xl p-4 text-center hover:shadow-lg transition-shadow">
        <div class="w-10 h-10 rounded-full bg-indigo-50 flex items-center justify-center mx-auto mb-2">
          <svg class="w-5 h-5 text-indigo-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
        </div>
        <p class="text-2xl font-bold text-indigo-500">{{ flashcardData?.avgEaseFactor || 2.5 }}</p>
        <p class="text-xs text-navy-400 mt-1">记忆强度</p>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- 闪卡掌握度 -->
      <div class="card rounded-2xl p-6">
        <h2 class="font-display text-base font-semibold text-navy-800 mb-4">闪卡掌握度</h2>
        <div class="h-[250px] flex items-center justify-center">
          <Doughnut v-if="masteryChartData" :data="masteryChartData" :options="doughnutOptions" />
          <div v-else class="text-sm text-navy-400">暂无闪卡数据</div>
        </div>
      </div>

      <!-- 记忆强度分布 -->
      <div class="card rounded-2xl p-6">
        <h2 class="font-display text-base font-semibold text-navy-800 mb-4">记忆强度分布</h2>
        <div class="h-[250px]">
          <Bar v-if="easeChartData" :data="easeChartData" :options="barOptions" />
          <div v-else class="flex items-center justify-center h-full text-sm text-navy-400">暂无数据</div>
        </div>
      </div>
    </div>

    <!-- 艾宾浩斯遗忘曲线 -->
    <div class="card rounded-2xl p-6">
      <h2 class="font-display text-base font-semibold text-navy-800 mb-4">艾宾浩斯遗忘曲线</h2>
      <div class="h-[300px]">
        <Line :data="curveData" :options="curveOptions" />
      </div>
      <p class="text-xs text-navy-400 mt-3 text-center">
        蓝色曲线为理论遗忘曲线，绿色点为你实际复习的时间点
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Chart as ChartJS, CategoryScale, LinearScale, ArcElement, BarElement, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js'
import { Doughnut, Bar, Line } from 'vue-chartjs'
import type { AnalyticsData } from '@/api/analytics'

ChartJS.register(CategoryScale, LinearScale, ArcElement, BarElement, PointElement, LineElement, Title, Tooltip, Legend)

const props = defineProps<{
  data: AnalyticsData
}>()

const router = useRouter()
const flashcardData = computed(() => props.data.flashcardStats)

// 智能建议
const smartAdvice = computed(() => {
  const d = flashcardData.value
  if (!d) return '开始创建闪卡，开启高效复习之旅！'

  const { dueToday, mastered, totalCards, avgEaseFactor } = d

  if (dueToday > 10) {
    return `你有 ${dueToday} 张闪卡待复习，建议分批次完成，每次复习 10-15 张效果最佳。`
  }
  if (dueToday > 0) {
    return `你有 ${dueToday} 张闪卡待复习，现在是复习的好时机！`
  }
  if (mastered > 0 && totalCards > 0 && mastered / totalCards > 0.8) {
    return `太棒了！你已经掌握了 ${Math.round(mastered / totalCards * 100)}% 的闪卡，继续保持！`
  }
  if (avgEaseFactor < 2.0) {
    return '你的记忆强度偏低，建议增加复习频率，使用主动回忆法来巩固记忆。'
  }
  return '今日复习已完成，继续保持学习节奏！'
})

// 开始复习
function startReview() {
  router.push('/flashcard/review')
}

// 掌握度图表数据
const masteryChartData = computed(() => {
  const d = flashcardData.value
  if (!d || d.totalCards === 0) return null

  return {
    labels: ['新卡片', '学习中', '已掌握'],
    datasets: [{
      data: [d.newCards, d.learning, d.mastered],
      backgroundColor: ['#94a3b8', '#f59e0b', '#10b981'],
      borderWidth: 2,
      borderColor: '#fff',
    }],
  }
})

// 记忆强度分布数据
const easeChartData = computed(() => {
  const dist = flashcardData.value?.easeFactorDistribution || []
  if (dist.length === 0) return null

  const colors = ['#ef4444', '#f59e0b', '#3b82f6', '#10b981', '#8b5cf6', '#ec4899']

  return {
    labels: dist.map(d => d.label),
    datasets: [{
      label: '闪卡数量',
      data: dist.map(d => d.count),
      backgroundColor: colors.slice(0, dist.length),
      borderRadius: 6,
    }],
  }
})

// 遗忘曲线数据
const curveData = computed(() => {
  const points = []
  for (let day = 0; day <= 30; day++) {
    const retention = Math.exp(-day / 5) * 100
    points.push({ day, retention: Math.round(retention * 10) / 10 })
  }

  const reviewDays = [1, 3, 7, 14, 30]
  const reviewBoost = [1.15, 1.08, 1.05, 1.03, 1.02]
  const reviewRetention = reviewDays.map((d, i) => Math.exp(-d / 5) * 100 * reviewBoost[i])

  return {
    labels: points.map(p => p.day.toString()),
    datasets: [
      {
        label: '理论遗忘曲线',
        data: points.map(p => p.retention),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
      },
      {
        label: '复习后记忆保持',
        data: reviewDays.map((d, i) => ({ x: d, y: Math.round(reviewRetention[i]) })),
        borderColor: '#10b981',
        backgroundColor: '#10b981',
        pointRadius: 6,
        pointHoverRadius: 8,
        showLine: false,
      },
    ],
  }
})

// 图表配置
const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '55%',
  plugins: {
    legend: { position: 'bottom' as const, labels: { padding: 14, usePointStyle: true, font: { size: 11 } } },
  },
}

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: 'rgba(0,0,0,0.04)' } },
    x: { grid: { display: false } },
  },
}

const curveOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' as const, labels: { usePointStyle: true, padding: 16, font: { size: 11 } } },
    tooltip: { callbacks: { label: (ctx: any) => `记忆保持率: ${ctx.parsed.y}%` } },
  },
  scales: {
    y: {
      beginAtZero: true,
      max: 100,
      ticks: { callback: (v: any) => `${v}%` },
      grid: { color: 'rgba(0,0,0,0.04)' },
    },
    x: {
      title: { display: true, text: '天数', font: { size: 12 } },
      grid: { display: false },
    },
  },
}
</script>
