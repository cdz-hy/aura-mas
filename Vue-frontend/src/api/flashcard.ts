import request from '@/api/request'
import { PYTHON_AI_BASE } from '@/api/request'
import type { Flashcard, FlashcardSaveRequest } from '@/types/flashcard'

/** 获取笔记的所有闪卡 */
export function getFlashcardsByNote(noteId: number) {
  return request.get<any, { data: Flashcard[] }>(`/flashcard/by-note/${noteId}`)
}

/** 获取待复习的闪卡 */
export function getDueFlashcards(limit = 10) {
  return request.get<any, { data: Flashcard[] }>('/flashcard/review', { params: { limit } })
}

/** 获取待复习闪卡数量 */
export function getDueFlashcardCount() {
  return request.get<any, { data: number }>('/flashcard/review/count')
}

/** 提交复习结果 */
export function reviewFlashcard(cardId: number, quality: number) {
  return request.put<any, { data: Flashcard }>(`/flashcard/${cardId}/review`, { quality })
}

/** 删除闪卡 */
export function deleteFlashcard(cardId: number) {
  return request.delete(`/flashcard/${cardId}`)
}

/** 保存闪卡 */
export function saveFlashcards(data: FlashcardSaveRequest) {
  return request.post('/flashcard/save', data)
}

/** 生成闪卡回调接口 */
export interface FlashcardGenerateHandlers {
  onProgress?: (content: string) => void
  onFlashcard?: (index: number, total: number, question: string, answer: string, difficulty: number) => void
  onDone?: (message: string) => void
  onError?: (error: string) => void
}

/** SSE 流式生成闪卡 */
export function generateFlashcardsSSE(
  ticket: string,
  noteId: number,
  handlers: FlashcardGenerateHandlers,
  selectedText?: string,
): EventSource {
  const params: Record<string, string> = {
    ticket,
    note_id: String(noteId),
  }
  if (selectedText) {
    params.selected_text = selectedText
  }
  const query = new URLSearchParams(params).toString()
  const url = `${PYTHON_AI_BASE}/api/ai/flashcard/generate?${query}`
  const source = new EventSource(url)

  function handleData(rawData: string) {
    try {
      const data = JSON.parse(rawData)
      switch (data.type) {
        case 'progress':
          handlers.onProgress?.(data.content)
          break
        case 'flashcard':
          handlers.onFlashcard?.(data.index, data.total, data.question, data.answer, data.difficulty)
          break
        case 'done':
          handlers.onDone?.(data.content)
          source.close()
          break
        case 'error':
          handlers.onError?.(data.content)
          source.close()
          break
      }
    } catch (e) {
      console.error('Flashcard SSE parse error:', e)
    }
  }

  source.onmessage = (event) => handleData(event.data)
  source.onerror = () => {
    handlers.onError?.('连接中断，请重试')
    source.close()
  }

  return source
}
