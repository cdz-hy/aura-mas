import type { TreePlanOutlineItem, TreePlanNodeItem, TreePlanResourceItem } from '@/components/tree/useTreePlanOutline'
import type { LearningResource } from '@/types/plan'

export type PlanOutlineModuleStatus = 'pending' | 'generating' | 'ready' | 'failed'

export interface PlanOutlineResource {
  id: string
  resourceId: number
  title: string
  resourceType: string
  status: number
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
  }
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
    const outlineResources = mod.resources.map(resourceFromLearning)
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
    const outlineResources = resourceItems.map(r => resourceFromTreeItem(r, resources))

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

/** 知识树模式：树形 outline → 扁平卡片列表（保留层级 depth） */
export function buildOutlineFromTreeItems(
  items: TreePlanOutlineItem[],
  resources: LearningResource[],
): PlanOutlineModule[] {
  return flattenNodeItems(items, resources, '', 0)
}

export function countOutlineModules(modules: PlanOutlineModule[]): number {
  return modules.filter(m => m.kind === 'module').length
}

export function countOutlineResources(modules: PlanOutlineModule[]): number {
  return modules.reduce((sum, mod) => sum + mod.resources.length, 0)
}
