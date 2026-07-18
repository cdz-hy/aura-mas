export type QuestionType = 'single_choice' | 'multiple_choice' | 'true_false' | 'fill_blank' | 'short_answer' | 'code_output'

export interface QuizQuestion {
  index: number
  type: QuestionType
  question: string
  options?: string[] // for choice questions
  correctAnswer: string | string[]
  explanation: string
  difficulty: number // 1-5
  points: number
}

export interface QuizData {
  id?: number
  title: string
  description: string
  questions: QuizQuestion[]
  totalPoints: number
  estimatedMinutes: number
}

export interface QuizAttempt {
  questionIndex: number
  userAnswer: string | string[]
  isCorrect: boolean
  timeSpent: number
}

export interface QuizRecord {
  id: number
  resourceId: number
  userId: number
  planId: number
  questionType: string
  difficulty: number | null
  correctAnswer: string | null
  userAnswer: string | null
  isCorrect: number | null
  answerTime: string
}

export const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  fill_blank: '填空题',
  short_answer: '简答题',
  code_output: '代码题',
}
