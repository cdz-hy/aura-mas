<template>
  <div class="space-y-6 animate-fade-in-up">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="section-title">学习计划</h1>
        <p class="text-sm text-navy-400 mt-1">管理你的学习计划，或创建新的学习路径</p>
      </div>
      <button class="btn-primary" @click="createNewPlan" :disabled="creating">
        <svg class="w-4 h-4 inline mr-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        {{ creating ? '创建中...' : '新建计划' }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center h-40">
      <svg class="w-8 h-8 text-navy-300 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" class="opacity-25" /><path d="M4 12a8 8 0 018-8" class="opacity-75" stroke-linecap="round" />
      </svg>
    </div>

    <!-- Empty state -->
    <div v-else-if="plans.length === 0" class="card p-12 text-center">
      <svg class="w-16 h-16 mx-auto text-navy-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
      </svg>
      <h3 class="mt-4 text-lg font-semibold text-navy-600">还没有学习计划</h3>
      <p class="mt-2 text-navy-400">点击「新建计划」开始你的学习之旅</p>
    </div>

    <!-- Plan list -->
    <div v-else class="grid gap-4">
      <div
        v-for="plan in plans"
        :key="plan.id"
        class="card p-5 cursor-pointer transition-all duration-200 hover:border-navy-300 hover:shadow-paper-hover group border-l-4"
        :class="statusBorderColor(plan.status)"
        @click="router.push(`/plan/${plan.id}`)"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1 min-w-0">
            <h3 class="font-display text-base font-semibold text-navy-800 group-hover:text-navy-900 truncate">
              {{ plan.title || '未命名计划' }}
            </h3>
            <p v-if="extractGoal(plan)" class="text-sm text-navy-400 mt-1 truncate">
              {{ extractGoal(plan).slice(0, 60) }}{{ extractGoal(plan).length > 60 ? '...' : '' }}
            </p>
            <div class="flex items-center gap-3 mt-2">
              <span class="text-xs px-2.5 py-1 rounded-full" :class="statusClass(plan.status)">
                {{ statusText(plan.status) }}
              </span>
              <span class="text-xs text-navy-400">{{ relativeTime(plan.updatedAt) }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2 ml-4">
            <button
              class="p-2 rounded-lg text-navy-300 hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100"
              @click.stop="removePlan(plan.id)"
              title="删除计划"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Resource stats + Progress bar -->
        <div class="mt-3 flex items-center justify-between gap-4">
          <span class="text-xs text-navy-400 flex-shrink-0">
            {{ planResourceStats[plan.id]?.total || 0 }} 个资源 · {{ planResourceStats[plan.id]?.completed || 0 }} 已完成
          </span>
          <div class="flex items-center gap-2 flex-1 max-w-[200px]">
            <div class="flex-1 h-1.5 bg-navy-100 rounded-full overflow-hidden">
              <div class="h-full bg-gradient-to-r from-navy-400 to-sage-500 rounded-full transition-all duration-500" :style="{ width: `${getPlanProgress(plan)}%` }"></div>
            </div>
            <span class="text-xs font-medium text-navy-600 w-8 text-right">{{ getPlanProgress(plan) }}%</span>
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getPlans, createPlan, deletePlan } from '@/api/plan'
import { getPlanResources, getProgressByPlan } from '@/api/resource'
import type { LearningPlan } from '@/types/plan'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const router = useRouter()
const plans = ref<LearningPlan[]>([])
const planProgressMap = ref<Record<number, number>>({})
const planResourceStats = ref<Record<number, { total: number; completed: number }>>({})
const loading = ref(true)

function extractGoal(plan: LearningPlan): string {
  const lg = plan.learningGoal
  if (!lg) return ''
  let obj: any = lg
  if (typeof lg === 'string') {
    try { obj = JSON.parse(lg) } catch { return '' }
  }
  if (typeof obj === 'string') return obj
  return obj.initial || obj.raw || obj.final_goal || ''
}

function relativeTime(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay === 1) return '昨天'
  if (diffDay < 30) return `${diffDay}天前`
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function statusBorderColor(status: number): string {
  const map: Record<number, string> = {
    0: 'border-l-navy-300',
    1: 'border-l-amber-400',
    2: 'border-l-blue-400',
    3: 'border-l-blue-500',
    4: 'border-l-emerald-500',
  }
  return map[status] || map[0]
}

const creating = ref(false)
const showDeleteConfirm = ref(false)
const deletingPlanId = ref<number | null>(null)

async function loadPlans() {
  loading.value = true
  try {
    const res = await getPlans({ page: 1, size: 50 })
    plans.value = res.data?.records || []
    // 加载每个计划的进度
    await loadAllProgress()
  } catch (e) {
    console.error('Failed to load plans:', e)
  } finally {
    loading.value = false
  }
}

async function loadAllProgress() {
  const map: Record<number, number> = {}
  const stats: Record<number, { total: number; completed: number }> = {}
  await Promise.all(plans.value.map(async (plan) => {
    try {
      const [resRes, progRes] = await Promise.all([
        getPlanResources(plan.id),
        getProgressByPlan(plan.id),
      ])
      const total = (resRes.data || []).filter((r: any) => r.status >= 2).length
      const completed = (progRes.data || []).filter((p: any) => p.status === 2).length
      map[plan.id] = total > 0 ? Math.round((completed / total) * 100) : 0
      stats[plan.id] = { total, completed }
    } catch {
      map[plan.id] = 0
      stats[plan.id] = { total: 0, completed: 0 }
    }
  }))
  planProgressMap.value = map
  planResourceStats.value = stats
}

function getPlanProgress(plan: LearningPlan): number {
  return planProgressMap.value[plan.id] ?? 0
}

async function createNewPlan() {
  creating.value = true
  try {
    const res = await createPlan({
      title: '新学习计划',
      learningGoal: { raw: '' },
    })
    const planId = res.data?.id
    if (planId) {
      router.push(`/plan/${planId}`)
    }
  } catch (e) {
    console.error('Failed to create plan:', e)
  } finally {
    creating.value = false
  }
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

function statusClass(status: number) {
  const map: Record<number, string> = {
    0: 'bg-navy-100 text-navy-500',
    1: 'bg-amber-100 text-amber-600',
    2: 'bg-blue-100 text-blue-600',
    3: 'bg-sage-100 text-sage-600',
    4: 'bg-emerald-100 text-emerald-600',
  }
  return map[status] || map[0]
}

function statusText(status: number) {
  const map: Record<number, string> = {
    0: '待规划', 1: '生成中', 2: '待确认', 3: '学习中', 4: '已完成',
  }
  return map[status] || '未知'
}

onMounted(loadPlans)
</script>
