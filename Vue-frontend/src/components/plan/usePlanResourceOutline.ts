import type { TreePlanOutlineItem, TreePlanNodeItem, TreePlanResourceItem } from '@/components/tree/useTreePlanOutline'
import type { LearningResource } from '@/types/plan'

export type PlanOutlineModuleStatus = 'pending' | 'generating' | 'ready' | 'failed'

export interface PlanOutlineResource {
  id: string
  resourceId: number
  title: string
  resourceType: string
  status: number
  childResources: PlanOutlineResource[]
}

export interface PlanOutlineModule {
  id: string
  displayIndex: string
  depth: number
  title: string
  summary?: string
  estimatedHours: number
  resourceTypes: string[]
  resources: PlanOutlineResource[]
  moduleStatus: PlanOutlineModuleStatus
  nodeId?: string
  kind: 'module' | 'group'
}

export type PlanOutlineTreeModule = PlanOutlineModule & {
  childModules: PlanOutlineTreeModule[]
}

export interface LearningModuleGroup {
  order: number
  title: string
  estimatedHours: number
  resourceTypes: string[]
  resources: LearningResource[]
}

/** 由资源列表推导模块整体状态 */
export function deriveModuleStatus(resources: PlanOutlineResource[]): PlanOutlineModuleStatus {
  if (resources.length === 0) return 'pending'
  if (resources.some(r => r.status === 3)) return 'failed'
  if (resources.some(r => r.status === 1)) return 'generating'
  if (resources.every(r => r.status === 2)) return 'ready'
  if (resources.some(r => r.status === 2)) return 'ready'
  return 'pending'
}

export function moduleStatusLabel(status: PlanOutlineModuleStatus): string {
  const map: Record<PlanOutlineModuleStatus, string> = {
    pending: '待生成',
    generating: '生成中',
    ready: '已生成',
    failed: '生成失败',
  }
  return map[status]
}

function toOutlineResource(
  resourceId: number,
  title: string,
  resourceType: string,
  status: number,
): PlanOutlineResource {
  return {
    id: `resource:${resourceId}`,
    resourceId,
    title,
    resourceType,
    status,
    childResources: [],
  }
}

function sortResourcesByOrder(a: LearningResource, b: LearningResource): number {
  return (a.moduleOrder - b.moduleOrder) || (a.id - b.id)
}

/** 同模块资源 flat 列表：parentId 仅用于邻接排序，不构建嵌套 UI */
export function buildOutlineResources(resources: LearningResource[]): PlanOutlineResource[] {
  if (resources.length === 0) return []

  const byId = new Map<number, PlanOutlineResource>()
  for (const resource of resources) {
    byId.set(resource.id, resourceFromLearning(resource))
  }

  const childrenByParent = new Map<number, LearningResource[]>()
  const roots: LearningResource[] = []

  for (const resource of resources) {
    const parentId = resource.parentId
    if (parentId != null && byId.has(parentId)) {
      const list = childrenByParent.get(parentId) || []
      list.push(resource)
      childrenByParent.set(parentId, list)
    } else {
      roots.push(resource)
    }
  }

  roots.sort(sortResourcesByOrder)
  for (const list of childrenByParent.values()) {
    list.sort(sortResourcesByOrder)
  }

  const ordered: PlanOutlineResource[] = []
  const placed = new Set<number>()

  function appendResource(learning: LearningResource) {
    if (placed.has(learning.id)) return
    placed.add(learning.id)
    ordered.push(byId.get(learning.id)!)
    for (const child of childrenByParent.get(learning.id) || []) {
      appendResource(child)
    }
  }

  for (const root of roots) {
    appendResource(root)
  }
  for (const resource of resources) {
    if (!placed.has(resource.id)) {
      appendResource(resource)
    }
  }

  return ordered
}

function resourceFromLearning(r: LearningResource): PlanOutlineResource {
  return toOutlineResource(
    r.id,
    r.moduleData?.title || r.moduleData?.module_title || `资源 ${r.id}`,
    r.moduleType,
    r.status ?? 0,
  )
}

function resourceFromTreeItem(item: TreePlanResourceItem, resources: LearningResource[]): PlanOutlineResource {
  const full = resources.find(r => r.id === item.resourceId)
  return toOutlineResource(
    item.resourceId,
    item.title,
    item.resourceType,
    full?.status ?? 2,
  )
}

