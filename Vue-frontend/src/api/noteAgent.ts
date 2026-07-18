import { PYTHON_AI_BASE } from '@/api/request'

export interface NoteFormatHandlers {
  onProgress?: (message: string) => void
  onChunk?: (chunk: string) => void
  onDone?: (formatted: string) => void
  onError?: (error: string) => void
}

export interface NoteAnnotation {
  id: string
  type: '易混淆' | '易错点' | '提醒' | '注意' | '技巧'
  text: string
}

/** Optional capture context forwarded to the note formatter. */
export interface NoteFormatContext {
  excerpt?: string
  sourceTitle?: string
  noteType?: string
}

/** SSE 流式整理笔记（POST 请求，避免 URL 长度限制） */
export function formatNoteSSE(
  ticket: string,
  content: string,
  handlers: NoteFormatHandlers,
  instruction?: string,
  context?: NoteFormatContext,
): { abort: () => void } {
  const controller = new AbortController()

  const body: Record<string, unknown> = {
    ticket,
    content,
    instruction: instruction || '',
  }
  if (context?.excerpt) body.excerpt = context.excerpt
  if (context?.sourceTitle) body.sourceTitle = context.sourceTitle
  if (context?.noteType) body.noteType = context.noteType

  fetch(`${PYTHON_AI_BASE}/api/ai/note/format`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        handlers.onError?.(`请求失败: ${response.status}`)
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        handlers.onError?.('无法读取响应流')
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const rawData = line.slice(6)
          if (!rawData.trim()) continue

          try {
            const data = JSON.parse(rawData)
            switch (data.type) {
              case 'progress':
                handlers.onProgress?.(data.content)
                break
              case 'chunk':
                handlers.onChunk?.(data.content)
                break
              case 'done':
                handlers.onDone?.(data.content)
                return
              case 'error':
                handlers.onError?.(data.content)
                return
            }
          } catch (e) {
            console.error('Note format SSE parse error:', e)
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        handlers.onError?.('连接中断，请重试')
      }
    })

  return { abort: () => controller.abort() }
}
