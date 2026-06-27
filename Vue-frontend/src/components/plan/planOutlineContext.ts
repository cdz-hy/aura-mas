import type { InjectionKey } from 'vue'
import type { PlanOutlineModule, PlanOutlineModuleStatus, PlanOutlineTreeModule } from './usePlanResourceOutline'

export interface OutlineContext {
  selectedModuleId: string | null
  selectedResourceId: number | null
  treeMode: boolean
  treeDnD: boolean
  stuckResourceIds?: Set<number>
  generateMenuNodeId: string | null
  dropTargetId: string | null
  generateOptions: Array<{ type: string; label: string }>
  typeLabel: (type: string) => string
  tagClass: (type: string) => string
  statusLabel: (status: number) => string
  statusClass: (status: number) => string
  moduleStatusText: (status: PlanOutlineModuleStatus) => string
  moduleStatusClass: (status: PlanOutlineModuleStatus) => string
  isExpanded: (id: string) => boolean
  toggleExpand: (id: string) => void
  toggleGenerateMenu: (nodeId: string) => void
  emitGenerate: (nodeId: string, type: string) => void
  selectResource: (resourceId: number) => void
  retryResource: (resourceId: number) => void
  onResourceDragStart: (event: DragEvent, resourceId: number, title: string) => void
  onModuleClick: (mod: PlanOutlineTreeModule) => void
  onModuleDragOver: (mod: PlanOutlineModule) => void
  onModuleDragLeave: (mod: PlanOutlineModule) => void
  onModuleDrop: (event: DragEvent, mod: PlanOutlineModule) => void
}

export const OUTLINE_CONTEXT_KEY: InjectionKey<OutlineContext> = Symbol('planOutlineContext')
