<template>
  <div class="space-y-6 animate-fade-in-up">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="section-title">学习计划</h1>
        <p class="text-sm text-navy-400 mt-1">管理你的学习计划，或创建新的学习路径</p>
      </div>
      <div class="flex items-center gap-3">
        <!-- View Toggle -->
        <div v-if="plans.length > 0" class="view-toggle-container">
          <button
            class="view-toggle-btn"
            :class="{ active: viewMode === 'card' }"
            @click="switchView('card')"
            title="卡片视图"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7" rx="1.5" />
              <rect x="14" y="3" width="7" height="7" rx="1.5" />
              <rect x="3" y="14" width="7" height="7" rx="1.5" />
              <rect x="14" y="14" width="7" height="7" rx="1.5" />
            </svg>
          </button>
          <button
            class="view-toggle-btn"
            :class="{ active: viewMode === 'list' }"
            @click="switchView('list')"
            title="列表视图"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>
        <button class="btn-primary" @click="createNewPlan" :disabled="creating">
          <svg class="w-4 h-4 inline mr-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          {{ creating ? '创建中...' : '新建计划' }}
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center h-40">
      <svg class="w-8 h-8 text-navy-300 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" class="opacity-25" /><path d="M4 12a8 8 0 018-8" class="opacity-75" stroke-linecap="round" />
      </svg>
    </div>

    <!-- Empty state -->
    <div v-else-if="plans.length === 0" class="card p-12 text-center flex flex-col items-center justify-center min-h-[400px] bg-gradient-to-br from-white to-navy-50/50 border-dashed border-2 border-navy-200">
      <div class="w-20 h-20 bg-white shadow-sm rounded-full flex items-center justify-center mb-6 border border-navy-100">
        <svg class="w-10 h-10 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
        </svg>
      </div>
      <h3 class="text-xl font-display font-semibold text-navy-800">开启知识探索之旅</h3>
      <p class="mt-2 text-navy-500 max-w-sm mb-8">您目前还没有创建任何学习计划。点击下方按钮，让 AI 为您量身定制一条专属的个性化学习路径吧！</p>
      <button class="btn-primary shadow-lg shadow-navy-600/20 px-8 py-3 text-base" @click="createNewPlan" :disabled="creating">
        <svg class="w-5 h-5 inline mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        {{ creating ? 'AI 正在规划中...' : '创建第一个学习计划' }}
      </button>
    </div>

    <!-- Plan List Container with transition -->
    <transition name="view-fade" mode="out-in">
      <!-- Plan list - Card View -->
      <div v-if="viewMode === 'card'" key="card" class="plan-grid grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
        <div
          v-for="(plan, index) in plans"
          :key="plan.id"
          class="plan-card flex flex-col gap-4 p-6 rounded-2xl border border-navy-100/60 bg-white hover:border-navy-300 hover:shadow-xl hover:shadow-navy-200/40 hover:-translate-y-1 transition-all duration-300 group cursor-pointer relative overflow-hidden"
          :style="{ animationDelay: `${index * 60}ms` }"
          @click="router.push(`/plan/${plan.id}`)"
        >
          <!-- Top section: Icon and Title -->
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-4 min-w-0 pr-16">
              <div class="w-12 h-12 rounded-[14px] flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform duration-500 shadow-sm" :class="(plan.status) === 4 ? 'bg-emerald-50 text-emerald-500' : 'bg-gradient-to-br from-navy-50 to-navy-100 text-navy-600'">
                <!-- 优先显示自定义图标 -->
                <div v-if="getPlanIcon(plan)" class="w-6 h-6" v-html="getPlanIcon(plan)"></div>
                <svg v-else-if="(plan.status) === 4" class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
                <svg v-else class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                </svg>
              </div>
              <div class="min-w-0 flex-1">
                <h3 class="font-display font-bold text-navy-800 truncate group-hover:text-navy-600 transition-colors text-lg" :title="plan.title || '未命名计划'">{{ plan.title || '未命名计划' }}</h3>
                <div class="flex items-center gap-2 mt-1">
                  <span class="text-[11px] px-2 py-0.5 rounded-full font-medium" :class="statusClass(plan.status)">
                    {{ statusText(plan.status) }}
                  </span>
                  <span class="text-xs text-navy-400 font-medium whitespace-nowrap">{{ formatDate(plan.createdAt) }}</span>
                </div>
              </div>
            </div>

            <!-- Complete & Delete buttons -->
            <div class="absolute top-5 right-4 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-1 group-hover:translate-y-0 z-10">
              <!-- Complete button -->
              <button
                v-if="(plan.status) !== 4"
                class="p-2 rounded-xl text-emerald-400 bg-emerald-50/50 border border-emerald-100/50 hover:text-white hover:bg-emerald-500 hover:border-emerald-500 transition-all shadow-sm"
                @click.stop="confirmCompletePlan(plan.id)"
                title="标记为已完成"
              >
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
              </button>
              <!-- Delete button -->
              <button
                class="p-2 rounded-xl text-red-400 bg-red-50/50 border border-red-100/50 hover:text-white hover:bg-red-500 hover:border-red-500 transition-all shadow-sm"
                @click.stop="removePlan(plan.id)"
                title="删除计划"
              >
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Bottom section: Progress -->
          <div class="mt-2 flex items-center gap-4">
            <div class="flex-1 h-2 bg-navy-50 rounded-full overflow-hidden relative">
              <div class="absolute inset-y-0 left-0 bg-gradient-to-r from-navy-400 to-navy-600 rounded-full transition-all duration-700 ease-out" :class="getPlanProgress(plan) === 100 ? 'from-emerald-400 to-emerald-500' : ''" :style="{ width: `${getPlanProgress(plan)}%` }"></div>
            </div>
            <span class="text-sm font-display font-bold w-12 text-right" :class="getPlanProgress(plan) === 100 ? 'text-emerald-500' : 'text-navy-600'">{{ getPlanProgress(plan) }}%</span>
          </div>
        </div>
      </div>

      <!-- Plan list - List View (Optimized layout, spacious and high-end) -->
      <div v-else key="list" class="space-y-4">
        <div
          v-for="(plan, index) in plans"
          :key="plan.id"
          class="plan-list-item group cursor-pointer relative"
          :style="{ animationDelay: `${index * 40}ms` }"
          @click="router.push(`/plan/${plan.id}`)"
        >
          <div class="flex items-center justify-between p-6 sm:p-7 rounded-2xl border border-navy-100/60 bg-white hover:border-navy-300 hover:shadow-xl hover:shadow-navy-200/30 hover:-translate-y-1 transition-all duration-300 relative gap-6">
            <div class="flex items-center gap-5 min-w-0 flex-1">
              <!-- Icon -->
              <div class="w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform duration-500 shadow-sm" :class="(plan.status) === 4 ? 'bg-emerald-50 text-emerald-500' : 'bg-gradient-to-br from-navy-50 to-navy-100 text-navy-600'">
                <!-- 优先显示自定义图标 -->
                <div v-if="getPlanIcon(plan)" class="w-7 h-7" v-html="getPlanIcon(plan)"></div>
                <svg v-else-if="(plan.status) === 4" class="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
                <svg v-else class="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                </svg>
              </div>

              <!-- Content details -->
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-3 flex-wrap">
                  <h3 class="font-display font-bold text-navy-800 text-lg group-hover:text-navy-600 transition-colors truncate" :title="plan.title || '未命名计划'">
                    {{ plan.title || '未命名计划' }}
                  </h3>
                  <span class="text-[11px] px-2.5 py-0.5 rounded-full font-semibold flex-shrink-0 shadow-sm" :class="statusClass(plan.status)">
                    {{ statusText(plan.status) }}
                  </span>
                </div>
                <div class="flex items-center gap-4 mt-2.5 text-xs text-navy-400 font-medium">
                  <span class="flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
                    </svg>
                    {{ formatDate(plan.createdAt) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Progress bar (aligned on same vertical line, shifted left from buttons) -->
            <div class="hidden sm:flex items-center gap-3 w-48 md:w-64 flex-shrink-0 mr-32">
              <div class="flex-1 h-2.5 bg-navy-50 rounded-full overflow-hidden relative shadow-inner">
                <div class="absolute inset-y-0 left-0 bg-gradient-to-r from-navy-400 to-navy-600 rounded-full transition-all duration-750 ease-out" :class="getPlanProgress(plan) === 100 ? 'from-emerald-400 to-emerald-500' : ''" :style="{ width: `${getPlanProgress(plan)}%` }"></div>
              </div>
              <span class="text-sm font-display font-extrabold w-12 text-right" :class="getPlanProgress(plan) === 100 ? 'text-emerald-500' : 'text-navy-600'">
                {{ getPlanProgress(plan) }}%
              </span>
            </div>

            <!-- Default Arrow indicator (Stays visible on hover next to buttons) -->
            <div class="absolute right-6 top-1/2 -translate-y-1/2 p-1 rounded-full text-navy-300 group-hover:text-navy-400 transition-all duration-300">
              <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M9 18l6-6-6-6"/>
              </svg>
            </div>

            <!-- Hover Actions (Same as Card View: Complete & Delete buttons, positioned left of the arrow) -->
            <div class="absolute right-16 top-1/2 -translate-y-[44%] group-hover:-translate-y-1/2 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-all duration-300 z-10">
              <!-- Complete button -->
              <button
                v-if="(plan.status) !== 4"
                class="p-2 rounded-xl text-emerald-400 bg-emerald-50/50 border border-emerald-100/50 hover:text-white hover:bg-emerald-500 hover:border-emerald-500 transition-all shadow-sm"
                @click.stop="confirmCompletePlan(plan.id)"
                title="标记为已完成"
              >
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
              </button>
              <!-- Delete button -->
              <button
                class="p-2 rounded-xl text-red-400 bg-red-50/50 border border-red-100/50 hover:text-white hover:bg-red-500 hover:border-red-500 transition-all shadow-sm"
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
    </transition>

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

    <ConfirmDialog
      :visible="showCompleteConfirm"
      title="标记计划为已完成"
      :message="`确定要将学习计划「${plans.find(p => p.id === completingPlanId)?.title || ''}」标记为已完全学习完成吗？这将会将其关联的所有子学习资源状态均标记为已完成。`"
      confirm-text="确认完成"
      cancel-text="取消"
      type="default"
      @confirm="handleCompleteConfirm"
      @cancel="handleCompleteCancel"
    />

    <!-- AI 学习顾问建议云朵（Teleport 到 body，避免被父容器 transform 影响 fixed 定位） -->
    <Teleport to="body">
      <AdvisorSuggestionCloud @open-chat="openAdvisor" />
    </Teleport>

    <!-- AI 学习顾问 -->
    <PlanAdvisorChat ref="planAdvisorRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { getPlans, createPlan, deletePlan, updatePlan } from '@/api/plan'
import { getPlanResources, getProgressByPlan, markResourceComplete, getBatchProgress, markAllComplete } from '@/api/resource'
import { getDashboardStats } from '@/api/stats'
import { tracker } from '@/utils/tracker'
import type { LearningPlan } from '@/types/plan'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import PlanAdvisorChat from '@/components/plan/PlanAdvisorChat.vue'
import AdvisorSuggestionCloud from '@/components/plan/AdvisorSuggestionCloud.vue'

const router = useRouter()
const plans = ref<LearningPlan[]>([])
const planProgressMap = ref<Record<number, number>>({}) // planId -> progress percentage
const planStatsMap = ref<Record<number, { completed: number; total: number }>>({}) // planId -> resource stats
const loading = ref(true)
const creating = ref(false)
const showDeleteConfirm = ref(false)
const deletingPlanId = ref<number | null>(null)
const showCompleteConfirm = ref(false)
const completingPlanId = ref<number | null>(null)
const viewMode = ref<'card' | 'list'>(localStorage.getItem('planViewMode') as 'card' | 'list' || 'card')
const isSwitching = ref(false)

function switchView(mode: 'card' | 'list') {
  if (viewMode.value === mode || isSwitching.value) return
  isSwitching.value = true
  viewMode.value = mode
  localStorage.setItem('planViewMode', mode)
  setTimeout(() => {
    isSwitching.value = false
  }, 400)
}

async function loadPlans() {
  loading.value = true
  try {
    const res = await getPlans({ page: 1, size: 50 })
    plans.value = res.data?.records || []
    // 加载每个计划的进度与统计信息
    await loadAllProgress()
  } catch (e) {
    console.error('Failed to load plans:', e)
  } finally {
    loading.value = false
  }
}

async function loadAllProgress() {
  const map: Record<number, number> = {}
  const statsMap: Record<number, { completed: number; total: number }> = {}
  const planIds = plans.value.map(p => p.id)
  if (planIds.length === 0) { planProgressMap.value = map; planStatsMap.value = statsMap; return }
  try {
    const res = await getBatchProgress(planIds)
    for (const [id, summary] of Object.entries(res.data || {})) {
      const s = summary as any
      map[Number(id)] = Math.min(100, Math.round(s.progress * 100))
      statsMap[Number(id)] = { completed: s.completed, total: s.total }
    }
  } catch {
    for (const id of planIds) { map[id] = 0; statsMap[id] = { completed: 0, total: 0 } }
  }
  planProgressMap.value = map
  planStatsMap.value = statsMap
}

function getPlanProgress(plan: LearningPlan): number {
  return planProgressMap.value[plan.id] ?? 0
}

function getPlanIcon(plan: LearningPlan): string | null {
  if (!plan.planConfig) return null
  try {
    const config = typeof plan.planConfig === 'string' ? JSON.parse(plan.planConfig) : plan.planConfig
    return config?.iconSvg || null
  } catch {
    return null
  }
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
      // 通知学习顾问：计划已创建
      localStorage.setItem('advisor_plan_created', '新创建了学习计划，请分析并给出后续学习建议')
      // 使用 location.href 确保页面完全刷新，信号不会丢失
      window.location.href = `/plan/${planId}`
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

function confirmCompletePlan(id: number) {
  completingPlanId.value = id
  showCompleteConfirm.value = true
}

async function handleCompleteConfirm() {
  if (!completingPlanId.value) return
  const planId = completingPlanId.value
  try {
    await markAllComplete(planId)
    await loadPlans()
  } catch (e) {
    console.error('Failed to complete plan:', e)
  } finally {
    showCompleteConfirm.value = false
    completingPlanId.value = null
  }
}

function handleCompleteCancel() {
  showCompleteConfirm.value = false
  completingPlanId.value = null
}

function statusClass(status: number) {
  const map: Record<number, string> = {
    0: 'bg-gray-100 text-gray-500',                        // 待规划 — 灰色
    1: 'bg-amber-50 text-amber-700 border border-amber-200',  // 生成中 — 琥珀
    2: 'bg-sky-50 text-sky-700 border border-sky-200',        // 待确认 — 天蓝
    3: 'bg-orange-50 text-orange-700 border border-orange-200', // 学习中 — 橙色
    4: 'bg-emerald-50 text-emerald-700 border border-emerald-200', // 已完成 — 翡翠绿
  }
  return map[status] || map[0]
}

function statusText(status: number) {
  const map: Record<number, string> = {
    0: '待规划', 1: '生成中', 2: '待确认', 3: '学习中', 4: '已完成',
  }
  return map[status] || '未知'
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function handlePlanIconUpdated(e: Event) {
  const detail = (e as CustomEvent).detail
  if (detail && detail.planId) {
    const planItem = plans.value.find(p => p.id === detail.planId)
    if (planItem) {
      planItem.planConfig = detail.planConfig
    }
  }
}

// AI 学习顾问
const planAdvisorRef = ref<any>(null)

async function openAdvisor() {
  if (planAdvisorRef.value) {
    planAdvisorRef.value.openChat()
  }
}

onMounted(async () => {
  await loadPlans()

  // 追踪页面浏览
  tracker.trackPageView({ page: 'plans' })

  window.addEventListener('plan-icon-updated', handlePlanIconUpdated)
})

onBeforeUnmount(() => {
  window.removeEventListener('plan-icon-updated', handlePlanIconUpdated)
})
</script>

<style scoped>
/* View Toggle Container */
.view-toggle-container {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  border-radius: 12px;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.06);
}

.view-toggle-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 32px;
  border-radius: 9px;
  color: #94a3b8;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1;
}

.view-toggle-btn:hover {
  color: #64748b;
}

.view-toggle-btn.active {
  color: #1e293b;
  background: white;
  box-shadow:
    0 1px 3px rgba(0, 0, 0, 0.08),
    0 1px 2px rgba(0, 0, 0, 0.06);
}

.view-toggle-btn.active:hover {
  color: #0f172a;
}

/* Card animation */
.plan-card {
  animation: cardEnter 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes cardEnter {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* List item animation */
.plan-list-item {
  animation: listEnter 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes listEnter {
  from {
    opacity: 0;
    transform: translateX(-12px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* Transition group for view switching */
.view-fade-enter-active {
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.view-fade-leave-active {
  transition: all 0.25s cubic-bezier(0.25, 1, 0.5, 1);
}

.view-fade-enter-from {
  opacity: 0;
  transform: scale(0.98) translateY(12px);
}

.view-fade-leave-to {
  opacity: 0;
  transform: scale(0.98) translateY(-12px);
}

/* Slide up animation */
.slide-up-enter-active {
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.slide-up-leave-active {
  transition: all 0.3s ease-in;
}

.slide-up-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.slide-up-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}

/* Gentle bounce animation */
@keyframes bounceGentle {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

.animate-bounce-gentle {
  animation: bounceGentle 2s ease-in-out infinite;
}
</style>
