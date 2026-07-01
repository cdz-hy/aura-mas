<template>
  <div class="cloud-container" ref="containerRef">
    <!-- 全部答完提示 -->
    <transition name="fade">
      <div v-if="allDone && showDoneHint" class="done-hint" @click="showDoneHint = false">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
        <span>画像问题已全部完成！</span>
      </div>
    </transition>

    <!-- 多个漂浮云朵 -->
    <div
      v-for="cloud in clouds"
      :key="cloud.id"
      class="cloud"
      :class="{ expanded: cloud.isExpanded, fading: cloud.isFading, dragging: cloud.isDragging }"
      :style="cloud.style"
      @mousedown.stop="onCloudMouseDown($event, cloud)"
    >
      <!-- 云朵形状 + 问题文字 -->
      <div class="cloud-body" @click="onCloudClick(cloud)">
        <div class="cloud-text">{{ cloud.question.question }}</div>
      </div>

      <!-- 展开后的选项卡片（自动边界检测） -->
      <transition name="options-pop">
        <div
          v-if="cloud.isExpanded"
          class="cloud-options"
          :class="cloud.optionsDirection"
        >
          <button
            class="cloud-option"
            :class="{ selected: cloud.selectedOption === 'A' }"
            @click="selectAnswer(cloud, 'A')"
          >
            {{ cloud.question.optionA }}
          </button>
          <button
            class="cloud-option"
            :class="{ selected: cloud.selectedOption === 'B' }"
            @click="selectAnswer(cloud, 'B')"
          >
            {{ cloud.question.optionB }}
          </button>
          <div v-if="cloud.answered" class="cloud-answered">
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <span>已记录</span>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import {
  profileQuestions,
  ANSWERED_QUESTIONS_KEY,
  type ProfileQuestion
} from '@/data/profileQuestions'

const props = defineProps<{
  userId: number
}>()

interface CloudState {
  id: number
  question: ProfileQuestion
  x: number
  y: number
  vx: number
  vy: number
  speed: number
  isExpanded: boolean
  isFading: boolean
  isDragging: boolean
  selectedOption: 'A' | 'B' | null
  answered: boolean
  optionsDirection: 'below' | 'above'
  style: Record<string, string>
}

const containerRef = ref<HTMLElement | null>(null)
const clouds = ref<CloudState[]>([])
const answeredIds = ref<Set<number>>(new Set())
const allDone = ref(false)
const showDoneHint = ref(true)

let animationFrame: number | null = null
let spawnTimer: ReturnType<typeof setTimeout> | null = null

// 加载已回答的题目
function loadAnsweredQuestions() {
  try {
    const saved = localStorage.getItem(ANSWERED_QUESTIONS_KEY)
    if (saved) {
      answeredIds.value = new Set(JSON.parse(saved))
    }
  } catch {
    answeredIds.value = new Set()
  }
}

// 保存已回答的题目
function saveAnsweredQuestions() {
  localStorage.setItem(ANSWERED_QUESTIONS_KEY, JSON.stringify([...answeredIds.value]))
}

// 获取未答过的题目
function getUnansweredQuestions(): ProfileQuestion[] {
  return profileQuestions.filter(q => !answeredIds.value.has(q.id))
}

// 随机选择一道题
function pickRandomQuestion(): ProfileQuestion | null {
  const unanswered = getUnansweredQuestions()
  if (unanswered.length === 0) return null
  return unanswered[Math.floor(Math.random() * unanswered.length)]
}

// 随机位置
function getRandomPosition(): { x: number; y: number } {
  const margin = 60
  const topSafe = 120
  const w = window.innerWidth
  const h = window.innerHeight
  return {
    x: margin + Math.random() * (w - margin * 2 - 200),
    y: topSafe + Math.random() * (h - topSafe - margin - 150)
  }
}

// 获取所有 .card 元素的边界
function getCardRects(): DOMRect[] {
  const cards = document.querySelectorAll('.card')
  return Array.from(cards).map(card => card.getBoundingClientRect())
}

// 创建新云朵
function createCloud(): CloudState | null {
  const question = pickRandomQuestion()
  if (!question) return null

  const pos = getRandomPosition()
  const angle = Math.random() * Math.PI * 2

  const cloud: CloudState = {
    id: Date.now() + Math.random(),
    question,
    x: pos.x,
    y: pos.y,
    vx: Math.cos(angle) * (0.3 + Math.random() * 0.4),
    vy: Math.sin(angle) * (0.3 + Math.random() * 0.4),
    speed: 0.15 + Math.random() * 0.25,
    isExpanded: false,
    isFading: false,
    isDragging: false,
    selectedOption: null,
    answered: false,
    optionsDirection: 'below',
    style: {}
  }

  updateCloudStyle(cloud)
  return cloud
}