/** 学习模式：按 moduleOrder 分组的模块列表 → 统一大纲项 */
export function buildOutlineFromLearningModules(groups: LearningModuleGroup[]): PlanOutlineModule[] {
  return groups.map((mod, index) => {
    const outlineResources = buildOutlineResources(mod.resources)
    return {
      id: `learning:${mod.order}`,
      displayIndex: String(index + 1),
      depth: 0,
      title: mod.title,
      estimatedHours: mod.estimatedHours || 2,
      resourceTypes: [...mod.resourceTypes],
      resources: outlineResources,
      moduleStatus: deriveModuleStatus(outlineResources),
      kind: 'module',
    }
  })
}

function collectResourceTypes(resources: PlanOutlineResource[]): string[] {
  return [...new Set(resources.map(r => r.resourceType))]
}

function flattenNodeItems(
  items: TreePlanOutlineItem[],
  resources: LearningResource[],
  prefix: string,
  depth: number,
): PlanOutlineModule[] {
  const result: PlanOutlineModule[] = []
  let nodeCounter = 0

  for (const item of items) {
    if (item.kind === 'group') {
      const groupResources = item.children.map(child => resourceFromTreeItem(child, resources))
      result.push({
        id: item.id,
        displayIndex: '',
        depth: 0,
        title: item.title,
        estimatedHours: 2,
        resourceTypes: collectResourceTypes(groupResources),
        resources: groupResources,
        moduleStatus: deriveModuleStatus(groupResources),
        kind: 'group',
      })
      continue
    }

    if (item.kind !== 'node') continue

    nodeCounter += 1
    const displayIndex = prefix ? `${prefix}.${nodeCounter}` : String(nodeCounter)
    const resourceItems = item.children.filter(child => child.kind === 'resource') as TreePlanResourceItem[]
    const childNodes = item.children.filter(child => child.kind === 'node') as TreePlanNodeItem[]
    const nodeResources = resourceItems
      .map(resourceItem => resources.find(r => r.id === resourceItem.resourceId))
      .filter((resource): resource is LearningResource => Boolean(resource))
    const outlineResources = buildOutlineResources(nodeResources)

    result.push({
      id: item.id,
      displayIndex,
      depth,
      title: item.title,
      summary: item.summary || undefined,
      estimatedHours: 2,
      resourceTypes: collectResourceTypes(outlineResources),
      resources: outlineResources,
      moduleStatus: deriveModuleStatus(outlineResources),
      nodeId: item.nodeId,
      kind: 'module',
    })

    if (childNodes.length > 0) {
      result.push(...flattenNodeItems(childNodes, resources, displayIndex, depth + 1))
    }
  }

  return result
}

/** 学习模式：扁平模块 → 树形大纲（通常无子模块） */
export function buildOutlineTreeFromLearningModules(groups: LearningModuleGroup[]): PlanOutlineTreeModule[] {
  return buildOutlineFromLearningModules(groups).map(mod => ({ ...mod, childModules: [] }))
}

function convertGroupItem(
  item: Extract<TreePlanOutlineItem, { kind: 'group' }>,
  resources: LearningResource[],
): PlanOutlineTreeModule {
  const groupLearningResources = item.children
    .map(child => resources.find(r => r.id === child.resourceId))
    .filter((resource): resource is LearningResource => Boolean(resource))
  const groupResources = buildOutlineResources(groupLearningResources)
  return {
    id: item.id,
    displayIndex: '',
    depth: item.depth,
    title: item.title,
    estimatedHours: 2,
    resourceTypes: collectResourceTypes(groupResources),
    resources: groupResources,
    moduleStatus: deriveModuleStatus(groupResources),
    kind: 'group',
    childModules: [],
  }
}

