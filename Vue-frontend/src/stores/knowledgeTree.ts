import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import { issueTicket } from '@/api/auth'
import {
  ensureKnowledgeTree,
  getKnowledgeTree,
  getTreeSubdivisionOptions,
  getKnowledgeNodeMessages,
  streamTreeFlashcards,
  streamTreeExplain,
  streamTreeFirstPrinciples,
  streamTreeMultiAngleSubdivide,
  streamTreeQuiz,
  streamTreeSubdivide,
  streamTreeBootstrap,
  updateKnowledgeNode,
  deleteKnowledgeNode,
  fetchPreviewTopics,
  streamGrowChildren,
} from '@/api/knowledgeTree'
import type {
  KnowledgeNode,
  KnowledgeTree,
  TreeSplitMode,
  TreeSubdivisionCaution,
  TreeFlashcard,
  TreeGeneratedResource,
  TreeMessage,
  TreeSubdivisionOption,
  TreeSseHandlers,
} from '@/types/knowledgeTree'

type StreamStarter = (ticket: string, handlers: TreeSseHandlers) => EventSource
const MAX_TREE_DEPTH = 3
const TREE_DEPTH_LIMIT_MESSAGE = '当前节点已达最深层，无法继续拆分'

export const useKnowledgeTreeStore = defineStore('knowledgeTree', () => {
  const tree = ref<KnowledgeTree | null>(null)
  const nodes = ref<KnowledgeNode[]>([])
  const messagesByNode = ref<Record<string, TreeMessage[]>>({})
  const currentNodeId = ref<string | null>(null)
  const streamingNodeId = ref<string | null>(null)
  const streamingText = ref('')
  const loading = ref(false)
  const error = ref('')
  const splitMode = ref<TreeSplitMode>('Lite')
  const subdivisionOptionsLoading = ref(false)
  const subdivisionOptionsError = ref('')
  const subdivisionCaution = ref<TreeSubdivisionCaution | null>(null)
  const panX = ref(0)
  const panY = ref(0)
  const zoom = ref(1)
  const activeSource = shallowRef<EventSource | null>(null)
  const draggingNodeId = ref<string | null>(null)
  const fpStreamingActive = ref(false)
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
      // 不在进入知识树时自动 bootstrap，避免一级模块被批量拆子节点
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

  async function reparentNode(nodeId: string, newParentId: string) {
    const node = nodes.value.find(item => item.id === nodeId)
    const parent = nodes.value.find(item => item.id === newParentId)
    if (!node || !parent || nodeId === newParentId) return false
    if (isDescendantOf(nodeId, newParentId)) return false
    if (!canMoveWithinDepthLimit(nodeId, newParentId)) {
      error.value = '移动后会超过树深度上限，请选择更浅的父节点'
      return false
    }

    const siblingOrders = nodes.value
      .filter(item => item.parentId === newParentId && item.id !== nodeId)
      .map(item => item.sortOrder ?? 0)
    const sortOrder = siblingOrders.length > 0 ? Math.max(...siblingOrders) + 1 : 0

    error.value = ''
    try {
      await updateKnowledgeNode(nodeId, {
        parentId: newParentId,
        depth: (parent.depth ?? 0) + 1,
        sortOrder,
      })
      if (!tree.value?.id) return false
      const res = await getKnowledgeTree(tree.value.id)
      nodes.value = res.data.nodes || []
      return true
    } catch (e) {
      error.value = getErrorMessage(e)
      return false
    }
  }

  async function deleteNode(nodeId: string): Promise<boolean> {
    const node = nodes.value.find(item => item.id === nodeId)
    if (!node) return false
    // 禁止删除根节点
    if (!node.parentId) return false

    error.value = ''
    try {
      const res = await deleteKnowledgeNode(nodeId)
      const deletedIds = new Set(res.data?.deletedIds || [nodeId])

      // 收集所有后代 ID（本地兜底，防止后端返回不完整）
      const allDeleted = new Set(deletedIds)
      collectLocalDescendants(nodeId, allDeleted)

      // 从 nodes 中移除
      nodes.value = nodes.value.filter(n => !allDeleted.has(n.id))

      // 重置 currentNodeId
      if (currentNodeId.value && allDeleted.has(currentNodeId.value)) {
        currentNodeId.value = node.parentId || null
      }

      // 清理 messagesByNode
      for (const id of allDeleted) {
        delete messagesByNode.value[id]
      }

      return true
    } catch (e) {
      error.value = getErrorMessage(e)
      return false
    }
  }

  function collectLocalDescendants(parentId: string, accumulator: Set<string>) {
    for (const n of nodes.value) {
      if (n.parentId === parentId) {
        accumulator.add(n.id)
        collectLocalDescendants(n.id, accumulator)
      }
    }
  }

  function isDescendantOf(ancestorId: string, candidateId: string) {
    const byId = new Map(nodes.value.map(item => [item.id, item]))
    let cursor: string | null | undefined = candidateId
    const seen = new Set<string>()
    while (cursor) {
      if (cursor === ancestorId) return true
      if (!seen.add(cursor)) break
      cursor = byId.get(cursor)?.parentId ?? null
    }
    return false
  }

  function isAtMaxDepth(nodeId: string) {
    const node = nodes.value.find(item => item.id === nodeId)
    return (node?.depth ?? 0) >= MAX_TREE_DEPTH
  }

  function canMoveWithinDepthLimit(nodeId: string, newParentId: string) {
    const parent = nodes.value.find(item => item.id === newParentId)
    if (!parent) return false

    const nextDepth = (parent.depth ?? 0) + 1
    if (nextDepth > MAX_TREE_DEPTH) return false

    return nextDepth + getSubtreeHeight(nodeId) <= MAX_TREE_DEPTH
  }

  function getSubtreeHeight(nodeId: string) {
    const childrenByParent = new Map<string, KnowledgeNode[]>()
    for (const node of nodes.value) {
      if (!node.parentId) continue
      const children = childrenByParent.get(node.parentId) || []
      children.push(node)
      childrenByParent.set(node.parentId, children)
    }

    function walk(parentId: string): number {
      const children = childrenByParent.get(parentId) || []
      if (children.length === 0) return 0
      return 1 + Math.max(...children.map(child => walk(child.id)))
    }

    return walk(nodeId)
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
    if (isAtMaxDepth(currentNodeId.value)) {
      error.value = TREE_DEPTH_LIMIT_MESSAGE
      return
    }
    const treeId = tree.value.id
    const nodeId = currentNodeId.value

    await startStream(nodeId, (ticket, handlers) => streamTreeSubdivide(
      ticket,
      treeId,
      nodeId,
      angle,
      splitMode.value,
      handlers,
    ))
  }

  async function loadSubdivisionOptionsCurrent(): Promise<TreeSubdivisionOption[]> {
    if (!tree.value || !currentNodeId.value) return []
    if (isAtMaxDepth(currentNodeId.value)) {
      subdivisionOptionsError.value = TREE_DEPTH_LIMIT_MESSAGE
      subdivisionCaution.value = {
        label: '已达三层上限',
        rationale: '请选择一、二层节点进行拆分',
      }
      return []
    }
    const token = nextSubdivisionOptionsToken()
    const treeId = tree.value.id
    const nodeId = currentNodeId.value
    subdivisionOptionsLoading.value = true
    subdivisionOptionsError.value = ''
    subdivisionCaution.value = null

    try {
      const ticketRes = await issueTicket()
      if (!isCurrentSubdivisionOptions(token) || currentNodeId.value !== nodeId) return []
      const res = await getTreeSubdivisionOptions(ticketRes.data.ticket, treeId, nodeId, splitMode.value)
      if (!isCurrentSubdivisionOptions(token) || currentNodeId.value !== nodeId) return []
      subdivisionCaution.value = res.data?.caution || null
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
    if (isAtMaxDepth(currentNodeId.value)) {
      error.value = TREE_DEPTH_LIMIT_MESSAGE
      return
    }
    const treeId = tree.value.id
    const nodeId = currentNodeId.value

    await startStream(nodeId, (ticket, handlers) => streamTreeMultiAngleSubdivide(
      ticket,
      treeId,
      nodeId,
      angles,
      splitMode.value,
      handlers,
    ))
  }

  async function firstPrinciplesCurrent() {
    if (!tree.value || !currentNodeId.value) return
    if (isAtMaxDepth(currentNodeId.value)) {
      error.value = TREE_DEPTH_LIMIT_MESSAGE
      return
    }
    const treeId = tree.value.id
    const nodeId = currentNodeId.value
    fpStreamingActive.value = true

    await startStream(nodeId, (ticket, handlers) => streamTreeFirstPrinciples(
      ticket,
      treeId,
      nodeId,
      splitMode.value,
      handlers,
      6,
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
    fpStreamingActive.value = false
    streamingNodeId.value = null
    streamingText.value = ''
    subdivisionOptionsLoading.value = false
    subdivisionOptionsError.value = ''
    subdivisionCaution.value = null
  }

  function setSplitMode(mode: TreeSplitMode) {
    splitMode.value = mode
    subdivisionCaution.value = null
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
        onThinking: content => {
          if (!isActiveStream(token, source)) return
          streamingText.value = content
        },
        onGroupPreview: content => {
          if (!isActiveStream(token, source)) return
          streamingText.value = `分组：${content}`
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
        onBranchDone: data => {
          if (!isActiveStream(token, source)) return
          if (data.children?.length) mergeNodes(data.children)
          streamingText.value = `「${data.parent_title}」子知识点生成完成`
        },
        onFpLayer: data => {
          if (!isActiveStream(token, source)) return
          if (data.parent) mergeNodes([data.parent])
          if (data.children?.length) mergeNodes(data.children)
          streamingText.value = data.reached_bottom
            ? `「${data.parent_title}」已触底`
            : `拆解「${data.parent_title}」完成，${data.children?.length || 0} 个前置依赖`
        },
        onAllDone: () => {
          if (!isActiveStream(token, source)) return
          activeSource.value = null
          loading.value = false
          fpStreamingActive.value = false
          streamingNodeId.value = null
          streamingText.value = ''
        },
        onCancelled: reason => {
          if (!isActiveStream(token, source)) return
          activeSource.value = null
          loading.value = false
          fpStreamingActive.value = false
          streamingNodeId.value = null
          streamingText.value = '已停止'
        },
        onDone: () => {
          if (!isActiveStream(token, source)) return
          activeSource.value = null
          loading.value = false
          fpStreamingActive.value = false
          streamingNodeId.value = null
          streamingText.value = ''
        },
        onError: message => {
          if (!isActiveStream(token, source)) return
          error.value = message
          activeSource.value = null
          loading.value = false
          fpStreamingActive.value = false
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

  function needsBootstrap(): boolean {
    if (!tree.value || nodes.value.length === 0) return false
    const root = nodes.value.find(node => !node.parentId)
    if (!root) return false
    const l1 = nodes.value.filter(node => node.parentId === root.id)
    if (l1.length === 0) return false
    return l1.some(module => !nodes.value.some(node => node.parentId === module.id))
  }

  async function maybeBootstrapTree(loadTokenValue: number) {
    if (!tree.value || !needsBootstrap()) return
    const treeId = tree.value.id
    const planId = tree.value.planId
    const token = streamToken
    loading.value = true
    streamingText.value = '正在生成知识树骨架…'
    try {
      const ticketRes = await issueTicket()
      if (!isCurrentLoad(loadTokenValue)) return
      await new Promise<void>((resolve, reject) => {
        const source = streamTreeBootstrap(ticketRes.data.ticket, planId, treeId, splitMode.value, {
          onThinking: content => {
            if (!isCurrentLoad(loadTokenValue)) return
            streamingText.value = content
          },
          onGroupPreview: content => {
            if (!isCurrentLoad(loadTokenValue)) return
            streamingText.value = `分组：${content}`
          },
          onNodes: nextNodes => {
            if (!isCurrentLoad(loadTokenValue)) return
            mergeNodes(nextNodes)
          },
          onDone: () => {
            source.close()
            resolve()
          },
          onError: message => {
            source.close()
            reject(new Error(message))
          },
        })
        if (!isCurrentLoad(loadTokenValue)) {
          source.close()
          resolve()
        }
      })
    } catch (e) {
      if (isCurrentLoad(loadTokenValue)) {
        error.value = getErrorMessage(e)
      }
    } finally {
      if (isCurrentLoad(loadTokenValue) && token === streamToken) {
        loading.value = false
        streamingText.value = ''
      }
    }
  }

  function replaceNode(nextNode: KnowledgeNode) {
    nodes.value = nodes.value.map(node => node.id === nextNode.id ? nextNode : node)
  }

  /**
   * 增量合并新节点：就地 patch + 只重排受影响父节点的 sibling 片段。
   *
   * 旧实现每次 SSE 批次都重建整棵树的 Map + 全量 pre-order DFS + 赋全新数组，
   * 导致每个 chunk 触发整树 reactivity 与全量 relayout。这里改为：
   *  - 未变更节点保持对象引用不变，只替换/追加新节点对象；
   *  - 仅对 nextNodes 涉及的 parent 重排其 children 区段；
   *  - 顶层 nodes 数组按 pre-order 重建以保证渲染顺序稳定，但底层节点引用尽量复用。
   *
   * 这样 KnowledgeTreeCanvas 的 computed(layout) 只需对实际变更区域做 diff。
   */
  function mergeNodes(nextNodes: KnowledgeNode[]) {
    if (nextNodes.length === 0) return

    const byId = new Map<string, KnowledgeNode>()
    for (const node of nodes.value) byId.set(node.id, node)
    for (const node of nextNodes) {
      byId.set(node.id, { ...byId.get(node.id), ...node })
    }

    // 收集 children 映射（用最终节点对象），用于 pre-order 重建
    const childrenByParent = new Map<string, KnowledgeNode[]>()
    let rootNodeId: string | null = null
    for (const node of byId.values()) {
      if (!node.parentId) {
        rootNodeId = node.id
        continue
      }
      const siblings = childrenByParent.get(node.parentId) || []
      siblings.push(node)
      childrenByParent.set(node.parentId, siblings)
    }
    for (const siblings of childrenByParent.values()) {
      siblings.sort((a, b) => {
        const sortDelta = (a.sortOrder ?? 0) - (b.sortOrder ?? 0)
        if (sortDelta !== 0) return sortDelta
        return a.id.localeCompare(b.id)
      })
    }

    const ordered: KnowledgeNode[] = []
    const visited = new Set<string>()
    function visit(parentId: string | null) {
      const children = childrenByParent.get(parentId || '') || []
      for (const child of children) {
        if (visited.has(child.id)) continue
        visited.add(child.id)
        ordered.push(child)
        visit(child.id)
      }
    }
    if (rootNodeId) {
      const root = byId.get(rootNodeId)
      if (root) {
        visited.add(rootNodeId)
        ordered.push(root)
        visit(rootNodeId)
      }
    }
    for (const node of byId.values()) {
      if (!visited.has(node.id)) ordered.push(node)
    }
    nodes.value = ordered
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

  function setDraggingNodeId(nodeId: string | null) {
    draggingNodeId.value = nodeId
  }

  // ── 预览-确认流程 ──────────────────────────────────────────────
  const previewTopics = ref<Array<{ title: string; summary: string; custom: boolean }>>([])
  const previewLoading = ref(false)
  const previewError = ref('')
  const growProgress = ref({ growing: false, currentBranch: '', doneCount: 0, totalCount: 0 })

  async function startPreview() {
    if (!tree.value) return
    previewLoading.value = true
    previewError.value = ''
    previewTopics.value = []
    try {
      const ticketRes = await issueTicket()
      const res = await fetchPreviewTopics(
        ticketRes.data.ticket,
        tree.value.planId,
        tree.value.id,
        splitMode.value,
      )
      previewTopics.value = res.data.topics || []
    } catch (e) {
      previewError.value = getErrorMessage(e)
    } finally {
      previewLoading.value = false
    }
  }

  async function confirmPreviewGrow(topics: Array<{ title: string; summary: string }>) {
    if (!tree.value) return
    stopStream()
    const token = ++streamToken
    loading.value = true
    streamingText.value = '正在生成子知识点…'
    growProgress.value = { growing: true, currentBranch: '', doneCount: 0, totalCount: topics.length }
    try {
      const ticketRes = await issueTicket()
      if (!isCurrentToken(token)) return
      const source = streamGrowChildren(
        ticketRes.data.ticket,
        tree.value.planId,
        tree.value.id,
        splitMode.value,
        {
          onThinking: content => {
            if (!isActiveStream(token, source)) return
            streamingText.value = content
          },
          onBranchDone: data => {
            if (!isActiveStream(token, source)) return
            if (data.children?.length) mergeNodes(data.children)
            growProgress.value = {
              ...growProgress.value,
              currentBranch: data.parent_title,
              doneCount: growProgress.value.doneCount + 1,
            }
            streamingText.value = `「${data.parent_title}」完成`
          },
          onNodes: nextNodes => {
            if (!isActiveStream(token, source)) return
            mergeNodes(nextNodes)
          },
          onAllDone: () => {
            if (!isActiveStream(token, source)) return
            activeSource.value = null
            loading.value = false
            streamingText.value = ''
            growProgress.value = { growing: false, currentBranch: '', doneCount: 0, totalCount: 0 }
            previewTopics.value = []
          },
          onDone: () => {
            if (!isActiveStream(token, source)) return
            activeSource.value = null
            loading.value = false
            streamingText.value = ''
            growProgress.value = { growing: false, currentBranch: '', doneCount: 0, totalCount: 0 }
            previewTopics.value = []
          },
          onError: message => {
            if (!isActiveStream(token, source)) return
            error.value = message
            activeSource.value = null
            loading.value = false
            streamingText.value = ''
            growProgress.value = { growing: false, currentBranch: '', doneCount: 0, totalCount: 0 }
          },
        },
        topics,
      )
      if (!isCurrentToken(token)) {
        source.close()
        return
      }
      activeSource.value = source
    } catch (e) {
      if (!isCurrentToken(token)) return
      error.value = getErrorMessage(e)
      loading.value = false
      growProgress.value = { growing: false, currentBranch: '', doneCount: 0, totalCount: 0 }
    }
  }

  function skipPreviewAndGrow() {
    // 跳过预览，直接用原始 L1 节点标题走 grow-children
    confirmPreviewGrow([])
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
    splitMode,
    subdivisionOptionsLoading,
    subdivisionOptionsError,
    subdivisionCaution,
    panX,
    panY,
    zoom,
    activeSource,
    draggingNodeId,
    fpStreamingActive,
    setDraggingNodeId,
    setSplitMode,
    loadByPlan,
    selectNode,
    toggleCollapsed,
    reparentNode,
    deleteNode,
    sendMessage,
    subdivideCurrent,
    loadSubdivisionOptionsCurrent,
    multiAngleSubdivideCurrent,
    firstPrinciplesCurrent,
    generateQuizCurrent,
    generateFlashcardsCurrent,
    stopStream,
    previewTopics,
    previewLoading,
    previewError,
    growProgress,
    startPreview,
    confirmPreviewGrow,
    skipPreviewAndGrow,
    needsBootstrap,
    isAtMaxDepth,
  }
})

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  return '请求失败'
}
