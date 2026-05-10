import request from './request'
import type { ChatSession, ChatMessage } from '@/types/chat'

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
