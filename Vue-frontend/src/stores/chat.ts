import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { createSSEConnection, cancelSSE } from '@/utils/sse'
import type { GeneratedResourceRef } from '@/utils/sse'
import { issueTicket } from '@/api/auth'
import { getSessions, getSessionMessages, getDialogueHistoryByPlan, deleteSession as apiDeleteSession, getStreamState, requestStopGeneration } from '@/api/chat'
import type { ChatSession, ChatMessage } from '@/types/chat'

const moduleTypeLabels: Record<string, string> = {
  text: '图文', image: '图片', diagram: '导图', code: '代码', quiz: '题目', summary: '总结',
  document: '文档', mindmap: '导图', reading: '阅读', video: '教学视频', podcast: '播客',
}

/** 单个会话的流式状态 */
interface SessionStreamState {
  streaming: boolean
  streamBuffer: string
  hasStreamText: boolean
  pendingModules: any[]
  pendingTaskBreakdown: any
  awaitingConfirmation: boolean
  skipNextModulesPush: boolean
  resourceStreamBuffers: Record<number, string>
  streamingPlaceholders: Array<{ id: number; type: string; title: string }>
  isResourceStreaming: boolean
}

function createEmptyStreamState(): SessionStreamState {
  return {
    streaming: false,
    streamBuffer: '',
    hasStreamText: false,
    pendingModules: [],
    pendingTaskBreakdown: null,
    awaitingConfirmation: false,
    skipNextModulesPush: false,
    resourceStreamBuffers: {},
    streamingPlaceholders: [],
    isResourceStreaming: false,
  }
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<ChatSession[]>([])
  const activeSessionId = ref(localStorage.getItem('chat_activeSessionId') || '')
  const sessionsLoading = ref(false)
  const messages = ref<Array<{ id?: number; role: string; content: string; type?: string; breakdown?: any; resources?: GeneratedResourceRef[]; thinkings?: Array<{ agent: string, content: string }> }>>([])

  // ─── 多会话并发：按 sessionId 隔离流式状态 ───
  const sessionStreams = new Map<string, SessionStreamState>()
  const activeSSEs = new Map<string, EventSource>()

  // 当前活跃会话的流式状态（响应式，供模板绑定）
  const streaming = ref(false)
  const streamBuffer = ref('')
  let hasStreamText = false

  // 任务分解确认状态（当前活跃会话）
  const pendingTaskBreakdown = ref<any>(null)
  const pendingModules = ref<any[]>([])
  const awaitingConfirmation = ref(false)
  let skipNextModulesPush = false
  let isNewlyCreated = false

  // 题目资源事件（供 PlanDetailView 拦截并创建侧栏卡片）
  const lastQuizResource = ref<{ questions: any[] } | null>(null)
  const lastGradingResult = ref<Record<string, any> | null>(null)
  const lastGeneratedResources = ref<GeneratedResourceRef[] | null>(null)
  const streamingResources = ref<Array<{ resource: { id: number; type: string; title: string }; content: string }>>([])
  const resourceStreamBuffers = ref<Record<number, string>>({})
  const streamingPlaceholders = ref<Array<{ id: number; type: string; title: string }>>([])
  const isResourceStreaming = ref(false)
  const resourceStreamBuffer = computed(() => {
    const buffers = resourceStreamBuffers.value
    const keys = Object.keys(buffers)
    return keys.length > 0 ? buffers[Number(keys[keys.length - 1])] || '' : ''
  })

  const selectedModuleContext = ref<{ title: string; description: string; moduleId: number; planId: number } | null>(null)

  let currentPlanId = localStorage.getItem('chat_currentPlanId') || ''

  function _removeEmptyPlaceholder() {
    const _last = messages.value[messages.value.length - 1]
    if (_last && _last.role === 'assistant' && !_last.type && !_last.content && (!_last.thinkings || _last.thinkings.length === 0)) {
      messages.value.pop()
    }
  }

  // 哪些会话正在流式输出（供侧边栏显示绿点指示）
  // 手动管理而非 computed，因 sessionStreams 为原始 Map 无法被 Vue 追踪
  const streamingSessionIds = ref(new Set<string>())

  function _syncStreamingSessions() {
    const ids = new Set<string>()
    if (streaming.value && activeSessionId.value) {
      ids.add(activeSessionId.value)
    }
    for (const [id, state] of sessionStreams) {
      if (state.streaming) ids.add(id)
    }
    streamingSessionIds.value = ids
  }

  // 流式状态或活跃会话变化时自动更新指示器
  watch([streaming, activeSessionId], () => _syncStreamingSessions())

  // ─── 持久化 ───
  function persistSessionState() {
    if (activeSessionId.value) {
      localStorage.setItem('chat_activeSessionId', activeSessionId.value)
    } else {
      localStorage.removeItem('chat_activeSessionId')
    }
    if (currentPlanId) {
      localStorage.setItem('chat_currentPlanId', currentPlanId)
    } else {
      localStorage.removeItem('chat_currentPlanId')
    }
  }

  // ─── 流式状态管理：保存/恢复当前活跃会话的状态 ───
  function saveActiveStreamState() {
    if (!activeSessionId.value) return
    sessionStreams.set(activeSessionId.value, {
      streaming: streaming.value,
      streamBuffer: streamBuffer.value,
      hasStreamText,
      pendingModules: [...pendingModules.value],
      pendingTaskBreakdown: pendingTaskBreakdown.value,
      awaitingConfirmation: awaitingConfirmation.value,
      skipNextModulesPush,
      resourceStreamBuffers: { ...resourceStreamBuffers.value },
      streamingPlaceholders: [...streamingPlaceholders.value],
      isResourceStreaming: isResourceStreaming.value,
    })
    _syncStreamingSessions()
  }

  function restoreStreamState(sessionId: string) {
    const state = sessionStreams.get(sessionId)
    if (state) {
      streaming.value = state.streaming
      streamBuffer.value = state.streamBuffer
      hasStreamText = state.hasStreamText
      pendingModules.value = state.pendingModules
      pendingTaskBreakdown.value = state.pendingTaskBreakdown
      awaitingConfirmation.value = state.awaitingConfirmation
      skipNextModulesPush = state.skipNextModulesPush
      resourceStreamBuffers.value = state.resourceStreamBuffers
      streamingPlaceholders.value = state.streamingPlaceholders
      isResourceStreaming.value = state.isResourceStreaming
    } else {
      // 无后台状态，重置为干净状态
      streaming.value = false
      streamBuffer.value = ''
      hasStreamText = false
      pendingModules.value = []
      pendingTaskBreakdown.value = null
      awaitingConfirmation.value = false
      skipNextModulesPush = false
      resourceStreamBuffers.value = {}
      streamingPlaceholders.value = []
      isResourceStreaming.value = false
    }
  }

  function clearStreamState(sessionId: string) {
    sessionStreams.delete(sessionId)
    const sse = activeSSEs.get(sessionId)
    if (sse) {
      cancelSSE(sse)
      activeSSEs.delete(sessionId)
    }
    _syncStreamingSessions()
  }

  function generateSessionId(): string {
    return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
  }

  /**
   * 刷新后恢复流式输出：轮询后端 stream-state 端点，获取已累积的文本并恢复动画
   * @returns true 如果检测到后端仍在流式处理中
   */
  const _recoverTimer = ref<ReturnType<typeof setInterval> | null>(null)

  async function recoverStreaming(planId: string): Promise<boolean> {
    const sessionId = activeSessionId.value
    if (!sessionId) return false

    // 先检查后端是否有该会话的流式状态
    const state = await getStreamState(sessionId)
    if (!state || !state.is_streaming) return false

    // 后端正流式中，恢复前端状态
    streaming.value = true
    streamBuffer.value = state.text || ''
    hasStreamText = !!state.text
    _syncStreamingSessions()

    // push 占位 assistant 消息，让三个点动画、思考过程和流式文本在同一个气泡内显示
    const _placeholder = { role: 'assistant', content: '', thinkings: [] } as any
    if (streamBuffer.value) {
      _placeholder.content = streamBuffer.value
    }
    if (state.thinkings && state.thinkings.length > 0) {
      _placeholder.thinkings = [...state.thinkings]
    }
    messages.value.push(_placeholder)

    // 持续轮询更新
    _recoverTimer.value = setInterval(async () => {
      try {
        const s = await getStreamState(sessionId)
        if (!s) {
          // 缓存过期或不存在
          _stopRecover()
          _removeEmptyPlaceholder()
          streaming.value = false
          loadSessions(planId)
          return
        }
        if (s.is_streaming) {
          // 仍在流式，更新占位消息的 content 和 thinkings
          streamBuffer.value = s.text || ''
          const _last = messages.value[messages.value.length - 1]
          if (_last && _last.role === 'assistant' && !_last.type) {
            _last.content = s.text || ''
            if (s.thinkings && s.thinkings.length > 0) {
              _last.thinkings = [...s.thinkings]
            }
          }
        } else {
          // 流式完成
          _stopRecover()
          streamBuffer.value = ''
          streaming.value = false
          hasStreamText = false
          // 移除占位消息，从 DB 加载完整消息（包含 thinkings 等持久化数据）
          _removeEmptyPlaceholder()
          await loadSessions(planId)
          if (sessionId === activeSessionId.value) {
            await selectSession(sessionId)
          }
        }
      } catch {
        _stopRecover()
        _removeEmptyPlaceholder()
        streaming.value = false
      }
    }, 500)  // 500ms 轮询间隔

    return true  // 检测到后端仍在流式处理
  }

  function _stopRecover() {
    if (_recoverTimer.value) {
      clearInterval(_recoverTimer.value)
      _recoverTimer.value = null
    }
  }

  async function loadSessions(planId: string) {
    sessionsLoading.value = true
    currentPlanId = planId
    persistSessionState()
    try {
      const res = await getSessions(undefined as any, Number(planId))
      // 过滤掉辅导会话（intentType=chat 或 sessionId 以 tutor- 开头）
      sessions.value = (res.data || []).filter(
        (s: any) => s.intentType !== 'chat' && !s.sessionId?.startsWith('tutor-')
      )

      // 刷新后恢复活跃会话消息（新建会话后跳过，避免覆盖用户刚创建的会话）
      if (isNewlyCreated) {
        isNewlyCreated = false
      } else if (activeSessionId.value && messages.value.length === 0) {
        const match = sessions.value.find(s => s.sessionId === activeSessionId.value)
        if (match) {
          await selectSession(activeSessionId.value)
        } else if (sessions.value.length > 0) {
          await selectSession(sessions.value[0].sessionId)
        }
      } else if (!activeSessionId.value && sessions.value.length > 0) {
        await selectSession(sessions.value[0].sessionId)
      }
    } catch (e) {
      console.error('Failed to load sessions:', e)
    } finally {
      sessionsLoading.value = false
    }
  }

  function dbMessageToChatMessage(m: ChatMessage) {
    let thinkings: Array<{ agent: string, content: string }> | undefined
    if (m.conversationContext) {
      try {
        const ctx = JSON.parse(m.conversationContext)
        if (ctx.thinkings) {
          thinkings = ctx.thinkings
        }
      } catch {}
    }

    if (m.intentType === 'task_breakdown') {
      try {
        const breakdown = JSON.parse(m.conversationText)
        return { id: m.id, role: 'assistant' as const, content: '学习路径已生成，请确认', type: 'confirm', breakdown, thinkings }
      } catch {}
    }
    if (m.intentType === 'resource_generated') {
      try {
        const data = JSON.parse(m.conversationText)
        return { id: m.id, role: 'assistant' as const, content: data.summary || '学习资源已生成', type: 'resource_generated', resources: data.resources || [], thinkings }
      } catch {}
    }
    return { id: m.id, role: m.dialogueType === 'USER' ? 'user' as const : 'assistant' as const, content: m.conversationText, thinkings }
  }

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

  function resetForPlan(planId: string) {
    if (planId === currentPlanId) return
    // 有活跃 SSE 时保持不断开
    if (streaming.value && activeSessionId.value && activeSSEs.has(activeSessionId.value)) {
      currentPlanId = planId
      persistSessionState()
      return
    }
    // 切换计划：清理所有流式状态
    for (const [id] of sessionStreams) clearStreamState(id)
    currentPlanId = planId
    activeSessionId.value = ''
    persistSessionState()
    messages.value = []
    streaming.value = false
    streamBuffer.value = ''
    pendingTaskBreakdown.value = null
    pendingModules.value = []
    awaitingConfirmation.value = false
    lastQuizResource.value = null
    lastGradingResult.value = null
    streamingResources.value = []
    resourceStreamBuffers.value = {}
    streamingPlaceholders.value = []
    isResourceStreaming.value = false
    selectedModuleContext.value = null
    skipNextModulesPush = false
  }

  function newSession() {
    // 不断开其他会话的 SSE，只切换到新会话
    activeSessionId.value = generateSessionId()
    isNewlyCreated = true
    persistSessionState()
    messages.value = []
    restoreStreamState(activeSessionId.value)
    lastQuizResource.value = null
    lastGradingResult.value = null
  }

  async function selectSession(sessionId: string) {
    // 如果是同一会话且消息已加载，跳过（避免重复加载）
    // 但如果是刷新后恢复（消息为空），仍需加载
    if (sessionId === activeSessionId.value && messages.value.length > 0) return

    // 保存当前活跃会话的流式状态（不断开 SSE）
    if (sessionId !== activeSessionId.value) {
      saveActiveStreamState()
    }

    // 切换到新会话
    activeSessionId.value = sessionId
    persistSessionState()

    // 恢复目标会话的流式状态
    restoreStreamState(sessionId)

    // 重置事件引用
    lastQuizResource.value = null
    lastGradingResult.value = null
    selectedModuleContext.value = null

    // 从数据库加载消息
    try {
      const res = await getSessionMessages(sessionId, 100)
      const dbMessages: ChatMessage[] = res.data || []
      messages.value = dbMessages.map(dbMessageToChatMessage)

      // 恢复确认状态
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg?.type === 'confirm' && lastMsg.breakdown) {
        awaitingConfirmation.value = true
        pendingTaskBreakdown.value = lastMsg.breakdown
      }
    } catch (e) {
      console.error('Failed to load session messages:', e)
      messages.value = []
    }
  }

  async function deleteSession(sessionId: string) {
    try {
      await apiDeleteSession(sessionId)
      sessions.value = sessions.value.filter(s => s.sessionId !== sessionId)
      clearStreamState(sessionId)
      if (activeSessionId.value === sessionId) {
        newSession()
      }
    } catch (e) {
      console.error('Failed to delete session:', e)
    }
  }

  async function deleteMessageAction(id: number) {
    try {
      const { deleteMessage } = await import('@/api/chat')
      await deleteMessage(id)
      messages.value = messages.value.filter(m => m.id !== id)
    } catch (e) {
      console.error('Failed to delete message:', e)
    }
  }

  async function deleteMessagesAction(ids: number[]) {
    try {
      const { deleteMessages } = await import('@/api/chat')
      await deleteMessages(ids)
      messages.value = messages.value.filter(m => m.id === undefined || !ids.includes(m.id))
    } catch (e) {
      console.error('Failed to delete messages:', e)
    }
  }

  async function sendMessage(text: string, planId: string, extraParams?: Record<string, string>) {
    if (!text) return
    // 检查当前会话是否已在流式中
    const currentStream = sessionStreams.get(activeSessionId.value)
    if (streaming.value || currentStream?.streaming) return

    const sessionId = activeSessionId.value
    if (!sessionId) {
      activeSessionId.value = generateSessionId()
    }
    persistSessionState()

    const capturedSessionId = activeSessionId.value
    messages.value.push({ role: 'user', content: text })
    messages.value.push({ role: 'assistant', content: '', thinkings: [] })
    streaming.value = true
    _syncStreamingSessions()
    streamBuffer.value = ''
    hasStreamText = false
    awaitingConfirmation.value = false

    try {
      const ticketRes = await issueTicket()
      const ticket = ticketRes.data.ticket

      const sse = createSSEConnection(
        '/api/ai/chat',
        ticket,
        { plan_id: planId || '', message: text, session_id: capturedSessionId, ...extraParams },
        {
          onStreamText(content) {
            streamBuffer.value += content
            hasStreamText = true
          },
          onThinking(agent, content) {
            const lastMsg = messages.value[messages.value.length - 1]
            if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.type) {
              if (!lastMsg.thinkings) lastMsg.thinkings = []
              lastMsg.thinkings.push({ agent, content })
            }
          },
          onThinkingStart(agent, content) {
            const lastMsg = messages.value[messages.value.length - 1]
            if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.type) {
              if (!lastMsg.thinkings) lastMsg.thinkings = []
              lastMsg.thinkings.push({ agent, content })
            }
          },
          onThinkingChunk(content) {
            const lastMsg = messages.value[messages.value.length - 1]
            if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.type && lastMsg.thinkings?.length) {
              lastMsg.thinkings[lastMsg.thinkings.length - 1].content += content
            }
          },
          onResourceStreamStart(placeholders) {
            streamingPlaceholders.value = placeholders
            isResourceStreaming.value = true
            for (const p of placeholders) {
              resourceStreamBuffers.value[p.id] = ''
            }
          },
          onResourceStreamText(resourceId, content) {
            resourceStreamBuffers.value[resourceId] = (resourceStreamBuffers.value[resourceId] || '') + content
            isResourceStreaming.value = true
          },
          onResourceStreamFailed(resourceId) {
            delete resourceStreamBuffers.value[resourceId]
          },
          onChunk(content) {
            if (!hasStreamText) {
              streamBuffer.value += content
            }
          },
          onProfileUpdate(dimensions) {
            console.debug('[Chat] Profile updated:', dimensions)
          },
          onModules(modules) {
            pendingModules.value = [...pendingModules.value, ...modules]
          },
          onNeedConfirmation(message, taskBreakdown) {
            // 仅在当前活跃会话时更新显示
            if (capturedSessionId !== activeSessionId.value) return
            if (streamBuffer.value) {
              const _last = messages.value[messages.value.length - 1]
              if (_last && _last.role === 'assistant' && !_last.type && !_last.content) {
                _last.content = streamBuffer.value
              } else {
                messages.value.push({ role: 'assistant', content: streamBuffer.value })
              }
              streamBuffer.value = ''
            }
            // 移除空的占位消息（无 content、无 thinkings）
            const _ph = messages.value[messages.value.length - 1]
            if (_ph && _ph.role === 'assistant' && !_ph.type && !_ph.content && (!_ph.thinkings || _ph.thinkings.length === 0)) {
              messages.value.pop()
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
            clearStreamState(capturedSessionId)
          },
          onResource(data) {
            if (capturedSessionId !== activeSessionId.value) return
            if (data?.type === 'quiz') {
              const questions = data.questions || []
              if (questions.length > 0) lastQuizResource.value = { questions }
            } else if (data?.type === 'quiz_result') {
              lastGradingResult.value = data.result || {}
            }
          },
          onResourceTrigger(type, moduleId) {
            if (capturedSessionId !== activeSessionId.value) return
            messages.value.push({
              role: 'assistant',
              content: `正在为模块 ${moduleId} 生成${type === 'quiz' ? '练习题' : type === 'code' ? '代码示例' : '资源'}...`,
            })
          },
          onResourceGenerated(resources) {
            if (capturedSessionId !== activeSessionId.value) return
            lastGeneratedResources.value = resources
            resourceStreamBuffers.value = {}
            streamingPlaceholders.value = []
            isResourceStreaming.value = false
            if (resources.length) {
              const summary = resources.map(r => r.title).join('、')
              messages.value.push({
                role: 'assistant',
                content: `已生成学习资源：${summary}`,
                type: 'resource_generated',
                resources,
              })
            }
          },
          onResourceTypeGenerated(resource) {
            if (capturedSessionId !== activeSessionId.value) return
            if (!resource.generated_content && !resource.content && !resource.html && !resource.nodeData) return
            lastGeneratedResources.value = [resource]
          },
          onStreamingResource(resource, content) {
            if (capturedSessionId !== activeSessionId.value) return
            streamingResources.value.push({ resource, content })
          },
          onDone() {
            const isActive = capturedSessionId === activeSessionId.value

            if (skipNextModulesPush) {
              skipNextModulesPush = false
              if (lastGeneratedResources.value) {
                pendingModules.value = []
                streamBuffer.value = ''
                resourceStreamBuffers.value = {}
                streamingPlaceholders.value = []
                isResourceStreaming.value = false
                streaming.value = false
                clearStreamState(capturedSessionId)
                if (isActive) {
                  _removeEmptyPlaceholder()
                  loadSessions(planId)
                }
                return
              }
            }
            if (pendingModules.value.length > 0) {
              const mods = pendingModules.value
              const hasContent = mods.some((m: any) => m.content)
              if (hasContent && lastGeneratedResources.value) {
                pendingModules.value = []
                streamBuffer.value = ''
              } else if (hasContent) {
                if (isActive) {
                  for (const mod of mods) {
                    const typeTag = mod.module_type ? `[${moduleTypeLabels[mod.module_type] || mod.module_type}]` : ''
                    const header = `## ${typeTag} ${mod.title || '学习模块'}`.trim()
                    const body = mod.content || ''
                    const concepts = mod.metadata?.key_concepts
                    const footer = concepts?.length ? `\n\n> **核心概念**: ${concepts.join('、')}` : ''
                    messages.value.push({ role: 'assistant', content: `${header}\n\n${body}${footer}` })
                  }
                }
              } else {
                if (isActive) {
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
              }
              pendingModules.value = []
            }
            if (isActive) {
              if (streamBuffer.value) {
                const _last = messages.value[messages.value.length - 1]
                if (_last && _last.role === 'assistant' && !_last.type && !_last.content) {
                  _last.content = streamBuffer.value
                } else {
                  messages.value.push({ role: 'assistant', content: streamBuffer.value })
                }
                streamBuffer.value = ''
              }
              _removeEmptyPlaceholder()
              streaming.value = false
              resourceStreamBuffers.value = {}
              streamingPlaceholders.value = []
              isResourceStreaming.value = false
            }
            clearStreamState(capturedSessionId)
            if (isActive) loadSessions(planId)
          },
          onError(err) {
            const isActive = capturedSessionId === activeSessionId.value
            if (pendingModules.value.length > 0) {
              const mods = pendingModules.value
              const hasContent = mods.some((m: any) => m.content)
              if (hasContent && isActive) {
                for (const mod of mods) {
                  const typeTag = mod.module_type ? `[${moduleTypeLabels[mod.module_type] || mod.module_type}]` : ''
                  const header = `## ${typeTag} ${mod.title || '学习模块'}`.trim()
                  const body = mod.content || ''
                  messages.value.push({ role: 'assistant', content: `${header}\n\n${body}` })
                }
              }
              pendingModules.value = []
            }
            if (isActive) {
              if (streamBuffer.value) {
                const _last = messages.value[messages.value.length - 1]
                if (_last && _last.role === 'assistant' && !_last.type && !_last.content) {
                  _last.content = streamBuffer.value
                } else {
                  messages.value.push({ role: 'assistant', content: streamBuffer.value })
                }
                streamBuffer.value = ''
              }
              _removeEmptyPlaceholder()
              messages.value.push({ role: 'assistant', content: `错误：${err}` })
              streaming.value = false
              resourceStreamBuffers.value = {}
              streamingPlaceholders.value = []
              isResourceStreaming.value = false
            }
            clearStreamState(capturedSessionId)
          },
        }
      )
      activeSSEs.set(capturedSessionId, sse)
    } catch (e: any) {
      messages.value.push({ role: 'assistant', content: `连接失败：${e.message}` })
      streaming.value = false
      resourceStreamBuffers.value = {}
      streamingPlaceholders.value = []
      isResourceStreaming.value = false
    }
  }

  async function confirmBreakdown(planId: string, feedback?: string) {
    const message = feedback || '确认，开始生成学习资源'
    const breakdown = pendingTaskBreakdown.value
    pendingTaskBreakdown.value = null
    awaitingConfirmation.value = false
    const extra: Record<string, string> = {}
    if (feedback) {
      skipNextModulesPush = false
    } else {
      skipNextModulesPush = true
    }
    if (breakdown) {
      extra.task_breakdown = JSON.stringify(breakdown)
    }
    await sendMessage(message, planId, extra)
  }

  async function stopGeneration(planId?: string) {
    const sessionId = activeSessionId.value
    if (!sessionId) return

    // 通知后端停止处理
    if (planId) {
      requestStopGeneration(sessionId, planId)
    }

    // 断开 SSE 连接
    const sse = activeSSEs.get(sessionId)
    if (sse) {
      cancelSSE(sse)
      activeSSEs.delete(sessionId)
    }

    // 保存已有的流式文本
    if (streamBuffer.value) {
      messages.value.push({ role: 'assistant', content: streamBuffer.value })
      streamBuffer.value = ''
    }

    // 更新状态
    streaming.value = false
    resourceStreamBuffers.value = {}
    streamingPlaceholders.value = []
    isResourceStreaming.value = false
    sessionStreams.delete(sessionId)
    _syncStreamingSessions()

    // 添加用户停止提示
    messages.value.push({ role: 'assistant', content: '（已停止生成）' })
  }

  async function requestSupplementaryResource(
    planId: string,
    moduleContext: { title: string; description: string; moduleId: number },
    resourceType: string,
  ) {
    if (streaming.value) return

    const typeLabels: Record<string, string> = {
      quiz: '测验', mindmap: '思维导图', code: '代码示例', summary: '总结', video: '教学视频', animation: '动画', podcast: '播客',
    }
    const typeLabel = typeLabels[resourceType] || resourceType
    const capturedSessionId = activeSessionId.value
    persistSessionState()

    messages.value.push({ role: 'user', content: `请为「${moduleContext.title}」生成${typeLabel}` })
    messages.value.push({ role: 'assistant', content: '', thinkings: [] })
    streaming.value = true
    _syncStreamingSessions()
    streamBuffer.value = ''
    let supHasStreamText = false

    try {
      const ticketRes = await issueTicket()
      const ticket = ticketRes.data.ticket

      const sse = createSSEConnection(
        '/api/ai/resource/generate',
        ticket,
        {
          plan_id: planId,
          module_id: String(moduleContext.moduleId),
          type: resourceType,
          title: moduleContext.title,
          description: moduleContext.description || '',
          session_id: capturedSessionId,
        },
        {
          onStreamText(content) {
            streamBuffer.value += content
            supHasStreamText = true
          },
          onThinking(agent, content) {
            const lastMsg = messages.value[messages.value.length - 1]
            if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.type) {
              if (!lastMsg.thinkings) lastMsg.thinkings = []
              lastMsg.thinkings.push({ agent, content })
            }
          },
          onThinkingStart(agent, content) {
            const lastMsg = messages.value[messages.value.length - 1]
            if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.type) {
              if (!lastMsg.thinkings) lastMsg.thinkings = []
              lastMsg.thinkings.push({ agent, content })
            }
          },
          onThinkingChunk(content) {
            const lastMsg = messages.value[messages.value.length - 1]
            if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.type && lastMsg.thinkings?.length) {
              lastMsg.thinkings[lastMsg.thinkings.length - 1].content += content
            }
          },
          onResourceStreamStart(placeholders) {
            streamingPlaceholders.value = placeholders
            isResourceStreaming.value = true
            for (const p of placeholders) {
              resourceStreamBuffers.value[p.id] = ''
            }
          },
          onResourceStreamText(resourceId, content) {
            resourceStreamBuffers.value[resourceId] = (resourceStreamBuffers.value[resourceId] || '') + content
            isResourceStreaming.value = true
          },
          onResourceStreamFailed(resourceId) {
            delete resourceStreamBuffers.value[resourceId]
          },
          onChunk(content) {
            if (!supHasStreamText) {
              streamBuffer.value += content
            }
          },
          onModules(modules) {
            pendingModules.value = [...pendingModules.value, ...modules]
          },
          onResourceGenerated(resources) {
            if (capturedSessionId !== activeSessionId.value) return
            lastGeneratedResources.value = resources
            resourceStreamBuffers.value = {}
            streamingPlaceholders.value = []
            isResourceStreaming.value = false
            if (resources.length) {
              const summary = resources.map(r => r.title).join('、')
              messages.value.push({
                role: 'assistant',
                content: `已为「${moduleContext.title}」生成${typeLabel}：${summary}`,
                type: 'resource_generated',
                resources,
              })
            }
          },
          onResourceTypeGenerated(resource) {
            if (capturedSessionId !== activeSessionId.value) return
            if (!resource.generated_content && !resource.content && !resource.html && !resource.nodeData) return
            lastGeneratedResources.value = [resource]
          },
          onStreamingResource(resource, content) {
            if (capturedSessionId !== activeSessionId.value) return
            streamingResources.value.push({ resource, content })
          },
          onDone() {
            const isActive = capturedSessionId === activeSessionId.value
            if (pendingModules.value.length > 0 && !lastGeneratedResources.value) {
              if (isActive) {
                for (const mod of pendingModules.value) {
                  messages.value.push({ role: 'assistant', content: mod.content || '' })
                }
              }
              pendingModules.value = []
            }
            if (isActive) {
              if (streamBuffer.value) {
                const _last = messages.value[messages.value.length - 1]
                if (_last && _last.role === 'assistant' && !_last.type && !_last.content) {
                  _last.content = streamBuffer.value
                } else {
                  messages.value.push({ role: 'assistant', content: streamBuffer.value })
                }
                streamBuffer.value = ''
              }
              _removeEmptyPlaceholder()
              streaming.value = false
              resourceStreamBuffers.value = {}
              streamingPlaceholders.value = []
              isResourceStreaming.value = false
            }
            clearStreamState(capturedSessionId)
            if (isActive) loadSessions(planId)
          },
          onError(err) {
            const isActive = capturedSessionId === activeSessionId.value
            if (isActive) {
              if (streamBuffer.value) {
                const _last = messages.value[messages.value.length - 1]
                if (_last && _last.role === 'assistant' && !_last.type && !_last.content) {
                  _last.content = streamBuffer.value
                } else {
                  messages.value.push({ role: 'assistant', content: streamBuffer.value })
                }
                streamBuffer.value = ''
              }
              _removeEmptyPlaceholder()
              messages.value.push({ role: 'assistant', content: `${typeLabel}生成失败：${err}` })
              streaming.value = false
              resourceStreamBuffers.value = {}
              streamingPlaceholders.value = []
              isResourceStreaming.value = false
            }
            clearStreamState(capturedSessionId)
          },
        }
      )
      activeSSEs.set(capturedSessionId, sse)
    } catch (e: any) {
      messages.value.push({ role: 'assistant', content: `连接失败：${e.message}` })
      streaming.value = false
    }
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
    lastGeneratedResources,
    streamingResources,
    resourceStreamBuffer,
    resourceStreamBuffers,
    streamingPlaceholders,
    isResourceStreaming,
    selectedModuleContext,
    streamingSessionIds,
    loadSessions,
    loadHistoryByPlan,
    resetForPlan,
    newSession,
    selectSession,
    deleteSession,
    deleteMessage: deleteMessageAction,
    deleteMessages: deleteMessagesAction,
    sendMessage,
    confirmBreakdown,
    stopGeneration,
    requestSupplementaryResource,
    recoverStreaming,
    stopRecovering: _stopRecover,
  }
})
