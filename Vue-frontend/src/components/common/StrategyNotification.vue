<template>
  <div class="strategy-notification" ref="containerRef">
    <!-- 通知按钮 -->
    <button
      class="notification-trigger"
      :class="{ 'has-badge': pendingCount > 0 }"
      @click="togglePanel"
    >
      <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2L2 7l10 5 10-5-10-5z" />
        <path d="M2 17l10 5 10-5" />
        <path d="M2 12l10 5 10-5" />
      </svg>
      <span v-if="pendingCount > 0" class="badge">{{ pendingCount > 9 ? '9+' : pendingCount }}</span>
    </button>

    <!-- 策略面板 -->
    <transition name="panel-slide">
      <div v-if="showPanel" class="strategy-panel">
        <!-- 头部 -->
        <div class="panel-header">
          <h3 class="panel-title">学习策略建议</h3>
          <button class="panel-close" @click="showPanel = false">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="panel-loading">
          <div class="loading-spinner"></div>
          <span>加载中...</span>
        </div>

        <!-- 空状态 -->
        <div v-else-if="strategies.length === 0" class="panel-empty">
          <svg class="w-12 h-12 text-navy-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>暂无新的学习建议</p>
          <p class="text-xs text-navy-400">系统会根据你的学习情况定期生成建议</p>
        </div>

        <!-- 策略列表 -->
        <div v-else class="strategy-list">
          <div
            v-for="strategy in strategies"
            :key="strategy.id"
            class="strategy-card"
            :class="strategy.status"
          >
            <!-- 策略类型标识 -->
            <div class="strategy-type" :class="strategy.strategyType">
              {{ getTypeLabel(strategy.strategyType) }}
            </div>

            <!-- 策略内容 -->
            <div class="strategy-content">
              <h4 class="strategy-title">{{ strategy.title }}</h4>
              <p class="strategy-desc">{{ strategy.description }}</p>
              <p v-if="getStrategyDetail(strategy)" class="strategy-detail">
                {{ getStrategyDetail(strategy) }}
              </p>
              <div class="strategy-time">
                {{ formatTime(strategy.createdAt) }}
              </div>
            </div>

            <!-- 操作按钮 -->
            <div v-if="strategy.status === 'pending'" class="strategy-actions">
              <button
                class="action-btn accept"
                @click="handleAccept(strategy)"
                :disabled="processing"
              >
                采纳
              </button>
              <button
                class="action-btn reject"
                @click="handleReject(strategy)"
                :disabled="processing"
              >
                忽略
              </button>
            </div>
            <div v-else class="strategy-status">
              <span :class="strategy.status">
                {{ strategy.status === 'accepted' ? '已采纳' : '已忽略' }}
              </span>
            </div>
          </div>
        </div>

        <!-- 底部 -->
        <div v-if="strategies.length > 0" class="panel-footer">
          <button class="view-all-btn" @click="viewAll">
            查看全部建议
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getPendingStrategyCount,
  getPendingStrategies,
  acceptStrategy,
  rejectStrategy,
  type LearningStrategy
} from '@/api/tracker'
import { getPlans } from '@/api/plan'
import { issueTicket } from '@/api/auth'
import { PYTHON_AI_BASE } from '@/api/request'

const router = useRouter()
const containerRef = ref<HTMLElement | null>(null)

// 状态
const showPanel = ref(false)
const loading = ref(false)
const processing = ref(false)
const pendingCount = ref(0)
const strategies = ref<LearningStrategy[]>([])

// 定时刷新
let refreshTimer: ReturnType<typeof setInterval> | null = null

// 切换面板
function togglePanel() {
  showPanel.value = !showPanel.value
  if (showPanel.value) {
    loadStrategies()
  }
}

// 加载策略
async function loadStrategies() {
  loading.value = true
  try {
    const res = await getPendingStrategies()
    strategies.value = res.data || []
  } catch (e) {
    console.error('加载策略失败:', e)
  } finally {
    loading.value = false
  }
}

// 刷新待处理数量
async function refreshCount() {
  try {
    const res = await getPendingStrategyCount()
    pendingCount.value = res.data || 0
  } catch (e) {
    // 静默失败
  }
}

