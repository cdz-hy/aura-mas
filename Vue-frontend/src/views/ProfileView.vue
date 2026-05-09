<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="section-title">我的学习画像</h1>
      <router-link to="/plan/create" class="btn-secondary text-sm">
        更新画像
      </router-link>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Radar chart -->
      <div class="card p-6 animate-fade-in-up">
        <h2 class="font-display text-lg font-semibold text-navy-800 mb-4">Felder-Silverman 学习风格</h2>
        <div class="aspect-square max-w-md mx-auto">
          <ProfileRadar :dimensions="dimensions" />
        </div>
      </div>

      <!-- Dimension details -->
      <div class="space-y-4 animate-fade-in-up" style="animation-delay: 0.1s">
        <!-- Felder-Silverman axes -->
        <div v-for="axis in felderAxes" :key="axis.key" class="card p-5">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-medium text-navy-800">{{ axis.label }}</h3>
            <span class="text-xs px-2 py-0.5 rounded-full"
              :class="Math.abs(dimensions[axis.key] ?? 0) >= 0.2 ? 'bg-sage-100 text-sage-700' : 'bg-navy-50 text-navy-400'">
              {{ felderAxisLabel(axis.key, dimensions[axis.key] ?? 0) }}
            </span>
          </div>
          <div class="flex items-center gap-3 mt-1">
            <span class="text-xs text-navy-400 w-14 text-right">{{ axis.negLabel }}</span>
            <div class="flex-1 h-2 bg-navy-100 rounded-full relative">
              <div class="absolute top-0 h-full rounded-full transition-all duration-500"
                :class="(dimensions[axis.key] ?? 0) >= 0 ? 'bg-blue-400' : 'bg-amber-400'"
                :style="barStyle(dimensions[axis.key] ?? 0)">
              </div>
              <div class="absolute top-0 left-1/2 w-0.5 h-full bg-navy-300/30"></div>
            </div>
            <span class="text-xs text-navy-400 w-14">{{ axis.posLabel }}</span>
          </div>
        </div>

        <!-- Auxiliary dimensions -->
        <div v-for="(dim, key) in auxiliaryDetails" :key="key" class="card p-5">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-medium text-navy-800">{{ dim.label }}</h3>
            <span class="text-xs px-2 py-0.5 rounded-full" :class="dim.filled ? 'bg-sage-100 text-sage-700' : 'bg-navy-50 text-navy-400'">
              {{ dim.filled ? '已完善' : '待完善' }}
            </span>
          </div>
          <p class="text-sm text-navy-500">{{ dim.display }}</p>
        </div>
      </div>
    </div>

    <!-- Profile history -->
    <div class="card p-6 mt-6 animate-fade-in-up" style="animation-delay: 0.2s">
      <h2 class="font-display text-lg font-semibold text-navy-800 mb-4">画像演变</h2>
      <div class="text-center py-8 text-navy-300">
        <p class="text-sm">画像会随着你的学习过程自动更新</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import ProfileRadar from '@/components/profile/ProfileRadar.vue'
import { getCurrentProfile } from '@/api/user'
import {
  PROFILE_DIMENSION_LABELS,
  GOAL_ORIENTATION_LABELS,
  felderAxisLabel,
} from '@/types/profile'

const dimensions = reactive<Record<string, any>>({})

const felderAxes = [
  { key: 'sensing_vs_intuitive', label: '感知-直觉', negLabel: '感知型', posLabel: '直觉型' },
  { key: 'visual_vs_verbal', label: '视觉-言语', negLabel: '视觉型', posLabel: '言语型' },
  { key: 'active_vs_reflective', label: '活跃-沉思', negLabel: '活跃型', posLabel: '沉思型' },
  { key: 'sequential_vs_global', label: '循序-全局', negLabel: '循序型', posLabel: '全局型' },
]

const auxiliaryKeys = ['knowledge_base', 'interest_tags', 'goal_orientation', 'weak_areas', 'preferred_resource_types']

const auxiliaryDetails = computed(() => {
  const details: Record<string, { label: string; display: string; filled: boolean }> = {}
  for (const key of auxiliaryKeys) {
    const label = PROFILE_DIMENSION_LABELS[key] || key
    const val = dimensions[key]
    let display = '暂未收集'
    let filled = false

    if (val !== undefined && val !== null) {
      filled = true
      if (key === 'goal_orientation') display = GOAL_ORIENTATION_LABELS[val] || val
      else if (Array.isArray(val)) {
        filled = val.length > 0
        display = val.length > 0 ? val.join('、') : '暂未收集'
      }
      else display = String(val)
    }
    details[key] = { label, display, filled }
  }
  return details
})

function barStyle(value: number) {
  const abs = Math.abs(value)
  const width = (abs / 1) * 50 // max 50% width from center
  if (value >= 0) {
    return { left: '50%', width: `${width}%` }
  } else {
    return { left: `${50 - width}%`, width: `${width}%` }
  }
}

onMounted(async () => {
  try {
    const res = await getCurrentProfile()
    const profile = res.data
    if (profile?.learningBehavior) {
      const behavior = typeof profile.learningBehavior === 'string'
        ? JSON.parse(profile.learningBehavior)
        : profile.learningBehavior
      Object.assign(dimensions, behavior)
    }
  } catch (e) {
    console.error('Failed to load profile:', e)
  }
})
</script>
