import request from './request'
import { PYTHON_AI_BASE } from './request'
import type { ChatSession, ChatMessage } from '@/types/chat'

export interface StreamState {
  text: string
  is_streaming: boolean
  source: string
  error?: string
  thinkings?: Array<{ agent: string, content: string }>
}

export function getSessions(intentType: string, planId?: number) {
  return request.get<any, { data: ChatSession[] }>('/dialogue/sessions', {
    params: { intentType, planId },
  })
}

export function getSessionMessages(sessionId: string, limit = 100) {
  return request.get<any, { data: ChatMessage[] }>(`/dialogue/session/${sessionId}`, {
    params: { limit },
  })
}

export function deleteSession(sessionId: string) {
  return request.delete<any, { data: null }>(`/dialogue/session/${sessionId}`)
}

export function deleteMessage(id: number) {
  return request.delete<any, { data: null }>(`/dialogue/${id}`)
}

export function deleteMessages(ids: number[]) {
  return request.delete<any, { data: null }>(`/dialogue/batch`, {
    data: { ids }
  })
}

export function linkSessionToPlan(sessionId: string, planId: number) {
  return request.put<any, { data: null }>(`/dialogue/session/${sessionId}/link-plan/${planId}`)
}

export function getDialogueHistoryByPlan(planId: number, limit = 200) {
  return request.get<any, { data: ChatMessage[] }>('/dialogue/history', {
    params: { planId, limit },
  })
}

/**
 * 查询会话的流式输出状态（用于刷新后恢复流式动画）
 * 直接调用 Python 后端，不经过 Java 代理
 */
export async function getStreamState(sessionId: string): Promise<{ state: StreamState | null; pendingConfirmation: { type: string; message: string; task_breakdown?: any } | null }> {
  try {
    const resp = await fetch(`${PYTHON_AI_BASE}/api/ai/stream-state?session_id=${encodeURIComponent(sessionId)}`)
    if (!resp.ok) return { state: null, pendingConfirmation: null }
    const json = await resp.json()
    return { state: json.data || null, pendingConfirmation: json.pending_confirmation || null }
  } catch {
    return { state: null, pendingConfirmation: null }
  }
}

/**
 * 请求停止指定会话的流式处理
 * 调用后后端会在下一个节点边界终止执行
 */
export async function requestStopGeneration(sessionId: string, planId: string): Promise<void> {
  try {
    await fetch(`${PYTHON_AI_BASE}/api/ai/stop?session_id=${encodeURIComponent(sessionId)}&plan_id=${encodeURIComponent(planId)}`, {
      method: 'POST',
    })
  } catch {
    // 忽略错误，前端已准备断开 SSE
  }
}
