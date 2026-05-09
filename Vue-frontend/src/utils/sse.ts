import { PYTHON_AI_BASE } from '@/api/request'

export interface SSEHandlers {
  onProgress?: (content: string) => void
  onChunk?: (content: string) => void
  onProfileUpdate?: (dimensions: Record<string, any>) => void
  onQuestion?: (content: string) => void
  onProfileComplete?: (profile: Record<string, any>) => void
  onModules?: (modules: any[]) => void
  onPlan?: (plan: any) => void
  onResource?: (resource: any) => void
  onResourceTrigger?: (resourceType: string, moduleId: number) => void
  onRecommendations?: (data: any[]) => void
  onNeedConfirmation?: (message: string, taskBreakdown: any) => void
  onDone?: () => void
  onError?: (error: string) => void
}

export function createSSEConnection(
  path: string,
  ticket: string,
  params: Record<string, string>,
  handlers: SSEHandlers
): EventSource {
  const query = new URLSearchParams({ ticket, ...params }).toString()
  const url = `${PYTHON_AI_BASE}${path}?${query}`
  const source = new EventSource(url)

  function handleSSEData(rawData: string) {
    try {
      const data = JSON.parse(rawData)
      switch (data.type) {
        case 'progress':
          handlers.onProgress?.(data.content)
          break
        case 'chunk':
          handlers.onChunk?.(data.content)
          break
        case 'profile_update':
          handlers.onProfileUpdate?.(data.dimensions)
          break
        case 'question':
          handlers.onQuestion?.(data.question || data.content)
          break
        case 'profile_complete':
          handlers.onProfileComplete?.(data.profile)
          break
        case 'modules':
          handlers.onModules?.(data.data)
          break
        case 'plan':
          handlers.onPlan?.(data.data)
          break
        case 'resource':
          handlers.onResource?.(data.data)
          break
        case 'resource_trigger':
          handlers.onResourceTrigger?.(data.resource_type, data.module_id)
          break
        case 'recommendations':
          handlers.onRecommendations?.(data.data)
          break
        case 'done':
          handlers.onDone?.()
          source.close()
          break
        case 'error':
          handlers.onError?.(data.content)
          source.close()
          break
        case 'format_chunk':
          handlers.onChunk?.(data.content)
          break
        case 'result_done':
          handlers.onDone?.()
          source.close()
          break
        case 'need_confirmation':
          handlers.onNeedConfirmation?.(data.message || '请确认', data.task_breakdown)
          break
      }
    } catch (e) {
      console.error('SSE parse error:', e)
    }
  }

  // Listen for default message events
  source.onmessage = (event) => {
    handleSSEData(event.data)
  }

  // Listen for custom event types (question, progress, done, error, etc.)
  const customEvents = ['question', 'progress', 'profile_update', 'profile_complete', 'done', 'error', 'chunk', 'format_chunk', 'resource', 'resource_trigger', 'plan', 'modules']
  for (const eventType of customEvents) {
    source.addEventListener(eventType, (event: MessageEvent) => {
      handleSSEData(event.data)
    })
  }

  source.onerror = () => {
    handlers.onError?.('连接中断，请重试')
    source.close()
  }

  return source
}

export function cancelSSE(source: EventSource | null) {
  if (source) {
    source.close()
  }
}
