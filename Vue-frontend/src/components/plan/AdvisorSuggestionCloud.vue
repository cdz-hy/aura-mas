<template>
  <div class="advisor-cloud-container" v-if="showCloud">
    <!-- 云朵主体 -->
    <div
      class="advisor-cloud"
      :class="{ expanded: isExpanded, fading: isFading }"
      :style="cloudStyle"
      @click="toggleExpand"
    >
      <!-- 云朵形状 + 建议摘要 -->
      <div class="cloud-body">
        <div class="cloud-icon">
          <img src="/学习顾问.png" alt="AI" class="w-6 h-6 rounded-full object-cover" />
        </div>
        <div class="cloud-text">{{ suggestionSummary }}</div>
      </div>

      <!-- 展开后的详细建议 -->
      <transition name="options-pop">
        <div v-if="isExpanded" class="cloud-detail">
          <div class="detail-content">
            <p class="detail-text">{{ suggestionDetail }}</p>
            <div v-if="suggestionPlan" class="detail-plan">
              <p class="plan-title">💡 建议学习计划：{{ suggestionPlan.title }}</p>
              <p class="plan-desc">{{ suggestionPlan.description }}</p>
            </div>
          </div>
          <div class="detail-actions">
            <button
              v-if="suggestionPlan"
              class="action-btn primary"
              @click.stop="acceptSuggestion"
            >
              采纳建议
            </button>
            <button
              class="action-btn secondary"
              @click.stop="openChat"
            >
              继续对话
            </button>
            <button
              class="action-btn ghost"
              @click.stop="dismiss"
            >
              稍后再说
            </button>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboardStats } from '@/api/stats'
import { getPlans } from '@/api/plan'
import { issueTicket } from '@/api/auth'
import { PYTHON_AI_BASE } from '@/api/request'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const uiStore = useUiStore()

// 状态
const showCloud = ref(false)
const isExpanded = ref(false)
const isFading = ref(false)
const suggestionSummary = ref('')
const suggestionDetail = ref('')
const suggestionPlan = ref<{ title: string; description: string; modules: any[] } | null>(null)

// 云朵位置和动画
const position = ref({ x: 0, y: 0 })
let floatTimer: ReturnType<typeof setInterval> | null = null
let checkTimer: ReturnType<typeof setTimeout> | null = null

// 计算云朵样式（定位在容器上，浮动在子元素上）
const containerStyle = computed(() => ({
  right: position.value.x + 'px',
  top: position.value.y + 'px',
}))
const cloudStyle = computed(() => ({}))

// 检测学习变化
async function checkLearningChanges() {
  try {
    const lastCheckKey = 'advisor_cloud_last_check'
    const lastCheckStr = localStorage.getItem(lastCheckKey)
    const lastCheck = lastCheckStr ? JSON.parse(lastCheckStr) : null

    const [statsRes, plansRes] = await Promise.all([
      getDashboardStats().catch(() => ({ data: null })),
      getPlans({ page: 1, size: 10 }).catch(() => ({ data: { records: [] } }))
    ])

    const stats = statsRes.data
    const plans = plansRes.data?.records || []

    console.log('[AdvisorCloud] checkLearningChanges', {
      lastCheck,
      currentPlanCount: plans.length,
      stats: stats ? { todayDurationSeconds: stats.todayDurationSeconds, totalStudyHours: stats.totalStudyHours } : null,
    })

    let hasChange = false
    let changeReason = ''

    if (lastCheck && stats) {
      const lastSeconds = lastCheck.todayDurationSeconds || 0
      const currentSeconds = stats.todayDurationSeconds || 0
      const lastMinutes = Math.floor(lastSeconds / 60)
      const currentMinutes = Math.floor(currentSeconds / 60)
      if (currentMinutes - lastMinutes > 30) {
        hasChange = true
        changeReason = `学习时长增加了 ${currentMinutes - lastMinutes} 分钟`
      }

      const lastStudyHours = lastCheck.totalStudyHours || 0
      const currentStudyHours = stats.totalStudyHours || 0
      if (currentStudyHours > lastStudyHours) {
        hasChange = true
        changeReason = `总学习时长增加到 ${currentStudyHours} 小时`
      }

      const lastPlanCount = lastCheck.planCount || 0
      const currentPlanCount = plans.length
      if (currentPlanCount > lastPlanCount) {
        hasChange = true
        changeReason = `新增了 ${currentPlanCount - lastPlanCount} 个学习计划`
      }
    } else if (!lastCheck && plans.length > 0) {
      hasChange = true
      changeReason = '发现你有学习计划'
    }

    // 保存当前数据
    localStorage.setItem(lastCheckKey, JSON.stringify({
      todayDurationSeconds: stats?.todayDurationSeconds || 0,
      totalStudyHours: stats?.totalStudyHours || 0,
      planCount: plans.length,
      timestamp: Date.now()
    }))

    console.log('[AdvisorCloud] 检测结果', { hasChange, changeReason })

    if (hasChange) {
      localStorage.setItem('advisor_cloud_change_reason', changeReason)
      await fetchAISuggestion(stats, plans, changeReason)
    }
  } catch (e) {
    console.error('Check learning changes failed:', e)
  }
}

