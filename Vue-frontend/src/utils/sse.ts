import { PYTHON_AI_BASE } from '@/api/request'

export interface GeneratedResourceRef {
  id: number
  type: string
  title: string
  content?: string
  html?: string
  nodeData?: Record<string, any>
  moduleData?: Record<string, any>
  generated_content?: Record<string, any>
  data?: Record<string, any>
  status?: number
}

export interface SSEHandlers {
  onProgress?: (content: string) => void
  onChunk?: (content: string) => void
  onStreamText?: (content: string) => void
  onResourceStreamStart?: (placeholders: Array<{ id: number; type: string; title: string }>) => void
  onResourceStreamText?: (resourceId: number, content: string) => void
  onResourceStreamFailed?: (resourceId: number) => void
  onProfileUpdate?: (dimensions: Record<string, any>) => void
  onQuestion?: (content: string) => void
  onProfileComplete?: (profile: Record<string, any>) => void
  onModules?: (modules: any[]) => void
  onPlan?: (plan: any) => void
  onResource?: (resource: any) => void
  onResourceTrigger?: (resourceType: string, moduleId: number) => void
  onResourceGenerated?: (resources: GeneratedResourceRef[]) => void
  onResourceTypeGenerated?: (resource: GeneratedResourceRef) => void
  onStreamingResource?: (resource: { id: number; type: string; title: string }, content: string) => void
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
        case 'stream_text':
          handlers.onStreamText?.(data.content)
          break
        case 'resource_stream_text':
          handlers.onResourceStreamText?.(data.resource_id, data.content)
          break
        case 'resource_stream_start':
          handlers.onResourceStreamStart?.(data.content ? JSON.parse(data.content) : [])
          break
        case 'resource_stream_failed':
          handlers.onResourceStreamFailed?.(data.resource_id)
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
        case 'resource_generated':
          handlers.onResourceGenerated?.(data.resources || [])
          break
        case 'resource_type_generated':
          handlers.onResourceTypeGenerated?.(normalizeResourceTypeGenerated(data))
          break
        case 'resource_stream_update':
          handlers.onStreamingResource?.(data.resource, data.content)
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
  const customEvents = ['question', 'progress', 'profile_update', 'profile_complete', 'done', 'error', 'chunk', 'format_chunk', 'resource', 'resource_trigger', 'resource_generated', 'resource_type_generated', 'resource_stream_update', 'plan', 'modules', 'resource_stream_start', 'resource_stream_text', 'resource_stream_failed']
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

function normalizeResourceTypeGenerated(data: Record<string, any>): GeneratedResourceRef {
  const payload = data.generated_content || data.data || data.content || data
  const moduleType = payload.module_type || payload.moduleType || data.resource_type || data.type || 'document'
  const title = payload.title || data.title || '学习资源'
  const idValue = data.id ?? data.resource_id ?? payload.id ?? payload.resource_id ?? 0

  return {
    id: Number(idValue) || 0,
    type: moduleType,
    title,
    content: payload.content,
    html: payload.html,
    nodeData: payload.nodeData,
    moduleData: payload.moduleData,
    generated_content: payload,
    data: payload,
    status: data.status,
  }
}

export function cancelSSE(source: EventSource | null) {
  if (source) {
    source.close()
  }
}
