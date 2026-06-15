import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { issueTicket } from '@/api/auth'
import {
  ensureKnowledgeTree,
  getTreeSubdivisionOptions,
  getKnowledgeNodeMessages,
  streamTreeExplain,
  streamTreeFlashcards,
  streamTreeFirstPrinciples,
  streamTreeMultiAngleSubdivide,
  streamTreeQuiz,
  streamTreeSubdivide,
  updateKnowledgeNode,
} from '@/api/knowledgeTree'
import { useKnowledgeTreeStore } from './knowledgeTree'
import type { KnowledgeNode, KnowledgeTree, TreeMessage, TreeSseHandlers } from '@/types/knowledgeTree'

vi.mock('@/api/auth', () => ({
  issueTicket: vi.fn(),
}))

vi.mock('@/api/knowledgeTree', () => ({
  ensureKnowledgeTree: vi.fn(),
  getKnowledgeTree: vi.fn(),
  getTreeSubdivisionOptions: vi.fn(),
  updateKnowledgeNode: vi.fn(),
  getKnowledgeNodeMessages: vi.fn(),
  streamTreeExplain: vi.fn(),
  streamTreeSubdivide: vi.fn(),
  streamTreeFirstPrinciples: vi.fn(),
  streamTreeMultiAngleSubdivide: vi.fn(),
  streamTreeQuiz: vi.fn(),
  streamTreeFlashcards: vi.fn(),
}))

const tree: KnowledgeTree = {
  id: 'tree_1',
  planId: 42,
  title: 'Knowledge Tree',
  currentNodeId: 'node_root',
}

const nodes: KnowledgeNode[] = [
  {
    id: 'node_root',
    treeId: 'tree_1',
    parentId: null,
    title: 'Root',
    collapsed: false,
  },
  {
    id: 'node_child',
    treeId: 'tree_1',
    parentId: 'node_root',
    title: 'Child',
    collapsed: false,
  },
]

const messages: TreeMessage[] = [
  {
    id: 1,
    treeId: 'tree_1',
    nodeId: 'node_root',
    role: 'assistant',
    content: 'hello',
  },
]

