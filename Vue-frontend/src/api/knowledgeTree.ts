import request, { PYTHON_AI_BASE } from '@/api/request'
import type {
  KnowledgeNode,
  KnowledgeTreeResponse,
  TreeMessage,
  TreeSseHandlers,
} from '@/types/knowledgeTree'

export function ensureKnowledgeTree(planId: number) {
  return request.post<any, { data: KnowledgeTreeResponse }>(`/knowledge-tree/plan/${planId}`)
}

export function getKnowledgeTree(treeId: string) {
  return request.get<any, { data: KnowledgeTreeResponse }>(`/knowledge-tree/${treeId}`)
}

export function updateKnowledgeNode(nodeId: string, data: Partial<KnowledgeNode>) {
  return request.patch<any, { data: KnowledgeNode }>(`/knowledge-tree/nodes/${nodeId}`, data)
}

export function getKnowledgeNodeMessages(nodeId: string) {
  return request.get<any, { data: TreeMessage[] }>(`/knowledge-tree/nodes/${nodeId}/messages`)
}

export function streamTreeExplain(
  ticket: string,
  treeId: string,
  nodeId: string,
  message: string,
  handlers: TreeSseHandlers,
): EventSource {
  return createTreeSse(
    `/api/ai/tree/${treeId}/nodes/${nodeId}/explain`,
    { ticket, message },
    handlers,
  )
}

export function streamTreeSubdivide(
  ticket: string,
  treeId: string,
  nodeId: string,
  angle: string,
  handlers: TreeSseHandlers,
): EventSource {
  return createTreeSse(
    `/api/ai/tree/${treeId}/nodes/${nodeId}/subdivide`,
    { ticket, angle },
    handlers,
  )
}

export function streamTreeFirstPrinciples(
  ticket: string,
  treeId: string,
  nodeId: string,
  handlers: TreeSseHandlers,
): EventSource {
  return createTreeSse(
    `/api/ai/tree/${treeId}/nodes/${nodeId}/first-principles`,
    { ticket },
    handlers,
  )
}

function createTreeSse(
  path: string,
  params: Record<string, string>,
  handlers: TreeSseHandlers,
): EventSource {
  const query = new URLSearchParams(params).toString()
  const source = new EventSource(`${PYTHON_AI_BASE}${path}?${query}`)

  function handleData(rawData: string) {
    try {
      const data = JSON.parse(rawData)
      switch (data.type) {
        case 'progress':
          handlers.onProgress?.(data.content || '')
          break
        case 'chunk':
          handlers.onChunk?.(data.content || '')
          break
        case 'stream_text':
          handlers.onStreamText?.(data.content || '')
          break
        case 'message':
        case 'message_saved':
          handlers.onMessage?.(data.message || data.data)
          break
        case 'nodes':
        case 'nodes_created':
          handlers.onNodes?.(data.nodes || data.data || [])
          break
        case 'done':
          handlers.onDone?.()
          source.close()
          break
        case 'error':
          handlers.onError?.(data.content || '请求失败')
          source.close()
          break
      }
    } catch (e) {
      console.error('Knowledge tree SSE parse error:', e)
      handlers.onError?.('响应解析失败')
      source.close()
    }
  }

  source.onmessage = (event) => handleData(event.data)

  for (const eventType of ['progress', 'chunk', 'stream_text', 'message', 'message_saved', 'nodes', 'nodes_created', 'done', 'error']) {
    source.addEventListener(eventType, (event: MessageEvent) => handleData(event.data))
  }

  source.onerror = () => {
    handlers.onError?.('连接中断，请重试')
    source.close()
  }

  return source
}
