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

export interface AnalyticsData {
  overview?: Partial<DashboardStats>
  quizAnalysis?: {
    byQuestionType?: Array<{
      type: string
      total: number
      correct: number
      accuracy: number
    }>
    byDifficulty?: Array<{
      difficulty: number
      total: number
      correct: number
      accuracy: number
    }>
    dailyAccuracy?: Array<{
      date: string
      total: number
      accuracy: number
    }>
    trend?: {
      direction?: string
      changePercent?: number
    }
  }
  heatmap?: {
    days?: Array<{
      date: string
      count?: number
      minutes?: number
    }>
  }
  flashcardStats?: Record<string, any>
  aiInteraction?: Record<string, any>
  knowledgeMastery?: {
    mastered?: string[]
    weakAreas?: string[]
    interests?: string[]
    performance?: Record<string, number>
  }
}

export function getAnalyticsData() {
  return request.get<any, { data: AnalyticsData }>('/stats/analytics')
}
