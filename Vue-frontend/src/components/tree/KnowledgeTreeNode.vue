<template>
  <div
    class="tree-node"
    :class="[
      selected ? 'border-navy-500 shadow-paper-hover ring-2 ring-navy-100' : 'border-navy-100 shadow-paper hover:border-navy-300',
      node.isFundamental ? 'bg-sage-50/80' : 'bg-white',
    ]"
    role="button"
    tabindex="0"
    :aria-label="`选择知识节点：${node.title || '未命名节点'}`"
    @click="emit('select', node.id)"
    @keydown.enter.prevent="selectFromKeyboard"
    @keydown.space.prevent="selectFromKeyboard"
  >
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-1.5 min-w-0">
          <span
            v-if="draggable"
            class="drag-handle"
            title="拖到左侧大纲以调整归属"
            draggable="true"
            @dragstart="onDragStart"
            @dragend="emit('drag-end')"
            @click.stop
          >
            <svg viewBox="0 0 10 16" fill="currentColor">
              <circle cx="2.5" cy="2.5" r="1.2" />
              <circle cx="7.5" cy="2.5" r="1.2" />
              <circle cx="2.5" cy="8" r="1.2" />
              <circle cx="7.5" cy="8" r="1.2" />
              <circle cx="2.5" cy="13.5" r="1.2" />
              <circle cx="7.5" cy="13.5" r="1.2" />
            </svg>
          </span>
          <h3 class="truncate text-sm font-semibold text-navy-800 flex-1" :title="node.title">
            {{ node.title || '未命名节点' }}
          </h3>
          <span class="status-badge" :class="statusClass">{{ statusLabel }}</span>
        </div>
        <p class="mt-1 line-clamp-2 h-9 text-xs leading-[18px] text-navy-500" :title="node.summary || ''">
          {{ node.summary || '暂无摘要' }}
        </p>
      </div>
      <button
        class="icon-button h-7 w-7 flex-shrink-0"
        :class="hasChildren ? 'text-navy-500 hover:bg-navy-50' : 'text-navy-200 cursor-default'"
        :disabled="!hasChildren"
        :title="node.collapsed ? '展开' : '折叠'"
        @click.stop="emit('toggle-collapse', node.id)"
      >
        <svg v-if="node.collapsed" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6" />
        </svg>
        <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
    </div>

    <div class="mt-3 flex items-end justify-between gap-2">
      <div class="node-metrics">
        <div
          v-for="metric in nodeMetrics"
          :key="metric.key"
          class="node-metric"
          :title="`${metric.label} ${metric.display > 0 ? metric.display : '-'} / 3`"
        >
          <span class="node-metric__label">{{ metric.label }}</span>
          <div class="node-metric__dots" aria-hidden="true">
            <span
              v-for="level in 3"
              :key="level"
              class="node-metric__dot"
              :class="level <= metric.display ? metric.colorClass : 'node-metric__dot--empty'"
            />
          </div>
        </div>
      </div>
      <div class="flex flex-shrink-0 items-center gap-1">
        <span v-if="hasPrerequisites" class="mini-badge bg-blue-50 text-blue-600" title="有前置知识">前置</span>
        <span v-if="node.isFundamental" class="mini-badge bg-sage-100 text-sage-700" :title="node.fpReason || '第一性原理'">原理</span>
      </div>
    </div>

    <button
      class="node-action mt-3 w-full"
      :class="{ 'node-action--disabled': atMaxDepth }"
      :title="atMaxDepth ? '已达 3 层上限，无法继续拆分' : '拆分当前节点'"
      :disabled="atMaxDepth"
      @click.stop="!atMaxDepth && emit('open-subdivide', node.id)"
    >
      <svg class="h-3.5 w-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M8 6h13" />
        <path d="M8 12h13" />
        <path d="M8 18h13" />
        <path d="M3 6h.01" />
        <path d="M3 12h.01" />
        <path d="M3 18h.01" />
      </svg>
      <span class="truncate">拆分</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { KnowledgeNode } from '@/types/knowledgeTree'
import { setNodeDragData } from './useTreeDragDrop'

const props = defineProps<{
  node: KnowledgeNode
  selected?: boolean
  hasChildren?: boolean
  rootNodeId?: string | null
}>()

const emit = defineEmits<{
  select: [nodeId: string]
  'toggle-collapse': [nodeId: string]
  'open-subdivide': [nodeId: string]
  'drag-start': [nodeId: string]
  'drag-end': []
}>()

const draggable = computed(() => Boolean(props.rootNodeId && props.node.id !== props.rootNodeId))

