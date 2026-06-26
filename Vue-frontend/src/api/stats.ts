import request from './request'
import { PYTHON_AI_BASE } from './request'

export interface DashboardStats {
  totalPlans: number
  activePlans: number
  completedPlans: number
  totalResources: number
  totalNotes: number
  totalQuizzes: number
  correctQuizzes: number
  todayDurationSeconds: number
  totalDurationSeconds: number
  completedResources: number
  totalStudyHours: number
  quizAccuracy: number
  weeklyMinutes: Array<{
    label: string
    minutes: number
  }>
  recentActivity: Array<{
    text: string
    time: string
    color: string
  }>
}

export function getDashboardStats() {
  return request.get<any, { data: DashboardStats }>('/stats/dashboard')
}

// 获取首页个性化问候语（Python后端，带2小时缓存）
export function getGreeting(userId: number) {
  return fetch(`${PYTHON_AI_BASE}/api/analytics/greeting?user_id=${userId}`)
    .then(res => res.json())
    .then(res => res.greeting as string)
}