// 计算弹窗方向
function computeOptionsDirection(cloud: CloudState) {
  const cloudBottom = cloud.y + 80 // 云朵大约高度
  const spaceBelow = window.innerHeight - cloudBottom
  cloud.optionsDirection = spaceBelow < 200 ? 'above' : 'below'
}

// 更新云朵样式
function updateCloudStyle(cloud: CloudState) {
  cloud.style = {
    transform: `translate(${cloud.x}px, ${cloud.y}px)`,
    opacity: cloud.isFading ? '0' : '0.85',
    transition: cloud.isFading ? 'opacity 1.5s ease-out' : 'none'
  }
}

// 动画循环（带 .card 碰撞反弹）
function animate() {
  const cardRects = getCardRects()
  const margin = 40
  const topSafe = 120
  const w = window.innerWidth
  const h = window.innerHeight
  const cloudW = 220
  const cloudH = 60

  clouds.value.forEach(cloud => {
    if (cloud.isExpanded || cloud.isFading || cloud.isDragging) return

    // 更新位置
    cloud.x += cloud.vx
    cloud.y += cloud.vy
    // 轻微上下浮动
    cloud.y += Math.sin(Date.now() * 0.001 + cloud.id) * 0.3

    // 屏幕边界反弹
    if (cloud.x < margin) { cloud.x = margin; cloud.vx = Math.abs(cloud.vx) }
    if (cloud.x > w - margin - cloudW) { cloud.x = w - margin - cloudW; cloud.vx = -Math.abs(cloud.vx) }
    if (cloud.y < topSafe) { cloud.y = topSafe; cloud.vy = Math.abs(cloud.vy) }
    if (cloud.y > h - margin - cloudH) { cloud.y = h - margin - cloudH; cloud.vy = -Math.abs(cloud.vy) }

    // .card 碰撞反弹
    for (const rect of cardRects) {
      const padding = 10
      const cardLeft = rect.left - padding
      const cardRight = rect.right + padding
      const cardTop = rect.top - padding
      const cardBottom = rect.bottom + padding

      // 检测云朵与 card 的重叠
      const overlapX = cloud.x + cloudW > cardLeft && cloud.x < cardRight
      const overlapY = cloud.y + cloudH > cardTop && cloud.y < cardBottom

      if (overlapX && overlapY) {
        // 计算各方向的穿透深度
        const pushLeft = (cloud.x + cloudW) - cardLeft
        const pushRight = cardRight - cloud.x
        const pushUp = (cloud.y + cloudH) - cardTop
        const pushDown = cardBottom - cloud.y

        const minPush = Math.min(pushLeft, pushRight, pushUp, pushDown)

        if (minPush === pushLeft) { cloud.x = cardLeft - cloudW; cloud.vx = -Math.abs(cloud.vx) }
        else if (minPush === pushRight) { cloud.x = cardRight; cloud.vx = Math.abs(cloud.vx) }
        else if (minPush === pushUp) { cloud.y = cardTop - cloudH; cloud.vy = -Math.abs(cloud.vy) }
        else { cloud.y = cardBottom; cloud.vy = Math.abs(cloud.vy) }
      }
    }

    updateCloudStyle(cloud)
  })

  animationFrame = requestAnimationFrame(animate)
}

// 生成云朵
function spawnClouds() {
  const maxClouds = 3

  function spawn() {
    // 检查是否全部答完
    if (getUnansweredQuestions().length === 0) {
      allDone.value = true
      return // 停止生成
    }

    if (clouds.value.length < maxClouds) {
      const cloud = createCloud()
      if (cloud) clouds.value.push(cloud)
    }

    const delay = 8000 + Math.random() * 12000
    spawnTimer = setTimeout(spawn, delay)
  }

  // 初始生成
  if (getUnansweredQuestions().length === 0) {
    allDone.value = true
    return
  }

  const initial = 1 + Math.floor(Math.random() * 2)
  for (let i = 0; i < initial; i++) {
    setTimeout(() => {
      const cloud = createCloud()
      if (cloud) clouds.value.push(cloud)
    }, i * 2000)
  }

  spawnTimer = setTimeout(spawn, 10000)
}

