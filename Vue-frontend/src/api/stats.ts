import request from './request'

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
