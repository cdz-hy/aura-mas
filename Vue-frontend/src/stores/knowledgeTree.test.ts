import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { issueTicket } from '@/api/auth'
import {
  ensureKnowledgeTree,
  getKnowledgeNodeMessages,
  streamTreeExplain,
  streamTreeFirstPrinciples,
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
  updateKnowledgeNode: vi.fn(),
  getKnowledgeNodeMessages: vi.fn(),
  streamTreeExplain: vi.fn(),
  streamTreeSubdivide: vi.fn(),
  streamTreeFirstPrinciples: vi.fn(),
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

    handlers?.onDone?.()
    expect(store.activeSource).toBeNull()
    expect(store.loading).toBe(false)
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
      expect.any(Object),
    )
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
    expect(store.messagesByNode.node_root).toEqual(messages)
    expect(store.nodes.some(node => node.id === 'node_late')).toBe(false)
  })

  it('refuses nonexistent node selection', async () => {
    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)

    await store.selectNode('missing_node')

    expect(store.currentNodeId).toBe('node_root')
    expect(getKnowledgeNodeMessages).not.toHaveBeenCalledWith('missing_node')
  })

  it('rolls back selection when message loading fails', async () => {
    const store = useKnowledgeTreeStore()
    await store.loadByPlan(42)
    vi.mocked(getKnowledgeNodeMessages).mockRejectedValueOnce(new Error('load failed'))

    await store.selectNode('node_child')

    expect(store.currentNodeId).toBe('node_root')
    expect(store.error).toBe('load failed')
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
  })
})