/** 知识树最多 3 层：depth 0 根 / 1 主模块 / 2 子知识点 */
const atMaxDepth = computed(() => (props.node.depth ?? 0) >= 2)

const hasPrerequisites = computed(() => Boolean(props.node.prerequisiteIds?.length))

/** 后端 relevance 为 0/1 标志，展示用 relevanceScore（1-3） */
function metricLevel(value: number | null | undefined) {
  if (value == null || Number.isNaN(value) || value <= 0) return 0
  return Math.max(1, Math.min(3, Math.round(value)))
}

function relevanceLevel(node: KnowledgeNode) {
  const score = node.relevanceScore ?? node.relevance
  return metricLevel(score)
}

const nodeMetrics = computed(() => [
  {
    key: 'importance',
    label: '重要',
    display: metricLevel(props.node.importance),
    colorClass: 'node-metric__dot--importance',
  },
  {
    key: 'relevance',
    label: '相关',
    display: relevanceLevel(props.node),
    colorClass: 'node-metric__dot--relevance',
  },
  {
    key: 'difficulty',
    label: '难度',
    display: metricLevel(props.node.difficulty),
    colorClass: 'node-metric__dot--difficulty',
  },
])

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '待学',
    learning: '学习中',
    in_progress: '学习中',
    completed: '已完成',
    done: '已完成',
    skipped: '跳过',
  }
  return map[(props.node.status || '').toLowerCase()] || props.node.status || '待学'
})

const statusClass = computed(() => {
  const status = (props.node.status || '').toLowerCase()
  if (['completed', 'done'].includes(status)) return 'bg-sage-100 text-sage-700'
  if (['learning', 'in_progress'].includes(status)) return 'bg-amber-100 text-amber-700'
  if (status === 'skipped') return 'bg-navy-100 text-navy-400'
  return 'bg-navy-50 text-navy-500'
})

function selectFromKeyboard(event: KeyboardEvent) {
  if (event.target !== event.currentTarget) return
  emit('select', props.node.id)
}

function onDragStart(event: DragEvent) {
  if (!draggable.value) {
    event.preventDefault()
    return
  }
  setNodeDragData(event, {
    nodeId: props.node.id,
    title: props.node.title || '未命名节点',
  })
  emit('drag-start', props.node.id)
}
</script>

<style scoped>
.tree-node {
  width: 236px;
  height: 172px;
  border-width: 1px;
  border-radius: 8px;
  padding: 12px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.tree-node:focus-visible {
  outline: 2px solid rgb(51 65 85);
  outline-offset: 3px;
}

.drag-handle {
  display: inline-flex;
  width: 14px;
  height: 20px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: rgb(148 163 184);
  cursor: grab;
  transition: color 0.15s ease, background 0.15s ease;
}

.drag-handle:hover {
  color: rgb(71 85 105);
  background: rgb(241 245 249);
}

.drag-handle:active {
  cursor: grabbing;
}

.drag-handle svg {
  width: 10px;
  height: 14px;
}

.status-badge,
.mini-badge {
  display: inline-flex;
  align-items: center;
  height: 20px;
  border-radius: 999px;
  padding: 0 8px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.mini-badge {
  height: 18px;
  padding: 0 6px;
  font-size: 10px;
}

.node-metrics {
  display: grid;
  min-width: 0;
  flex: 1;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

.node-metric {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}

.node-metric__label {
  font-size: 10px;
  line-height: 1;
  color: rgb(148 163 184);
  white-space: nowrap;
}

.node-metric__dots {
  display: flex;
  align-items: center;
  gap: 3px;
}

.node-metric__dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  flex-shrink: 0;
}

.node-metric__dot--empty {
  background: rgb(226 232 240);
}

.node-metric__dot--importance {
  background: rgb(251 191 36);
}

.node-metric__dot--relevance {
  background: rgb(96 165 250);
}

.node-metric__dot--difficulty {
  background: rgb(251 113 133);
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: background-color 0.18s ease, color 0.18s ease;
}

.node-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 30px;
  min-width: 0;
  border-radius: 7px;
  background: rgb(248 250 252);
  padding: 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: rgb(71 85 105);
  transition: background-color 0.18s ease, color 0.18s ease;
}

.node-action:hover {
  background: rgb(226 232 240);
  color: rgb(30 41 59);
}

.node-action--disabled,
.node-action:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.node-action--disabled:hover,
.node-action:disabled:hover {
  background: rgb(248 250 252);
  color: rgb(71 85 105);
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
