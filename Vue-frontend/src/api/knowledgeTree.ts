import request, { PYTHON_AI_BASE } from '@/api/request'
import type {
  KnowledgeNode,
  KnowledgeTreeResponse,
  TreeSplitMode,
  TreeMessage,
  TreeSubdivisionOption,
  TreeSubdivisionOptionsResponse,
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

export function getTreeSubdivisionOptions(
  ticket: string,
  treeId: string,
  nodeId: string,
  mode: TreeSplitMode = 'Lite',
) {
  return request.get<any, { data: TreeSubdivisionOptionsResponse }>(
    `${PYTHON_AI_BASE}/api/ai/tree/${treeId}/nodes/${nodeId}/subdivision-options`,
    { params: { ticket, mode } },
  )
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
  mode: TreeSplitMode,
  handlers: TreeSseHandlers,
): EventSource {
  return createTreeSse(
    `/api/ai/tree/${treeId}/nodes/${nodeId}/subdivide`,
    { ticket, angle, mode },
    handlers,
  )
}

export function streamTreeMultiAngleSubdivide(
  ticket: string,
  treeId: string,
  nodeId: string,
  angles: TreeSubdivisionOption[],
  mode: TreeSplitMode,
  handlers: TreeSseHandlers,
): EventSource {
  return createTreeSse(
    `/api/ai/tree/${treeId}/nodes/${nodeId}/multi-angle-subdivide`,
    { ticket, angles: JSON.stringify(angles), mode },
    handlers,
  )
}

export function streamTreeFirstPrinciples(
  ticket: string,
  treeId: string,
  nodeId: string,
  mode: TreeSplitMode,
  handlers: TreeSseHandlers,
): EventSource {
  return createTreeSse(
    `/api/ai/tree/${treeId}/nodes/${nodeId}/first-principles`,
    { ticket, mode },
    handlers,
  )
}

export function streamTreeQuiz(
  ticket: string,
  treeId: string,
  nodeId: string,
  planId: number,
  handlers: TreeSseHandlers,
): EventSource {
  return createTreeSse(
    `/api/ai/tree/${treeId}/nodes/${nodeId}/quiz`,
    { ticket, plan_id: String(planId) },
    handlers,
  )
}

export function streamTreeFlashcards(
  ticket: string,
  treeId: string,
  nodeId: string,
  planId: number,
  handlers: TreeSseHandlers,
): EventSource {
  return createTreeSse(
    `/api/ai/tree/${treeId}/nodes/${nodeId}/flashcards`,
    { ticket, plan_id: String(planId) },
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
        case 'resource_generated':
          handlers.onResources?.(data.resources || [])
          break
        case 'flashcards_generated':
          handlers.onFlashcards?.(data.cards || [])
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

  for (const eventType of ['progress', 'chunk', 'stream_text', 'message', 'message_saved', 'nodes', 'nodes_created', 'resource_generated', 'flashcards_generated', 'done', 'error']) {
    source.addEventListener(eventType, (event: MessageEvent) => handleData(event.data))
  }

  source.onerror = () => {
    handlers.onError?.('连接中断，请重试')
    source.close()
  }

  return source
}
