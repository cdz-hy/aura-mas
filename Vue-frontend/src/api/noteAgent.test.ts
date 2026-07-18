import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/api/request', () => ({
  PYTHON_AI_BASE: 'http://localhost:8002',
  default: {},
}))

import { formatNoteSSE } from './noteAgent'

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

function sseResponse(events: Array<{ type: string; content: string }>) {
  const payload = events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('')
  const encoder = new TextEncoder()
  let sent = false
  return {
    ok: true,
    body: {
      getReader() {
        return {
          async read() {
            if (sent) return { done: true, value: undefined }
            sent = true
            return { done: false, value: encoder.encode(payload) }
          },
        }
      },
    },
  }
}

describe('formatNoteSSE', () => {
  it('sends excerpt/source/noteType context in the request body', async () => {
    fetchMock.mockResolvedValue(sseResponse([{ type: 'done', content: '整理后' }]))

    const onDone = vi.fn()
    formatNoteSSE(
      'ticket-1',
      '我的理解',
      { onDone },
      '请更简洁',
      {
        excerpt: '当 x 趋近于 a 时',
        sourceTitle: '极限的定义',
        noteType: 'excerpt',
      },
    )

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled())

    const [, init] = fetchMock.mock.calls[0]
    expect(init.method).toBe('POST')
    const body = JSON.parse(init.body as string)
    expect(body).toMatchObject({
      ticket: 'ticket-1',
      content: '我的理解',
      instruction: '请更简洁',
      excerpt: '当 x 趋近于 a 时',
      sourceTitle: '极限的定义',
      noteType: 'excerpt',
    })
  })

  it('remains compatible when context is omitted', async () => {
    fetchMock.mockResolvedValue(sseResponse([{ type: 'done', content: 'ok' }]))

    formatNoteSSE('t', 'content', {})
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled())

    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string)
    expect(body).toEqual({ ticket: 't', content: 'content', instruction: '' })
    expect(body.excerpt).toBeUndefined()
  })

  it('maps progress, done, and error events to callbacks', async () => {
    fetchMock.mockResolvedValue(
      sseResponse([
        { type: 'progress', content: '正在整理笔记...' },
        { type: 'chunk', content: '部分' },
        { type: 'done', content: '完整结果' },
      ]),
    )

    const onProgress = vi.fn()
    const onChunk = vi.fn()
    const onDone = vi.fn()
    const onError = vi.fn()

    formatNoteSSE('t', 'c', { onProgress, onChunk, onDone, onError })
    await vi.waitFor(() => expect(onDone).toHaveBeenCalledWith('完整结果'))

    expect(onProgress).toHaveBeenCalledWith('正在整理笔记...')
    expect(onChunk).toHaveBeenCalledWith('部分')
    expect(onError).not.toHaveBeenCalled()
  })

  it('maps error events to onError', async () => {
    fetchMock.mockResolvedValue(sseResponse([{ type: 'error', content: '模型失败' }]))
    const onError = vi.fn()
    formatNoteSSE('t', 'c', { onError })
    await vi.waitFor(() => expect(onError).toHaveBeenCalledWith('模型失败'))
  })
})
