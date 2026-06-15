import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  getTreeSubdivisionOptions,
  streamTreeExplain,
  streamTreeFlashcards,
  streamTreeMultiAngleSubdivide,
  streamTreeQuiz,
} from './knowledgeTree'
import type { TreeMessage } from '@/types/knowledgeTree'

const requestMock = vi.hoisted(() => ({
  get: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  default: {
    get: requestMock.get,
  },
  PYTHON_AI_BASE: 'http://localhost:8002',
}))

type Listener = (event: MessageEvent) => void

class FakeEventSource {
  static instances: FakeEventSource[] = []

  url: string
  onmessage: Listener | null = null
  onerror: (() => void) | null = null
  listeners = new Map<string, Listener[]>()
  close = vi.fn()

  constructor(url: string) {
    this.url = url
    FakeEventSource.instances.push(this)
  }

  addEventListener(type: string, listener: Listener) {
    const listeners = this.listeners.get(type) || []
    listeners.push(listener)
    this.listeners.set(type, listeners)
  }

  emit(type: string, data: unknown) {
    const event = { data: JSON.stringify(data) } as MessageEvent
    for (const listener of this.listeners.get(type) || []) {
      listener(event)
    }
  }
}

describe('knowledge tree SSE API', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
    requestMock.get.mockReset()
  })

  it('maps saved-message and created-node backend events to tree handlers', () => {
    const onMessage = vi.fn()
    const onNodes = vi.fn()
    const message: TreeMessage = {
      id: 7,
      treeId: 'tree_1',
      nodeId: 'node_root',
      role: 'assistant',
      content: 'saved',
    }
    const createdNodes = [
      {
        id: 'node_child',
        treeId: 'tree_1',
        parentId: 'node_root',
        title: 'Child',
      },
    ]

    streamTreeExplain('ticket_1', 'tree_1', 'node_root', 'Explain this', {
      onMessage,
      onNodes,
    })

    const source = FakeEventSource.instances[0]
    expect(source.listeners.has('message_saved')).toBe(true)
    expect(source.listeners.has('nodes_created')).toBe(true)

    source.emit('message_saved', {
      type: 'message_saved',
      message,
    })
    source.emit('nodes_created', {
      type: 'nodes_created',
      nodes: createdNodes,
    })

    expect(onMessage).toHaveBeenCalledWith(message)
    expect(onNodes).toHaveBeenCalledWith(createdNodes)
  })

  it('maps generated resource and flashcard backend events to tree handlers', () => {
    const onResources = vi.fn()
    const onFlashcards = vi.fn()
    const resources = [{ id: 123, type: 'quiz', title: '节点练习题' }]
    const cards = [{ question: 'Q', answer: 'A', difficulty: 1 }]

    streamTreeQuiz('ticket_1', 'tree_1', 'node_root', 42, { onResources })
    streamTreeFlashcards('ticket_1', 'tree_1', 'node_root', 42, { onFlashcards })

    const quizSource = FakeEventSource.instances[0]
    const flashcardSource = FakeEventSource.instances[1]
    expect(quizSource.url).toContain('plan_id=42')
    expect(flashcardSource.url).toContain('plan_id=42')
    expect(quizSource.listeners.has('resource_generated')).toBe(true)
    expect(flashcardSource.listeners.has('flashcards_generated')).toBe(true)

    quizSource.emit('resource_generated', {
      type: 'resource_generated',
      resources,
    })
    flashcardSource.emit('flashcards_generated', {
      type: 'flashcards_generated',
      cards,
    })

    expect(onResources).toHaveBeenCalledWith(resources)
    expect(onFlashcards).toHaveBeenCalledWith(cards)
  })

  it('requests subdivision options from the Python AI base with ticket auth', async () => {
    requestMock.get.mockResolvedValueOnce({ data: { node_id: 'node_root', options: [] } })

    await getTreeSubdivisionOptions('ticket_1', 'tree_1', 'node_root')

    expect(requestMock.get).toHaveBeenCalledWith(
      'http://localhost:8002/api/ai/tree/tree_1/nodes/node_root/subdivision-options',
      { params: { ticket: 'ticket_1', mode: 'Lite' } },
    )
  })

  it('streams multi-angle subdivision with encoded angles', () => {
    const onNodes = vi.fn()

    streamTreeMultiAngleSubdivide('ticket_1', 'tree_1', 'node_root', [
      { angle: 'by_concept', label: '按概念拆', rationale: '先拆概念' },
    ], 'Medium', { onNodes })

    const source = FakeEventSource.instances[0]
    expect(decodeURIComponent(source.url)).toContain('/api/ai/tree/tree_1/nodes/node_root/multi-angle-subdivide')
    expect(decodeURIComponent(source.url)).toContain('"label":"按概念拆"')
    expect(decodeURIComponent(source.url)).toContain('mode=Medium')

    source.emit('nodes_created', {
      type: 'nodes_created',
      nodes: [{ id: 'node_child', treeId: 'tree_1', parentId: 'node_root', title: 'Child' }],
    })

    expect(onNodes).toHaveBeenCalledWith([
      { id: 'node_child', treeId: 'tree_1', parentId: 'node_root', title: 'Child' },
    ])
  })

  it('surfaces parse errors and closes the source', () => {
    const onError = vi.fn()
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    streamTreeExplain('ticket_1', 'tree_1', 'node_root', 'Explain this', {
      onError,
    })

    const source = FakeEventSource.instances[0]
    for (const listener of source.listeners.get('message_saved') || []) {
      listener({ data: '{bad json' } as MessageEvent)
    }

    expect(onError).toHaveBeenCalledWith('响应解析失败')
    expect(source.close).toHaveBeenCalled()
    consoleError.mockRestore()
  })
})
