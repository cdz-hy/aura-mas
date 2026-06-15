<template>
  <div class="space-y-6">
    <!-- AI Suggestions -->
    <AiSuggestions :data="data" />

    <!-- Study Heatmap -->
    <div class="card rounded-2xl p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="font-display text-base font-semibold text-navy-800">学习连续性</h2>
        <div class="flex items-center gap-4 text-xs text-navy-400">
          <span>当前连续 <strong class="text-navy-700">{{ data.heatmap?.currentStreak || 0 }}</strong> 天</span>
          <span>最长 <strong class="text-navy-700">{{ data.heatmap?.longestStreak || 0 }}</strong> 天</span>
          <span>总活跃 <strong class="text-navy-700">{{ data.heatmap?.totalActiveDays || 0 }}</strong> 天</span>
        </div>
      </div>
      <StudyHeatmap :heatmap-data="data.heatmap" />
    </div>

    <!-- Study Efficiency -->
    <StudyEfficiency :efficiency-data="data.studyEfficiency" />

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Quiz Analysis -->
      <div class="card rounded-2xl p-6">
        <h2 class="font-display text-base font-semibold text-navy-800 mb-4">答题分析</h2>
        <QuizAnalysis :quiz-data="data.quizAnalysis" />
      </div>

      <!-- Study Trend -->
      <div class="card rounded-2xl p-6">
        <h2 class="font-display text-base font-semibold text-navy-800 mb-4">学习时长趋势</h2>
        <StudyTrend :heatmap-data="data.heatmap" />
      </div>
    </div>

    <!-- Accuracy Trend -->
    <div class="card rounded-2xl p-6">
      <h2 class="font-display text-base font-semibold text-navy-800 mb-4">正确率趋势（近30天）</h2>
      <AccuracyTrend :quiz-data="data.quizAnalysis" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AnalyticsData } from '@/api/analytics'
import StudyHeatmap from './StudyHeatmap.vue'
import QuizAnalysis from './QuizAnalysis.vue'
import StudyTrend from './StudyTrend.vue'
import AccuracyTrend from './AccuracyTrend.vue'
import StudyEfficiency from './StudyEfficiency.vue'
import AiSuggestions from './AiSuggestions.vue'

defineProps<{
  data: AnalyticsData
}>()
</script>
