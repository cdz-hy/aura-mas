<template>
  <div>
    <!-- Welcome header -->
    <div class="mb-8 flex items-start justify-between">
      <div>
        <h1 class="section-title">
          {{ greeting }}，{{ authStore.user?.nickname || '同学' }}
        </h1>
        <p class="mt-1 text-navy-400 h-6">
          <span class="typewriter" :class="{ 'typewriter-typing': isTyping }">{{ displayedGreeting }}</span>
        </p>
      </div>
      <button
        class="mt-1 flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium transition-all border"
        :class="cloudEnabled
          ? 'bg-violet-50 text-violet-600 border-violet-200 hover:bg-violet-100'
          : 'bg-navy-50 text-navy-400 border-navy-200 hover:bg-navy-100'"
        @click="toggleCloud"
        :title="cloudEnabled ? '关闭画像气泡' : '开启画像气泡'"
      >
        <svg v-if="cloudEnabled" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/></svg>
        <svg v-else class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
        {{ cloudEnabled ? '气泡已开' : '气泡已关' }}
      </button>
    </div>

    <!-- Stats cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
      <div v-for="(stat, i) in stats" :key="stat.label" class="stat-card animate-fade-in-up relative overflow-hidden group cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300 bg-white" :style="{ animationDelay: `${i * 0.08}s` }">
        <!-- Background decorative icon -->
        <div class="absolute -right-6 -bottom-6 w-32 h-32 opacity-[0.04] transition-transform duration-700 group-hover:scale-110 group-hover:-rotate-12 pointer-events-none" :class="stat.iconClass" v-html="stat.icon"></div>
        
        <!-- Background decorative gradient blob -->
        <div class="absolute -left-10 -top-10 w-24 h-24 rounded-full opacity-30 blur-2xl transition-all duration-700 group-hover:scale-150 pointer-events-none" :class="stat.decorationClass"></div>

        <div class="relative z-10 flex items-center justify-between">
          <span class="stat-label group-hover:text-navy-600 transition-colors">{{ stat.label }}</span>
          <div class="w-10 h-10 rounded-xl flex items-center justify-center shadow-sm transition-transform duration-500 group-hover:scale-110 group-hover:rotate-3" :class="stat.bgClass">
            <div class="w-5 h-5" :class="stat.iconClass" v-html="stat.icon"></div>
          </div>
        </div>
        
        <div class="relative z-10 mt-1 flex flex-col">
          <span class="stat-value group-hover:text-navy-900 transition-colors">{{ stat.value }}</span>
          <div class="mt-2 h-1 w-12 rounded-full opacity-60 transition-all duration-500 group-hover:w-16" :class="stat.lineClass"></div>
        </div>
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

        <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-4 max-h-[560px] overflow-y-auto p-1 custom-scrollbar">
          <div
            v-for="plan in plans"
            :key="plan.id"
            class="flex flex-col gap-3 p-5 rounded-2xl border border-navy-100/60 bg-white hover:border-navy-300 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300 group cursor-pointer relative overflow-hidden"
            @click="router.push(`/plan/${plan.id}`)"
          >
            <!-- Top section: Icon and Title -->
            <div class="flex items-start justify-between">
              <div class="flex items-center gap-3 min-w-0 pr-8">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-navy-50 to-navy-100 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                  <div v-if="getPlanIcon(plan)" class="w-5 h-5 flex items-center justify-center" v-html="getPlanIcon(plan)"></div>
                  <svg v-else class="w-5 h-5 text-navy-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                  </svg>
                </div>
                <div class="min-w-0 flex-1">
                  <h3 class="font-semibold text-navy-800 truncate group-hover:text-navy-600 transition-colors text-base" :title="plan.title">{{ plan.title }}</h3>
                  <div class="flex items-center gap-2 mt-0.5">
                    <span class="text-xs text-navy-400">{{ formatDate(plan.createdAt) }}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded-full font-medium" :class="statusClass(plan.displayStatus ?? plan.status)">
                      {{ statusText(plan.displayStatus ?? plan.status) }}
                    </span>
                  </div>
                </div>
              </div>
              
              <!-- Complete button -->
              <button
                v-if="plan.status !== 4 && (plan.displayStatus ?? plan.status) !== 4"
                class="absolute top-4 right-12 p-1.5 rounded-lg text-emerald-400 hover:text-white hover:bg-emerald-500 transition-all opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0 z-10"
                @click.stop="confirmCompletePlan(plan.id)"
                title="标记为已完成"
              >
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
              </button>
              
              <!-- Delete button -->
              <button
                class="absolute top-4 right-4 p-1.5 rounded-lg text-red-400 hover:text-white hover:bg-red-500 transition-all opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0 z-10"
                @click.stop="removePlan(plan.id)"
                title="删除计划"
              >
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                </svg>
              </button>
            </div>

            <!-- Bottom section: Progress -->
            <div class="mt-1 flex items-center gap-3">
              <div class="flex-1 h-1.5 bg-navy-50 rounded-full overflow-hidden">
                <div class="h-full bg-gradient-to-r from-navy-400 to-navy-600 rounded-full transition-all duration-700 ease-out" :style="{ width: `${getPlanProgress(plan)}%` }"></div>
              </div>
              <span class="text-xs font-semibold text-navy-600 w-10 text-right">{{ getPlanProgress(plan) }}%</span>
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
          <div v-if="recentActivity.length > 0" class="space-y-2.5">
            <div v-for="(act, i) in recentActivity" :key="i" class="flex items-start gap-3">
              <div class="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" :class="act.color"></div>
              <div>
                <p class="text-sm text-navy-700">{{ act.text }}</p>
                <p class="text-xs text-navy-300">{{ act.time }}</p>
              </div>
            </div>
          </div>
          <p v-else class="text-sm text-navy-300 text-center py-4">暂无最近活动</p>
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

    <!-- 画像问题气泡 -->
    <ProfileBubble
      v-if="authStore.user?.id && cloudEnabled"
      :user-id="authStore.user.id"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getPlans, deletePlan, updatePlan } from '@/api/plan'
