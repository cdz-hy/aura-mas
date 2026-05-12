import request from '@/api/request'
import { PYTHON_AI_BASE } from '@/api/request'
import type { QuizRecord } from '@/types/quiz'

/** 获取用户对指定资源的答题记录 */
export function getQuizRecords(userId: number, resourceId: number) {
  return request.get<any, { data: QuizRecord[] }>(
    `/quiz/internal/user/${userId}`,
    { params: { resourceId } }
  )
}

export interface QuizQuestionResult {
  index: number
  question: string
  question_type: string
  user_answer: string
  correct_answer: string
  score: number
  is_correct: boolean
  feedback: string
  key_points_hit: string[]
  key_points_missed: string[]
  improvement_suggestions: string[]
  explanation: string
}

export interface QuizOverallResult {
  score: number
  total: number
  correct: number
  details: QuizQuestionResult[]
}

export interface QuizSubmitHandlers {
  onProgress?: (content: string) => void
  onQuestionResult?: (index: number, result: QuizQuestionResult) => void
  onQuizResult?: (result: QuizOverallResult) => void
  onDone?: () => void
  onError?: (error: string) => void
}

/** 提交答题 - SSE 流式批改 */
export function submitQuizSSE(
  ticket: string,
  resourceId: number,
  planId: number,
  answers: Record<number, any>,
  handlers: QuizSubmitHandlers,
): EventSource {
  const params = new URLSearchParams({
    ticket,
    resource_id: String(resourceId),
    plan_id: String(planId),
    answers: JSON.stringify(answers),
  }).toString()
  const url = `${PYTHON_AI_BASE}/api/ai/quiz/submit?${params}`
  const source = new EventSource(url)

  function handleData(rawData: string) {
    try {
      const data = JSON.parse(rawData)
      switch (data.type) {
        case 'progress':
          handlers.onProgress?.(data.content)
          break
        case 'quiz_question_result':
          handlers.onQuestionResult?.(data.index, data.result)
          break
        case 'quiz_result':
          handlers.onQuizResult?.(data.result)
          break
        case 'done':
          handlers.onDone?.()
          source.close()
          break
        case 'error':
          handlers.onError?.(data.content)
          source.close()
          break
      }
    } catch (e) {
      console.error('Quiz SSE parse error:', e)
    }
  }

  source.onmessage = (event) => handleData(event.data)

  // 处理自定义事件类型
  for (const eventType of ['progress', 'done', 'error']) {
    source.addEventListener(eventType, (event: MessageEvent) => handleData(event.data))
  }

  source.onerror = () => {
    handlers.onError?.('连接中断，请重试')
    source.close()
  }

  return source
}
