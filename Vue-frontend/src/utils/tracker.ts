/**
 * 学习行为追踪 SDK
 * 自动采集用户学习行为，批量上报到后端
 */

import { useAuthStore } from '@/stores/auth'
import request from '@/api/request'

export interface LearningEvent {
  eventType: string
  data: Record<string, any>
}

class LearningTracker {
  private events: LearningEvent[] = []
  private flushInterval = 30000 // 30秒批量发送
  private maxBatchSize = 50     // 最大批量大小
  private maxRetries = 3        // 最大重试次数
  private retryCount = 0        // 当前重试次数
  private timer: ReturnType<typeof setInterval> | null = null
  private enabled = true

  constructor() {
    // 延迟启动，等待用户登录
    setTimeout(() => this.start(), 5000)
  }

  private start() {
    if (this.timer) return

    // 检查用户是否登录
    const authStore = useAuthStore()
    if (!authStore.isLoggedIn) {
      // 未登录，延迟后再检查
      setTimeout(() => this.start(), 10000)
      return
    }

    this.timer = setInterval(() => this.flush(), this.flushInterval)

    // 启动心跳（每分钟发送一次）
    this.heartbeatTimer = setInterval(() => this.sendHeartbeat(), 60000)

    // 页面关闭前发送剩余事件
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => {
        this.flushSync()
      })
    }
  }

  stop() {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 发送心跳
   */
  private async sendHeartbeat() {
    try {
      const authStore = useAuthStore()
      if (!authStore.isLoggedIn) return

      await request.post('/tracker/heartbeat', {})
    } catch (error) {
      // 静默失败
    }
  }

  /**
   * 追踪学习事件
   */
  track(eventType: string, data: Record<string, any> = {}) {
    if (!this.enabled) return

    const authStore = useAuthStore()
    if (!authStore.isLoggedIn) return

    this.events.push({
      eventType,
      data: {
        ...data,
        timestamp: Date.now()
      }
    })

    // 达到批量大小时立即发送
    if (this.events.length >= this.maxBatchSize) {
      this.flush()
    }
  }

  /**
   * 批量发送事件
   */
  private async flush() {
    if (this.events.length === 0) return

    // 检查重试次数
    if (this.retryCount >= this.maxRetries) {
      console.warn('[Tracker] 达到最大重试次数，丢弃事件')
      this.events = []
      this.retryCount = 0
      return
    }

    const eventsToSend = [...this.events]
    this.events = []

    try {
      await request.post('/tracker/events', eventsToSend)
      this.retryCount = 0  // 成功后重置
    } catch (error) {
      // 发送失败，放回队列
      this.events = [...eventsToSend, ...this.events]
      this.retryCount++
      console.warn(`[Tracker] 发送失败 (${this.retryCount}/${this.maxRetries}):`, error)
    }
  }

  /**
   * 同步发送（页面关闭时）
   */
  private flushSync() {
    if (this.events.length === 0) return

    const eventsToSend = [...this.events]
    this.events = []

    try {
      const authStore = useAuthStore()
      if (!authStore.isLoggedIn) return

      // 使用 fetch + keepalive 发送（可以携带 headers）
      fetch('/api/tracker/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify(eventsToSend),
        keepalive: true  // 页面关闭后仍可发送
      }).catch(() => {
        // 静默失败
      })
    } catch (error) {
      console.warn('[Tracker] 同步发送失败:', error)
    }
  }

  // ========== 便捷方法 ==========

  // 页面停留时间追踪
  private pageStartTime: number = 0
  private currentPage: string = ''

  // 心跳定时器
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null

  /**
   * 追踪页面浏览（自动计算停留时间）
   */
  trackPageView(data: {
    page: string
    planId?: number
    resourceId?: number
    resourceType?: string
  }) {
    // 如果有上一个页面，先发送上一个页面的停留时间
    if (this.currentPage && this.pageStartTime > 0) {
      const duration = Math.floor((Date.now() - this.pageStartTime) / 1000)
      if (duration > 5) { // 只记录停留超过5秒的
        this.track('page_view', {
          page: this.currentPage,
          duration: duration
        })
      }
    }

    // 记录新页面
    this.currentPage = data.page
    this.pageStartTime = Date.now()

    // 发送页面浏览事件（不含 duration）
    this.track('page_view', data)
  }

  /**
   * 追踪资源学习
   */
  trackResourceView(data: {
    resourceId: number
    resourceType: string
    planId?: number
    duration?: number
  }) {
    this.track('resource_view', data)
  }

  /**
   * 追踪资源完成
   */
  trackResourceComplete(data: {
    resourceId: number
    resourceType: string
    planId?: number
    duration?: number
  }) {
    this.track('resource_complete', data)
  }

  /**
   * 追踪测验提交
   */
  trackQuizSubmit(data: {
    resourceId: number
    planId?: number
    score: number
    totalQuestions: number
    correctAnswers: number
    duration?: number
  }) {
    this.track('quiz_submit', data)
  }

  /**
   * 追踪笔记创建
   */
  trackNoteCreate(data: {
    noteId: number
    title: string
    contentLength: number
  }) {
    this.track('note_create', data)
  }

  /**
   * 追踪闪卡复习
   */
  trackFlashcardReview(data: {
    noteId?: number
    cardId: number
    quality: number  // 1-5
    isCorrect: boolean
  }) {
    this.track('flashcard_review', data)
  }

  /**
   * 追踪学习时长
   */
  trackStudyDuration(data: {
    planId?: number
    resourceId?: number
    duration: number  // 秒
  }) {
    this.track('study_duration', data)
  }

  /**
   * 追踪搜索行为
   */
  trackSearch(data: {
    query: string
    resultCount: number
  }) {
    this.track('search', data)
  }

  /**
   * 追踪 AI 对话
   */
  trackAiChat(data: {
    sessionId: string
    planId?: number
    messageLength: number
  }) {
    this.track('ai_chat', data)
  }
}

// 导出单例
export const tracker = new LearningTracker()
