<template>
  <div class="space-y-6">
    <!-- AI Suggestions -->
    <AiSuggestions :data="data" />

    <!-- Study Heatmap -->
    <StudyHeatmap />

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
