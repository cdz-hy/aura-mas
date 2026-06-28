import type { KnowledgeNode } from '@/types/knowledgeTree'

export type TreeLayoutItemKind = 'root' | 'main' | 'branch-left' | 'branch-right'

export interface TreeLayoutItem {
  node: KnowledgeNode
  kind: TreeLayoutItemKind
  x: number
  y: number
  /** 该节点子树占用的水平半宽（用于碰撞检测和视口计算） */
  subtreeHalfWidth?: number
}

export interface TreeLayoutEdge {
  fromNodeId: string
  toNodeId: string
  kind: 'main' | 'branch'
}

export interface TreeLayout {
  items: TreeLayoutItem[]
  edges: TreeLayoutEdge[]
}

export interface TreeLayoutBounds {
  minX: number
  minY: number
  width: number
  height: number
}

export interface TreeViewportFit {
  panX: number
  panY: number
  zoom: number
}

const ROOT_Y = 0
const TRUNK_START_GAP = 230
const TRUNK_GAP = 96
const BRANCH_X_GAP = 370
const BRANCH_ROW_GAP = 34
const NODE_BAND_HEIGHT = 172

/**
 * 构建按 (parentId → sortOrder → createdAt) 的 pre-order DFS 序列。
 * 用于在整棵树上定义稳定的"下一个知识点"顺序：深度优先、自左向右。
 */
export function buildPreOrder(nodes: KnowledgeNode[], rootNodeId: string): KnowledgeNode[] {
  const byId = new Map(nodes.map(node => [node.id, node]))
  const root = byId.get(rootNodeId)
  if (!root) return []

  const childrenByParent = new Map<string, KnowledgeNode[]>()
  for (const node of nodes) {
    if (!node.parentId) continue
    const siblings = childrenByParent.get(node.parentId) || []
    siblings.push(node)
    childrenByParent.set(node.parentId, siblings)
  }

  for (const siblings of childrenByParent.values()) {
    siblings.sort(compareNodes)
  }

  const order: KnowledgeNode[] = []

  function visit(parentId: string | null | undefined) {
    const children = childrenByParent.get(parentId || '') || []
    for (const child of children) {
      order.push(child)
      visit(child.id)
    }
  }

  // root 自身先入列
  order.push(root)
  visit(root.id)
  return order
}

/**
 * 构建知识树布局。
 *
 * 优化点（参考 TJ-Sylva 的主干 + 分支布局）：
 * 1. 根节点固定在中心，一级节点沿中心主干向上排列。
 * 2. 一级节点按子树高度预留竖向空间，避免左右分支互相覆盖。
 * 3. 二级及以下节点从主干节点左右展开，子孙沿所在侧递归。
 */
export function buildTreeLayout(nodes: KnowledgeNode[], rootNodeId: string): TreeLayout {
  const byId = new Map(nodes.map(node => [node.id, node]))
  const root = byId.get(rootNodeId)
  if (!root) {
    return { items: [], edges: [] }
  }

  const childrenByParent = new Map<string, KnowledgeNode[]>()
  for (const node of nodes) {
    if (!node.parentId) continue
    const siblings = childrenByParent.get(node.parentId) || []
    siblings.push(node)
    childrenByParent.set(node.parentId, siblings)
  }

  for (const siblings of childrenByParent.values()) {
    siblings.sort(compareNodes)
  }

  const items: TreeLayoutItem[] = []
  const edges: TreeLayoutEdge[] = []

  items.push({ node: root, kind: 'root', x: 0, y: ROOT_Y, subtreeHalfWidth: 0 })

  if (root.collapsed) {
    return { items, edges }
  }

  const rootChildren = childrenByParent.get(root.id) || []
  const mainBands = rootChildren.map(node => ({
    node,
    height: Math.max(NODE_BAND_HEIGHT, branchHeight(node, childrenByParent)),
  }))

  let cursorY = ROOT_Y - TRUNK_START_GAP
  let previousMainNodeId = root.id
  let previousMainY = ROOT_Y

  mainBands.forEach((band, index) => {
    const y = cursorY - band.height / 2
    const main = band.node
    items.push({ node: main, kind: 'main', x: 0, y, subtreeHalfWidth: BRANCH_X_GAP })
    edges.push({
      fromNodeId: previousMainNodeId,
      toNodeId: main.id,
      kind: 'main',
    })

    if (!main.collapsed) {
      placeBranchChildren(main, 0, y, index % 2 === 0 ? 1 : -1, true)
    }

    previousMainNodeId = main.id
    previousMainY = y
    cursorY = previousMainY - band.height / 2 - TRUNK_GAP
  })

  function placeBranchChildren(
    parent: KnowledgeNode,
    parentX: number,
    parentY: number,
    side: -1 | 1,
    alternateDirectChildren = false,
  ) {
    const children = childrenByParent.get(parent.id) || []
    if (children.length === 0) return

    const childBands = children.map(child => ({
      node: child,
      height: Math.max(NODE_BAND_HEIGHT, branchHeight(child, childrenByParent)),
    }))
    const totalHeight = childBands.reduce((sum, band) => sum + band.height, 0)
      + Math.max(0, childBands.length - 1) * BRANCH_ROW_GAP
    let cursor = parentY - totalHeight / 2

    childBands.forEach((band, index) => {
      const childSide: -1 | 1 = alternateDirectChildren
        ? index % 2 === 0 ? side === 1 ? -1 : 1 : side
        : side
      const child = band.node
      const y = cursor + band.height / 2
      const x = parentX + childSide * BRANCH_X_GAP
      items.push({
        node: child,
        kind: childSide > 0 ? 'branch-right' : 'branch-left',
        x,
        y,
        subtreeHalfWidth: BRANCH_X_GAP,
      })
      edges.push({
        fromNodeId: parent.id,
        toNodeId: child.id,
        kind: 'branch',
      })

      if (!child.collapsed) {
        placeBranchChildren(child, x, y, childSide)
      }

      cursor += band.height + BRANCH_ROW_GAP
    })
  }

  return { items, edges }
}

