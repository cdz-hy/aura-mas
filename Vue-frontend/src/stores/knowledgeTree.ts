import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import { issueTicket } from '@/api/auth'
import {
  ensureKnowledgeTree,
  getKnowledgeNodeMessages,
  streamTreeExplain,
  streamTreeFirstPrinciples,
  streamTreeSubdivide,
  updateKnowledgeNode,
} from '@/api/knowledgeTree'
import type { KnowledgeNode, KnowledgeTree, TreeMessage, TreeSseHandlers } from '@/types/knowledgeTree'

type StreamStarter = (ticket: string, handlers: TreeSseHandlers) => EventSource

export const useKnowledgeTreeStore = defineStore('knowledgeTree', () => {
  const tree = ref<KnowledgeTree | null>(null)
  const nodes = ref<KnowledgeNode[]>([])
  const messagesByNode = ref<Record<string, TreeMessage[]>>({})
  const currentNodeId = ref<string | null>(null)
  const streamingNodeId = ref<string | null>(null)
  const streamingText = ref('')
  const loading = ref(false)
  const error = ref('')
  const panX = ref(0)
  const panY = ref(0)
  const zoom = ref(1)
  const activeSource = shallowRef<EventSource | null>(null)
  let loadToken = 0
  let selectionToken = 0
  let streamToken = 0

  async function loadByPlan(planId: number) {
    const token = nextLoadToken()
    stopStream()
    loading.value = true
    error.value = ''
    clearTreeState()
    try {
      const res = await ensureKnowledgeTree(planId)
      if (!isCurrentLoad(token)) return
      tree.value = res.data.tree
      nodes.value = res.data.nodes || []
      const candidateNodeId = tree.value.currentNodeId
      const nextNodeId = candidateNodeId && hasNode(candidateNodeId)
        ? candidateNodeId
        : nodes.value[0]?.id || null
      currentNodeId.value = nextNodeId
      if (nextNodeId) {
        await selectNodeForLoad(nextNodeId, token)
      }
    } catch (e) {
      if (!isCurrentLoad(token)) return
      clearTreeState()
      error.value = getErrorMessage(e)
    } finally {
      if (isCurrentLoad(token)) {
        loading.value = false
      }
    }
  }

  async function selectNode(nodeId: string) {
    if (!hasNode(nodeId)) return false

    const token = nextSelectionToken()
    const previousNodeId = currentNodeId.value
    currentNodeId.value = nodeId
    error.value = ''
    try {
      const res = await getKnowledgeNodeMessages(nodeId)
      if (!isCurrentSelection(token) || currentNodeId.value !== nodeId) return false
      messagesByNode.value[nodeId] = res.data || []
      return true
    } catch (e) {
      if (!isCurrentSelection(token)) return false
      currentNodeId.value = previousNodeId
      error.value = getErrorMessage(e)
      return false
    }
  }

  async function selectNodeForLoad(nodeId: string, token: number) {
    if (!hasNode(nodeId)) return false

    currentNodeId.value = nodeId
    try {
      const res = await getKnowledgeNodeMessages(nodeId)
      if (!isCurrentLoad(token)) return false
      messagesByNode.value[nodeId] = res.data || []
      return true
    } catch (e) {
      if (!isCurrentLoad(token)) return false
      clearTreeState()
      error.value = getErrorMessage(e)
      return false
    }
  }

  async function toggleCollapsed(nodeId: string) {
    const node = nodes.value.find(item => item.id === nodeId)
    if (!node) return

    const nextCollapsed = !node.collapsed
    node.collapsed = nextCollapsed
    error.value = ''

    try {
      const res = await updateKnowledgeNode(nodeId, { collapsed: nextCollapsed })
      replaceNode(res.data)
    } catch (e) {
      node.collapsed = !nextCollapsed
      error.value = getErrorMessage(e)
    }
  }

  async function sendMessage(message: string) {
    const trimmed = message.trim()
    if (!trimmed || !tree.value || !currentNodeId.value) return
    const treeId = tree.value.id
    const nodeId = currentNodeId.value

    await startStream(nodeId, (ticket, handlers) => streamTreeExplain(
      ticket,
      treeId,
      nodeId,
      trimmed,
      handlers,
    ))
  }

  async function subdivideCurrent(angle: string) {
    if (!tree.value || !currentNodeId.value) return
    const treeId = tree.value.id
    const nodeId = currentNodeId.value

    await startStream(nodeId, (ticket, handlers) => streamTreeSubdivide(
      ticket,
      treeId,
      nodeId,
      angle,
      handlers,
    ))
  }

  async function firstPrinciplesCurrent() {
    if (!tree.value || !currentNodeId.value) return
    const treeId = tree.value.id
    const nodeId = currentNodeId.value

    await startStream(nodeId, (ticket, handlers) => streamTreeFirstPrinciples(
      ticket,
      treeId,
      nodeId,
      handlers,
    ))
  }

  function stopStream() {
    streamToken += 1
    if (activeSource.value) {
      activeSource.value.close()
      activeSource.value = null
    }
    loading.value = false
    streamingNodeId.value = null
    streamingText.value = ''
  }

  function clearTreeState() {
    nextSelectionToken()
    tree.value = null
    nodes.value = []
    currentNodeId.value = null
    messagesByNode.value = {}
    streamingNodeId.value = null
    streamingText.value = ''
  }

  function nextLoadToken() {
    loadToken += 1
    return loadToken
  }

  function isCurrentLoad(token: number) {
    return token === loadToken
  }

  function nextSelectionToken() {
    selectionToken += 1
    return selectionToken
  }

  function isCurrentSelection(token: number) {
    return token === selectionToken
  }

  async function startStream(nodeId: string, start: StreamStarter) {
    stopStream()
    const token = streamToken
    loading.value = true
    error.value = ''
    streamingNodeId.value = nodeId
    streamingText.value = ''

    try {
      const ticketRes = await issueTicket()
      if (!isCurrentToken(token)) return

      const source = start(ticketRes.data.ticket, {
        onProgress: content => {
          if (!isActiveStream(token, source)) return
          streamingText.value = content
        },
        onChunk: content => {
          if (!isActiveStream(token, source)) return
          streamingText.value += content
        },
        onStreamText: content => {
          if (!isActiveStream(token, source)) return
          streamingText.value += content
        },
        onMessage: message => {
          if (!isActiveStream(token, source)) return
          const existing = messagesByNode.value[message.nodeId] || []
          messagesByNode.value[message.nodeId] = [...existing, message]
        },
        onNodes: nextNodes => {
          if (!isActiveStream(token, source)) return
          mergeNodes(nextNodes)
        },
        onDone: () => {
          if (!isActiveStream(token, source)) return
          activeSource.value = null
          loading.value = false
          streamingNodeId.value = null
          streamingText.value = ''
        },
        onError: message => {
          if (!isActiveStream(token, source)) return
          error.value = message
          activeSource.value = null
          loading.value = false
          streamingNodeId.value = null
          streamingText.value = ''
        },
      })
      if (!isCurrentToken(token)) {
        source.close()
        return
      }
      activeSource.value = source
    } catch (e) {
      if (!isCurrentToken(token)) return
      error.value = getErrorMessage(e)
      loading.value = false
      activeSource.value = null
      streamingNodeId.value = null
      streamingText.value = ''
    }
  }

  function replaceNode(nextNode: KnowledgeNode) {
    nodes.value = nodes.value.map(node => node.id === nextNode.id ? nextNode : node)
  }

  function mergeNodes(nextNodes: KnowledgeNode[]) {
    const byId = new Map(nodes.value.map(node => [node.id, node]))
    for (const node of nextNodes) {
      byId.set(node.id, { ...byId.get(node.id), ...node })
    }
    nodes.value = Array.from(byId.values())
  }

  function hasNode(nodeId: string) {
    return nodes.value.some(node => node.id === nodeId)
  }

  function isCurrentToken(token: number) {
    return token === streamToken
  }

  function isActiveStream(token: number, source: EventSource) {
    return isCurrentToken(token) && activeSource.value === source
  }

  return {
    tree,
    nodes,
    messagesByNode,
    currentNodeId,
    streamingNodeId,
    streamingText,
    loading,
    error,
    panX,
    panY,
    zoom,
    activeSource,
    loadByPlan,
    selectNode,
    toggleCollapsed,
    sendMessage,
    subdivideCurrent,
    firstPrinciplesCurrent,
    stopStream,
  }
})

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  return '请求失败'
}
