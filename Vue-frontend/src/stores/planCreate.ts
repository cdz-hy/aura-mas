import { defineStore } from 'pinia'
import { ref, reactive, nextTick } from 'vue'
import { createSSEConnection, cancelSSE } from '@/utils/sse'
import { issueTicket } from '@/api/auth'
import { createPlan, updatePlan } from '@/api/plan'
import { bulkCreateResources } from '@/api/resource'
import { getSessions, getSessionMessages, deleteSession as apiDeleteSession, linkSessionToPlan } from '@/api/chat'
import type { ChatSession, ChatMessage } from '@/types/chat'

interface Message {
  role: 'user' | 'assistant'
  content: string
  type?: string
  breakdown?: any
}

export const usePlanCreateStore = defineStore('planCreate', () => {
  // Session
  const sessions = ref<ChatSession[]>([])
  const activeSessionId = ref(localStorage.getItem('planCreate_activeSessionId') || '')
  const sessionsLoading = ref(false)

  // Chat
  const messages = ref<Message[]>([])
  const streaming = ref(false)
  const streamBuffer = ref('')
  const progressLogs = ref<string[]>([])

  // Profile
  const profileDimensions = reactive<Record<string, any>>({})

  // Plan
  const generatedPlan = ref<any>(null)
  const currentPlanId = ref<number | null>(null)

  // Task breakdown confirmation
  const pendingTaskBreakdown = ref<any>(null)
  const pendingModules = ref<any[]>([])
  const awaitingConfirmation = ref(false)

  // SSE
  let currentSSE: EventSource | null = null

  // 持久化会话状态
  function persistSessionState() {
    if (activeSessionId.value) {
      localStorage.setItem('planCreate_activeSessionId', activeSessionId.value)
    } else {
      localStorage.removeItem('planCreate_activeSessionId')
    }
  }

  // ─── Session ops ───

  function generateSessionId(): string {
    return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
  }

  async function loadSessions() {
    sessionsLoading.value = true
    try {
      const res = await getSessions('profile')
      sessions.value = res.data || []
    } catch (e) {
      console.error('Failed to load sessions:', e)
    } finally {
      sessionsLoading.value = false
    }
  }

  function newSession() {
    cancelSSE(currentSSE)
    currentSSE = null
    activeSessionId.value = generateSessionId()
    persistSessionState()
    messages.value = []
    streamBuffer.value = ''
    progressLogs.value = []
    streaming.value = false
    Object.keys(profileDimensions).forEach(k => delete profileDimensions[k])
    generatedPlan.value = null
    currentPlanId.value = null
    pendingTaskBreakdown.value = null
    pendingModules.value = []
    awaitingConfirmation.value = false
  }

  async function selectSession(sessionId: string) {
    if (sessionId === activeSessionId.value) return
    cancelSSE(currentSSE)
    currentSSE = null
    streaming.value = false
    streamBuffer.value = ''
    activeSessionId.value = sessionId
    persistSessionState()

    // Check if session already has a linked plan
    const existingSession = sessions.value.find(s => s.sessionId === sessionId)
    currentPlanId.value = existingSession?.planId ?? null

    try {
      const res = await getSessionMessages(sessionId, 100)
      const dbMessages: ChatMessage[] = res.data || []
      messages.value = dbMessages.map(m => ({
        role: m.dialogueType === 'USER' ? 'user' : 'assistant',
        content: m.conversationText,
      }))
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

  // ─── Send message (profile building) ───

  async function sendMessage(text: string, extraParams?: Record<string, string>) {
    if (!text || streaming.value) return

    if (!activeSessionId.value) {
      activeSessionId.value = generateSessionId()
      persistSessionState()
    }

    messages.value.push({ role: 'user', content: text })
    streaming.value = true
    streamBuffer.value = ''
    progressLogs.value = []
    awaitingConfirmation.value = false

    try {
      const ticketRes = await issueTicket()
      const ticket = ticketRes.data.ticket

      currentSSE = createSSEConnection(
        '/api/ai/profile/chat',
        ticket,
        { message: text, session_id: activeSessionId.value, plan_id: currentPlanId.value ? String(currentPlanId.value) : '', ...extraParams },
        {
          onProgress(content) {
            progressLogs.value.push(content)
          },
          onChunk(content) {
            streamBuffer.value += content
          },
          onProfileUpdate(dimensions) {
            Object.assign(profileDimensions, dimensions)
          },
          onProfileComplete(profile) {
            Object.assign(profileDimensions, profile)
            progressLogs.value.push('画像构建完成！')
            triggerPlanGeneration(text, ticket)
          },
          onQuestion(content) {
            if (streamBuffer.value) {
              messages.value.push({ role: 'assistant', content: streamBuffer.value })
              streamBuffer.value = ''
            }
            messages.value.push({ role: 'assistant', content })
            streaming.value = false
          },
          onModules(modules) {
            pendingModules.value = [...pendingModules.value, ...modules]
          },
          onNeedConfirmation(message, taskBreakdown) {
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
          onDone() {
            if (pendingModules.value.length > 0) {
              const mods = pendingModules.value
              const hasContent = mods.some((m: any) => m.content)
              if (hasContent) {
                for (const mod of mods) {
                  const typeTag = mod.module_type ? `[${mod.module_type}]` : ''
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
            loadSessions()
          },
          onError(err) {
            if (pendingModules.value.length > 0) {
              const mods = pendingModules.value
              const hasContent = mods.some((m: any) => m.content)
              if (hasContent) {
                for (const mod of mods) {
                  const typeTag = mod.module_type ? `[${mod.module_type}]` : ''
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
            messages.value.push({ role: 'assistant', content: `抱歉，出现了错误：${err}` })
            streaming.value = false
          },
        }
      )
    } catch (e: any) {
      messages.value.push({ role: 'assistant', content: `连接失败：${e.message}` })
      streaming.value = false
    }
  }

  // ─── Plan generation (Phase 2) ───

  async function triggerPlanGeneration(goal: string, ticket: string) {
    progressLogs.value.push('正在生成学习计划...')

    try {
      let planId: number

      if (currentPlanId.value) {
        // Reuse existing plan for this session
        planId = currentPlanId.value
        progressLogs.value.push('检测到已有计划，将更新现有计划...')
      } else {
        // Create a new plan
        const planRes = await createPlan({ title: goal.substring(0, 50), learningGoal: { raw: goal } })
        planId = planRes.data.id
        currentPlanId.value = planId

        linkSessionToPlan(activeSessionId.value, planId).catch(e =>
          console.warn('Link session to plan failed:', e)
        )
      }

      let planData: any = null

      currentSSE = createSSEConnection(
        '/api/ai/plan/generate',
        ticket,
        { goal, plan_id: String(planId) },
        {
          onProgress(content) {
            progressLogs.value.push(content)
          },
          onModules(modules) {
            generatedPlan.value = { ...generatedPlan.value, modules }
          },
          onPlan(plan) {
            planData = plan
            generatedPlan.value = { ...plan, id: planId }
          },
          async onDone() {
            streaming.value = false
            progressLogs.value.push('学习计划生成完成！')

            if (planData) {
              try {
                progressLogs.value.push('正在保存计划配置...')
                await updatePlan(planId, {
                  planConfig: planData,
                  title: planData.summary || goal.substring(0, 50),
                })

                const modules = planData.modules || []
                const resourcesToCreate: Array<{
                  planId: number; moduleOrder: number; moduleType: string;
                  moduleData: string; status: number
                }> = []
                for (const mod of modules) {
                  const moduleOrder = mod.module_id || 0
                  for (const res of (mod.resources || [])) {
                    resourcesToCreate.push({
                      planId,
                      moduleOrder,
                      moduleType: res.resource_type || 'document',
                      moduleData: JSON.stringify({
                        module_title: mod.title,
                        module_description: mod.description,
                        estimated_hours: mod.estimated_hours,
                        title: res.title,
                        description: res.description,
                      }),
                      status: 0,
                    })
                  }
                }
                if (resourcesToCreate.length > 0) {
                  await bulkCreateResources(resourcesToCreate)
                  progressLogs.value.push(`已保存 ${resourcesToCreate.length} 个资源条目`)
                }
              } catch (e: any) {
                console.error('Failed to persist plan data:', e)
                progressLogs.value.push(`保存失败: ${e.message}`)
              }
            }

            // Reply to user with plan summary
            const moduleCount = planData?.modules?.length || 0
            const hours = planData?.total_estimated_hours || planData?.modules?.reduce((sum: number, m: any) => sum + (m.estimated_hours || 0), 0) || 0
            messages.value.push({
              role: 'assistant',
              content: `学习计划已生成！共 ${moduleCount} 个模块，预估 ${hours} 学时。\n\n[进入学习计划 →](/plan/${planId})`,
            })

            loadSessions()
          },
          onError(err) {
            streaming.value = false
            messages.value.push({ role: 'assistant', content: `计划生成失败：${err}` })
          },
        }
      )
    } catch (e: any) {
      streaming.value = false
      messages.value.push({ role: 'assistant', content: `创建计划失败：${e.message}` })
    }
  }

  // ─── Confirm task breakdown ───

  async function confirmBreakdown(feedback?: string) {
    const message = feedback || '确认，开始生成学习资源'
    const breakdown = pendingTaskBreakdown.value
    pendingTaskBreakdown.value = null
    awaitingConfirmation.value = false
    const extra: Record<string, string> = {}
    if (breakdown) {
      extra.task_breakdown = JSON.stringify(breakdown)
    }
    await sendMessage(message, extra)
  }

  // ─── Stop generation ───

  function stopGeneration() {
    cancelSSE(currentSSE)
    currentSSE = null
    if (streamBuffer.value) {
      messages.value.push({ role: 'assistant', content: streamBuffer.value })
      streamBuffer.value = ''
    }
    streaming.value = false
    progressLogs.value.push('已停止生成')
  }

  return {
    sessions,
    activeSessionId,
    sessionsLoading,
    messages,
    streaming,
    streamBuffer,
    progressLogs,
    profileDimensions,
    generatedPlan,
    pendingTaskBreakdown,
    pendingModules,
    awaitingConfirmation,
    loadSessions,
    newSession,
    selectSession,
    deleteSession,
    sendMessage,
    confirmBreakdown,
    stopGeneration,
  }
})