// 关闭所有云朵
function closeAllClouds() {
  clouds.value.forEach(cloud => {
    if (!cloud.answered) {
      cloud.isExpanded = false
    }
  })
}

// ========== 长按拖拽 ==========
let dragTarget: CloudState | null = null
let dragStartX = 0
let dragStartY = 0
let dragOffsetX = 0
let dragOffsetY = 0
let longPressTimer: ReturnType<typeof setTimeout> | null = null
let isDragging = false
const LONG_PRESS_DELAY = 100 // 长按 100ms 触发拖拽
const DRAG_THRESHOLD = 5    // 移动超过 5px 才算拖拽

function onCloudMouseDown(e: MouseEvent, cloud: CloudState) {
  if (cloud.answered || cloud.isFading) return

  dragStartX = e.clientX
  dragStartY = e.clientY
  dragOffsetX = e.clientX - cloud.x
  dragOffsetY = e.clientY - cloud.y
  isDragging = false

  // 长按定时器
  longPressTimer = setTimeout(() => {
    if (dragTarget) {
      dragTarget.isDragging = true
      isDragging = true
      // 拖拽时关闭展开
      dragTarget.isExpanded = false
      document.body.style.cursor = 'grabbing'
      document.body.style.userSelect = 'none'
    }
  }, LONG_PRESS_DELAY)

  dragTarget = cloud

  // 监听全局 mousemove / mouseup
  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e: MouseEvent) {
  if (!dragTarget) return

  // 如果还没触发长按，检查是否移动超过阈值（超过则取消长按）
  if (!isDragging) {
    const dx = e.clientX - dragStartX
    const dy = e.clientY - dragStartY
    if (Math.sqrt(dx * dx + dy * dy) > DRAG_THRESHOLD) {
      // 移动太多但还没到长按时间，取消长按
      if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null }
      dragTarget = null
      document.removeEventListener('mousemove', onDragMove)
      document.removeEventListener('mouseup', onDragEnd)
      return
    }
    return
  }

  // 拖拽中：更新位置
  const margin = 20
  const newX = Math.max(margin, Math.min(window.innerWidth - 240, e.clientX - dragOffsetX))
  const newY = Math.max(margin, Math.min(window.innerHeight - 80, e.clientY - dragOffsetY))

  dragTarget.x = newX
  dragTarget.y = newY
  updateCloudStyle(dragTarget)
}

function onDragEnd() {
  if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null }

  if (dragTarget && isDragging) {
    dragTarget.isDragging = false
    // 拖拽结束后速度归零，从新位置重新开始漂浮
    dragTarget.vx = (Math.random() - 0.5) * 0.6
    dragTarget.vy = (Math.random() - 0.5) * 0.6
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  dragTarget = null
  isDragging = false
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
}

// 点击云朵（区分拖拽和点击）
function onCloudClick(cloud: CloudState) {
  if (isDragging) return // 刚拖拽完，不触发点击
  toggleCloud(cloud)
}

// 切换展开
function toggleCloud(cloud: CloudState) {
  if (cloud.answered) return

  clouds.value.forEach(c => {
    if (c.id !== cloud.id && !c.answered) {
      c.isExpanded = false
    }
  })

  cloud.isExpanded = !cloud.isExpanded
  if (cloud.isExpanded) {
    computeOptionsDirection(cloud)
  }
}

// 选择答案（JWT 认证，不再暴露 X-Service-Secret）
async function selectAnswer(cloud: CloudState, option: 'A' | 'B') {
  if (cloud.answered) return

  cloud.selectedOption = option
  cloud.answered = true

  const question = cloud.question
  const increment = option === 'A' ? question.scoreA : -question.scoreA
  const delta = increment * 0.1

  answeredIds.value.add(question.id)
  saveAnsweredQuestions()

  // 检查是否全部答完
  if (getUnansweredQuestions().length === 0) {
    allDone.value = true
  }

  // 使用 JWT 认证的用户接口
  try {
    const token = localStorage.getItem('token')
    await fetch('/api/profile/incremental', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        updates: { [question.dimension]: delta },
        updateReason: 'profile_bubble_survey'
      })
    })
  } catch (error) {
    console.warn('更新画像请求失败:', error)
  }

  // 延迟后淡出消失
  setTimeout(() => {
    cloud.isFading = true
    cloud.style = {
      transform: `translate(${cloud.x}px, ${cloud.y}px)`,
      opacity: '0',
      transition: 'opacity 1.5s ease-out'
    }

    setTimeout(() => {
      clouds.value = clouds.value.filter(c => c.id !== cloud.id)
    }, 1500)
  }, 1200)
}

