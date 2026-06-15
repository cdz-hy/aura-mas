import request from './request'

// ======================== 类型定义 ========================

export interface QuizAnalysis {
  byQuestionType: Array<{
    type: string
    total: number
    correct: number
    accuracy: number
  }>
  byDifficulty: Array<{
    difficulty: number
    total: number
    correct: number
    accuracy: number
  }>
  dailyAccuracy: Array<{
    date: string
    accuracy: number
    total: number
  }>
  recentTrend: {
    direction: 'up' | 'down' | 'stable'
    changePercent: number
  }
}

export interface HeatmapData {
  dailyData: Array<{
    date: string
    minutes: number
    level: number
  }>
  currentStreak: number
  longestStreak: number
  totalActiveDays: number
}

export interface FlashcardStats {
  totalCards: number
  dueToday: number
  mastered: number
  learning: number
  newCards: number
  avgEaseFactor: number
  easeFactorDistribution: Array<{
    label: string
    count: number
  }>
}

export interface AiInteraction {
  totalDialogues: number
  byIntentType: Array<{
    intent: string
    count: number
    percentage: number
  }>
  dailyDialogues: Array<{
    date: string
    count: number
  }>
  avgSessionLength: number
}

export interface KnowledgeMastery {
  mastered: string[]
  weakAreas: string[]
  interests: string[]
  performance: {
    learningSpeed: number
    engagement: number
    quizAccuracy: number
    completionRate: number
  }
}

export interface StudyEfficiency {
  hourlyData: Array<{
    hour: number
    studyMinutes: number
    sessionCount: number
    quizTotal: number
    quizCorrect: number
    accuracy: number
  }>
  bestStudyHour: number
  bestQuizHour: number
  bestQuizAccuracy: number
}

export interface WeekComparison {
  studyMinutes: {
    thisWeek: number
    lastWeek: number
    change: number
  }
  quizAccuracy: {
    thisWeek: number
    lastWeek: number
    change: number
  }
  activeDays: {
    thisWeek: number
    lastWeek: number
  }
}

export interface AnalyticsData {
  overview: Record<string, any>
  quizAnalysis: QuizAnalysis
  heatmap: HeatmapData
  flashcardStats: FlashcardStats
  aiInteraction: AiInteraction
  knowledgeMastery: KnowledgeMastery
  studyEfficiency: StudyEfficiency
  weekComparison: WeekComparison
}

// ======================== API函数 ========================

export function getQuizAnalysis() {
  return request.get<any, { data: QuizAnalysis }>('/stats/quiz-analysis')
}

export function getStudyHeatmap(days?: number) {
  return request.get<any, { data: HeatmapData }>('/stats/study-heatmap', { params: { days } })
}

export function getFlashcardStats() {
  return request.get<any, { data: FlashcardStats }>('/stats/flashcard-stats')
}

export function getAiInteraction() {
  return request.get<any, { data: AiInteraction }>('/stats/ai-interaction')
}

export function getKnowledgeMastery() {
  return request.get<any, { data: KnowledgeMastery }>('/stats/knowledge-mastery')
}

export function getAnalyticsData(days?: number) {
  return request.get<any, { data: AnalyticsData }>('/stats/analytics', { params: { days } })
}

export function getStudyEfficiency() {
  return request.get<any, { data: StudyEfficiency }>('/stats/study-efficiency')
}

export function getWeekComparison() {
  return request.get<any, { data: WeekComparison }>('/stats/week-comparison')
}
