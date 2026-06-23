import request from './request'
import type { LearningResource, ResourceGenerationTask } from '@/types/plan'

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
  moduleData: Record<string, any>
  status?: number
}>) {
  return request.post<any, { data: LearningResource[] }>('/resource/bulk', resources)
}
