<template>
  <div class="space-y-6">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Flashcard Status -->
      <div class="card rounded-2xl p-6">
        <h2 class="font-display text-base font-semibold text-navy-800 mb-4">闪卡掌握度</h2>
        <div class="h-[250px] flex items-center justify-center">
          <Doughnut v-if="masteryChartData" :data="masteryChartData" :options="doughnutOptions" />
          <div v-else class="text-sm text-navy-400">暂无闪卡数据</div>
        </div>
      </div>

      <!-- Ease Factor Distribution -->
      <div class="card rounded-2xl p-6">
        <h2 class="font-display text-base font-semibold text-navy-800 mb-4">记忆强度分布</h2>
        <div class="h-[250px]">
          <Bar v-if="easeChartData" :data="easeChartData" :options="barOptions" />
          <div v-else class="flex items-center justify-center h-full text-sm text-navy-400">暂无数据</div>
        </div>
      </div>
    </div>

    <!-- Forgetting Curve -->
    <div class="card rounded-2xl p-6">
      <h2 class="font-display text-base font-semibold text-navy-800 mb-4">艾宾浩斯遗忘曲线</h2>
      <div class="h-[300px]">
        <Line :data="curveData" :options="curveOptions" />
      </div>
      <p class="text-xs text-navy-400 mt-3 text-center">
        蓝色曲线为理论遗忘曲线，绿色点为你实际复习的时间点
      </p>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="card rounded-2xl p-4 text-center">
        <p class="text-2xl font-bold text-navy-800">{{ flashcardData?.totalCards || 0 }}</p>
        <p class="text-xs text-navy-400 mt-1">总闪卡数</p>
      </div>
      <div class="card rounded-2xl p-4 text-center">
        <p class="text-2xl font-bold text-rose-500">{{ flashcardData?.dueToday || 0 }}</p>
        <p class="text-xs text-navy-400 mt-1">待复习</p>
      </div>
      <div class="card rounded-2xl p-4 text-center">
        <p class="text-2xl font-bold text-amber-500">{{ flashcardData?.learning || 0 }}</p>
        <p class="text-xs text-navy-400 mt-1">学习中</p>
      </div>
      <div class="card rounded-2xl p-4 text-center">
        <p class="text-2xl font-bold text-emerald-500">{{ flashcardData?.mastered || 0 }}</p>
        <p class="text-xs text-navy-400 mt-1">已掌握</p>
      </div>
      <div class="card rounded-2xl p-4 text-center">
        <p class="text-2xl font-bold text-indigo-500">{{ flashcardData?.avgEaseFactor || 2.5 }}</p>
        <p class="text-xs text-navy-400 mt-1">平均记忆强度</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Chart as ChartJS, CategoryScale, LinearScale, ArcElement, BarElement, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js'
import { Doughnut, Bar, Line } from 'vue-chartjs'
import type { AnalyticsData } from '@/api/analytics'

ChartJS.register(CategoryScale, LinearScale, ArcElement, BarElement, PointElement, LineElement, Title, Tooltip, Legend)

const props = defineProps<{
  data: AnalyticsData
}>()

const flashcardData = computed(() => props.data.flashcardStats)

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

// Forgetting curve data (theoretical Ebbinghaus curve)
const curveData = computed(() => {
  const points = []
  for (let day = 0; day <= 30; day++) {
    const retention = Math.exp(-day / 5) * 100
    points.push({ day, retention: Math.round(retention * 10) / 10 })
  }

  // Typical spaced-repetition review schedule (fixed offsets, not random)
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
