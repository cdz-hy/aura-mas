<template>
  <div class="plan-outline">
    <div v-if="headerLabel || headerSubtitle || metaText" class="plan-outline__header">
      <div>
        <span v-if="headerLabel" class="plan-outline__label">{{ headerLabel }}</span>
        <p v-if="headerSubtitle" class="plan-outline__subtitle">{{ headerSubtitle }}</p>
      </div>
      <span v-if="metaText" class="plan-outline__meta">{{ metaText }}</span>
    </div>

    <p v-if="dragHint" class="plan-outline__hint">{{ dragHint }}</p>

    <div v-if="loading" class="plan-outline__state">
      <span class="plan-outline__spinner" />
      <p>加载大纲...</p>
    </div>

    <div v-else-if="outlineTree.length === 0" class="plan-outline__state">
      <svg class="plan-outline__empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M4 6h16M4 12h16M4 18h10" stroke-linecap="round" />
      </svg>
      <p>{{ emptyTitle }}</p>
      <p v-if="emptyHint" class="plan-outline__empty-hint">{{ emptyHint }}</p>
    </div>

    <div v-else class="plan-outline__list custom-scrollbar">
      <section v-for="mod in outlineTree" :key="mod.id" class="plan-outline__block">
        <div v-if="mod.kind === 'group'" class="plan-outline__group">
          <div class="plan-outline__group-head">
            <span class="plan-outline__group-title">{{ mod.title }}</span>
            <span class="plan-outline__group-badge">{{ mod.resources.length }}</span>
          </div>
          <div class="plan-outline__group-body">
            <PlanOutlineResourceCard
              v-for="res in mod.resources"
              :key="res.id"
              :resource="res"
            />
          </div>
        </div>

        <PlanOutlineModuleNode
          v-else
          :module="mod"
          :depth="0"
        />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, provide, ref, watch } from 'vue'
import PlanOutlineModuleNode from './PlanOutlineModuleNode.vue'
import PlanOutlineResourceCard from './PlanOutlineResourceCard.vue'
import type { PlanOutlineModule, PlanOutlineModuleStatus, PlanOutlineTreeModule } from './usePlanResourceOutline'
import { moduleStatusLabel, nestOutlineModules } from './usePlanResourceOutline'
import { OUTLINE_CONTEXT_KEY } from './planOutlineContext'
import {
  readNodeDragData,
  readResourceDragData,
  setResourceDragData,
} from '@/components/tree/useTreeDragDrop'

const props = withDefaults(defineProps<{
  modules?: PlanOutlineModule[]
  treeModules?: PlanOutlineTreeModule[]
  selectedModuleId?: string | null
  selectedResourceId?: number | null
  typeLabels: Record<string, string>
  loading?: boolean
  headerLabel?: string
  headerSubtitle?: string
  metaText?: string
  emptyTitle?: string
  emptyHint?: string
  dragHint?: string
  treeMode?: boolean
  treeDnD?: boolean
  stuckResourceIds?: Set<number>
  progressMap?: Record<number, number>
}>(), {
  selectedModuleId: null,
  selectedResourceId: null,
  loading: false,
  modules: () => [],
  headerLabel: '学习大纲',
  emptyTitle: '暂无学习模块',
  emptyHint: '在右侧对话中描述学习目标，AI 会自动规划',
  progressMap: () => ({}),
})

const emit = defineEmits<{
  'select-module': [moduleId: string, nodeId?: string]
  'select-resource': [resourceId: number]
  'retry-resource': [resourceId: number]
  'generate-content': [payload: { nodeId: string; type: string }]
  'drop-node': [payload: { nodeId: string; targetNodeId: string }]
  'mount-resource': [payload: { resourceId: number; targetNodeId: string }]
  'toggle-complete': [resourceId: number]
  'delete-resource': [resourceId: number]
}>()

const expandedIds = ref<Set<string>>(new Set())
const generateMenuNodeId = ref<string | null>(null)
const dropTargetId = ref<string | null>(null)

const generateOptions = [
  { type: 'text', label: '正文讲解' },
  { type: 'mindmap', label: '思维导图' },
  { type: 'quiz', label: '测验题' },
  { type: 'summary', label: '总结' },
  { type: 'code', label: '代码示例' },
]

const outlineTree = computed(() =>
  props.treeModules?.length ? props.treeModules : nestOutlineModules(props.modules || []),
)

