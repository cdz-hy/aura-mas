import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import { issueTicket } from '@/api/auth'
import {
  ensureKnowledgeTree,
  getTreeSubdivisionOptions,
  getKnowledgeNodeMessages,
  streamTreeFlashcards,
  streamTreeExplain,
  streamTreeFirstPrinciples,
  streamTreeMultiAngleSubdivide,
  streamTreeQuiz,
  streamTreeSubdivide,
  updateKnowledgeNode,
} from '@/api/knowledgeTree'
import type {
  KnowledgeNode,
  KnowledgeTree,
  TreeFlashcard,
  TreeGeneratedResource,
  TreeMessage,
  TreeSubdivisionOption,
  TreeSseHandlers,
} from '@/types/knowledgeTree'

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
  const subdivisionOptionsLoading = ref(false)
  const subdivisionOptionsError = ref('')
  const panX = ref(0)
  const panY = ref(0)
  const zoom = ref(1)
  const activeSource = shallowRef<EventSource | null>(null)
  let loadToken = 0
  let selectionToken = 0
  let streamToken = 0
  let subdivisionOptionsToken = 0

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

  async function loadSubdivisionOptionsCurrent(): Promise<TreeSubdivisionOption[]> {
    if (!tree.value || !currentNodeId.value) return []
    const token = nextSubdivisionOptionsToken()
    const treeId = tree.value.id
    const nodeId = currentNodeId.value
    subdivisionOptionsLoading.value = true
    subdivisionOptionsError.value = ''

    try {
      const ticketRes = await issueTicket()
      if (!isCurrentSubdivisionOptions(token) || currentNodeId.value !== nodeId) return []
      const res = await getTreeSubdivisionOptions(ticketRes.data.ticket, treeId, nodeId)
      if (!isCurrentSubdivisionOptions(token) || currentNodeId.value !== nodeId) return []
      return res.data?.options || []
    } catch (e) {
      if (isCurrentSubdivisionOptions(token)) {
        subdivisionOptionsError.value = getErrorMessage(e)
      }
      return []
    } finally {
      if (isCurrentSubdivisionOptions(token)) {
        subdivisionOptionsLoading.value = false
      }
    }
  }

  async function multiAngleSubdivideCurrent(angles: TreeSubdivisionOption[]) {
    if (!tree.value || !currentNodeId.value || angles.length === 0) return
    const treeId = tree.value.id
    const nodeId = currentNodeId.value

    await startStream(nodeId, (ticket, handlers) => streamTreeMultiAngleSubdivide(
      ticket,
      treeId,
      nodeId,
      angles,
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

  async function generateQuizCurrent() {
    if (!tree.value || !currentNodeId.value) return
    const treeId = tree.value.id
    const nodeId = currentNodeId.value
    const planId = tree.value.planId

    await startStream(nodeId, (ticket, handlers) => streamTreeQuiz(
      ticket,
      treeId,
      nodeId,
      planId,
      handlers,
    ))
  }

  async function generateFlashcardsCurrent() {
    if (!tree.value || !currentNodeId.value) return
    const treeId = tree.value.id
    const nodeId = currentNodeId.value
    const planId = tree.value.planId

    await startStream(nodeId, (ticket, handlers) => streamTreeFlashcards(
      ticket,
      treeId,
      nodeId,
      planId,
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
    subdivisionOptionsLoading.value = false
    subdivisionOptionsError.value = ''
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

  function nextSubdivisionOptionsToken() {
    subdivisionOptionsToken += 1
    return subdivisionOptionsToken
  }

  function isCurrentSubdivisionOptions(token: number) {
    return token === subdivisionOptionsToken
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
        onResources: resources => {
          if (!isActiveStream(token, source)) return
          appendGeneratedResourcesMessage(nodeId, resources)
        },
        onFlashcards: cards => {
          if (!isActiveStream(token, source)) return
          appendFlashcardsMessage(nodeId, cards)
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

  function appendGeneratedResourcesMessage(nodeId: string, resources: TreeGeneratedResource[]) {
    if (!resources.length || !tree.value) return
    const titles = resources.map(resource => resource.title || resource.type).join('、')
    appendLocalAssistantMessage(nodeId, `已生成学习资源：${titles}`)
  }

  function appendFlashcardsMessage(nodeId: string, cards: TreeFlashcard[]) {
    if (!cards.length || !tree.value) return
    const preview = cards
      .slice(0, 3)
      .map((card, index) => `${index + 1}. ${card.question}\n   ${card.answer}`)
      .join('\n')
    const suffix = cards.length > 3 ? `\n...共 ${cards.length} 张` : `\n共 ${cards.length} 张`
    appendLocalAssistantMessage(nodeId, `已生成闪卡：\n${preview}${suffix}`)
  }

  function appendLocalAssistantMessage(nodeId: string, content: string) {
    if (!tree.value) return
    const existing = messagesByNode.value[nodeId] || []
    messagesByNode.value[nodeId] = [
      ...existing,
      {
        id: -Date.now(),
        treeId: tree.value.id,
        nodeId,
        role: 'assistant',
        content,
      },
    ]
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
    subdivisionOptionsLoading,
    subdivisionOptionsError,
    panX,
    panY,
    zoom,
    activeSource,
    loadByPlan,
    selectNode,
    toggleCollapsed,
    sendMessage,
    subdivideCurrent,
    loadSubdivisionOptionsCurrent,
    multiAngleSubdivideCurrent,
    firstPrinciplesCurrent,
    generateQuizCurrent,
    generateFlashcardsCurrent,
    stopStream,
  }
})

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  return '请求失败'
}
