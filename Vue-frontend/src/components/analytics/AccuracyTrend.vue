<template>
  <div class="h-[250px]">
    <Line v-if="chartData" :data="chartData" :options="chartOptions" />
    <div v-else class="flex items-center justify-center h-full text-navy-400 text-sm">
      暂无答题数据
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Filler, Title, Tooltip, Legend } from 'chart.js'
import { Line } from 'vue-chartjs'
import type { QuizAnalysis } from '@/api/analytics'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Title, Tooltip, Legend)

const props = defineProps<{
  quizData?: QuizAnalysis
}>()

const chartData = computed(() => {
  const daily = props.quizData?.dailyAccuracy || []
  if (daily.length === 0) return null

  // Calculate 7-day moving average
  const movingAvg: (number | null)[] = []
  for (let i = 0; i < daily.length; i++) {
    if (i < 6) {
      movingAvg.push(null)
    } else {
      const window = daily.slice(i - 6, i + 1)
      const avg = window.reduce((s, d) => s + d.accuracy, 0) / window.length
      movingAvg.push(Math.round(avg * 10) / 10)
    }
  }

  return {
    labels: daily.map(d => {
      const date = new Date(d.date)
      return `${date.getMonth() + 1}/${date.getDate()}`
    }),
    datasets: [
      {
        label: '每日正确率',
        data: daily.map(d => d.accuracy),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.05)',
        tension: 0.35,
        pointRadius: 2,
        pointHoverRadius: 4,
      },
      {
        label: '7日移动平均',
        data: movingAvg,
        borderColor: '#f59e0b',
        borderWidth: 2,
        borderDash: [5, 5],
        tension: 0.35,
        pointRadius: 0,
        spanGaps: true,
      },
    ],
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' as const, labels: { usePointStyle: true, padding: 16, font: { size: 11 } } },
    tooltip: { callbacks: { label: (ctx: any) => `${ctx.dataset.label}: ${ctx.parsed.y}%` } },
  },
  scales: {
    y: {
      beginAtZero: true,
      max: 100,
      ticks: { callback: (v: any) => `${v}%` },
      grid: { color: 'rgba(0,0,0,0.04)' },
    },
    x: {
      grid: { display: false },
      ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 15 },
    },
  },
}
</script>
