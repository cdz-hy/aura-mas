<template>
  <div>
    <!-- Welcome header -->
    <div class="mb-8">
      <h1 class="section-title">
        {{ greeting }}，{{ authStore.user?.nickname || '同学' }}
      </h1>
      <p class="mt-1 text-navy-400">继续你的学习之旅</p>
    </div>

    <!-- Stats cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
      <div v-for="(stat, i) in stats" :key="stat.label" class="stat-card animate-fade-in-up" :style="{ animationDelay: `${i * 0.08}s` }">
        <div class="flex items-center justify-between">
          <span class="stat-label">{{ stat.label }}</span>
          <div class="w-9 h-9 rounded-lg flex items-center justify-center" :class="stat.bgClass">
            <div class="w-5 h-5" :class="stat.iconClass" v-html="stat.icon"></div>
          </div>
        </div>
        <span class="stat-value">{{ stat.value }}</span>
      </div>
    </div>

    <!-- Main content grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Recent plans -->
      <div class="lg:col-span-2 card p-6 animate-fade-in-up" style="animation-delay: 0.35s">
        <div class="flex items-center justify-between mb-5">
          <h2 class="font-display text-lg font-semibold text-navy-800">学习计划</h2>
          <router-link to="/plan/create" class="btn-primary text-sm py-1.5 px-4">
            + 新建计划
          </router-link>
        </div>

        <div v-if="plans.length === 0" class="text-center py-12">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-navy-50 flex items-center justify-center">
            <svg class="w-8 h-8 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <p class="text-navy-400 mb-3">还没有学习计划</p>
          <router-link to="/plan/create" class="btn-secondary text-sm">创建第一个计划</router-link>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="plan in plans"
            :key="plan.id"
            class="flex items-center gap-4 p-4 rounded-xl border border-navy-100/50 hover:border-navy-200 hover:shadow-paper transition-all group cursor-pointer"
            @click="router.push(`/plan/${plan.id}`)"
          >
            <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-navy-100 to-navy-200 flex items-center justify-center flex-shrink-0">
              <svg class="w-5 h-5 text-navy-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-medium text-navy-800 truncate group-hover:text-navy-600 transition-colors">{{ plan.title }}</p>
              <div class="flex items-center gap-3 mt-1">
                <span class="text-xs text-navy-400">{{ formatDate(plan.createdAt) }}</span>
                <span class="text-xs px-2 py-0.5 rounded-full" :class="statusClass(plan.status)">
                  {{ statusText(plan.status) }}
                </span>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <div class="w-20 h-1.5 bg-navy-100 rounded-full overflow-hidden">
                <div class="h-full bg-gradient-to-r from-navy-400 to-navy-600 rounded-full transition-all" :style="{ width: `${plan.progress}%` }"></div>
              </div>
              <span class="text-xs text-navy-400 w-10 text-right">{{ Math.round(plan.progress) }}%</span>
              <button
                class="p-1.5 rounded-lg text-navy-300 hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100"
                @click.stop="removePlan(plan.id)"
                title="删除计划"
              >
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Weekly activity -->
      <div class="card p-6 animate-fade-in-up" style="animation-delay: 0.45s">
        <h2 class="font-display text-lg font-semibold text-navy-800 mb-5">本周学习</h2>
        <div class="space-y-3">
          <div v-for="day in weekDays" :key="day.label" class="flex items-center gap-3">
            <span class="text-xs text-navy-400 w-6">{{ day.label }}</span>
            <div class="flex-1 h-5 bg-navy-50 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-500"
                :class="day.minutes > 0 ? 'bg-gradient-to-r from-sage-300 to-sage-500' : ''"
                :style="{ width: `${Math.min(100, (day.minutes / maxMinutes) * 100)}%` }"
              ></div>
            </div>
            <span class="text-xs text-navy-400 w-12 text-right">{{ day.minutes }}分钟</span>
          </div>
        </div>

        <div class="mt-6 pt-5 border-t border-navy-100/50">
          <h3 class="text-sm font-medium text-navy-600 mb-3">最近活动</h3>
          <div class="space-y-2.5">
            <div v-for="(act, i) in recentActivity" :key="i" class="flex items-start gap-3">
              <div class="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" :class="act.color"></div>
              <div>
                <p class="text-sm text-navy-700">{{ act.text }}</p>
                <p class="text-xs text-navy-300">{{ act.time }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="showDeleteConfirm"
      title="删除学习计划"
      :message="`确定要删除学习计划「${plans.find(p => p.id === deletingPlanId)?.title || ''}」吗？该计划下的所有对话、资源和测验记录将一并删除，此操作不可恢复。`"
      confirm-text="确认删除"
      cancel-text="取消"
      type="danger"
      @confirm="handleDeleteConfirm"
      @cancel="handleDeleteCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getPlans, deletePlan } from '@/api/plan'
import { getDashboardStats } from '@/api/stats'
import type { DashboardStats } from '@/api/stats'
import type { LearningPlan } from '@/types/plan'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import dayjs from 'dayjs'

const router = useRouter()
const authStore = useAuthStore()
const plans = ref<LearningPlan[]>([])
const statsData = ref<DashboardStats | null>(null)
const showDeleteConfirm = ref(false)
const deletingPlanId = ref<number | null>(null)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const stats = computed(() => [
  { label: '学习计划', value: statsData.value?.totalPlans ?? plans.value.length, icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>', bgClass: 'bg-blue-50', iconClass: 'text-blue-500' },
  { label: '已完成', value: statsData.value?.completedPlans ?? plans.value.filter(p => p.status === 4).length, icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>', bgClass: 'bg-emerald-50', iconClass: 'text-emerald-500' },
  { label: '学习资源', value: statsData.value?.totalResources ?? 0, icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>', bgClass: 'bg-amber-50', iconClass: 'text-amber-500' },
  { label: '学习时长', value: statsData.value?.totalStudyHours != null ? `${statsData.value.totalStudyHours}h` : '--', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>', bgClass: 'bg-purple-50', iconClass: 'text-purple-500' },
])

const weekDays = [
  { label: '一', minutes: 45 },
  { label: '二', minutes: 90 },
  { label: '三', minutes: 30 },
  { label: '四', minutes: 120 },
  { label: '五', minutes: 60 },
  { label: '六', minutes: 0 },
  { label: '日', minutes: 0 },
]

const maxMinutes = computed(() => Math.max(...weekDays.map(d => d.minutes), 1))

const recentActivity = [
  { text: '完成了「Python基础」模块测验', time: '2小时前', color: 'bg-emerald-400' },
  { text: '生成了新学习计划', time: '昨天', color: 'bg-blue-400' },
  { text: '更新了学习画像', time: '3天前', color: 'bg-amber-400' },
]

function formatDate(date: string) {
  return dayjs(date).format('MM月DD日')
}

function removePlan(id: number) {
  deletingPlanId.value = id
  showDeleteConfirm.value = true
}

async function handleDeleteConfirm() {
  if (!deletingPlanId.value) return
  try {
    await deletePlan(deletingPlanId.value)
    plans.value = plans.value.filter(p => p.id !== deletingPlanId.value)
  } catch (e) {
    console.error('Failed to delete plan:', e)
  } finally {
    showDeleteConfirm.value = false
    deletingPlanId.value = null
  }
}

function handleDeleteCancel() {
  showDeleteConfirm.value = false
  deletingPlanId.value = null
}

function statusText(status: number) {
  return ['待规划', '生成中', '确认中', '学习中', '已完成'][status] || '未知'
}

function statusClass(status: number) {
  return ['bg-gray-100 text-gray-600', 'bg-blue-100 text-blue-600', 'bg-amber-100 text-amber-600', 'bg-emerald-100 text-emerald-600', 'bg-sage-100 text-sage-700'][status] || 'bg-gray-100 text-gray-600'
}

onMounted(async () => {
  try {
    const [plansRes, statsRes] = await Promise.all([
      getPlans({ page: 1, size: 50 }),
      getDashboardStats().catch(() => null),
    ])
    plans.value = plansRes.data?.records || []
    if (statsRes) statsData.value = statsRes.data
  } catch {
    // Use empty state
  }
})
</script>
