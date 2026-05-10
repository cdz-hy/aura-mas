import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createSSEConnection, cancelSSE } from '@/utils/sse'
import { issueTicket } from '@/api/auth'
import { getSessions, getSessionMessages, getDialogueHistoryByPlan, deleteSession as apiDeleteSession } from '@/api/chat'
import type { ChatSession, ChatMessage } from '@/types/chat'

const moduleTypeLabels: Record<string, string> = {
  text: '文本', image: '图片', diagram: '导图', code: '代码', quiz: '题目', summary: '总结',
  document: '文档', mindmap: '导图', reading: '阅读',
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<ChatSession[]>([])
  const activeSessionId = ref('')
  const sessionsLoading = ref(false)
  const messages = ref<Array<{ role: string; content: string; type?: string; breakdown?: any }>>([])
  const streaming = ref(false)
  const streamBuffer = ref('')

  // 任务分解确认状态
  const pendingTaskBreakdown = ref<any>(null)
  const pendingModules = ref<any[]>([])
  const awaitingConfirmation = ref(false)
  // 用户确认后，跳过 onDone 中的模块消息推送（避免重复）
  let skipNextModulesPush = false

  // 题目资源事件（供 PlanDetailView 拦截并创建侧栏卡片）
  const lastQuizResource = ref<{ questions: any[] } | null>(null)
  // 批改结果事件（供 PlanDetailView 显示在中间面板）
  const lastGradingResult = ref<Record<string, any> | null>(null)

  let currentSSE: EventSource | null = null
  let currentPlanId = ''

  function generateSessionId(): string {
    return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
  }

  async function loadSessions(planId: string) {
    sessionsLoading.value = true
    currentPlanId = planId
    try {
      const res = await getSessions(undefined, Number(planId))
      sessions.value = res.data || []
    } catch (e) {
      console.error('Failed to load sessions:', e)
    } finally {
      sessionsLoading.value = false
    }
  }

  /**
   * 将数据库消息转为前端消息格式
   */
  function dbMessageToChatMessage(m: ChatMessage) {
    if (m.intentType === 'task_breakdown') {
      try {
        const breakdown = JSON.parse(m.conversationText)
        return {
          role: 'assistant' as const,
          content: '学习路径已生成，请确认',
          type: 'confirm',
          breakdown,
        }
      } catch {}
    }
    return {
      role: m.dialogueType === 'USER' ? 'user' as const : 'assistant' as const,
      content: m.conversationText,
    }
  }

  /**
   * 加载指定学习计划的所有对话历史（跨会话）
   */
  async function loadHistoryByPlan(planId: string) {
    sessionsLoading.value = true
    currentPlanId = planId
    try {
      const res = await getDialogueHistoryByPlan(Number(planId))
      const dbMessages: ChatMessage[] = res.data || []
      messages.value = dbMessages.map(dbMessageToChatMessage)
    } catch (e) {
      console.error('Failed to load plan dialogue history:', e)
      messages.value = []
    } finally {
      sessionsLoading.value = false
    }
  }

  /**
   * 切换计划时重置整个对话状态，防止残留其他计划的消息
   */
  function resetForPlan(planId: string) {
    cancelSSE(currentSSE)
    currentSSE = null
    currentPlanId = planId
    activeSessionId.value = ''
    messages.value = []
    streamBuffer.value = ''
    streaming.value = false
    pendingTaskBreakdown.value = null
    pendingModules.value = []
    awaitingConfirmation.value = false
    lastQuizResource.value = null
    lastGradingResult.value = null
    skipNextModulesPush = false
  }

  function newSession() {
    cancelSSE(currentSSE)
    currentSSE = null
    activeSessionId.value = generateSessionId()
    messages.value = []
    streamBuffer.value = ''
    streaming.value = false
    pendingTaskBreakdown.value = null
    pendingModules.value = []
    awaitingConfirmation.value = false
    lastQuizResource.value = null
    lastGradingResult.value = null
  }

  async function selectSession(sessionId: string) {
    if (sessionId === activeSessionId.value) return
    cancelSSE(currentSSE)
    currentSSE = null
    streaming.value = false
    streamBuffer.value = ''
    pendingTaskBreakdown.value = null
    awaitingConfirmation.value = false
    lastQuizResource.value = null
    lastGradingResult.value = null
    skipNextModulesPush = false
    activeSessionId.value = sessionId

    try {
      const res = await getSessionMessages(sessionId, 100)
      const dbMessages: ChatMessage[] = res.data || []
      messages.value = dbMessages.map(dbMessageToChatMessage)
    } catch (e) {
      console.error('Failed to load session messages:', e)
      messages.value = []
    }
  }

  async function deleteSession(sessionId: string) {
    try {
      await apiDeleteSession(sessionId)
      sessions.value = sessions.value.filter(s => s.sessionId !== sessionId)
      if (activeSessionId.value === sessionId) {
        newSession()
      }
    } catch (e) {
      console.error('Failed to delete session:', e)
    }
  }

  async function sendMessage(text: string, planId: string, extraParams?: Record<string, string>) {
    if (!text || streaming.value) return

    if (!activeSessionId.value) {
      activeSessionId.value = generateSessionId()
    }

    messages.value.push({ role: 'user', content: text })
    streaming.value = true
    streamBuffer.value = ''
    awaitingConfirmation.value = false

    try {
      const ticketRes = await issueTicket()
      const ticket = ticketRes.data.ticket

      currentSSE = createSSEConnection(
        '/api/ai/chat',
        ticket,
        { plan_id: planId || '', message: text, session_id: activeSessionId.value, ...extraParams },
        {
          onProgress() {},
          onChunk(content) {
            streamBuffer.value += content
          },
          onProfileUpdate(dimensions) {
            console.debug('[Chat] Profile updated:', dimensions)
          },
          onModules(modules) {
            // 累积模块列表（多个 modules 事件合并），等 need_confirmation 或 onDone 显示
            pendingModules.value = [...pendingModules.value, ...modules]
          },
          onNeedConfirmation(message, taskBreakdown) {
            // 收到需要确认的信号，显示任务分解卡片
            if (streamBuffer.value) {
              messages.value.push({ role: 'assistant', content: streamBuffer.value })
              streamBuffer.value = ''
            }
            const breakdown = taskBreakdown || (pendingModules.value.length ? { modules: pendingModules.value } : null)
            pendingTaskBreakdown.value = breakdown
            awaitingConfirmation.value = true
            messages.value.push({
              role: 'assistant',
              content: message || '学习路径已生成，请确认',
              type: 'confirm',
              breakdown,
            })
            pendingModules.value = []
            streaming.value = false
          },
          onResource(data) {
            if (data?.type === 'quiz') {
              const questions = data.questions || []
              if (questions.length > 0) {
                // 通知 PlanDetailView 创建侧栏卡片并在中间面板显示
                lastQuizResource.value = { questions }
              }
            } else if (data?.type === 'quiz_result') {
              const r = data.result || {}
              // 通知 PlanDetailView 显示批改结果
              lastGradingResult.value = r
            }
          },
          onResourceTrigger(type, moduleId) {
            messages.value.push({
              role: 'assistant',
              content: `正在为模块 ${moduleId} 生成${type === 'quiz' ? '练习题' : type === 'code' ? '代码示例' : '资源'}...`,
            })
          },
          onDone() {
            // 用户确认后跳过模块消息推送（已在 onNeedConfirmation 中显示过）
            if (skipNextModulesPush) {
              skipNextModulesPush = false
              pendingModules.value = []
              streamBuffer.value = ''
              streaming.value = false
              loadSessions(planId)
              return
            } else if (pendingModules.value.length > 0) {
              const mods = pendingModules.value
              const hasContent = mods.some((m: any) => m.content)
              if (hasContent) {
                // 编排后的学习资源 — 每个模块作为独立消息显示
                for (const mod of mods) {
                  const typeTag = mod.module_type ? `[${moduleTypeLabels[mod.module_type] || mod.module_type}]` : ''
                  const header = `## ${typeTag} ${mod.title || '学习模块'}`.trim()
                  const body = mod.content || ''
                  const concepts = mod.metadata?.key_concepts
                  const footer = concepts?.length ? `\n\n> **核心概念**: ${concepts.join('、')}` : ''
                  messages.value.push({
                    role: 'assistant',
                    content: `${header}\n\n${body}${footer}`,
                  })
                }
              } else {
                // 任务分解模块列表（首次对话，非确认后）
                const moduleList = mods.map((m: any, i: number) =>
                  `**${i + 1}. ${m.title}**\n${m.description || ''}${m.estimated_hours ? ` (${m.estimated_hours}h)` : ''}`
                ).join('\n\n')
                messages.value.push({
                  role: 'assistant',
                  content: `已规划 ${mods.length} 个学习模块：\n\n${moduleList}`,
                  type: 'modules',
                  breakdown: { modules: mods },
                })
              }
              pendingModules.value = []
            }
            if (streamBuffer.value) {
              messages.value.push({ role: 'assistant', content: streamBuffer.value })
              streamBuffer.value = ''
            }
            streaming.value = false
            loadSessions(planId)
          },
          onError(err) {
            // 即使出错，也显示已生成的模块内容
            if (pendingModules.value.length > 0) {
              const mods = pendingModules.value
              const hasContent = mods.some((m: any) => m.content)
              if (hasContent) {
                for (const mod of mods) {
                  const typeTag = mod.module_type ? `[${moduleTypeLabels[mod.module_type] || mod.module_type}]` : ''
                  const header = `## ${typeTag} ${mod.title || '学习模块'}`.trim()
                  const body = mod.content || ''
                  messages.value.push({ role: 'assistant', content: `${header}\n\n${body}` })
                }
              }
              pendingModules.value = []
            }
            if (streamBuffer.value) {
              messages.value.push({ role: 'assistant', content: streamBuffer.value })
              streamBuffer.value = ''
            }
            messages.value.push({ role: 'assistant', content: `错误：${err}` })
            streaming.value = false
          },
        }
      )
    } catch (e: any) {
      messages.value.push({ role: 'assistant', content: `连接失败：${e.message}` })
      streaming.value = false
    }
  }

  /**
   * 确认任务分解 - 发送确认消息继续流程
   */
  async function confirmBreakdown(planId: string, feedback?: string) {
    const message = feedback || '确认，开始生成学习资源'
    const breakdown = pendingTaskBreakdown.value
    pendingTaskBreakdown.value = null
    awaitingConfirmation.value = false
    // 标记跳过下次 onDone 中的模块推送（避免重复显示学习路径）
    skipNextModulesPush = true
    // 将已有的任务分解结果传回后端，避免状态丢失
    const extra: Record<string, string> = {}
    if (breakdown) {
      extra.task_breakdown = JSON.stringify(breakdown)
    }
    await sendMessage(message, planId, extra)
  }

  function stopGeneration() {
    cancelSSE(currentSSE)
    currentSSE = null
    if (streamBuffer.value) {
      messages.value.push({ role: 'assistant', content: streamBuffer.value })
      streamBuffer.value = ''
    }
    streaming.value = false
  }

  return {
    sessions,
    activeSessionId,
    sessionsLoading,
    messages,
    streaming,
    streamBuffer,
    pendingTaskBreakdown,
    awaitingConfirmation,
    lastQuizResource,
    lastGradingResult,
    loadSessions,
    loadHistoryByPlan,
    resetForPlan,
    newSession,
    selectSession,
    deleteSession,
    sendMessage,
    confirmBreakdown,
    stopGeneration,
  }
})
