import type { KnowledgeNode } from '@/types/knowledgeTree'

export type TreeLayoutItemKind = 'root' | 'main' | 'branch-left' | 'branch-right'

export interface TreeLayoutItem {
  node: KnowledgeNode
  kind: TreeLayoutItemKind
  x: number
  y: number
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

const MAIN_Y_GAP = 180
const BRANCH_X_GAP = 260
const BRANCH_Y_GAP = 120

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

  function addNode(
    node: KnowledgeNode,
    kind: TreeLayoutItemKind,
    x: number,
    y: number,
    branchSide: -1 | 1,
  ) {
    items.push({ node, kind, x, y })

    if (node.collapsed) {
      return
    }

    const children = childrenByParent.get(node.id) || []
    children.forEach((child, index) => {
      const isMain = kind !== 'branch-left' && kind !== 'branch-right' && index === 0
      edges.push({
        fromNodeId: node.id,
        toNodeId: child.id,
        kind: isMain ? 'main' : 'branch',
      })

      if (isMain) {
        addNode(child, 'main', x, y + MAIN_Y_GAP, branchSide)
        return
      }

      const side = index % 2 === 1 ? 1 : -1
      const branchIndex = Math.floor((index - 1) / 2)
      addNode(
        child,
        side === 1 ? 'branch-right' : 'branch-left',
        x + side * BRANCH_X_GAP * (branchIndex + 1),
        y + BRANCH_Y_GAP * (branchIndex + 1),
        side,
      )
    })
  }

  addNode(root, 'root', 0, 0, 1)

  return { items, edges }
}

function compareNodes(a: KnowledgeNode, b: KnowledgeNode) {
  const sortDelta = (a.sortOrder ?? 0) - (b.sortOrder ?? 0)
  if (sortDelta !== 0) return sortDelta
  const depthDelta = (a.depth ?? 0) - (b.depth ?? 0)
  if (depthDelta !== 0) return depthDelta
  return a.id.localeCompare(b.id)
}
