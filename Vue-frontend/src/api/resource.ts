import request from './request'
import type { LearningResource, ResourceGenerationTask } from '@/types/plan'

export function getPlanResources(planId: number) {
  return request.get<any, { data: LearningResource[] }>(`/resource/plan/${planId}`)
}

export function getResource(resourceId: number) {
  return request.get<any, { data: LearningResource }>(`/resource/${resourceId}`)
}

export function generateResource(data: {
  planId: number
  moduleId?: number
  resourceType: string
  params?: Record<string, any>
}) {
  return request.post<any, { data: { taskId: number } }>('/resource/generate', data)
}

export function getTaskStatus(taskId: number) {
  return request.get<any, { data: ResourceGenerationTask }>(`/resource/task/${taskId}`)
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
