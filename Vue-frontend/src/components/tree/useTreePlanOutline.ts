import type { KnowledgeNode } from '@/types/knowledgeTree'
import type { LearningResource } from '@/types/plan'

export type TreePlanOutlineItem =
  | TreePlanNodeItem
  | TreePlanResourceItem
  | TreePlanGroupItem

export interface TreePlanNodeItem {
  kind: 'node'
  id: string
  nodeId: string
  title: string
  summary: string
  depth: number
  collapsed: boolean
  children: TreePlanOutlineItem[]
}

export interface TreePlanResourceItem {
  kind: 'resource'
  id: string
  resourceId: number
  title: string
  resourceType: string
  depth: number
  children: []
}

export interface TreePlanGroupItem {
  kind: 'group'
  id: string
  title: string
  depth: number
  children: TreePlanResourceItem[]
}

export function buildTreePlanOutline(
  nodes: KnowledgeNode[],
  resources: LearningResource[],
  rootNodeId: string | null,
): TreePlanOutlineItem[] {
  if (!rootNodeId) return []

  const nodeById = new Map(nodes.map(node => [node.id, node]))
  const root = nodeById.get(rootNodeId)
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

  const mountedResourceIds = new Set<number>()
  const resourcesByNodeId = mountResources(nodes, resources, mountedResourceIds)

  function toNodeItem(node: KnowledgeNode, depth: number): TreePlanNodeItem {
    const resourceItems = (resourcesByNodeId.get(node.id) || [])
      .map(resource => toResourceItem(resource, depth + 1))
    const childItems = (childrenByParent.get(node.id) || [])
      .map(child => toNodeItem(child, depth + 1))

    return {
      kind: 'node',
      id: `node:${node.id}`,
      nodeId: node.id,
      title: node.title || '未命名节点',
      summary: node.summary || '',
      depth,
      collapsed: Boolean(node.collapsed),
      children: [...resourceItems, ...childItems],
    }
  }

  const rootItem = toNodeItem(root, 0)
  const unmatchedResources = resources
    .filter(resource => resource.id != null && !mountedResourceIds.has(resource.id))
    .map(resource => toResourceItem(resource, 1))

  if (unmatchedResources.length > 0) {
    rootItem.children.push({
      kind: 'group',
      id: 'group:uncategorized',
      title: '未归类资源',
      depth: 1,
      children: unmatchedResources,
    })
  }

  return [rootItem]
}

function mountResources(
  nodes: KnowledgeNode[],
  resources: LearningResource[],
  mountedResourceIds: Set<number>,
) {
  const result = new Map<string, LearningResource[]>()
  const nodeById = new Map(nodes.map(node => [node.id, node]))
  const nodeByResourceId = new Map<number, string>()
  const nodeByTitle = new Map<string, string>()

  for (const node of nodes) {
    if (node.resourceId != null) nodeByResourceId.set(node.resourceId, node.id)
    if (node.title) nodeByTitle.set(normalizeTitle(node.title), node.id)
  }

  for (const resource of resources) {
    const nodeId = resourceNodeId(resource)
      || (resource.id != null ? nodeByResourceId.get(resource.id) : undefined)
      || titleMatchedNodeId(resource, nodeByTitle)
    if (!nodeId || !nodeById.has(nodeId) || resource.id == null) continue

    const mounted = result.get(nodeId) || []
    mounted.push(resource)
    result.set(nodeId, mounted)
    mountedResourceIds.add(resource.id)
  }

  return result
}

function resourceNodeId(resource: LearningResource) {
  const data = resource.moduleData || {}
  return (resource as LearningResource & { nodeId?: string }).nodeId
    || data.nodeId
    || data.node_id
    || null
}

function titleMatchedNodeId(resource: LearningResource, nodeByTitle: Map<string, string>) {
  const data = resource.moduleData || {}
  const candidates = [
    data.module_title,
    data.moduleTitle,
    data.title,
  ]

  for (const candidate of candidates) {
    const nodeId = nodeByTitle.get(normalizeTitle(String(candidate || '')))
    if (nodeId) return nodeId
  }

  return undefined
}

function toResourceItem(resource: LearningResource, depth: number): TreePlanResourceItem {
  return {
    kind: 'resource',
    id: `resource:${resource.id}`,
    resourceId: resource.id,
    title: resource.moduleData?.title || resource.moduleData?.module_title || `资源 ${resource.id}`,
    resourceType: resource.moduleType,
    depth,
    children: [],
  }
}

function compareNodes(a: KnowledgeNode, b: KnowledgeNode) {
  const sortDelta = (a.sortOrder ?? 0) - (b.sortOrder ?? 0)
  if (sortDelta !== 0) return sortDelta
  return a.id.localeCompare(b.id)
}

function normalizeTitle(value: string) {
  return value.replace(/\s+/g, '').trim().toLowerCase()
}