// 获取 AI 建议
async function fetchAISuggestion(stats: any, plans: any[], changeReason: string) {
  try {
    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket

    const response = await fetch(`${PYTHON_AI_BASE}/api/ai/plan-advisor/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ticket}`
      },
      body: JSON.stringify({
        stats: stats,
        plans: plans,
        userMessage: `[系统自动触发] 检测到学生学习情况变化：${changeReason}。请主动分析学生的学习情况，根据学习计划和资源内容，主动提出建议。如果需要新学习计划，请在 plan_suggestion 中提供。`
      })
    })

    if (response.ok) {
      const data = await response.json()
      console.log('[AdvisorCloud] AI 返回完整数据:', JSON.stringify(data).slice(0, 300))

      suggestionSummary.value = extractSummary(data.message)
      suggestionDetail.value = data.message

      // 如果有计划建议
      if (data.type === 'plan_suggestion' && data.suggestion) {
        suggestionPlan.value = data.suggestion
      }

      // 随机位置（右上角区域）
      position.value = {
        x: 20 + Math.random() * 60,
        y: 80 + Math.random() * 40
      }

      // 显示云朵
      showCloud.value = true
      startFloating()
      console.log('[AdvisorCloud] 云朵已显示', { showCloud: showCloud.value, position: position.value, summary: suggestionSummary.value.slice(0, 40) })
    }
  } catch (e) {
    console.error('Fetch AI suggestion failed:', e)
  }
}

// 提取摘要（前30个字）
function extractSummary(message: string): string {
  if (!message) return '有些建议想告诉你'
  // 去掉标点符号
  const clean = message.replace(/[，。！？、；：""''（）\[\]]/g, '')
  if (clean.length <= 30) return clean
  return clean.substring(0, 30) + '...'
}

// 浮动动画（双轴无规则运动）
function startFloating() {
  let phaseX = Math.random() * Math.PI * 2
  let phaseY = Math.random() * Math.PI * 2
  const speedX = 0.015 + Math.random() * 0.02
  const speedY = 0.02 + Math.random() * 0.015
  floatTimer = setInterval(() => {
    phaseX += speedX
    phaseY += speedY
    position.value = {
      x: position.value.x + Math.sin(phaseX) * 0.8,
      y: position.value.y + Math.cos(phaseY) * 0.6,
    }
  }, 50)
}

function stopFloating() {
  if (floatTimer) {
    clearInterval(floatTimer)
    floatTimer = null
  }
}

// 切换展开
function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

// 采纳建议
async function acceptSuggestion() {
  if (!suggestionPlan.value) return

  try {
    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket

    const response = await fetch(`${PYTHON_AI_BASE}/api/ai/plan-advisor/create-plan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ticket}`
      },
      body: JSON.stringify({
        title: suggestionPlan.value.title,
        description: suggestionPlan.value.description || '',
        modules: suggestionPlan.value.modules || []
      })
    })

    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        // 通知学习顾问
        localStorage.setItem('advisor_plan_created', `通过顾问建议创建了学习计划「${suggestionPlan.value?.title}」`)
        router.push(`/plan/${data.planId}`)
        dismiss()
      }
    }
  } catch (e) {
    console.error('Accept suggestion failed:', e)
  }
}

// 打开对话
function openChat() {
  uiStore.toggleAdvisorPanel()
  dismiss()
}

