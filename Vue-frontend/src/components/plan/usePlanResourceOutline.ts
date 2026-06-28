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

/** 按 parentId 将同模块资源组装为「主资源 + 子资源」树 */
export function nestOutlineResources(resources: LearningResource[]): PlanOutlineResource[] {
  if (resources.length === 0) return []

  const byId = new Map<number, PlanOutlineResource>()
  for (const resource of resources) {
    byId.set(resource.id, resourceFromLearning(resource))
  }

  const roots: PlanOutlineResource[] = []
  for (const resource of resources) {
    const item = byId.get(resource.id)!
    const parentId = resource.parentId
    if (parentId != null && byId.has(parentId)) {
      byId.get(parentId)!.childResources.push(item)
    } else {
      roots.push(item)
    }
  }

  return roots
}

function flattenOutlineResources(resources: PlanOutlineResource[]): PlanOutlineResource[] {
  const result: PlanOutlineResource[] = []
  for (const resource of resources) {
    result.push(resource)
    if (resource.childResources.length > 0) {
      result.push(...flattenOutlineResources(resource.childResources))
    }
  }
  return result
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
    const outlineResources = nestOutlineResources(mod.resources)
    const flatResources = flattenOutlineResources(outlineResources)
    return {
      id: `learning:${mod.order}`,
      displayIndex: String(index + 1),
      depth: 0,
      title: mod.title,
      estimatedHours: mod.estimatedHours || 2,
      resourceTypes: [...mod.resourceTypes],
      resources: outlineResources,
      moduleStatus: deriveModuleStatus(flatResources),
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
    const outlineResources = nestOutlineResources(nodeResources)
    const flatResources = flattenOutlineResources(outlineResources)

    result.push({
      id: item.id,
      displayIndex,
      depth,
      title: item.title,
      summary: item.summary || undefined,
      estimatedHours: 2,
      resourceTypes: collectResourceTypes(flatResources),
      resources: outlineResources,
      moduleStatus: deriveModuleStatus(flatResources),
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
  const groupResources = nestOutlineResources(groupLearningResources)
  const flatGroupResources = flattenOutlineResources(groupResources)
  return {
    id: item.id,
    displayIndex: '',
    depth: item.depth,
    title: item.title,
    estimatedHours: 2,
    resourceTypes: collectResourceTypes(flatGroupResources),
    resources: groupResources,
    moduleStatus: deriveModuleStatus(flatGroupResources),
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
  const outlineResources = nestOutlineResources(nodeResources)
  const flatResources = flattenOutlineResources(outlineResources)

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
    resourceTypes: collectResourceTypes(flatResources),
    resources: outlineResources,
    moduleStatus: deriveModuleStatus(flatResources),
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
  const countResources = (items: PlanOutlineResource[]): number =>
    items.reduce((sum, item) => sum + 1 + countResources(item.childResources), 0)

  return modules.reduce((sum, mod) => {
    return sum + countResources(mod.resources) + countOutlineTreeResources(mod.childModules)
  }, 0)
}

export function countOutlineModules(modules: PlanOutlineModule[]): number {
  return modules.filter(m => m.kind === 'module').length
}

export function countOutlineResources(modules: PlanOutlineModule[]): number {
  const countResources = (items: PlanOutlineResource[]): number =>
    items.reduce((sum, item) => sum + 1 + countResources(item.childResources), 0)
  return modules.reduce((sum, mod) => sum + countResources(mod.resources), 0)
}
