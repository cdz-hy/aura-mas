<template>
  <div class="card rounded-2xl p-6 animate-fade-in-up">
    <!-- Header with streak stats -->
    <div class="flex items-center justify-between mb-4 flex-wrap gap-3">
      <h2 class="font-display text-base font-semibold text-navy-800">学习连续性</h2>
      <div class="flex items-center gap-5">
        <div class="flex items-center gap-1.5">
          <svg class="w-4 h-4 text-orange-400" viewBox="0 0 24 24" fill="currentColor">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
          </svg>
          <span class="text-sm text-navy-500">连续学习</span>
          <span class="text-sm font-bold text-navy-800">{{ heatmapData?.currentStreak ?? 0 }}</span>
          <span class="text-sm text-navy-400">天</span>
        </div>
        <div class="flex items-center gap-1.5">
          <svg class="w-4 h-4 text-amber-500" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
          </svg>
          <span class="text-sm text-navy-500">最长连续</span>
          <span class="text-sm font-bold text-navy-800">{{ heatmapData?.longestStreak ?? 0 }}</span>
          <span class="text-sm text-navy-400">天</span>
        </div>
        <div class="flex items-center gap-1.5">
          <svg class="w-4 h-4 text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <span class="text-sm text-navy-500">活跃天数</span>
          <span class="text-sm font-bold text-navy-800">{{ heatmapData?.totalActiveDays ?? 0 }}</span>
          <span class="text-sm text-navy-400">天</span>
        </div>
      </div>
    </div>

    <!-- Heatmap grid -->
    <div class="overflow-x-auto">
      <div class="inline-block min-w-[700px]">
        <!-- Month labels -->
        <div class="flex ml-8 mb-1" :style="{ gap: cellGap + 'px' }">
          <div
            v-for="(month, i) in monthLabels"
            :key="i"
            class="text-[10px] text-navy-400 whitespace-nowrap"
            :style="{ width: month.width + 'px' }"
          >
            {{ month.label }}
          </div>
        </div>

        <!-- Grid body -->
        <div class="flex">
          <!-- Day labels (left side) -->
          <div class="flex flex-col mr-2" :style="{ gap: cellGap + 'px' }">
            <div
              v-for="d in 7"
              :key="d"
              class="text-[10px] text-navy-400 flex items-center"
              :style="{ height: cellSize + 'px' }"
            >
              <span v-if="d === 2 || d === 4 || d === 6">{{ dayLabels[d - 1] }}</span>
            </div>
          </div>

          <!-- Cells grid (columns = weeks, rows = days) -->
          <div class="flex" :style="{ gap: cellGap + 'px' }">
            <div
              v-for="(week, wi) in weeks"
              :key="wi"
              class="flex flex-col"
              :style="{ gap: cellGap + 'px' }"
            >
              <div
                v-for="(day, di) in week"
                :key="di"
                :style="{
                  width: cellSize + 'px',
                  height: cellSize + 'px',
                  backgroundColor: day ? levelColor(day.level) : 'transparent',
                  borderRadius: '3px',
                }"
                class="cursor-pointer transition-all hover:ring-2 hover:ring-navy-300"
                @mouseenter="showTooltip($event, day)"
                @mouseleave="hideTooltip"
              />
            </div>
          </div>
        </div>

        <!-- Legend -->
        <div class="flex items-center justify-end mt-3 gap-1.5">
          <span class="text-[10px] text-navy-400 mr-1">少</span>
          <div
            v-for="level in [0, 1, 2, 3, 4]"
            :key="level"
            :style="{
              width: cellSize + 'px',
              height: cellSize + 'px',
              backgroundColor: levelColor(level),
              borderRadius: '3px',
            }"
          />
          <span class="text-[10px] text-navy-400 ml-1">多</span>
        </div>
      </div>
    </div>

    <!-- Tooltip -->
    <Teleport to="body">
      <div
        v-if="tooltip.visible"
        class="fixed z-50 px-3 py-2 bg-navy-800 text-white text-xs rounded-lg shadow-lg pointer-events-none whitespace-nowrap"
        :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
      >
        <span class="font-medium">{{ tooltip.date }}</span>
        <span class="mx-1.5 text-navy-300">·</span>
        <span>{{ tooltip.minutes > 0 ? `${tooltip.minutes} 分钟` : '未学习' }}</span>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getStudyHeatmap } from '@/api/stats'
import type { StudyHeatmapData, HeatmapDay } from '@/api/stats'

const cellSize = 14
const cellGap = 3

const heatmapData = ref<StudyHeatmapData | null>(null)

const tooltip = ref({ visible: false, x: 0, y: 0, date: '', minutes: 0 })

const dayLabels = ['', '一', '', '三', '', '五', '']

const LEVEL_COLORS = [
  '#ebedf0',
  '#9be9a8',
  '#40c463',
  '#30a14e',
  '#216e39',
]

function levelColor(level: number): string {
  return LEVEL_COLORS[level] || LEVEL_COLORS[0]
}

// Arrange dailyData into weeks (7 days per column, starting from Monday)
const weeks = computed(() => {
  const data = heatmapData.value?.dailyData
  if (!data || data.length === 0) return []

  const result: (HeatmapDay | null)[][] = []
  let currentWeek: (HeatmapDay | null)[] = []

  const firstDate = new Date(data[0].date)
  let firstDow = firstDate.getDay()
  firstDow = firstDow === 0 ? 6 : firstDow - 1

  for (let i = 0; i < firstDow; i++) {
    currentWeek.push(null)
  }

  for (const day of data) {
    currentWeek.push(day)
    if (currentWeek.length === 7) {
      result.push(currentWeek)
      currentWeek = []
    }
  }

  if (currentWeek.length > 0) {
    while (currentWeek.length < 7) {
      currentWeek.push(null)
    }
    result.push(currentWeek)
  }

  return result
})

// Compute month labels
const monthLabels = computed(() => {
  const data = heatmapData.value?.dailyData
  if (!data || data.length === 0) return []

  const labels: { label: string; width: number }[] = []
  const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

  const weekStartMonths: number[] = []
  for (const week of weeks.value) {
    const firstDay = week.find(d => d !== null)
    if (firstDay) {
      weekStartMonths.push(new Date(firstDay.date).getMonth())
    }
  }

  let i = 0
  while (i < weekStartMonths.length) {
    const month = weekStartMonths[i]
    let span = 0
    while (i + span < weekStartMonths.length && weekStartMonths[i + span] === month) {
      span++
    }
    labels.push({
      label: monthNames[month],
      width: span * cellSize + (span - 1) * cellGap,
    })
    i += span
  }

  return labels
})

function showTooltip(event: MouseEvent, day: HeatmapDay | null) {
  if (!day) return
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  tooltip.value = {
    visible: true,
    x: rect.left + rect.width / 2 - 50,
    y: rect.top - 50,
    date: formatDateLabel(day.date),
    minutes: day.minutes,
  }
}

function hideTooltip() {
  tooltip.value.visible = false
}

function formatDateLabel(dateStr: string): string {
  const d = new Date(dateStr)
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${d.getMonth() + 1}月${d.getDate()}日 ${weekdays[d.getDay()]}`
}

onMounted(async () => {
  try {
    const res = await getStudyHeatmap(180)
    heatmapData.value = res.data
  } catch (e) {
    console.error('Failed to load heatmap:', e)
  }
})
</script>
