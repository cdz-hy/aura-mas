import request from './request'
import type { LearningPlan, PlanCreateRequest } from '@/types/plan'

export function createPlan(data: PlanCreateRequest) {
  return request.post<any, { data: LearningPlan }>('/plan', data)
}

export function getPlans(params: { page?: number; size?: number }) {
  return request.get<any, { data: { records: LearningPlan[]; total: number } }>('/plan/list', { params })
}

export function getPlan(planId: number) {
  return request.get<any, { data: LearningPlan }>(`/plan/${planId}`)
}

export function updatePlan(planId: number, data: Partial<LearningPlan>) {
  return request.put<any, { data: LearningPlan }>(`/plan/${planId}`, data)
}

export function deletePlan(planId: number) {
  return request.delete(`/plan/${planId}`)
}