// 接受策略
async function handleAccept(strategy: LearningStrategy) {
  processing.value = true
  try {
    await acceptStrategy(strategy.id)
    strategy.status = 'accepted'
    pendingCount.value = Math.max(0, pendingCount.value - 1)

    // 解析策略数据
    let data: any = {}
    try {
      data = JSON.parse(strategy.strategyData || '{}')
    } catch (e) {
      console.warn('解析策略数据失败:', e)
    }

    // 如果是计划调整策略，执行实际调整
    if (strategy.strategyType === 'plan_adjustment' && data.adjustment) {
      const adj = data.adjustment
      const action = adj.action || ''
      const modules = adj.modules_to_adjust || []

      // 根据调整类型执行不同操作
      if (action === 'add_review' && modules.length > 0) {
        // 添加复习模块到现有计划
        await addReviewModules(modules)
      } else if (action === 'decelerate' || action === 'accelerate') {
        // 调整计划进度
        showPanel.value = false
        router.push('/plan/create')
      }
    }

    // 如果是计划建议策略，创建新计划
    if (strategy.strategyType === 'plan_adjustment' && data.suggested_plan_focus) {
      const suggestedModules = data.suggested_modules || []
      if (suggestedModules.length > 0) {
        // 有具体模块建议，调用 AI 顾问创建计划
        await createPlanFromSuggestion(data.suggested_plan_focus, suggestedModules)
      } else {
        // 没有具体模块，跳转到计划创建页面
        showPanel.value = false
        router.push({
          path: '/plan/create',
          query: { goal: data.suggested_plan_focus }
        })
      }
    }

    // 如果是资源推荐策略，记录推荐类型
    if (strategy.strategyType === 'resource_recommendation' && data.recommendations) {
      const types = data.recommendations.recommended_resource_types || []
      // 可以将推荐类型保存到本地存储，供后续使用
      localStorage.setItem('recommended_resource_types', JSON.stringify(types))
    }
  } catch (e) {
    console.error('接受策略失败:', e)
  } finally {
    processing.value = false
  }
}

// 添加复习模块到现有计划
async function addReviewModules(modules: string[]) {
  try {
    // 获取用户的第一个计划
    const plansRes = await getPlans({ page: 1, size: 1 })
    const plans = plansRes.data?.records || []
    if (plans.length === 0) {
      showPanel.value = false
      router.push('/plan/create')
      return
    }

    const planId = plans[0].id

    // 调用 AI 顾问创建复习计划
    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket

    const response = await fetch(`${PYTHON_AI_BASE}/api/ai/plan-advisor/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ticket}`
      },
      body: JSON.stringify({
        stats: {},
        plans: plans,
        userMessage: `[系统自动触发] 请为以下知识点创建复习计划：${modules.join('、')}`
      })
    })

    if (response.ok) {
      const data = await response.json()
      if (data.type === 'plan_suggestion' && data.suggestion) {
        // 显示建议
        showPanel.value = false
      }
    }
  } catch (e) {
    console.error('添加复习模块失败:', e)
  }
}

