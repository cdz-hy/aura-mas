import request from './request'

export interface DashboardStats {
  totalPlans: number
  completedPlans: number
  totalResources: number
  totalStudyHours: number
  quizAccuracy: number
  recentActivity: Array<{
    type: string
    description: string
    time: string
  }>
  weeklyProgress: Array<{
    date: string
    studyMinutes: number
    resourcesViewed: number
  }>
}

export function getDashboardStats() {
  return request.get<any, { data: DashboardStats }>('/stats/dashboard')
}