import { getDashboardStats, getGreeting } from '@/api/stats'
import { getPlanResources, getProgressByPlan, markResourceComplete } from '@/api/resource'
import type { DashboardStats } from '@/api/stats'
import type { LearningPlan } from '@/types/plan'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import ProfileBubble from '@/components/dashboard/ProfileBubble.vue'
import dayjs from 'dayjs'

const router = useRouter()
const authStore = useAuthStore()
const plans = ref<LearningPlan[]>([])
const planProgressMap = ref<Record<number, number>>({})
const statsData = ref<DashboardStats | null>(null)
const showDeleteConfirm = ref(false)
const deletingPlanId = ref<number | null>(null)
const showCompleteConfirm = ref(false)
const completingPlanId = ref<number | null>(null)
const dynamicGreeting = ref('继续你的学习之旅')
const displayedGreeting = ref('继续你的学习之旅')
const isTyping = ref(false)

// 画像气泡开关（默认开启）
const CLOUD_ENABLED_KEY = 'profile_cloud_enabled'
const cloudEnabled = ref(localStorage.getItem(CLOUD_ENABLED_KEY) !== 'false')

function toggleCloud() {
  cloudEnabled.value = !cloudEnabled.value
  localStorage.setItem(CLOUD_ENABLED_KEY, String(cloudEnabled.value))
}

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const stats = computed(() => [
  { label: '学习计划', value: statsData.value?.totalPlans ?? plans.value.length, icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>', bgClass: 'bg-blue-50', iconClass: 'text-blue-500', decorationClass: 'bg-blue-200', lineClass: 'bg-blue-300' },
  { label: '已完成', value: statsData.value?.completedPlans ?? plans.value.filter(p => p.status === 4).length, icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>', bgClass: 'bg-emerald-50', iconClass: 'text-emerald-500', decorationClass: 'bg-emerald-200', lineClass: 'bg-emerald-300' },
  { label: '学习资源', value: statsData.value?.totalResources ?? 0, icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>', bgClass: 'bg-amber-50', iconClass: 'text-amber-500', decorationClass: 'bg-amber-200', lineClass: 'bg-amber-300' },
  { label: '学习时长', value: statsData.value?.totalStudyHours != null ? `${statsData.value.totalStudyHours}h` : '--', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>', bgClass: 'bg-purple-50', iconClass: 'text-purple-500', decorationClass: 'bg-purple-200', lineClass: 'bg-purple-300' },
])

const weekDays = computed(() => statsData.value?.weeklyMinutes ?? [
  { label: '周一', minutes: 0 },
  { label: '周二', minutes: 0 },
  { label: '周三', minutes: 0 },
  { label: '周四', minutes: 0 },
  { label: '周五', minutes: 0 },
  { label: '周六', minutes: 0 },
  { label: '周日', minutes: 0 },
])

const maxMinutes = computed(() => Math.max(...weekDays.value.map(d => d.minutes), 1))

const recentActivity = computed(() => statsData.value?.recentActivity ?? [])

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

function confirmCompletePlan(id: number) {
  completingPlanId.value = id
  showCompleteConfirm.value = true
}

async function handleCompleteConfirm() {
  if (!completingPlanId.value) return
  const planId = completingPlanId.value
  try {
    const resRes = await getPlanResources(planId)
    const resources = resRes.data || []
    await Promise.all(resources.map(r => markResourceComplete(planId, r.id).catch(() => {})))
    await updatePlan(planId, { status: 4, displayStatus: 4 })
    await loadDashboard()
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

function statusText(status: number) {
  return ['待规划', '生成中', '确认中', '学习中', '已完成'][status] || '未知'
}

function statusClass(status: number) {
  return ['bg-gray-100 text-gray-600', 'bg-blue-100 text-blue-600', 'bg-amber-100 text-amber-600', 'bg-emerald-100 text-emerald-600', 'bg-sage-100 text-sage-700'][status] || 'bg-gray-100 text-gray-600'
}

async function loadDashboard() {
  try {
    const [plansRes, statsRes] = await Promise.all([
      getPlans({ page: 1, size: 50 }),
      getDashboardStats().catch(() => null),
    ])
    plans.value = plansRes.data?.records || []
    if (statsRes) statsData.value = statsRes.data
    // 加载每个计划的进度
    await loadAllProgress()
    // 获取个性化问候语
    loadGreeting()
  } catch {
    // Use empty state
  }
}

async function loadGreeting() {
  try {
    const userId = authStore.user?.id
    if (userId) {
      const greeting = await getGreeting(userId)
      if (greeting) {
        dynamicGreeting.value = greeting
        // 启动打字机动画
        typewriterEffect(greeting)
      }
    }
  } catch (e) {
    console.warn('获取个性化问候语失败，使用默认值', e)
  }
}

function typewriterEffect(text: string) {
  displayedGreeting.value = ''
  isTyping.value = true
  let i = 0
  const speed = 60 // 每个字符的间隔时间（毫秒）

  function type() {
    if (i < text.length) {
      displayedGreeting.value += text.charAt(i)
      i++
      setTimeout(type, speed)
    } else {
      isTyping.value = false
    }
  }

  type()
}

async function loadAllProgress() {
  const map: Record<number, number> = {}
  await Promise.all(plans.value.map(async (plan) => {
    try {
      const [resRes, progRes] = await Promise.all([
        getPlanResources(plan.id),
        getProgressByPlan(plan.id),
      ])
      const validResourceIds = new Set(
        (resRes.data || [])
          .filter((r: any) => r.status >= 2)
          .map((r: any) => r.id)
      )
      const total = validResourceIds.size
      const completed = (progRes.data || []).filter(
        (p: any) => p.status === 2 && validResourceIds.has(p.resourceId)
      ).length
      map[plan.id] = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0
    } catch {
      map[plan.id] = 0
    }
  }))
  planProgressMap.value = map
}

function getPlanProgress(plan: LearningPlan): number {
  return planProgressMap.value[plan.id] ?? 0
}

function getPlanIcon(planObj: LearningPlan): string | null {
  if (!planObj.planConfig) return null
  try {
    const config = typeof planObj.planConfig === 'string' ? JSON.parse(planObj.planConfig) : planObj.planConfig
    return config?.iconSvg || null
  } catch {
    return null
  }
}

function onVisibilityChange() {
  if (document.visibilityState === 'visible') {
    loadDashboard()
  }
}

onMounted(() => {
  loadDashboard()
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<style scoped>
.typewriter {
  display: inline;
}

.typewriter-typing::after {
  content: '|';
  animation: blink 0.7s infinite;
  color: var(--color-navy-400);
  font-weight: 300;
  margin-left: 1px;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* Custom Scrollbar for Plan List */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: var(--color-navy-200, #e2e8f0);
  border-radius: 20px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: var(--color-navy-300, #cbd5e1);
}
</style>