/**
 * 计算分支子树在竖向布局中需要预留的高度。
 */
function branchHeight(
  node: KnowledgeNode,
  childrenByParent: Map<string, KnowledgeNode[]>,
): number {
  const children = childrenByParent.get(node.id) || []
  if (children.length === 0 || node.collapsed) return NODE_BAND_HEIGHT
  return Math.max(
    NODE_BAND_HEIGHT,
    children.reduce((sum, child) => sum + branchHeight(child, childrenByParent), 0)
      + Math.max(0, children.length - 1) * BRANCH_ROW_GAP,
  )
}

export function getTreeLayoutBounds(
  items: TreeLayoutItem[],
  nodeWidth: number,
  nodeHeight: number,
): TreeLayoutBounds {
  if (items.length === 0) {
    return { minX: -nodeWidth / 2, minY: -nodeHeight / 2, width: nodeWidth, height: nodeHeight }
  }

  // 用单次遍历代替 flatMap + Math.min(...spread)，
  // 避免极大树（数万节点）触发调用栈溢出。
  const halfW = nodeWidth / 2
  const halfH = nodeHeight / 2
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const item of items) {
    const left = item.x - halfW
    const right = item.x + halfW
    const top = item.y - halfH
    const bottom = item.y + halfH
    if (left < minX) minX = left
    if (right > maxX) maxX = right
    if (top < minY) minY = top
    if (bottom > maxY) maxY = bottom
  }
  return { minX, minY, width: maxX - minX, height: maxY - minY }
}

export function fitTreeViewport(
  bounds: TreeLayoutBounds,
  viewportWidth: number,
  viewportHeight: number,
  paddingX: number,
  paddingY: number,
  minZoom: number,
  maxZoom: number,
): TreeViewportFit {
  const availableWidth = Math.max(1, viewportWidth - paddingX * 2)
  const availableHeight = Math.max(1, viewportHeight - paddingY * 2)
  const fitZoom = Math.min(1, availableWidth / bounds.width, availableHeight / bounds.height)
  const zoom = Math.min(maxZoom, Math.max(minZoom, fitZoom))
  const centerX = bounds.minX + bounds.width / 2
  const centerY = bounds.minY + bounds.height / 2

  return {
    panX: -centerX * zoom,
    panY: -centerY * zoom,
    zoom,
  }
}

/**
 * 虚拟化过滤：根据当前视口范围和缩放比例，只返回可见区域内的布局项。
 * 用于大树（>50 节点）时减少 DOM 渲染压力。
 */
export function getVisibleItems(
  items: TreeLayoutItem[],
  bounds: TreeLayoutBounds,
  viewport: { panX: number; panY: number; zoom: number; width: number; height: number },
  nodeWidth: number,
  nodeHeight: number,
  overscan: number = 2,
): TreeLayoutItem[] {
  // 节点数少时直接返回全部，避免虚拟化开销
  if (items.length <= 50) {
    return items
  }

  const halfW = nodeWidth / 2
  const halfH = nodeHeight / 2
  const viewMinX = -viewport.panX / viewport.zoom - overscan * nodeWidth
  const viewMaxX = viewMinX + viewport.width / viewport.zoom + overscan * nodeWidth * 2
  const viewMinY = -viewport.panY / viewport.zoom - overscan * nodeHeight
  const viewMaxY = viewMinY + viewport.height / viewport.zoom + overscan * nodeHeight * 2

  return items.filter(item =>
    item.x + halfW >= viewMinX &&
    item.x - halfW <= viewMaxX &&
    item.y + halfH >= viewMinY &&
    item.y - halfH <= viewMaxY,
  )
}

function compareNodes(a: KnowledgeNode, b: KnowledgeNode) {
  const sortDelta = (a.sortOrder ?? 0) - (b.sortOrder ?? 0)
  if (sortDelta !== 0) return sortDelta
  const depthDelta = (a.depth ?? 0) - (b.depth ?? 0)
  if (depthDelta !== 0) return depthDelta
  return a.id.localeCompare(b.id)
}
