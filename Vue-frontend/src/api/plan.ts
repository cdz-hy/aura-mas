import request from './request'
import { PYTHON_AI_BASE } from './request'
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

// 生成计划SVG图标（Python后端，会直接更新Java后端）
export async function generatePlanIcon(planId: number, planTitle: string, resourceTitles: string[]): Promise<{ svg: string | null; description?: string }> {
  try {
    const res = await fetch(`${PYTHON_AI_BASE}/api/analytics/plan-icon`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan_id: planId, plan_title: planTitle, resource_titles: resourceTitles })
    })
    const data = await res.json()
    return { svg: data.svg || null, description: data.description }
  } catch (e) {
    console.warn('[PlanIcon] 生成图标失败:', e)
    return { svg: null }
  }
}
