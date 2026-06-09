<template>
  <div class="h-full overflow-y-auto p-3">
    <div v-if="items.length === 0" class="py-8 text-center text-sm text-navy-300">
      暂无知识树节点
    </div>
    <div v-else class="space-y-1">
      <OutlineRow
        v-for="item in items"
        :key="item.id"
        :item="item"
        :selected-node-id="selectedNodeId"
        :type-labels="typeLabels"
        @select-node="$emit('select-node', $event)"
        @open-resource="$emit('open-resource', $event)"
        @toggle-collapse="$emit('toggle-collapse', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineComponent, h } from 'vue'
import type { PropType, VNode } from 'vue'
import type { TreePlanOutlineItem } from './useTreePlanOutline'

defineProps<{
  items: TreePlanOutlineItem[]
  selectedNodeId: string | null
  typeLabels: Record<string, string>
}>()

defineEmits<{
  'select-node': [nodeId: string]
  'open-resource': [resourceId: number]
  'toggle-collapse': [nodeId: string]
}>()

type OutlineEmit = {
  (event: 'select-node', value: string): void
  (event: 'open-resource', value: number): void
  (event: 'toggle-collapse', value: string): void
}

const OutlineRow = defineComponent({
  name: 'OutlineRow',
  props: {
    item: { type: Object as PropType<TreePlanOutlineItem>, required: true },
    selectedNodeId: { type: String as PropType<string | null>, default: null },
    typeLabels: { type: Object as PropType<Record<string, string>>, required: true },
  },
  emits: ['select-node', 'open-resource', 'toggle-collapse'],
  setup(props, { emit }) {
    return (): VNode => renderOutlineRow(props.item, props.selectedNodeId, props.typeLabels, emit as OutlineEmit)
  },
})

function renderOutlineRow(
  item: TreePlanOutlineItem,
  selectedNodeId: string | null,
  typeLabels: Record<string, string>,
  emit: OutlineEmit,
): VNode {
  const paddingLeft = `${Math.min(item.depth, 6) * 14}px`

  if (item.kind === 'resource') {
    return h('button', {
      class: 'outline-resource-row',
      style: { paddingLeft },
      title: item.title,
      onClick: () => emit('open-resource', item.resourceId),
    }, [
      h('span', { class: 'outline-resource-type' }, typeLabels[item.resourceType] || item.resourceType),
      h('span', { class: 'truncate' }, item.title),
    ])
  }

  if (item.kind === 'group') {
    return h('div', { class: 'space-y-1' }, [
      h('div', { class: 'outline-group-row', style: { paddingLeft } }, item.title),
      ...item.children.map(child => renderOutlineRow(child, selectedNodeId, typeLabels, emit)),
    ])
  }

  const selected = item.nodeId === selectedNodeId
  return h('div', { class: 'space-y-1' }, [
    h('div', {
      class: ['outline-node-row', selected ? 'outline-node-row--selected' : ''],
      style: { paddingLeft },
      title: item.summary || item.title,
    }, [
      h('button', {
        class: ['outline-collapse', item.children.length ? '' : 'outline-collapse--empty'],
        disabled: item.children.length === 0,
        title: item.collapsed ? '展开' : '收起',
        onClick: (event: MouseEvent) => {
          event.stopPropagation()
          emit('toggle-collapse', item.nodeId)
        },
      }, item.children.length ? (item.collapsed ? '>' : 'v') : ''),
      h('button', {
        class: 'min-w-0 flex-1 truncate text-left',
        onClick: () => emit('select-node', item.nodeId),
      }, item.title),
    ]),
    ...(item.collapsed ? [] : item.children.map(child => renderOutlineRow(child, selectedNodeId, typeLabels, emit))),
  ])
}
</script>

<style scoped>
.outline-node-row,
.outline-resource-row,
.outline-group-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 34px;
  border-radius: 7px;
  padding-right: 8px;
  font-size: 12px;
}

.outline-node-row {
  color: #1f3158;
  font-weight: 600;
}

.outline-node-row:hover,
.outline-node-row--selected {
  background: #eef3fb;
}

.outline-resource-row {
  color: #53627c;
  font-weight: 500;
}

.outline-resource-row:hover {
  background: #f7f9fc;
}

.outline-group-row {
  color: #8a95a8;
  font-size: 11px;
  font-weight: 700;
}

.outline-collapse {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  color: #64748b;
  font-size: 10px;
}

.outline-collapse:hover:not(:disabled) {
  background: white;
}

.outline-collapse--empty {
  opacity: 0;
}

.outline-resource-type {
  display: inline-flex;
  align-items: center;
  height: 18px;
  border-radius: 999px;
  background: #eaf0ff;
  padding: 0 6px;
  color: #4164b2;
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}
</style>