function convertNodeItem(
  item: TreePlanNodeItem,
  resources: LearningResource[],
  displayIndex: string,
  depth: number,
): PlanOutlineTreeModule {
  const childNodes = item.children.filter(child => child.kind === 'node') as TreePlanNodeItem[]
  const resourceItems = item.children.filter(child => child.kind === 'resource') as TreePlanResourceItem[]
  const nodeResources = resourceItems
    .map(resourceItem => resources.find(r => r.id === resourceItem.resourceId))
    .filter((resource): resource is LearningResource => Boolean(resource))
  const outlineResources = buildOutlineResources(nodeResources)

  let childCounter = 0
  const childModules = childNodes.map(child => {
    childCounter += 1
    const childIndex = `${displayIndex}.${childCounter}`
    return convertNodeItem(child, resources, childIndex, depth + 1)
  })

  return {
    id: item.id,
    displayIndex,
    depth,
    title: item.title,
    summary: item.summary || undefined,
    estimatedHours: 2,
    resourceTypes: collectResourceTypes(outlineResources),
    resources: outlineResources,
    moduleStatus: deriveModuleStatus(outlineResources),
    nodeId: item.nodeId,
    kind: 'module',
    childModules,
  }
}

/** 知识树模式：直接构建可折叠的树形大纲 */
export function buildOutlineTreeFromTreeItems(
  items: TreePlanOutlineItem[],
  resources: LearningResource[],
): PlanOutlineTreeModule[] {
  let nodeCounter = 0
  const result: PlanOutlineTreeModule[] = []

  for (const item of items) {
    if (item.kind === 'group') {
      result.push(convertGroupItem(item, resources))
      continue
    }
    if (item.kind !== 'node') continue
    nodeCounter += 1
    result.push(convertNodeItem(item, resources, String(nodeCounter), 0))
  }

  return result
}

/** 扁平模块列表 → 按 displayIndex 挂到父模块下 */
export function nestOutlineModules(modules: PlanOutlineModule[]): PlanOutlineTreeModule[] {
  if (!Array.isArray(modules) || modules.length === 0) return []
  const wrapped: PlanOutlineTreeModule[] = modules.map(mod => ({ ...mod, childModules: [] }))
  const byIndex = new Map<string, PlanOutlineTreeModule>()
  for (const mod of wrapped) {
    if (mod.displayIndex) byIndex.set(mod.displayIndex, mod)
  }

  const roots: PlanOutlineTreeModule[] = []
  for (const mod of wrapped) {
    if (mod.kind === 'group' || !mod.displayIndex.includes('.')) {
      roots.push(mod)
      continue
    }

    const parentIndex = mod.displayIndex.split('.').slice(0, -1).join('.')
    const parent = byIndex.get(parentIndex)
    if (parent && parent.kind !== 'group') {
      parent.childModules.push(mod)
    } else {
      roots.push(mod)
    }
  }

  return roots
}

function flattenOutlineTree(modules: PlanOutlineTreeModule[]): PlanOutlineModule[] {
  const result: PlanOutlineModule[] = []
  for (const mod of modules) {
    const { childModules, ...flat } = mod
    result.push(flat)
    if (childModules.length > 0) {
      result.push(...flattenOutlineTree(childModules))
    }
  }
  return result
}

/** 知识树模式：树形 outline → 扁平卡片列表（保留层级 depth） */
export function buildOutlineFromTreeItems(
  items: TreePlanOutlineItem[],
  resources: LearningResource[],
): PlanOutlineModule[] {
  return flattenOutlineTree(buildOutlineTreeFromTreeItems(items, resources))
}

export function countOutlineTreeModules(modules: PlanOutlineTreeModule[]): number {
  return modules.reduce((sum, mod) => {
    if (mod.kind !== 'module') return sum
    return sum + 1 + countOutlineTreeModules(mod.childModules)
  }, 0)
}

export function countOutlineTreeResources(modules: PlanOutlineTreeModule[]): number {
  return modules.reduce((sum, mod) => {
    return sum + mod.resources.length + countOutlineTreeResources(mod.childModules)
  }, 0)
}

export function countOutlineModules(modules: PlanOutlineModule[]): number {
  return modules.filter(m => m.kind === 'module').length
}

export function countOutlineResources(modules: PlanOutlineModule[]): number {
  return modules.reduce((sum, mod) => sum + mod.resources.length, 0)
}

/** 仅顶级编号模块（如 1、2）展示右侧「你正在查看模块」提示 */
export function shouldShowModuleContextPromptForOutlineModule(
  module: Pick<PlanOutlineTreeModule, 'kind' | 'depth' | 'displayIndex'>,
): boolean {
  return module.kind === 'module'
    && module.depth === 0
    && module.displayIndex.length > 0
    && !module.displayIndex.includes('.')
}
