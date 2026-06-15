<template>
  <div v-if="weekData" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
    <div v-for="(card, i) in cards" :key="card.label"
      class="card rounded-2xl p-5 animate-fade-in-up"
      :style="{ animationDelay: `${i * 0.08}s` }">
      <div class="flex items-center justify-between mb-3">
        <span class="text-sm text-navy-500 font-medium">{{ card.label }}</span>
        <div class="w-8 h-8 rounded-lg flex items-center justify-center" :class="card.bgClass">
          <div class="w-4 h-4" :class="card.iconClass" v-html="card.icon"></div>
        </div>
      </div>

      <div class="flex items-baseline gap-2 mb-1">
        <span class="text-2xl font-display font-bold text-navy-800">{{ card.thisWeek }}</span>
        <span class="text-xs text-navy-400">{{ card.unit }}</span>
      </div>

      <div class="flex items-center gap-2">
        <span class="text-xs text-navy-400">上周 {{ card.lastWeek }}{{ card.unit }}</span>
        <span v-if="card.change !== null" class="inline-flex items-center gap-0.5 text-xs font-semibold"
          :class="changeClass(card.change, card.isInverse)">
          <svg v-if="card.change > 0" class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="18 15 12 9 6 15"/>
          </svg>
          <svg v-else-if="card.change < 0" class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
          <span v-else class="w-3 h-3 text-center leading-3">-</span>
          {{ Math.abs(card.change) }}%
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WeekComparison } from '@/api/analytics'

const props = defineProps<{
  weekData?: WeekComparison
}>()

const cards = computed(() => {
  const d = props.weekData
  if (!d) return []

  return [
    {
      label: '学习时长',
      thisWeek: d.studyMinutes.thisWeek,
      lastWeek: d.studyMinutes.lastWeek,
      change: d.studyMinutes.change,
      unit: '分钟',
      isInverse: false,
      bgClass: 'bg-blue-50',
      iconClass: 'text-blue-500',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
    },
    {
      label: '答题正确率',
      thisWeek: `${d.quizAccuracy.thisWeek}%`,
      lastWeek: `${d.quizAccuracy.lastWeek}%`,
      change: d.quizAccuracy.change,
      unit: '',
      isInverse: false,
      bgClass: 'bg-emerald-50',
      iconClass: 'text-emerald-500',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    },
    {
      label: '活跃天数',
      thisWeek: d.activeDays.thisWeek,
      lastWeek: d.activeDays.lastWeek,
      change: null,
      unit: '天',
      isInverse: false,
      bgClass: 'bg-amber-50',
      iconClass: 'text-amber-500',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
    },
  ]
})

function changeClass(change: number, isInverse: boolean): string {
  const positive = isInverse ? change < 0 : change > 0
  if (change === 0) return 'text-navy-400'
  return positive ? 'text-emerald-500' : 'text-rose-500'
}
</script>