const parentIdsByModuleId = computed(() => {
  const result = new Map<string, string[]>()
  const walk = (items: PlanOutlineTreeModule[], parents: string[]) => {
    for (const item of items) {
      result.set(item.id, parents)
      walk(item.childModules, [...parents, item.id])
    }
  }
  walk(outlineTree.value, [])
  return result
})

const descendantIdsByModuleId = computed(() => {
  const result = new Map<string, string[]>()
  const walk = (item: PlanOutlineTreeModule): string[] => {
    const ids = item.childModules.flatMap(child => [child.id, ...walk(child)])
    result.set(item.id, ids)
    return ids
  }
  for (const mod of outlineTree.value) walk(mod)
  return result
})

watch(
  () => [props.modules, props.treeModules] as const,
  () => {
    const validIds = collectModuleIds(outlineTree.value)
    expandedIds.value = new Set([...expandedIds.value].filter(id => validIds.has(id)))
    syncExpandedToSelection(props.selectedModuleId)
  },
  { immediate: true, deep: true },
)

watch(
  () => props.selectedModuleId,
  id => syncExpandedToSelection(id),
)

function collectModuleIds(items: PlanOutlineTreeModule[], acc = new Set<string>()) {
  for (const item of items) {
    acc.add(item.id)
    collectModuleIds(item.childModules, acc)
  }
  return acc
}

function syncExpandedToSelection(id: string | null | undefined) {
  if (!id) return
  const parentIds = parentIdsByModuleId.value.get(id) || []
  expandedIds.value = new Set([...expandedIds.value, ...parentIds, id])
}

function typeLabel(type: string) {
  return props.typeLabels[type] || type
}

function tagClass(type: string) {
  if (type === 'quiz') return 'plan-outline__tag--quiz'
  if (type === 'mindmap') return 'plan-outline__tag--mindmap'
  if (type === 'video') return 'plan-outline__tag--video'
  return 'plan-outline__tag--default'
}

function statusLabel(status: number) {
  if (status === 2) return '已生成'
  if (status === 1) return '生成中'
  if (status === 3) return '失败'
  return '待生成'
}

function statusClass(status: number) {
  if (status === 2) return 'plan-outline__status--ready'
  if (status === 1) return 'plan-outline__status--generating'
  if (status === 3) return 'plan-outline__status--failed'
  return 'plan-outline__status--pending'
}

function moduleStatusText(status: PlanOutlineModuleStatus) {
  return moduleStatusLabel(status)
}

function moduleStatusClass(status: PlanOutlineModuleStatus) {
  if (status === 'ready') return 'plan-outline__status--ready'
  if (status === 'generating') return 'plan-outline__status--generating'
  if (status === 'failed') return 'plan-outline__status--failed'
  return 'plan-outline__status--pending'
}

function isExpanded(id: string) {
  return expandedIds.value.has(id)
}

function toggleExpand(id: string) {
  const next = new Set(expandedIds.value)
  if (next.has(id)) {
    next.delete(id)
    for (const childId of descendantIdsByModuleId.value.get(id) || []) {
      next.delete(childId)
    }
  } else {
    next.add(id)
  }
  expandedIds.value = next
}

function onModuleClick(mod: PlanOutlineTreeModule) {
  generateMenuNodeId.value = null
  emit('select-module', mod.id, mod.nodeId)
}

function toggleGenerateMenu(nodeId: string) {
  generateMenuNodeId.value = generateMenuNodeId.value === nodeId ? null : nodeId
}

function emitGenerate(nodeId: string, type: string) {
  generateMenuNodeId.value = null
  emit('generate-content', { nodeId, type })
}

function onResourceDragStart(event: DragEvent, resourceId: number, title: string) {
  if (!props.treeDnD) {
    event.preventDefault()
    return
  }
  setResourceDragData(event, { resourceId, title })
}

function onModuleDragOver(mod: PlanOutlineModule) {
  if (!props.treeDnD || !mod.nodeId) return
  dropTargetId.value = mod.nodeId
}

function onModuleDragLeave(mod: PlanOutlineModule) {
  if (dropTargetId.value === mod.nodeId) dropTargetId.value = null
}

