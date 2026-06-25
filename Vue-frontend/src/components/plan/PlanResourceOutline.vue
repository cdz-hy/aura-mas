<template>
  <div class="plan-outline">
    <div v-if="headerSubtitle || metaText" class="plan-outline__header">
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

    <div v-else-if="modules.length === 0" class="plan-outline__state">
      <svg class="plan-outline__empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M4 6h16M4 12h16M4 18h10" stroke-linecap="round" />
      </svg>
      <p>{{ emptyTitle }}</p>
      <p v-if="emptyHint" class="plan-outline__empty-hint">{{ emptyHint }}</p>
    </div>

    <div v-else class="plan-outline__list custom-scrollbar">
      <section
        v-for="mod in modules"
        :key="mod.id"
        class="plan-outline__block"
        :style="indentStyle(mod.depth)"
      >
        <!-- 分组：未归类资源等 -->
        <div v-if="mod.kind === 'group'" class="plan-outline__group">
          <div class="plan-outline__group-head">
            <span class="plan-outline__group-title">{{ mod.title }}</span>
            <span class="plan-outline__group-badge">{{ mod.resources.length }}</span>
          </div>
          <div class="plan-outline__resources">
            <button
              v-for="res in mod.resources"
              :key="res.id"
              type="button"
              class="plan-outline__resource"
              :class="{ 'plan-outline__resource--active': res.resourceId === selectedResourceId }"
              :draggable="treeDnD"
              @click="$emit('select-resource', res.resourceId)"
              @dragstart="onResourceDragStart($event, res.resourceId, res.title)"
            >
              <span class="plan-outline__resource-title">{{ res.title }}</span>
              <span class="plan-outline__tag">{{ typeLabel(res.resourceType) }}</span>
              <span class="plan-outline__status" :class="statusClass(res.status)">{{ statusLabel(res.status) }}</span>
            </button>
          </div>
        </div>

        <!-- 学习模块卡片 -->
        <article
          v-else
          class="plan-outline__card"
          :class="{
            'plan-outline__card--active': mod.id === selectedModuleId,
            'plan-outline__card--drop': treeDnD && dropTargetId === mod.nodeId,
          }"
          @click="onModuleClick(mod)"
          @dragover.prevent="onModuleDragOver(mod)"
          @dragleave="onModuleDragLeave(mod)"
          @drop.prevent="onModuleDrop($event, mod)"
        >
          <div class="plan-outline__card-head">
            <span
              class="plan-outline__index"
              :class="{ 'plan-outline__index--active': mod.id === selectedModuleId }"
            >
              {{ mod.displayIndex }}
            </span>
            <div class="plan-outline__card-body">
              <p class="plan-outline__title" :title="mod.title">{{ mod.title }}</p>
              <div class="plan-outline__meta-row">
                <span class="plan-outline__hours">{{ mod.estimatedHours }}学时</span>
                <span
                  v-for="type in mod.resourceTypes.slice(0, 2)"
                  :key="type"
                  class="plan-outline__tag"
                  :class="tagClass(type)"
                >
                  {{ typeLabel(type) }}
                </span>
                <span v-if="mod.resourceTypes.length > 2" class="plan-outline__tag plan-outline__tag--muted">
                  +{{ mod.resourceTypes.length - 2 }}
                </span>
                <span class="plan-outline__status" :class="moduleStatusClass(mod.moduleStatus)">
                  {{ moduleStatusText(mod.moduleStatus) }}
                </span>
              </div>
            </div>

            <button
              v-if="hasExpandableResources(mod)"
              type="button"
              class="plan-outline__chevron"
              :class="{ 'plan-outline__chevron--open': isExpanded(mod.id) }"
              :title="isExpanded(mod.id) ? '收起资源' : '展开资源'"
              @click.stop="toggleExpand(mod.id)"
            >
              <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M4 2.5 8.5 6 4 9.5" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>

            <button
              v-if="treeMode && mod.nodeId"
              type="button"
              class="plan-outline__generate"
              title="生成学习内容"
              @click.stop="toggleGenerateMenu(mod.nodeId!)"
            >
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M8 3v10M3 8h10" stroke-linecap="round" />
              </svg>
            </button>
          </div>

          <div
            v-if="generateMenuNodeId === mod.nodeId"
            class="plan-outline__generate-menu"
            @click.stop
          >
            <button
              v-for="opt in generateOptions"
              :key="opt.type"
              type="button"
              @click="emitGenerate(mod.nodeId!, opt.type)"
            >
              {{ opt.label }}
            </button>
          </div>

          <div
            v-if="hasExpandableResources(mod) && isExpanded(mod.id)"
            class="plan-outline__resources plan-outline__resources--nested"
          >
            <button
              v-for="res in mod.resources"
              :key="res.id"
              type="button"
              class="plan-outline__resource"
              :class="{ 'plan-outline__resource--active': res.resourceId === selectedResourceId }"
              :draggable="treeDnD"
              @click.stop="$emit('select-resource', res.resourceId)"
              @dragstart="onResourceDragStart($event, res.resourceId, res.title)"
            >
              <span class="plan-outline__resource-title">{{ res.title }}</span>
              <span class="plan-outline__tag">{{ typeLabel(res.resourceType) }}</span>
              <span
                v-if="res.status === 1 && stuckResourceIds?.has(res.resourceId)"
                class="plan-outline__status plan-outline__status--failed plan-outline__status--action"
                @click.stop="$emit('retry-resource', res.resourceId)"
              >
                重试
              </span>
              <span v-else class="plan-outline__status" :class="statusClass(res.status)">
                {{ statusLabel(res.status) }}
              </span>
            </button>
          </div>
        </article>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { PlanOutlineModule, PlanOutlineModuleStatus } from './usePlanResourceOutline'
