import request from './request'
import type { LearningResource, ResourceGenerationTask, AnimationExportQuality, AnimationExportState } from '@/types/plan'
import { issueTicket } from './auth'
import { PYTHON_AI_BASE } from './request'
export type { AnimationExportQuality, AnimationExportState }

function formatExportErrorDetail(detail: unknown): string {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && 'msg' in item) return String((item as { msg: unknown }).msg)
        return ''
      })
      .filter(Boolean)
    if (parts.length) return parts.join('; ')
  }
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message: unknown }).message)
  }
  return '视频导出请求失败'
}

async function animationExportRequest(resourceId: number, method: 'GET' | 'POST', quality?: AnimationExportQuality) {
  const ticket = (await issueTicket()).data.ticket
  const response = await fetch(`${PYTHON_AI_BASE}/api/ai/animation/${resourceId}/exports`, {
    method,
    headers: { 'Content-Type': 'application/json', 'X-Ticket': ticket },
    body: quality ? JSON.stringify({ quality }) : undefined,
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(formatExportErrorDetail(payload?.detail))
  }
  return response.json() as Promise<{ accepted?: boolean; qualities: Record<AnimationExportQuality, AnimationExportState> }>
}
export const getAnimationExports = (resourceId: number) => animationExportRequest(resourceId, 'GET')
export const createAnimationExport = (resourceId: number, quality: AnimationExportQuality) => animationExportRequest(resourceId, 'POST', quality)

export function getPlanResources(planId: number) {
  return request.get<any, { data: LearningResource[] }>(`/resource/plan/${planId}`)
}

export function getResource(resourceId: number) {
  return request.get<any, { data: LearningResource }>(`/resource/${resourceId}`)
}

export function deleteResource(resourceId: number) {
  return request.delete<any, { data: null }>(`/resource/${resourceId}`)
}

export function dispatchTask(data: {
  planId: number
  resourceId: number
  agentChain?: string
}) {
  return request.post<any, { data: ResourceGenerationTask }>('/task/dispatch', data)
}

export function getTaskStatus(taskId: number) {
  return request.get<any, { data: ResourceGenerationTask }>(`/task/${taskId}`)
}

export function getLatestTask(resourceId: number) {
  return request.get<any, { data: ResourceGenerationTask | null }>(`/task/by-resource/${resourceId}`)
}

export function retryTask(taskId: number) {
  return request.post<any, { data: null }>(`/task/${taskId}/retry`)
}

export function updateResourceContent(resourceId: number, moduleData: Record<string, any>, status: number) {
  return request.put<any, { data: null }>(`/resource/${resourceId}/content`, { moduleData, status })
}

export function bulkCreateResources(resources: Array<{
  planId: number
  moduleOrder: number
  moduleType: string
  moduleData: Record<string, any> | string
  status?: number
}>) {
  return request.post<any, { data: LearningResource[] }>('/resource/bulk', resources)
}

// ─── 资源完成进度 ───

export interface ResourceProgress {
  resourceId: number
  status: number // 0=未开始, 1=学习中, 2=已完成
  durationSeconds: number
}

export function markResourceComplete(planId: number, resourceId: number) {
  return request.post<any, { data: null }>('/progress/complete', null, { params: { planId, resourceId } })
}

export function unmarkResourceComplete(planId: number, resourceId: number) {
  return request.delete<any, { data: null }>('/progress/complete', { params: { planId, resourceId } })
}

export function getProgressByPlan(planId: number) {
  return request.get<any, { data: ResourceProgress[] }>('/progress/plan', { params: { planId } })
}

export function getBatchProgress(planIds: number[]) {
  return request.get<any, { data: Record<string, { completed: number; total: number; progress: number; isCompleted: boolean }> }>('/progress/batch', { params: { planIds } })
}

export function markAllComplete(planId: number) {
  return request.post<any, { data: null }>('/progress/complete-all', null, { params: { planId } })
}