class FakeEventSource {
  closed = false
  close = vi.fn(() => {
    this.closed = true
  })
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('useKnowledgeTreeStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(ensureKnowledgeTree).mockResolvedValue({ data: { tree, nodes } })
    vi.mocked(getKnowledgeNodeMessages).mockResolvedValue({ data: messages })
    vi.mocked(updateKnowledgeNode).mockResolvedValue({ data: { ...nodes[0], collapsed: true } })
    vi.mocked(issueTicket).mockResolvedValue({ data: { ticket: 'ticket_1' } })
  })

  it('loads a plan tree and selects the current node messages', async () => {
    const store = useKnowledgeTreeStore()

    await store.loadByPlan(42)

    expect(ensureKnowledgeTree).toHaveBeenCalledWith(42)
    expect(store.tree?.id).toBe('tree_1')
    expect(store.nodes).toHaveLength(2)
    expect(store.currentNodeId).toBe('node_root')
    expect(store.messagesByNode.node_root).toEqual(messages)
  })

  it('keeps the newest plan load when an older load finishes later', async () => {
    const olderLoad = deferred<{ data: { tree: KnowledgeTree, nodes: KnowledgeNode[] } }>()
    const newerLoad = deferred<{ data: { tree: KnowledgeTree, nodes: KnowledgeNode[] } }>()
    const olderMessages = deferred<{ data: TreeMessage[] }>()
    const newerMessages = deferred<{ data: TreeMessage[] }>()
    const newerTree: KnowledgeTree = {
      id: 'tree_2',
      planId: 43,
      title: 'Newer Tree',
      currentNodeId: 'node_new',
    }
    const newerNodes: KnowledgeNode[] = [
      {
        id: 'node_new',
        treeId: 'tree_2',
        parentId: null,
        title: 'New Root',
        collapsed: false,
      },
    ]
    const newerMessage: TreeMessage = {
      id: 2,
      treeId: 'tree_2',
      nodeId: 'node_new',
      role: 'assistant',
      content: 'newer',
    }
    const olderMessage: TreeMessage = {
      id: 3,
      treeId: 'tree_1',
      nodeId: 'node_root',
      role: 'assistant',
      content: 'older',
    }

    vi.mocked(ensureKnowledgeTree)
      .mockReturnValueOnce(olderLoad.promise)
      .mockReturnValueOnce(newerLoad.promise)
    vi.mocked(getKnowledgeNodeMessages).mockImplementation(nodeId => {
      if (nodeId === 'node_root') return olderMessages.promise
      return newerMessages.promise
    })

    const store = useKnowledgeTreeStore()
    const olderPromise = store.loadByPlan(42)
    const newerPromise = store.loadByPlan(43)

    olderLoad.resolve({ data: { tree, nodes } })
    await Promise.resolve()
    newerLoad.resolve({ data: { tree: newerTree, nodes: newerNodes } })
    await Promise.resolve()
    newerMessages.resolve({ data: [newerMessage] })
    await newerPromise
    olderMessages.resolve({ data: [olderMessage] })
    await olderPromise

    expect(store.tree?.id).toBe('tree_2')
    expect(store.nodes).toEqual(newerNodes)
    expect(store.currentNodeId).toBe('node_new')
    expect(store.messagesByNode).toEqual({ node_new: [newerMessage] })
    expect(store.loading).toBe(false)
  })

  it('clears previous plan state while a new plan is loading and when it fails', async () => {
    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)
    store.streamingNodeId = 'node_root'
    store.streamingText = 'partial'

    const pendingLoad = deferred<{ data: { tree: KnowledgeTree, nodes: KnowledgeNode[] } }>()
    vi.mocked(ensureKnowledgeTree).mockReturnValueOnce(pendingLoad.promise)
    const loadPromise = store.loadByPlan(43)

    expect(store.tree).toBeNull()
    expect(store.nodes).toEqual([])
    expect(store.currentNodeId).toBeNull()
    expect(store.messagesByNode).toEqual({})
    expect(store.streamingNodeId).toBeNull()
    expect(store.streamingText).toBe('')

    pendingLoad.reject(new Error('plan failed'))
    await loadPromise

    expect(store.error).toBe('plan failed')
    expect(store.tree).toBeNull()
    expect(store.nodes).toEqual([])
    expect(store.currentNodeId).toBeNull()
    expect(store.messagesByNode).toEqual({})
    expect(store.loading).toBe(false)
  })

  it('toggles collapsed state locally and persists it', async () => {
    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)

    await store.toggleCollapsed('node_root')

    expect(store.nodes.find(node => node.id === 'node_root')?.collapsed).toBe(true)
    expect(updateKnowledgeNode).toHaveBeenCalledWith('node_root', { collapsed: true })
  })

  it('issues a ticket before streaming a message and appends stream text', async () => {
    const source = new FakeEventSource() as unknown as EventSource
    let handlers: TreeSseHandlers | undefined
    vi.mocked(streamTreeExplain).mockImplementation((_ticket, _treeId, _nodeId, _message, h) => {
      handlers = h
      return source
    })

    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)
    await store.sendMessage('Explain this')

    expect(issueTicket).toHaveBeenCalled()
    expect(streamTreeExplain).toHaveBeenCalledWith(
      'ticket_1',
      'tree_1',
      'node_root',
      'Explain this',
      expect.any(Object),
    )

    handlers?.onChunk?.('partial')
    expect(store.streamingText).toBe('partial')
    expect(store.streamingNodeId).toBe('node_root')

    handlers?.onDone?.()
    expect(store.activeSource).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.streamingNodeId).toBeNull()
  })

  it('starts a message stream with the originally selected node when ticket issuance is pending', async () => {
    const ticket = deferred<{ data: { ticket: string } }>()
    vi.mocked(issueTicket).mockReturnValue(ticket.promise)
    vi.mocked(getKnowledgeNodeMessages).mockResolvedValue({ data: [] })
    vi.mocked(streamTreeExplain).mockReturnValue(new FakeEventSource() as unknown as EventSource)

    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)
    const sendPromise = store.sendMessage('Explain this')

    await store.selectNode('node_child')
    ticket.resolve({ data: { ticket: 'ticket_1' } })
    await sendPromise

    expect(streamTreeExplain).toHaveBeenCalledWith(
      'ticket_1',
      'tree_1',
      'node_root',
      'Explain this',
      expect.any(Object),
    )
  })

  it('starts action streams with the originally selected node when ticket issuance is pending', async () => {
    vi.mocked(getKnowledgeNodeMessages).mockResolvedValue({ data: [] })
    vi.mocked(streamTreeSubdivide).mockReturnValue(new FakeEventSource() as unknown as EventSource)
    vi.mocked(streamTreeFirstPrinciples).mockReturnValue(new FakeEventSource() as unknown as EventSource)
    vi.mocked(streamTreeQuiz).mockReturnValue(new FakeEventSource() as unknown as EventSource)
    vi.mocked(streamTreeFlashcards).mockReturnValue(new FakeEventSource() as unknown as EventSource)

    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)

    const subdivideTicket = deferred<{ data: { ticket: string } }>()
    vi.mocked(issueTicket).mockReturnValueOnce(subdivideTicket.promise)
    const subdividePromise = store.subdivideCurrent('angle')
    await store.selectNode('node_child')
    subdivideTicket.resolve({ data: { ticket: 'ticket_1' } })
    await subdividePromise

    expect(streamTreeSubdivide).toHaveBeenCalledWith(
      'ticket_1',
      'tree_1',
      'node_root',
      'angle',
      'Lite',
      expect.any(Object),
    )

    await store.selectNode('node_root')
    const firstPrinciplesTicket = deferred<{ data: { ticket: string } }>()
    vi.mocked(issueTicket).mockReturnValueOnce(firstPrinciplesTicket.promise)
    const firstPrinciplesPromise = store.firstPrinciplesCurrent()
    await store.selectNode('node_child')
    firstPrinciplesTicket.resolve({ data: { ticket: 'ticket_2' } })
    await firstPrinciplesPromise

    expect(streamTreeFirstPrinciples).toHaveBeenCalledWith(
      'ticket_2',
      'tree_1',
      'node_root',
      'Lite',
      expect.any(Object),
    )

    await store.selectNode('node_root')
    const quizTicket = deferred<{ data: { ticket: string } }>()
    vi.mocked(issueTicket).mockReturnValueOnce(quizTicket.promise)
    const quizPromise = store.generateQuizCurrent()
    await store.selectNode('node_child')
    quizTicket.resolve({ data: { ticket: 'ticket_3' } })
    await quizPromise

    expect(streamTreeQuiz).toHaveBeenCalledWith(
      'ticket_3',
      'tree_1',
      'node_root',
      42,
      expect.any(Object),
    )

    await store.selectNode('node_root')
    const flashcardsTicket = deferred<{ data: { ticket: string } }>()
    vi.mocked(issueTicket).mockReturnValueOnce(flashcardsTicket.promise)
    const flashcardsPromise = store.generateFlashcardsCurrent()
    await store.selectNode('node_child')
    flashcardsTicket.resolve({ data: { ticket: 'ticket_4' } })
    await flashcardsPromise

    expect(streamTreeFlashcards).toHaveBeenCalledWith(
      'ticket_4',
      'tree_1',
      'node_root',
      42,
      expect.any(Object),
    )
  })

  it('loads subdivision options for the current node with a ticket', async () => {
    vi.mocked(getTreeSubdivisionOptions).mockResolvedValueOnce({
      data: {
        node_id: 'node_root',
        options: [{ angle: 'by_concept', label: '按概念拆', rationale: '先拆概念' }],
      },
    })
    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)

    const options = await store.loadSubdivisionOptionsCurrent()

    expect(issueTicket).toHaveBeenCalled()
    expect(getTreeSubdivisionOptions).toHaveBeenCalledWith('ticket_1', 'tree_1', 'node_root', 'Lite')
    expect(options).toEqual([{ angle: 'by_concept', label: '按概念拆', rationale: '先拆概念' }])
    expect(store.subdivisionOptionsLoading).toBe(false)
    expect(store.subdivisionOptionsError).toBe('')
  })

  it('ignores stale subdivision options when selection changes while loading', async () => {
    const pendingOptions = deferred<{
      data: {
        node_id: string
        options: { angle: string; label: string; rationale: string }[]
      }
    }>()
    vi.mocked(getTreeSubdivisionOptions).mockReturnValueOnce(pendingOptions.promise)
    vi.mocked(getKnowledgeNodeMessages).mockResolvedValue({ data: [] })

    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)
    const optionsPromise = store.loadSubdivisionOptionsCurrent()
    await store.selectNode('node_child')
    pendingOptions.resolve({
      data: {
        node_id: 'node_root',
        options: [{ angle: 'stale', label: '过期角度', rationale: '不应使用' }],
      },
    })

    expect(await optionsPromise).toEqual([])
    expect(store.currentNodeId).toBe('node_child')
    expect(store.subdivisionOptionsError).toBe('')
  })

  it('starts multi-angle split stream and merges created nodes', async () => {
    const source = new FakeEventSource() as unknown as EventSource
    let handlers: TreeSseHandlers | undefined
    vi.mocked(streamTreeMultiAngleSubdivide).mockImplementation((_ticket, _treeId, _nodeId, _angles, _mode, h) => {
      handlers = h
      return source
    })
    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)

    await store.multiAngleSubdivideCurrent([
      { angle: 'by_concept', label: '按概念拆', rationale: '先拆概念' },
    ])
    handlers?.onNodes?.([
      { id: 'group_1', treeId: 'tree_1', parentId: 'node_root', title: '按概念拆' },
    ])
    handlers?.onDone?.()

    expect(streamTreeMultiAngleSubdivide).toHaveBeenCalledWith(
      'ticket_1',
      'tree_1',
      'node_root',
      [{ angle: 'by_concept', label: '按概念拆', rationale: '先拆概念' }],
      'Lite',
      expect.any(Object),
    )
    expect(store.nodes.some(node => node.id === 'group_1')).toBe(true)
    expect(store.loading).toBe(false)
  })

  it('ignores stale callbacks from an old stream after a newer stream starts', async () => {
    const source1 = new FakeEventSource() as unknown as EventSource
    const source2 = new FakeEventSource() as unknown as EventSource
    const handlers: TreeSseHandlers[] = []
    vi.mocked(streamTreeExplain).mockImplementation((_ticket, _treeId, _nodeId, _message, h) => {
      handlers.push(h)
      return handlers.length === 1 ? source1 : source2
    })

    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)
    await store.sendMessage('first')
    await store.sendMessage('second')

    handlers[1].onChunk?.('new')
    handlers[0].onChunk?.('old')
    handlers[0].onMessage?.({
      id: 99,
      treeId: 'tree_1',
      nodeId: 'node_root',
      role: 'assistant',
      content: 'stale',
    })
    handlers[0].onNodes?.([
      {
        id: 'node_stale',
        treeId: 'tree_1',
        parentId: 'node_root',
        title: 'Stale',
      },
    ])
    handlers[0].onDone?.()

    expect(store.streamingText).toBe('new')
    expect(store.streamingNodeId).toBe('node_root')
    expect(store.messagesByNode.node_root).toEqual(messages)
    expect(store.nodes.some(node => node.id === 'node_stale')).toBe(false)
    expect(store.activeSource).toBe(source2)
    expect(store.loading).toBe(true)
  })

  it('ignores callbacks from a source after it has completed', async () => {
    const source = new FakeEventSource() as unknown as EventSource
    let handlers: TreeSseHandlers | undefined
    vi.mocked(streamTreeExplain).mockImplementation((_ticket, _treeId, _nodeId, _message, h) => {
      handlers = h
      return source
    })

    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)
    await store.sendMessage('Explain this')

    handlers?.onChunk?.('live')
    handlers?.onDone?.()
    handlers?.onChunk?.('late')
    handlers?.onMessage?.({
      id: 100,
      treeId: 'tree_1',
      nodeId: 'node_root',
      role: 'assistant',
      content: 'late',
    })
    handlers?.onNodes?.([
      {
        id: 'node_late',
        treeId: 'tree_1',
        parentId: 'node_root',
        title: 'Late',
      },
    ])

    expect(store.activeSource).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.streamingText).toBe('')
    expect(store.streamingNodeId).toBeNull()
    expect(store.messagesByNode.node_root).toEqual(messages)
    expect(store.nodes.some(node => node.id === 'node_late')).toBe(false)
  })

  it('refuses nonexistent node selection', async () => {
    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)

    const selected = await store.selectNode('missing_node')

    expect(selected).toBe(false)
    expect(store.currentNodeId).toBe('node_root')
    expect(getKnowledgeNodeMessages).not.toHaveBeenCalledWith('missing_node')
  })

  it('rolls back selection when message loading fails', async () => {
    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)
    vi.mocked(getKnowledgeNodeMessages).mockRejectedValueOnce(new Error('load failed'))

    const selected = await store.selectNode('node_child')

    expect(selected).toBe(false)
    expect(store.currentNodeId).toBe('node_root')
    expect(store.error).toBe('load failed')
  })

  it('ignores stale selection failure after a newer selection succeeds', async () => {
    const siblingNode: KnowledgeNode = {
      id: 'node_sibling',
      treeId: 'tree_1',
      parentId: 'node_root',
      title: 'Sibling',
      collapsed: false,
    }
    const staleSelection = deferred<{ data: TreeMessage[] }>()
    const newerSelection = deferred<{ data: TreeMessage[] }>()
    const siblingMessage: TreeMessage = {
      id: 4,
      treeId: 'tree_1',
      nodeId: 'node_sibling',
      role: 'assistant',
      content: 'sibling',
    }
    vi.mocked(getKnowledgeNodeMessages).mockImplementation(nodeId => {
      if (nodeId === 'node_child') return staleSelection.promise
      if (nodeId === 'node_sibling') return newerSelection.promise
      return Promise.resolve({ data: messages })
    })
    vi.mocked(ensureKnowledgeTree).mockResolvedValueOnce({ data: { tree, nodes: [...nodes, siblingNode] } })

    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)

    const stalePromise = store.selectNode('node_child')
    const newerPromise = store.selectNode('node_sibling')
    newerSelection.resolve({ data: [siblingMessage] })
    await newerPromise
    staleSelection.reject(new Error('stale failed'))
    await stalePromise

    expect(store.currentNodeId).toBe('node_sibling')
    expect(store.messagesByNode.node_sibling).toEqual([siblingMessage])
    expect(store.error).toBe('')
  })

  it('falls back to the first loaded node when tree current node is absent', async () => {
    vi.mocked(ensureKnowledgeTree).mockResolvedValueOnce({
      data: {
        tree: { ...tree, currentNodeId: 'missing_node' },
        nodes,
      },
    })

    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)

    expect(store.currentNodeId).toBe('node_root')
  })

  it('applies captured message and node handlers to store state', async () => {
    const source = new FakeEventSource() as unknown as EventSource
    let handlers: TreeSseHandlers | undefined
    vi.mocked(streamTreeExplain).mockImplementation((_ticket, _treeId, _nodeId, _message, h) => {
      handlers = h
      return source
    })

    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)
    await store.sendMessage('Explain this')

    handlers?.onMessage?.({
      id: 2,
      treeId: 'tree_1',
      nodeId: 'node_root',
      role: 'assistant',
      content: 'saved',
    })
    handlers?.onNodes?.([
      {
        id: 'node_created',
        treeId: 'tree_1',
        parentId: 'node_root',
        title: 'Created',
      },
    ])

    expect(store.messagesByNode.node_root.map(message => message.content)).toEqual(['hello', 'saved'])
    expect(store.nodes.some(node => node.id === 'node_created')).toBe(true)
  })

  it('appends local summaries for generated resources and flashcards', async () => {
    const source = new FakeEventSource() as unknown as EventSource
    let handlers: TreeSseHandlers | undefined
    vi.mocked(streamTreeQuiz).mockImplementation((_ticket, _treeId, _nodeId, _planId, h) => {
      handlers = h
      return source
    })

    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)
    await store.generateQuizCurrent()

    handlers?.onResources?.([{ id: 123, type: 'quiz', title: '节点练习题' }])
    handlers?.onFlashcards?.([
      { question: 'Q1', answer: 'A1', difficulty: 1 },
      { question: 'Q2', answer: 'A2', difficulty: 2 },
    ])

    expect(store.messagesByNode.node_root.map(message => message.content)).toEqual([
      'hello',
      '已生成学习资源：节点练习题',
      '已生成闪卡：\n1. Q1\n   A1\n2. Q2\n   A2\n共 2 张',
    ])
  })

  it('closes the active stream when stopped', async () => {
    const source = new FakeEventSource() as unknown as EventSource
    vi.mocked(streamTreeExplain).mockReturnValue(source)

    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)
    await store.sendMessage('Explain this')
    store.stopStream()

    expect(source.close).toHaveBeenCalled()
    expect(store.activeSource).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.streamingNodeId).toBeNull()
  })
})