import { moduleStatusLabel } from './usePlanResourceOutline'
import {
  isNodeDragEvent,
  isResourceDragEvent,
  readNodeDragData,
  readResourceDragData,
  setResourceDragData,
} from '@/components/tree/useTreeDragDrop'

const props = withDefaults(defineProps<{
  modules: PlanOutlineModule[]
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
}>(), {
  selectedModuleId: null,
  selectedResourceId: null,
  loading: false,
  headerLabel: '学习大纲',
  emptyTitle: '暂无学习模块',
  emptyHint: '在右侧对话中描述学习目标，AI 会自动规划',
})

const emit = defineEmits<{
  'select-module': [moduleId: string, nodeId?: string]
  'select-resource': [resourceId: number]
  'retry-resource': [resourceId: number]
  'generate-content': [payload: { nodeId: string; type: string }]
  'drop-node': [payload: { nodeId: string; targetNodeId: string }]
  'mount-resource': [payload: { resourceId: number; targetNodeId: string }]
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

watch(
  () => props.modules,
  modules => {
    const next = new Set(expandedIds.value)
    for (const mod of modules) {
      if (mod.resources.length > 0) next.add(mod.id)
    }
    expandedIds.value = next
  },
  { immediate: true, deep: true },
)

watch(
  () => props.selectedModuleId,
  id => {
    if (id) expandedIds.value = new Set([...expandedIds.value, id])
  },
)

function indentStyle(depth: number) {
  if (depth <= 0) return undefined
  return { paddingLeft: `${8 + depth * 10}px` }
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

function hasExpandableResources(mod: PlanOutlineModule) {
  return mod.resources.length > 0
}

function isExpanded(id: string) {
  return expandedIds.value.has(id)
}

function toggleExpand(id: string) {
  const next = new Set(expandedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedIds.value = next
}

function onModuleClick(mod: PlanOutlineModule) {
  generateMenuNodeId.value = null
  emit('select-module', mod.id, mod.nodeId)
  if (hasExpandableResources(mod)) {
    expandedIds.value = new Set([...expandedIds.value, mod.id])
  }
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
</script>

<style scoped>
.plan-outline {
  display: flex;
  height: 100%;
  flex-direction: column;
  background: linear-gradient(180deg, #fafbfd 0%, #f5f7fb 100%);
}

.plan-outline__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px 8px;
  border-bottom: 1px solid rgba(154, 173, 216, 0.25);
}

.plan-outline__label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #8aa0c8;
}

.plan-outline__subtitle {
  margin: 2px 0 0;
  font-size: 10px;
  color: #a8b8d4;
  line-height: 1.3;
}

.plan-outline__meta {
  font-size: 10px;
  color: #a8b8d4;
  white-space: nowrap;
  padding-top: 2px;
}

.plan-outline__hint {
  margin: 0;
  padding: 0 14px 8px;
  font-size: 11px;
  color: #4164b2;
  border-bottom: 1px solid rgba(154, 173, 216, 0.2);
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
  padding: 10px 10px 16px;
}

.plan-outline__block + .plan-outline__block {
  margin-top: 8px;
}

.plan-outline__card {
  border: 1px solid transparent;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
  cursor: pointer;
}

.plan-outline__card:hover {
  background: rgba(255, 255, 255, 0.95);
}

.plan-outline__card--active {
  border-color: rgba(65, 100, 178, 0.45);
  background: rgba(238, 245, 255, 0.95);
  box-shadow: 0 1px 4px rgba(65, 100, 178, 0.08);
}

.plan-outline__card--drop {
  border-color: rgba(65, 100, 178, 0.55);
  background: rgba(65, 100, 178, 0.08);
}

.plan-outline__card-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 10px 8px;
}

.plan-outline__index {
  display: inline-flex;
  min-width: 22px;
  height: 22px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: #e8eef8;
  padding: 0 4px;
  font-size: 10px;
  font-weight: 700;
  color: #4164b2;
  line-height: 1;
}

.plan-outline__index--active {
  background: #294a8d;
  color: #fff;
}

.plan-outline__card-body {
  min-width: 0;
  flex: 1;
}

.plan-outline__title {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
  color: #1e3358;
  word-break: break-word;
}

.plan-outline__meta-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
}

.plan-outline__hours {
  font-size: 11px;
  color: #8aa0c8;
}

.plan-outline__tag {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 500;
  line-height: 1.4;
}

.plan-outline__tag--default {
  background: #eef3fb;
  color: #5a7ab8;
}

.plan-outline__tag--quiz {
  background: #f3efff;
  color: #7c5cbf;
}

.plan-outline__tag--mindmap {
  background: #fdf4ff;
  color: #a855f7;
}

.plan-outline__tag--video {
  background: #ecfdf5;
  color: #059669;
}

.plan-outline__tag--muted {
  background: #f1f5f9;
  color: #94a3b8;
}

.plan-outline__status {
  margin-left: auto;
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}

.plan-outline__status--ready { color: #059669; }
.plan-outline__status--generating { color: #2563eb; }
.plan-outline__status--failed { color: #dc2626; }
.plan-outline__status--pending { color: #94a3b8; }

.plan-outline__status--action {
  cursor: pointer;
  text-decoration: underline;
}

.plan-outline__chevron,
.plan-outline__generate {
  display: flex;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #8aa0c8;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, transform 0.15s ease;
}

.plan-outline__chevron:hover,
.plan-outline__generate:hover {
  background: rgba(65, 100, 178, 0.1);
  color: #4164b2;
}

.plan-outline__chevron svg {
  width: 10px;
  height: 10px;
}

.plan-outline__chevron--open {
  transform: rotate(90deg);
}

.plan-outline__generate {
  opacity: 0;
}

.plan-outline__card:hover .plan-outline__generate,
.plan-outline__card--active .plan-outline__generate {
  opacity: 1;
}

.plan-outline__generate svg {
  width: 14px;
  height: 14px;
}

.plan-outline__generate-menu {
  display: grid;
  gap: 2px;
  margin: 0 10px 8px;
  border: 1px solid rgba(154, 173, 216, 0.35);
  border-radius: 8px;
  background: #fff;
  padding: 4px;
  box-shadow: 0 6px 18px rgba(30, 51, 88, 0.1);
}

.plan-outline__generate-menu button {
  border: none;
  border-radius: 6px;
  background: transparent;
  padding: 6px 8px;
  text-align: left;
  font-size: 12px;
  color: #3d5278;
  cursor: pointer;
}

.plan-outline__generate-menu button:hover {
  background: #eef3fb;
  color: #4164b2;
}

.plan-outline__resources {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 8px 8px;
}

.plan-outline__resources--nested {
  margin-left: 30px;
  padding-left: 8px;
  border-left: 1px solid rgba(154, 173, 216, 0.35);
}

.plan-outline__resource {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 6px;
  border: none;
  border-radius: 8px;
  background: transparent;
  padding: 6px 8px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease;
}

.plan-outline__resource:hover {
  background: rgba(255, 255, 255, 0.95);
}

.plan-outline__resource--active {
  background: rgba(226, 232, 240, 0.85);
}

.plan-outline__resource-title {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: #3d5278;
}

.plan-outline__group {
  border: 1px dashed rgba(154, 173, 216, 0.45);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.65);
  overflow: hidden;
}

.plan-outline__group-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: rgba(238, 243, 251, 0.8);
}

.plan-outline__group-title {
  flex: 1;
  font-size: 12px;
  font-weight: 600;
  color: #5a7099;
}

.plan-outline__group-badge {
  display: inline-flex;
  min-width: 20px;
  height: 18px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #e4ebf8;
  padding: 0 6px;
  font-size: 10px;
  font-weight: 700;
  color: #4164b2;
}

@keyframes plan-outline-spin {
  to { transform: rotate(360deg); }
}
</style>
