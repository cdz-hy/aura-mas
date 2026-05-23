import request from './request'
import { PYTHON_AI_BASE } from './request'
import type { ChatSession, ChatMessage } from '@/types/chat'

export interface StreamState {
  text: string
  is_streaming: boolean
  source: string
  error?: string
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
export async function getStreamState(sessionId: string): Promise<StreamState | null> {
  try {
    const resp = await fetch(`${PYTHON_AI_BASE}/api/ai/stream-state?session_id=${encodeURIComponent(sessionId)}`)
    if (!resp.ok) return null
    const json = await resp.json()
    return json.data || null
  } catch {
    return null
  }
}
