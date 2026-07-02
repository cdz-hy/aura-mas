import request from './request'
import { PYTHON_AI_BASE } from './request'

// ==================== 类型定义 ====================

export interface ResourceLibrary {
  id: number
  title: string
  contentType: 'text' | 'image'
  content?: string
  imageUrl?: string
  imageCaption?: string
  qdrantDocId?: number
  status: number // 0=待审核, 1=已入库, 2=已拒绝
  createdBy: number
  createdAt: string
  updatedAt: string
}

export interface AdminResourceQuery {
  page: number
  size: number
  keyword?: string
  contentType?: string
  status?: number
}

export interface AdminPageResult<T> {
  total: number
  page: number
  size: number
  records: T[]
}

// ==================== Java 后端 CRUD API ====================

/** 分页查询资源库列表 */
export function getAdminResources(params: AdminResourceQuery) {
  return request.get<any, { data: AdminPageResult<ResourceLibrary> }>('/admin/resource', { params })
}

/** 获取资源详情 */
export function getAdminResource(id: number) {
  return request.get<any, { data: ResourceLibrary }>(`/admin/resource/${id}`)
}

/** 保存草稿 */
export function saveDraft(data: Partial<ResourceLibrary>) {
  return request.post<any, { data: ResourceLibrary }>('/admin/resource/save-draft', data)
}

/** 审核通过并入库 */
export function approveResource(id: number) {
  return request.put<any, { data: ResourceLibrary }>(`/admin/resource/${id}/approve`)
}

/** 拒绝 */
export function rejectResource(id: number) {
  return request.put<any, { data: ResourceLibrary }>(`/admin/resource/${id}/reject`)
}

/** 润色提示词 */
export async function polishPrompt(prompt: string, mode: 'text' | 'image' | 'rich' = 'text'): Promise<string> {
  const token = getAdminToken()
  const resp = await fetch(`${PYTHON_AI_BASE}/api/ai/admin/resource/polish-prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, mode, token }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || '润色失败')
  }
  const result = await resp.json()
  return result.data
}

/** 删除资源 */
export function deleteAdminResource(id: number) {
  return request.delete(`/admin/resource/${id}`)
}

/** 更新资源内容（改写后保存） */
export function updateAdminResource(id: number, data: Partial<ResourceLibrary>) {
  return request.put<any, { data: ResourceLibrary }>(`/admin/resource/${id}`, data)
}

// ==================== Python 后端 AI 生成 API ====================

/** 获取管理员 token（从 localStorage） */
function getAdminToken(): string {
  return localStorage.getItem('token') || ''
}

/** SSE 流式文本生成 - 直接连接 Python 后端 */
export function generateTextSSE(
  topic: string,
  prompt: string,
  handlers: {
    onChunk?: (content: string) => void
    onDone?: () => void
    onError?: (error: string) => void
  }
): EventSource {
  const token = getAdminToken()
  const params = new URLSearchParams({
    topic,
    token,
    prompt: prompt || '',
  }).toString()
  const url = `${PYTHON_AI_BASE}/api/ai/admin/resource/generate/text?${params}`
  const source = new EventSource(url)

  source.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      switch (data.type) {
        case 'chunk':
          handlers.onChunk?.(data.content)
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
      // 忽略解析错误
    }
  }

  source.onerror = () => {
    handlers.onError?.('连接异常断开')
    source.close()
  }

  return source
}

/** 图片生成 - 直接调用 Python 后端 */
export async function generateImage(prompt: string): Promise<{ url: string; caption: string }> {
  const token = getAdminToken()
  const resp = await fetch(`${PYTHON_AI_BASE}/api/ai/admin/resource/generate/image`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, token }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || '图片生成失败')
  }
  const result = await resp.json()
  return result.data
}

/** 图文一体化生成 SSE - 直接调用 Python 后端 */
export function generateTextWithImagesSSE(
  topic: string,
  prompt: string,
  handlers: {
    onTextChunk?: (content: string) => void
    onTextDone?: (content: string) => void
    onImageStart?: (index: number, prompt: string) => void
    onImageDone?: (index: number, url: string) => void
    onDone?: (finalContent: string) => void
    onError?: (error: string) => void
  }
): EventSource {
  const token = getAdminToken()
  const params = new URLSearchParams({
    topic,
    token,
    prompt: prompt || '',
  }).toString()
  const url = `${PYTHON_AI_BASE}/api/ai/admin/resource/generate/text-with-images?${params}`
  const source = new EventSource(url)

  source.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      switch (data.type) {
        case 'text_chunk':
          handlers.onTextChunk?.(data.content)
          break
        case 'text_done':
          handlers.onTextDone?.(data.content)
          break
        case 'image_start':
          handlers.onImageStart?.(data.index, data.prompt)
          break
        case 'image_done':
          handlers.onImageDone?.(data.index, data.url)
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
      // 忽略解析错误
    }
  }

  source.onerror = () => {
    handlers.onError?.('连接异常断开')
    source.close()
  }

  return source
}

/** 智能改写 SSE - 整篇内容改写，POST 方式 */
export function rewriteSSE(
  content: string,
  requirement: string,
  topic: string,
  handlers: {
    onChunk?: (content: string) => void
    onDone?: () => void
    onError?: (error: string) => void
  }
): EventSource {
  // POST 请求无法直接用 EventSource，改用 fetch + ReadableStream
  const token = getAdminToken()
  const controller = new AbortController()

  fetch(`${PYTHON_AI_BASE}/api/ai/admin/resource/rewrite`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, requirement, topic, token }),
    signal: controller.signal,
  }).then(async (resp) => {
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }))
      handlers.onError?.(err.detail || '改写请求失败')
      return
    }
    const reader = resp.body?.getReader()
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

      // 解析 SSE 事件
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            switch (data.type) {
              case 'chunk':
                handlers.onChunk?.(data.content)
                break
              case 'done':
                handlers.onDone?.()
                break
              case 'error':
                handlers.onError?.(data.content)
                break
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }
    handlers.onDone?.()
  }).catch((e) => {
    if (e.name !== 'AbortError') {
      handlers.onError?.(e.message || '改写请求失败')
    }
  })

  // 返回一个模拟的 EventSource-like 对象，支持 close()
  return {
    close: () => controller.abort(),
  } as unknown as EventSource
}
