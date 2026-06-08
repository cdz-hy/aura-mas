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
        <div class="flex items-center gap-2 min-w-0">
          <h3 class="truncate text-sm font-semibold text-navy-800" :title="node.title">
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

    <div class="mt-3 flex items-center justify-between gap-2">
      <div class="flex items-center gap-2 text-[11px] text-navy-400">
        <MetricDots title="重要性" :value="node.importance ?? undefined" color-class="bg-amber-400" />
        <MetricDots title="相关性" :value="node.relevance ?? node.relevanceScore ?? undefined" color-class="bg-blue-400" />
        <MetricDots title="难度" :value="node.difficulty ?? undefined" color-class="bg-rose-400" />
      </div>
      <div class="flex flex-shrink-0 items-center gap-1">
        <span v-if="hasPrerequisites" class="mini-badge bg-blue-50 text-blue-600" title="有前置知识">前置</span>
        <span v-if="node.isFundamental" class="mini-badge bg-sage-100 text-sage-700" :title="node.fpReason || '第一性原理'">原理</span>
      </div>
    </div>

    <div class="mt-3 grid grid-cols-2 gap-2">
      <button class="node-action" title="解释当前节点" @click.stop="emit('select', node.id)">
        <svg class="h-3.5 w-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a4 4 0 0 1-4 4H7l-4 4V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z" />
        </svg>
        <span class="truncate">解释</span>
      </button>
      <button class="node-action" title="按学习顺序拆分" @click.stop="emit('subdivide', node.id)">
        <svg class="h-3.5 w-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M8 6h13" /><path d="M8 12h13" /><path d="M8 18h13" /><path d="M3 6h.01" /><path d="M3 12h.01" /><path d="M3 18h.01" />
        </svg>
        <span class="truncate">拆分</span>
      </button>
    </div>
    <button class="node-action mt-2 w-full" title="第一性原理分析" @click.stop="emit('first-principles', node.id)">
      <svg class="h-3.5 w-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="3" /><path d="M12 2v4" /><path d="M12 18v4" /><path d="m4.93 4.93 2.83 2.83" /><path d="m16.24 16.24 2.83 2.83" /><path d="M2 12h4" /><path d="M18 12h4" /><path d="m4.93 19.07 2.83-2.83" /><path d="m16.24 7.76 2.83-2.83" />
      </svg>
      <span class="truncate">第一性原理</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h } from 'vue'
import type { KnowledgeNode } from '@/types/knowledgeTree'

const props = defineProps<{
  node: KnowledgeNode
  selected?: boolean
  hasChildren?: boolean
}>()

const emit = defineEmits<{
  select: [nodeId: string]
  'toggle-collapse': [nodeId: string]
  subdivide: [nodeId: string]
  'first-principles': [nodeId: string]
}>()

const hasPrerequisites = computed(() => Boolean(props.node.prerequisiteIds?.length))

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

const MetricDots = defineComponent({
  props: {
    title: { type: String, required: true },
    value: { type: Number, default: null },
    colorClass: { type: String, required: true },
  },
  setup(metricProps) {
    return () => {
      const active = Math.max(0, Math.min(5, Math.round(metricProps.value || 0)))
      return h('div', { class: 'flex items-center gap-1', title: `${metricProps.title}: ${active || '-'}` }, [
        h('span', { class: 'w-8 text-[10px]' }, metricProps.title.slice(0, 1)),
        ...Array.from({ length: 5 }, (_, index) => h('span', {
          class: [
            'h-1.5 w-1.5 rounded-full',
            index < active ? metricProps.colorClass : 'bg-navy-100',
          ],
        })),
      ])
    }
  },
})
</script>

<style scoped>
.tree-node {
  width: 236px;
  height: 188px;
  border-width: 1px;
  border-radius: 8px;
  padding: 12px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.tree-node:focus-visible {
  outline: 2px solid rgb(51 65 85);
  outline-offset: 3px;
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
  height: 28px;
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

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