// 点击空白区域关闭
function handleDocumentClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.cloud')) {
    closeAllClouds()
  }
}

onMounted(() => {
  loadAnsweredQuestions()
  spawnClouds()
  animate()
  document.addEventListener('click', handleDocumentClick)
})

onUnmounted(() => {
  if (animationFrame) cancelAnimationFrame(animationFrame)
  if (spawnTimer) clearTimeout(spawnTimer)
  document.removeEventListener('click', handleDocumentClick)
})
</script>

<style scoped>
.cloud-container {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 30;
  overflow: hidden;
}

.done-hint {
  position: absolute;
  top: 140px;
  right: 24px;
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  color: #16a34a;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  animation: fadeInUp 0.4s ease-out;
}

.cloud {
  position: absolute;
  pointer-events: auto;
  cursor: pointer;
  will-change: transform;
}

.cloud-body {
  position: relative;
  background: white;
  border-radius: 50px;
  padding: 14px 22px;
  box-shadow:
    0 4px 20px rgba(139, 92, 246, 0.12),
    0 1px 4px rgba(0, 0, 0, 0.05),
    inset 0 -2px 4px rgba(139, 92, 246, 0.05);
  max-width: 220px;
  text-align: center;
  transition: all 0.3s ease;
  border: 1px solid rgba(139, 92, 246, 0.1);
}

.cloud-body::before {
  content: '';
  position: absolute;
  top: -8px;
  left: 20%;
  width: 30px;
  height: 16px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 -2px 8px rgba(139, 92, 246, 0.08);
}

.cloud-body::after {
  content: '';
  position: absolute;
  top: -14px;
  left: 45%;
  width: 22px;
  height: 12px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 -2px 6px rgba(139, 92, 246, 0.06);
}

.cloud:hover .cloud-body {
  box-shadow:
    0 6px 25px rgba(139, 92, 246, 0.2),
    0 2px 8px rgba(0, 0, 0, 0.08);
  transform: scale(1.02);
}

.cloud.dragging .cloud-body {
  box-shadow:
    0 12px 40px rgba(139, 92, 246, 0.3),
    0 4px 12px rgba(0, 0, 0, 0.1);
  transform: scale(1.08);
  cursor: grabbing;
}

.cloud.dragging {
  z-index: 50;
  opacity: 1 !important;
}

.cloud-text {
  font-size: 12.5px;
  color: #6b7280;
  line-height: 1.5;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}

.cloud.expanded .cloud-text {
  white-space: normal;
  max-width: 200px;
}

/* 弹窗默认在下方 */
.cloud-options {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  background: white;
  border-radius: 16px;
  padding: 10px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(139, 92, 246, 0.1);
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 180px;
  z-index: 10;
}

/* 弹窗在上方 */
.cloud-options.above {
  top: auto;
  bottom: calc(100% + 8px);
}

.cloud-option {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 12.5px;
  text-align: center;
  transition: all 0.2s;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  color: #4b5563;
  white-space: nowrap;
}

.cloud-option:hover {
  background: #f3f4f6;
  border-color: #a78bfa;
  color: #7c3aed;
}

.cloud-option.selected {
  background: linear-gradient(135deg, #a78bfa, #818cf8);
  border-color: transparent;
  color: white;
}

.cloud-answered {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  margin-top: 4px;
  padding: 6px;
  background: #f0fdf4;
  border-radius: 8px;
  font-size: 12px;
  color: #16a34a;
}

.options-pop-enter-active {
  animation: pop-in 0.25s ease-out;
}

.options-pop-leave-active {
  animation: pop-out 0.15s ease-in;
}

@keyframes pop-in {
  from { opacity: 0; transform: translateX(-50%) scale(0.9) translateY(-5px); }
  to { opacity: 1; transform: translateX(-50%) scale(1) translateY(0); }
}

@keyframes pop-out {
  from { opacity: 1; transform: translateX(-50%) scale(1); }
  to { opacity: 0; transform: translateX(-50%) scale(0.9); }
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-enter-active { transition: opacity 0.3s ease; }
.fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
