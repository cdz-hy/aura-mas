<template>
  <div class="h-[300px]">
    <Line v-if="chartData" :data="chartData" :options="chartOptions" />
    <div v-else class="flex items-center justify-center h-full text-navy-400 text-sm">
      暂无学习数据
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Filler, Title, Tooltip, Legend } from 'chart.js'
import { Line } from 'vue-chartjs'
import type { HeatmapData } from '@/api/analytics'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Title, Tooltip, Legend)

const props = defineProps<{
  heatmapData?: HeatmapData
}>()

const chartData = computed(() => {
  const dailyData = props.heatmapData?.dailyData || []
  if (dailyData.length === 0) return null

  // Use last 30 days
  const last30 = dailyData.slice(-30)

  return {
    labels: last30.map(d => {
      const date = new Date(d.date)
      return `${date.getMonth() + 1}/${date.getDate()}`
    }),
    datasets: [
      {
        label: '学习时长（分钟）',
        data: last30.map(d => d.minutes),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.35,
        pointRadius: 3,
        pointHoverRadius: 5,
      },
    ],
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: (ctx: any) => `${ctx.parsed.y} 分钟` } },
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: { callback: (v: any) => `${v}分` },
      grid: { color: 'rgba(0,0,0,0.04)' },
    },
    x: {
      grid: { display: false },
      ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 10 },
    },
  },
}
</script>
