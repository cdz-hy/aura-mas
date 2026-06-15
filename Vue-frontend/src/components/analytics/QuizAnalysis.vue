<template>
  <div class="space-y-4">
    <!-- By Question Type -->
    <div>
      <h3 class="text-sm font-medium text-navy-600 mb-3">按题型分布</h3>
      <div class="h-[200px]">
        <Bar v-if="typeChartData" :data="typeChartData" :options="barOptions" />
        <div v-else class="flex items-center justify-center h-full text-sm text-navy-400">暂无答题数据</div>
      </div>
    </div>

    <!-- By Difficulty -->
    <div>
      <h3 class="text-sm font-medium text-navy-600 mb-3">按难度正确率</h3>
      <div class="h-[200px]">
        <Line v-if="diffChartData" :data="diffChartData" :options="lineOptions" />
        <div v-else class="flex items-center justify-center h-full text-sm text-navy-400">暂无难度数据</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend } from 'chart.js'
import { Line, Bar } from 'vue-chartjs'
import type { QuizAnalysis } from '@/api/analytics'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend)

const props = defineProps<{
  quizData?: QuizAnalysis
}>()

const typeLabelMap: Record<string, string> = {
  single_choice: '单选',
  multiple_choice: '多选',
  true_false: '判断',
  fill_blank: '填空',
  short_answer: '简答',
}

const typeChartData = computed(() => {
  const byType = props.quizData?.byQuestionType || []
  if (byType.length === 0) return null

  return {
    labels: byType.map(t => typeLabelMap[t.type] || t.type),
    datasets: [
      {
        label: '正确',
        data: byType.map(t => t.correct),
        backgroundColor: 'rgba(16, 185, 129, 0.7)',
        borderRadius: 4,
      },
      {
        label: '错误',
        data: byType.map(t => t.total - t.correct),
        backgroundColor: 'rgba(244, 63, 94, 0.7)',
        borderRadius: 4,
      },
    ],
  }
})

const diffChartData = computed(() => {
  const byDiff = props.quizData?.byDifficulty || []
  if (byDiff.length === 0) return null

  return {
    labels: byDiff.map(d => `难度${d.difficulty}`),
    datasets: [
      {
        label: '正确率',
        data: byDiff.map(d => d.accuracy),
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        fill: true,
        tension: 0.35,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  }
})

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' as const, labels: { usePointStyle: true, padding: 12, font: { size: 11 } } },
  },
  scales: {
    x: { stacked: true, grid: { display: false } },
    y: { stacked: true, beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' } },
  },
}

const lineOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: (ctx: any) => `正确率: ${ctx.parsed.y}%` } },
  },
  scales: {
    y: { beginAtZero: true, max: 100, ticks: { callback: (v: any) => `${v}%` }, grid: { color: 'rgba(0,0,0,0.04)' } },
    x: { grid: { display: false } },
  },
}
</script>
