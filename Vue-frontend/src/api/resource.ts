import request from './request'
import type { LearningResource, ResourceGenerationTask } from '@/types/plan'

export function getPlanResources(planId: number) {
  return request.get<any, { data: LearningResource[] }>(`/resource/plan/${planId}`)
}

export function getResource(resourceId: number) {
  return request.get<any, { data: LearningResource }>(`/resource/${resourceId}`)
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
  moduleData: Record<string, any>
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
