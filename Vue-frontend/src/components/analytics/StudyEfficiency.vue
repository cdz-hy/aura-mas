<template>
  <div class="card rounded-2xl p-6 relative">
    <div class="flex items-center justify-between mb-4">
      <h2 class="font-display text-base font-semibold text-navy-800">学习效率时段分析</h2>
      <div class="flex items-center gap-3 text-xs">
        <span v-if="hasStudyData"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-50 text-blue-600 font-medium">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
          </svg>
          最佳学习 {{ efficiencyData!.bestStudyHour }}:00
        </span>
        <span v-if="efficiencyData?.bestQuizHour !== undefined && efficiencyData.bestQuizAccuracy > 0"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 font-medium">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          最佳答题 {{ efficiencyData.bestQuizHour }}:00 ({{ efficiencyData.bestQuizAccuracy }}%)
        </span>
      </div>
    </div>

    <div v-if="!efficiencyData || noData" class="flex items-center justify-center h-[120px] text-sm text-navy-400">
      暂无学习时段数据
    </div>

    <template v-else>
      <!-- Hour labels -->
      <div class="flex mb-1">
        <div v-for="h in labelHours" :key="h"
          class="text-[10px] text-navy-400 text-center"
          :style="{ width: `${100 / 24}%` }">
          {{ h }}时
        </div>
      </div>

      <!-- 24-hour heatmap -->
      <div class="flex gap-[2px]">
        <div v-for="item in efficiencyData.hourlyData" :key="item.hour"
          class="flex-1 h-8 rounded-[3px] cursor-pointer transition-all hover:ring-2 hover:ring-navy-300 relative group"
          :class="hourColorClass(item.studyMinutes)"
          @mouseenter="hoveredHour = item"
          @mouseleave="hoveredHour = null">
        </div>
      </div>

      <!-- Legend -->
      <div class="flex items-center gap-2 mt-3 justify-end">
        <span class="text-[10px] text-navy-400">少</span>
        <div v-for="level in 5" :key="level"
          class="w-[14px] h-[14px] rounded-[3px]"
          :class="hourColorClassByLevel(level - 1)" />
        <span class="text-[10px] text-navy-400">多</span>
      </div>

      <!-- Tooltip (absolute, no layout shift) -->
      <transition name="fade">
        <div v-if="hoveredHour"
          class="absolute left-0 right-0 bottom-0 p-3 bg-navy-800 text-white text-xs rounded-xl flex items-center gap-6 shadow-lg z-10 pointer-events-none">
          <div class="font-semibold text-sm">{{ hoveredHour.hour }}:00 - {{ hoveredHour.hour + 1 }}:00</div>
          <div class="flex items-center gap-1">
            <svg class="w-3.5 h-3.5 text-blue-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
            </svg>
            {{ hoveredHour.studyMinutes }} 分钟
          </div>
          <div class="flex items-center gap-1">
            <svg class="w-3.5 h-3.5 text-emerald-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            {{ hoveredHour.quizTotal > 0 ? `${hoveredHour.accuracy}%` : '无答题' }}
          </div>
          <div class="flex items-center gap-1">
            <svg class="w-3.5 h-3.5 text-amber-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
            </svg>
            {{ hoveredHour.sessionCount }} 次会话
          </div>
        </div>
      </transition>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { StudyEfficiency } from '@/api/analytics'

const props = defineProps<{
  efficiencyData?: StudyEfficiency
}>()

const hoveredHour = ref<StudyEfficiency['hourlyData'][0] | null>(null)

const noData = computed(() => {
  if (!props.efficiencyData?.hourlyData) return true
  return props.efficiencyData.hourlyData.every(h => h.studyMinutes === 0 && h.quizTotal === 0)
})

const hasStudyData = computed(() => {
  if (!props.efficiencyData?.hourlyData) return false
  return props.efficiencyData.hourlyData.some(h => h.studyMinutes > 0)
})

// Only show labels at 0, 6, 12, 18
const labelHours = computed(() => {
  const labels: (number | string)[] = []
  for (let h = 0; h < 24; h++) {
    labels.push(h % 6 === 0 ? h : '')
  }
  return labels
})

const maxMinutes = computed(() => {
  if (!props.efficiencyData?.hourlyData) return 1
  return Math.max(1, ...props.efficiencyData.hourlyData.map(h => h.studyMinutes))
})

function hourColorClass(minutes: number): string {
  if (minutes === 0) return 'bg-navy-50'
  const ratio = minutes / maxMinutes.value
  if (ratio <= 0.25) return 'bg-navy-200'
  if (ratio <= 0.5) return 'bg-navy-400'
  if (ratio <= 0.75) return 'bg-navy-600'
  return 'bg-navy-800'
}

function hourColorClassByLevel(level: number): string {
  const classes = ['bg-navy-50', 'bg-navy-200', 'bg-navy-400', 'bg-navy-600', 'bg-navy-800']
  return classes[level] || classes[0]
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