// 关闭/消失
function dismiss() {
  isFading.value = true
  stopFloating()
  setTimeout(() => {
    showCloud.value = false
    isFading.value = false
    isExpanded.value = false
  }, 500)
}

// 生命周期
onMounted(() => {
  // 检查是否有计划创建信号（由 PlanCreateView 写入）
  const planCreated = localStorage.getItem('advisor_plan_created')
  if (planCreated) {
    localStorage.removeItem('advisor_plan_created')
    // 直接调用 AI 分析
    setTimeout(async () => {
      const [statsRes, plansRes] = await Promise.all([
        getDashboardStats().catch(() => ({ data: null })),
        getPlans({ page: 1, size: 10 }).catch(() => ({ data: { records: [] } }))
      ])
      await fetchAISuggestion(statsRes.data, plansRes.data?.records || [], planCreated)
    }, 1000)
  } else {
    checkTimer = setTimeout(() => {
      checkLearningChanges()
    }, 2000)
  }
})

onUnmounted(() => {
  stopFloating()
  if (checkTimer) {
    clearTimeout(checkTimer)
  }
})
</script>

<style scoped>
.advisor-cloud-container {
  position: fixed;
  z-index: 50;
  pointer-events: none;
  top: 200px;
  right: 60px;
}

.advisor-cloud {
  position: relative;
  pointer-events: auto;
  cursor: pointer;
  transition: opacity 0.5s ease;
}

.advisor-cloud.fading {
  opacity: 0;
}

.cloud-body {
  display: flex;
  align-items: center;
  gap: 8px;
  background: white;
  border-radius: 50px;
  padding: 10px 16px;
  box-shadow:
    0 4px 20px rgba(16, 185, 129, 0.15),
    0 1px 4px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(16, 185, 129, 0.2);
  max-width: 280px;
  transition: all 0.3s ease;
}

.cloud-body::before {
  content: '';
  position: absolute;
  top: -6px;
  left: 20%;
  width: 24px;
  height: 12px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 -2px 6px rgba(16, 185, 129, 0.1);
}

.cloud-body::after {
  content: '';
  position: absolute;
  top: -10px;
  left: 40%;
  width: 18px;
  height: 10px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 -2px 4px rgba(16, 185, 129, 0.08);
}

.advisor-cloud:hover .cloud-body {
  box-shadow:
    0 6px 25px rgba(16, 185, 129, 0.25),
    0 2px 8px rgba(0, 0, 0, 0.08);
  transform: scale(1.02);
}

.cloud-icon {
  flex-shrink: 0;
}

.cloud-text {
  font-size: 13px;
  color: #374151;
  line-height: 1.5;
  font-weight: 500;
}

.cloud-detail {
  position: absolute;
  top: calc(100% + 12px);
  left: 50%;
  transform: translateX(-50%);
  background: white;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.15);
  min-width: 280px;
  max-width: 360px;
  z-index: 10;
}

.detail-content {
  margin-bottom: 12px;
}

.detail-text {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.6;
  margin-bottom: 8px;
}

.detail-plan {
  background: #f0fdf4;
  border-radius: 10px;
  padding: 10px;
  border: 1px solid #bbf7d0;
}

.plan-title {
  font-size: 13px;
  font-weight: 600;
  color: #166534;
  margin-bottom: 4px;
}

.plan-desc {
  font-size: 12px;
  color: #4b5563;
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  flex: 1;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.action-btn.primary {
  background: #10b981;
  color: white;
}

.action-btn.primary:hover {
  background: #059669;
}

.action-btn.secondary {
  background: #f3f4f6;
  color: #374151;
}

.action-btn.secondary:hover {
  background: #e5e7eb;
}

.action-btn.ghost {
  background: transparent;
  color: #6b7280;
}

.action-btn.ghost:hover {
  background: #f9fafb;
}

/* 动画 */
.options-pop-enter-active {
  animation: pop-in 0.25s ease-out;
}

.options-pop-leave-active {
  animation: pop-out 0.15s ease-in;
}

@keyframes pop-in {
  from {
    opacity: 0;
    transform: translateX(-50%) scale(0.95) translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) scale(1) translateY(0);
  }
}

@keyframes pop-out {
  from {
    opacity: 1;
    transform: translateX(-50%) scale(1);
  }
  to {
    opacity: 0;
    transform: translateX(-50%) scale(0.95);
  }
}
</style>
