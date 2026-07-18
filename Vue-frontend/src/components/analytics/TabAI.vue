<template>
  <div class="space-y-6">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Intent Distribution -->
      <div class="card rounded-2xl p-6">
        <h2 class="font-display text-base font-semibold text-navy-800 mb-4">对话意图分布</h2>
        <div class="h-[280px] flex items-center justify-center">
          <Doughnut v-if="intentChartData" :data="intentChartData" :options="doughnutOptions" />
          <div v-else class="text-sm text-navy-400">暂无对话数据</div>
        </div>
      </div>

      <!-- Daily Dialogue Trend -->
      <div class="card rounded-2xl p-6">
        <h2 class="font-display text-base font-semibold text-navy-800 mb-4">每日对话趋势</h2>
        <div class="h-[280px]">
          <Bar v-if="dailyChartData" :data="dailyChartData" :options="barOptions" />
          <div v-else class="flex items-center justify-center h-full text-sm text-navy-400">暂无数据</div>
        </div>
      </div>
    </div>

    <!-- Stats Summary -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="card rounded-2xl p-4 text-center">
        <p class="text-2xl font-bold text-navy-800">{{ aiData?.totalDialogues || 0 }}</p>
        <p class="text-xs text-navy-400 mt-1">总对话轮次</p>
      </div>
      <div class="card rounded-2xl p-4 text-center">
        <p class="text-2xl font-bold text-navy-800">{{ aiData?.avgSessionLength || 0 }}</p>
        <p class="text-xs text-navy-400 mt-1">平均会话长度</p>
      </div>
      <div class="card rounded-2xl p-4 text-center">
        <p class="text-2xl font-bold text-navy-800">{{ topIntent }}</p>
        <p class="text-xs text-navy-400 mt-1">最常用意图</p>
      </div>
      <div class="card rounded-2xl p-4 text-center">
        <p class="text-2xl font-bold text-navy-800">{{ activeDays }}</p>
        <p class="text-xs text-navy-400 mt-1">AI交互天数</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Chart as ChartJS, CategoryScale, LinearScale, ArcElement, BarElement, Title, Tooltip, Legend } from 'chart.js'
import { Doughnut, Bar } from 'vue-chartjs'
import type { AnalyticsData } from '@/api/analytics'

ChartJS.register(CategoryScale, LinearScale, ArcElement, BarElement, Title, Tooltip, Legend)

const props = defineProps<{
  data: AnalyticsData
}>()

const aiData = computed(() => props.data.aiInteraction)

const intentLabelMap: Record<string, string> = {
  // 资源生成类
  generate_resource: '资源生成',
  resource_generated: '资源已生成',
  generate_quiz: '题目生成',
  generate_animation: '动画生成',
  generate_type_resource: '类型资源生成',
  grade_quiz: '题目批改',
  task_breakdown: '任务分解',
  // 对话类
  simple_qa: '简单问答',
  chat: '普通对话',
  plan_chat: '计划对话',
  follow_up: '追问',
  ambiguous: '意图模糊',
  clarify: '需求澄清',
  // 系统类
  plan_advisor: '学习顾问',
  profile: '画像构建',
  profile_maintenance: '画像维护',
  stopped: '已停止',
  cancel: '取消操作',
}

const intentColors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

const intentChartData = computed(() => {
  const byIntent = aiData.value?.byIntentType || []
  if (byIntent.length === 0) return null

  return {
    labels: byIntent.map(i => intentLabelMap[i.intent] || i.intent),
    datasets: [{
      data: byIntent.map(i => i.count),
      backgroundColor: intentColors.slice(0, byIntent.length),
      borderWidth: 2,
      borderColor: '#fff',
    }],
  }
})

const dailyChartData = computed(() => {
  const daily = aiData.value?.dailyDialogues || []
  if (daily.length === 0) return null

  const last14 = daily.slice(-14)

  return {
    labels: last14.map(d => {
      const date = new Date(d.date)
      return `${date.getMonth() + 1}/${date.getDate()}`
    }),
    datasets: [{
      label: '对话次数',
      data: last14.map(d => d.count),
      backgroundColor: 'rgba(99, 102, 241, 0.6)',
      borderRadius: 4,
      maxBarThickness: 30,
    }],
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

const topIntent = computed(() => {
  const byIntent = aiData.value?.byIntentType || []
  if (byIntent.length === 0) return '-'
  const top = byIntent.reduce((a, b) => a.count > b.count ? a : b)
  return intentLabelMap[top.intent] || top.intent
})

const activeDays = computed(() => {
  const daily = aiData.value?.dailyDialogues || []
  return daily.filter(d => d.count > 0).length
})

</script>