function onModuleDrop(event: DragEvent, mod: PlanOutlineModule) {
  if (!props.treeDnD || !mod.nodeId) return
  dropTargetId.value = null
  const nodePayload = readNodeDragData(event)
  if (nodePayload) {
    if (nodePayload.nodeId === mod.nodeId) return
    emit('drop-node', { nodeId: nodePayload.nodeId, targetNodeId: mod.nodeId })
    return
  }
  const resourcePayload = readResourceDragData(event)
  if (resourcePayload) {
    emit('mount-resource', { resourceId: resourcePayload.resourceId, targetNodeId: mod.nodeId })
  }
}

watch(
  () => props.treeDnD,
  enabled => {
    if (!enabled) dropTargetId.value = null
  },
)

provide(OUTLINE_CONTEXT_KEY, {
  get selectedModuleId() { return props.selectedModuleId },
  get selectedResourceId() { return props.selectedResourceId },
  get treeMode() { return !!props.treeMode },
  get treeDnD() { return !!props.treeDnD },
  get stuckResourceIds() { return props.stuckResourceIds },
  get progressMap() { return props.progressMap },
  get generateMenuNodeId() { return generateMenuNodeId.value },
  get dropTargetId() { return dropTargetId.value },
  generateOptions,
  typeLabel,
  tagClass,
  statusLabel,
  statusClass,
  moduleStatusText,
  moduleStatusClass,
  isExpanded,
  toggleExpand,
  toggleGenerateMenu,
  emitGenerate,
  selectResource: (resourceId: number) => emit('select-resource', resourceId),
  retryResource: (resourceId: number) => emit('retry-resource', resourceId),
  toggleComplete: (resourceId: number) => emit('toggle-complete', resourceId),
  deleteResource: (resourceId: number) => emit('delete-resource', resourceId),
  onResourceDragStart,
  onModuleClick,
  onModuleDragOver,
  onModuleDragLeave,
  onModuleDrop,
})
</script>

<style scoped src="./planOutlineModule.css"></style>

<style scoped>
.plan-outline {
  display: flex;
  height: 100%;
  flex-direction: column;
  background: linear-gradient(180deg, #fbfcff 0%, #f8fbff 100%);
}

.plan-outline__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 13px 14px 10px;
  border-bottom: 1px solid rgba(188, 203, 232, 0.48);
  background: rgba(255, 255, 255, 0.82);
}

.plan-outline__label {
  display: block;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7891bd;
}

.plan-outline__subtitle {
  margin: 2px 0 0;
  font-size: 10.5px;
  color: #9aaed0;
  line-height: 1.3;
}

.plan-outline__meta {
  font-size: 10px;
  color: #8ea3c8;
  white-space: nowrap;
  padding-top: 2px;
}

.plan-outline__hint {
  margin: 0;
  padding: 8px 14px;
  font-size: 11px;
  color: #4164b2;
  border-bottom: 1px solid rgba(154, 173, 216, 0.22);
  background: rgba(238, 245, 255, 0.72);
}

.plan-outline__state {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px 20px;
  text-align: center;
  font-size: 13px;
  color: #8aa0c8;
}

.plan-outline__spinner {
  width: 28px;
  height: 28px;
  border: 2px solid #e2e8f0;
  border-top-color: #4164b2;
  border-radius: 999px;
  animation: plan-outline-spin 0.8s linear infinite;
}

.plan-outline__empty-icon {
  width: 36px;
  height: 36px;
  color: #c5d0e3;
}

.plan-outline__empty-hint {
  font-size: 11px;
  color: #b8c5da;
}

.plan-outline__list {
  flex: 1;
  overflow-y: auto;
  padding: 6px 8px 10px;
}

.plan-outline__block + .plan-outline__block {
  margin-top: 2px;
  border-top: 1px solid rgba(188, 203, 232, 0.35);
  padding-top: 2px;
}

.plan-outline__group {
  border: 1px solid rgba(201, 213, 236, 0.5);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.6);
  overflow: hidden;
}

.plan-outline__group-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  background: rgba(244, 248, 255, 0.7);
}

.plan-outline__group-title {
  flex: 1;
  font-size: 11.5px;
  font-weight: 600;
  color: #5a7099;
}

.plan-outline__group-badge {
  display: inline-flex;
  min-width: 18px;
  height: 16px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #e4ebf8;
  padding: 0 5px;
  font-size: 9.5px;
  font-weight: 700;
  color: #4164b2;
}

.plan-outline__group-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 4px 6px 6px;
}

@keyframes plan-outline-spin {
  to { transform: rotate(360deg); }
}
</style>
