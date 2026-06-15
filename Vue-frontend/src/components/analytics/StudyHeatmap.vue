<template>
  <div ref="containerRef" class="relative">
    <div class="overflow-x-auto">
      <div class="min-w-[700px]">
        <!-- Month labels -->
        <div class="flex mb-1 ml-8">
          <div v-for="month in monthLabels" :key="month.label"
            class="text-[10px] text-navy-400"
            :style="{ marginLeft: `${month.offset * 17}px` }">
            {{ month.label }}
          </div>
        </div>

        <div class="flex gap-1">
          <!-- Day labels -->
          <div class="flex flex-col gap-[3px] pr-1">
            <div v-for="(day, i) in ['一', '二', '三', '四', '五', '六', '日']" :key="day"
              class="h-[14px] flex items-center"
              :class="i % 2 === 0 ? 'visible' : 'invisible'">
              <span class="text-[10px] text-navy-400 w-6 text-right">{{ day }}</span>
            </div>
          </div>

          <!-- Grid -->
          <div class="flex gap-[3px]">
            <div v-for="(week, wi) in weeks" :key="wi" class="flex flex-col gap-[3px]">
              <div v-for="(day, di) in week" :key="di"
                class="w-[14px] h-[14px] rounded-[3px] cursor-pointer transition-all hover:ring-2 hover:ring-navy-300"
                :class="levelClass(day?.level || 0)"
                @mouseenter="onCellEnter($event, day)"
                @mouseleave="hoveredDay = null" />
            </div>
          </div>
        </div>

        <!-- Legend -->
        <div class="flex items-center gap-2 mt-3 ml-8">
          <span class="text-[10px] text-navy-400">少</span>
          <div v-for="level in [0, 1, 2, 3, 4]" :key="level"
            class="w-[14px] h-[14px] rounded-[3px]"
            :class="levelClass(level)" />
          <span class="text-[10px] text-navy-400">多</span>
        </div>
      </div>
    </div>

    <!-- Tooltip (outside overflow container, positioned relative to wrapper) -->
    <transition name="fade">
      <div v-if="hoveredDay"
        class="absolute px-3 py-2 bg-navy-800 text-white text-xs rounded-lg whitespace-nowrap shadow-lg pointer-events-none z-50"
        style="transform: translateY(-50%);"
        :style="{ top: tooltipPos.top + 'px', left: tooltipPos.left + 'px' }">
        <span class="font-medium">{{ formatDate(hoveredDay.date) }}</span>
        <span class="mx-1.5 text-navy-300">·</span>
        <span>{{ hoveredDay.minutes > 0 ? `${hoveredDay.minutes} 分钟` : '未学习' }}</span>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { HeatmapData } from '@/api/analytics'

const props = defineProps<{
  heatmapData?: HeatmapData
}>()

const hoveredDay = ref<{ date: string; minutes: number; level: number } | null>(null)
const tooltipPos = ref({ top: 0, left: 0 })
const containerRef = ref<HTMLElement | null>(null)

function onCellEnter(e: MouseEvent, day: { date: string; minutes: number; level: number } | null) {
  if (!day || !containerRef.value) return
  hoveredDay.value = day
  const cellRect = (e.target as HTMLElement).getBoundingClientRect()
  const containerRect = containerRef.value.getBoundingClientRect()
  tooltipPos.value = {
    top: cellRect.top - containerRect.top + cellRect.height / 2,
    left: cellRect.right - containerRect.left + 8,
  }
}

// Helper to format date as YYYY-MM-DD in local timezone
function formatDateLocal(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const dailyMap = computed(() => {
  const map = new Map<string, { date: string; minutes: number; level: number }>()
  if (props.heatmapData?.dailyData) {
    for (const d of props.heatmapData.dailyData) {
      // Normalize date format
      const dateKey = d.date?.split('T')[0] || d.date
      map.set(dateKey, d)
    }
  }
  return map
})

// Generate weeks grid (7 rows x N columns)
const weeks = computed(() => {
  const result: Array<Array<{ date: string; minutes: number; level: number } | null>> = []
  const today = new Date()
  const startDate = new Date(today)
  startDate.setDate(startDate.getDate() - 179) // ~26 weeks

  // Adjust to start on Monday
  const dayOfWeek = startDate.getDay()
  const adjust = dayOfWeek === 0 ? 6 : dayOfWeek - 1
  startDate.setDate(startDate.getDate() - adjust)

  const current = new Date(startDate)
  let week: Array<{ date: string; minutes: number; level: number } | null> = []

  while (current <= today) {
    const dateStr = formatDateLocal(current)
    const dayData = dailyMap.value.get(dateStr) || { date: dateStr, minutes: 0, level: 0 }
    week.push(dayData)

    if (week.length === 7) {
      result.push(week)
      week = []
    }
    current.setDate(current.getDate() + 1)
  }

  if (week.length > 0) {
    while (week.length < 7) week.push(null)
    result.push(week)
  }

  return result
})

// Month labels for the grid
const monthLabels = computed(() => {
  const labels: Array<{ label: string; offset: number }> = []
  const today = new Date()
  const startDate = new Date(today)
  startDate.setDate(startDate.getDate() - 179)

  const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

  let lastMonth = -1
  const current = new Date(startDate)
  let weekIndex = 0

  const dayOfWeek = current.getDay()
  const adjust = dayOfWeek === 0 ? 6 : dayOfWeek - 1
  current.setDate(current.getDate() - adjust)

  while (current <= today) {
    const month = current.getMonth()
    if (month !== lastMonth) {
      labels.push({
        label: monthNames[month],
        offset: weekIndex - (labels.length > 0 ? labels.reduce((s, l) => s + l.offset, 0) : 0),
      })
      lastMonth = month
    }
    if (current.getDay() === 1 || current.getTime() === startDate.getTime()) {
      weekIndex++
    }
    current.setDate(current.getDate() + 1)
  }

  return labels
})

function levelClass(level: number): string {
  const classes = [
    'bg-navy-50',       // 0: no study
    'bg-navy-200',      // 1: light
    'bg-navy-400',      // 2: medium
    'bg-navy-600',      // 3: heavy
    'bg-navy-800',      // 4: intense
  ]
  return classes[level] || classes[0]
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
