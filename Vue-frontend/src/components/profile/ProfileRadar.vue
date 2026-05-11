<template>
  <div class="relative w-full h-full flex items-center justify-center">
    <svg :viewBox="`0 0 ${viewBoxSize} ${viewBoxSize}`" class="w-full h-full">
      <!-- Background rings -->
      <g v-for="ring in 5" :key="ring">
        <polygon
          :points="ringPoints(ring * 20)"
          fill="none"
          stroke="rgba(26, 40, 71, 0.06)"
          stroke-width="1"
        />
      </g>

      <!-- Center cross lines (bipolar reference) -->
      <line :x1="center" :y1="center - maxRadius" :x2="center" :y2="center + maxRadius"
        stroke="rgba(26, 40, 71, 0.08)" stroke-width="0.5" stroke-dasharray="4 4" />
      <line :x1="center - maxRadius" :y1="center" :x2="center + maxRadius" :y2="center"
        stroke="rgba(26, 40, 71, 0.08)" stroke-width="0.5" stroke-dasharray="4 4" />

      <!-- Axis lines -->
      <line v-for="(_, i) in axisLabels" :key="'axis-' + i"
        :x1="center" :y1="center"
        :x2="axisPoint(i, 100).x" :y2="axisPoint(i, 100).y"
        stroke="rgba(26, 40, 71, 0.08)" stroke-width="1"
      />

      <!-- Data polygon -->
      <polygon
        :points="dataPolygon"
        fill="rgba(65, 100, 178, 0.15)"
        stroke="rgba(65, 100, 178, 0.6)"
        stroke-width="2"
        stroke-linejoin="round"
        class="transition-all duration-700"
      />

      <!-- Data points -->
      <circle v-for="(pt, i) in dataPoints" :key="'point-' + i"
        :cx="pt.x" :cy="pt.y" r="4"
        fill="rgba(65, 100, 178, 0.8)"
        stroke="white" stroke-width="2"
        class="transition-all duration-700"
      />

      <!-- Labels -->
      <text v-for="(label, i) in axisLabels" :key="'label-' + i"
        :x="labelPoint(i).x" :y="labelPoint(i).y"
        text-anchor="middle" dominant-baseline="middle"
        class="text-[11px] fill-navy-500 font-body select-none">
        {{ label }}
      </text>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  dimensions: Record<string, any>
}>()

const viewBoxSize = 360
const size = 300
const center = viewBoxSize / 2
const maxRadius = 110

const axisLabels = ['感知 <-> 直觉', '视觉 <-> 言语', '活跃 <-> 沉思', '循序 <-> 全局']

const fsKeys = ['sensing_vs_intuitive', 'visual_vs_verbal', 'active_vs_reflective', 'sequential_vs_global']

function axisPoint(index: number, value: number) {
  const angle = (Math.PI * 2 * index) / axisLabels.length - Math.PI / 2
  const r = (value / 100) * maxRadius
  return {
    x: center + r * Math.cos(angle),
    y: center + r * Math.sin(angle),
  }
}

function ringPoints(value: number) {
  return axisLabels.map((_, i) => {
    const p = axisPoint(i, value)
    return `${p.x},${p.y}`
  }).join(' ')
}

const dataValues = computed(() => {
  const d = props.dimensions
  return fsKeys.map(key => {
    const val = d[key] ?? 0
    // Map -1..+1 to 0..100 (0 in model = 50 on radar)
    return ((val + 1) / 2) * 100
  })
})

const dataPolygon = computed(() => {
  return dataValues.value.map((v, i) => {
    const p = axisPoint(i, v)
    return `${p.x},${p.y}`
  }).join(' ')
})

const dataPoints = computed(() => {
  return dataValues.value.map((v, i) => axisPoint(i, v))
})

function labelPoint(index: number) {
  const angle = (Math.PI * 2 * index) / axisLabels.length - Math.PI / 2
  const r = maxRadius + 28
  return {
    x: center + r * Math.cos(angle),
    y: center + r * Math.sin(angle),
  }
}
</script>
