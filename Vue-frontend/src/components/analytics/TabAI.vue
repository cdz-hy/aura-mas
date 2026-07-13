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

    <!-- AI Learning Report -->
    <div class="card rounded-2xl p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="font-display text-base font-semibold text-navy-800">AI 学习报告</h2>
        <button class="btn-primary text-sm" @click="generateReport" :disabled="reportLoading">
          <svg v-if="reportLoading" class="w-4 h-4 animate-spin mr-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 11-6.219-8.56" />
          </svg>
          {{ reportLoading ? '生成中...' : '生成学习报告' }}
        </button>
      </div>

      <div v-if="reportContent" class="prose prose-sm max-w-none">
        <div v-html="renderedReport" />
      </div>

      <div v-else-if="reportLoading" class="space-y-3 animate-pulse">
        <div class="h-4 bg-navy-100 rounded w-3/4" />
        <div class="h-4 bg-navy-100 rounded w-full" />
        <div class="h-4 bg-navy-100 rounded w-5/6" />
        <div class="h-4 bg-navy-100 rounded w-2/3" />
      </div>

      <div v-else class="text-center py-12">
        <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-indigo-50 to-purple-50 flex items-center justify-center">
          <svg class="w-8 h-8 text-indigo-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <p class="text-sm text-navy-500">点击"生成学习报告"，AI将为你分析学习数据</p>
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
import { PYTHON_AI_BASE } from '@/api/request'
import { useAuthStore } from '@/stores/auth'

ChartJS.register(CategoryScale, LinearScale, ArcElement, BarElement, Title, Tooltip, Legend)

const props = defineProps<{
  data: AnalyticsData
}>()

const authStore = useAuthStore()

const reportLoading = ref(false)
const reportContent = ref('')

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

const renderedReport = computed(() => {
  // Simple markdown rendering
  return reportContent.value
    .replace(/^### (.*$)/gm, '<h3 class="text-base font-semibold text-navy-800 mt-4 mb-2">$1</h3>')
    .replace(/^## (.*$)/gm, '<h2 class="text-lg font-semibold text-navy-800 mt-5 mb-2">$1</h2>')
    .replace(/^# (.*$)/gm, '<h1 class="text-xl font-bold text-navy-800 mt-6 mb-3">$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^- (.*$)/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/^\d+\. (.*$)/gm, '<li class="ml-4 list-decimal">$1</li>')
    .replace(/\n\n/g, '</p><p class="mb-2">')
    .replace(/\n/g, '<br>')
})

async function generateReport() {
  reportLoading.value = true
  reportContent.value = ''

  try {
    const data = props.data

    // Call Python backend SSE endpoint
    const response = await fetch(`${PYTHON_AI_BASE}/api/analytics/learning-report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: authStore.user?.id || 0,
        overview: data.overview || {},
        quiz_analysis: data.quizAnalysis || {},
        heatmap: data.heatmap || {},
        flashcard_stats: data.flashcardStats || {},
        ai_interaction: data.aiInteraction || {},
        knowledge_mastery: data.knowledgeMastery || {},
        learning_style: {},
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('No reader available')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'chunk' && data.content) {
              reportContent.value += data.content
            } else if (data.type === 'error') {
              throw new Error(data.content)
            }
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    }
  } catch (e) {
    console.error('Failed to generate report:', e)
    reportContent.value = '报告生成失败，请确保 Python 后端服务已启动。'
  } finally {
    reportLoading.value = false
  }
}
</script>