// 根据建议创建新计划并生成资源
async function createPlanFromSuggestion(focus: string, modules: Array<{title: string, description: string}>) {
  try {
    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket

    // 调用 AI 顾问创建计划
    const response = await fetch(`${PYTHON_AI_BASE}/api/ai/plan-advisor/create-plan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ticket}`
      },
      body: JSON.stringify({
        title: focus,
        description: `基于学习分析推荐的${focus}学习计划`,
        modules: modules
      })
    })

    if (response.ok) {
      const data = await response.json()
      if (data.success && data.planId) {
        // 为每个资源触发生成，传递正确的学习目标
        if (data.resourceIds && data.resourceIds.length > 0) {
          for (let i = 0; i < data.resourceIds.length; i++) {
            const resourceId = data.resourceIds[i]
            const module = modules[i] || { title: focus, description: '' }

            try {
              // 构建明确的学习目标消息
              const userMessage = `请为「${module.title}」生成学习资源。学习目标：${module.description || focus}`

              // 触发资源生成，传递明确的学习目标
              await fetch(`${PYTHON_AI_BASE}/api/ai/resource/generate?ticket=${ticket}&plan_id=${data.planId}&module_id=${resourceId}&type=text&title=${encodeURIComponent(module.title)}&description=${encodeURIComponent(module.description || '')}&user_message=${encodeURIComponent(userMessage)}`, {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${ticket}` }
              })
            } catch (e) {
              console.error(`生成资源 ${resourceId} 失败:`, e)
            }
          }
        }

        showPanel.value = false
        // 跳转到新创建的计划
        router.push(`/plan/${data.planId}`)
      }
    }
  } catch (e) {
    console.error('创建计划失败:', e)
  }
}

// 拒绝策略
async function handleReject(strategy: LearningStrategy) {
  processing.value = true
  try {
    await rejectStrategy(strategy.id)
    strategy.status = 'rejected'
    pendingCount.value = Math.max(0, pendingCount.value - 1)
  } catch (e) {
    console.error('拒绝策略失败:', e)
  } finally {
    processing.value = false
  }
}

// 查看全部
function viewAll() {
  showPanel.value = false
  router.push('/analytics')
}

// 获取类型标签
function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    resource_recommendation: '资源推荐',
    plan_adjustment: '计划调整',
    review_schedule: '复习安排',
    learning_habit: '学习习惯',
    general: '综合建议'
  }
  return labels[type] || '建议'
}

// 获取策略详情
function getStrategyDetail(strategy: LearningStrategy): string {
  try {
    const data = JSON.parse(strategy.strategyData || '{}')

    // 资源推荐策略
    if (strategy.strategyType === 'resource_recommendation' && data.recommendations) {
      const recs = data.recommendations
      const types = recs.recommended_resource_types || []
      return `推荐资源类型：${types.join('、')}`
    }

    // 计划调整策略
    if (strategy.strategyType === 'plan_adjustment' && data.adjustment) {
      const adj = data.adjustment
      const modules = adj.modules_to_adjust || []
      if (modules.length > 0) {
        return `涉及模块：${modules.join('、')}`
      }
    }

    return ''
  } catch {
    return ''
  }
}

// 格式化时间
function formatTime(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

// 点击外部关闭
function handleClickOutside(event: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(event.target as Node)) {
    showPanel.value = false
  }
}

// 生命周期
onMounted(() => {
  refreshCount()
  refreshTimer = setInterval(refreshCount, 60000) // 每分钟刷新
  document.addEventListener('mousedown', handleClickOutside)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  document.removeEventListener('mousedown', handleClickOutside)
})
</script>

<style scoped>
.strategy-notification {
  position: relative;
}

.notification-trigger {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: transparent;
  color: #64748b;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.notification-trigger:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.notification-trigger.has-badge {
  color: #10b981;
}

.badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: #ef4444;
  color: white;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid white;
}

.strategy-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 380px;
  max-height: 500px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.12);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 100;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #f1f5f9;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.panel-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.panel-close:hover {
  background: #f1f5f9;
  color: #64748b;
}

.panel-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px;
  color: #94a3b8;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #e2e8f0;
  border-top-color: #10b981;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.panel-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px;
  color: #94a3b8;
}

.strategy-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.strategy-card {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  transition: all 0.2s ease;
  margin-bottom: 4px;
}

.strategy-card:hover {
  background: #f8fafc;
}

.strategy-type {
  flex-shrink: 0;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  background: #f1f5f9;
  color: #64748b;
  height: fit-content;
}

.strategy-type.resource_recommendation {
  background: #dbeafe;
  color: #2563eb;
}

.strategy-type.plan_adjustment {
  background: #fef3c7;
  color: #d97706;
}

.strategy-type.review_schedule {
  background: #d1fae5;
  color: #059669;
}

.strategy-type.learning_habit {
  background: #ede9fe;
  color: #7c3aed;
}

.strategy-content {
  flex: 1;
  min-width: 0;
}

.strategy-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
}

.strategy-desc {
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
  margin-bottom: 6px;
}

.strategy-detail {
  font-size: 12px;
  color: #10b981;
  background: #f0fdf4;
  padding: 6px 10px;
  border-radius: 6px;
  margin-bottom: 6px;
}

.strategy-time {
  font-size: 11px;
  color: #94a3b8;
}

.strategy-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.action-btn {
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.action-btn.accept {
  background: #10b981;
  color: white;
}

.action-btn.accept:hover {
  background: #059669;
}

.action-btn.reject {
  background: #f1f5f9;
  color: #64748b;
}

.action-btn.reject:hover {
  background: #e2e8f0;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.strategy-status {
  flex-shrink: 0;
}

.strategy-status span {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 6px;
}

.strategy-status span.accepted {
  background: #d1fae5;
  color: #059669;
}

.strategy-status span.rejected {
  background: #f1f5f9;
  color: #94a3b8;
}

.panel-footer {
  padding: 12px 16px;
  border-top: 1px solid #f1f5f9;
}

.view-all-btn {
  width: 100%;
  padding: 10px;
  border-radius: 10px;
  background: #f8fafc;
  color: #10b981;
  font-size: 13px;
  font-weight: 500;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.2s ease;
}

.view-all-btn:hover {
  background: #f0fdf4;
  border-color: #10b981;
}

/* 动画 */
.panel-slide-enter-active {
  transition: all 0.25s ease-out;
}

.panel-slide-leave-active {
  transition: all 0.2s ease-in;
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.95);
}
</style>
