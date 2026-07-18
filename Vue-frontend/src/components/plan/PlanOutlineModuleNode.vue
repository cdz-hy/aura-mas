<template>
  <article
    ref="cardRef"
    class="plan-outline__card"
    :class="{
      'plan-outline__card--active': module.id === ctx.selectedModuleId,
      'plan-outline__card--drop': ctx.treeDnD && ctx.dropTargetId === module.nodeId,
    }"
    :draggable="ctx.treeDnD && !!module.nodeId"
    @click.stop="onModuleClick"
    @dragstart="onNodeDragStart"
    @dragover.prevent="onModuleDragOver"
    @dragleave="onModuleDragLeave"
    @drop.prevent="onModuleDrop"
  >
    <div class="plan-outline__card-head">
      <span
        class="plan-outline__index"
        :class="{ 'plan-outline__index--active': module.id === ctx.selectedModuleId }"
      >
        {{ module.displayIndex }}
      </span>
      <div class="plan-outline__card-body">
        <p class="plan-outline__title" :title="module.title">{{ module.title }}</p>
        <div class="plan-outline__meta-row">
          <span class="plan-outline__hours">{{ module.estimatedHours }}学时</span>
          <span
            v-for="type in module.resourceTypes.slice(0, 2)"
            :key="type"
            class="plan-outline__tag"
            :class="ctx.tagClass(type)"
          >
            {{ ctx.typeLabel(type) }}
          </span>
          <span
            v-if="module.resourceTypes.length > 2"
            class="plan-outline__tag plan-outline__tag--muted"
          >
            +{{ module.resourceTypes.length - 2 }}
          </span>
          <span
            v-if="!ctx.isExpanded(module.id) && childCount > 0"
            class="plan-outline__child-count"
          >
            {{ childCount }} 子项
          </span>
          <span class="plan-outline__status" :class="ctx.moduleStatusClass(module.moduleStatus)">
            {{ ctx.moduleStatusText(module.moduleStatus) }}
          </span>
        </div>
      </div>

      <button
        v-if="hasExpandableItems"
        type="button"
        class="plan-outline__chevron"
        :class="{ 'plan-outline__chevron--open': ctx.isExpanded(module.id) }"
        :title="ctx.isExpanded(module.id) ? '收起子项' : '展开子项'"
        @click.stop="ctx.toggleExpand(module.id)"
      >
        <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M4 2.5 8.5 6 4 9.5" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>

      <button
        v-if="ctx.treeMode && module.nodeId"
        type="button"
        class="plan-outline__generate"
        title="生成学习内容"
        @click.stop="ctx.toggleGenerateMenu(module.nodeId!)"
      >
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
          <path d="M8 3v10M3 8h10" stroke-linecap="round" />
        </svg>
      </button>
    </div>

    <div
      v-if="ctx.treeMode && ctx.generateMenuNodeId === module.nodeId"
      class="plan-outline__generate-menu"
      @click.stop
    >
      <button
        v-for="opt in ctx.generateOptions"
        :key="opt.type"
        type="button"
        @click="ctx.emitGenerate(module.nodeId!, opt.type)"
      >
        {{ opt.label }}
      </button>
    </div>

    <div
      v-if="hasExpandableItems"
      class="plan-outline__children-wrap"
      :class="{ 'plan-outline__children-wrap--open': ctx.isExpanded(module.id) }"
    >
      <div class="plan-outline__children-inner">
        <div
          v-if="module.resources.length > 0 || module.childModules.length > 0"
          class="plan-outline__child-modules"
        >
          <PlanOutlineResourceCard
            v-for="res in module.resources"
            :key="res.id"
            :resource="res"
          />
          <PlanOutlineModuleNode
            v-for="child in module.childModules"
            :key="child.id"
            :module="child"
            :depth="depth + 1"
          />
        </div>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, inject, ref, watch, nextTick } from 'vue'
import PlanOutlineModuleNode from './PlanOutlineModuleNode.vue'
import PlanOutlineResourceCard from './PlanOutlineResourceCard.vue'
import type { PlanOutlineTreeModule } from './usePlanResourceOutline'
import { OUTLINE_CONTEXT_KEY, type OutlineContext } from './planOutlineContext'
import { setNodeDragData } from '@/components/tree/useTreeDragDrop'

const props = defineProps<{
  module: PlanOutlineTreeModule
  depth: number
}>()

const ctx = inject(OUTLINE_CONTEXT_KEY) as OutlineContext
const cardRef = ref<HTMLElement | null>(null)

// 当选中状态变化时，自动滚动到可见区域
watch(
  () => ctx.selectedModuleId,
  async (newId) => {
    if (newId === props.module.id && cardRef.value) {
      await nextTick()
      cardRef.value.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  },
)

function onNodeDragStart(event: DragEvent) {
  if (!ctx.treeDnD || !props.module.nodeId) {
    event.preventDefault()
    return
  }
  setNodeDragData(event, { nodeId: props.module.nodeId, title: props.module.title })
}

const childCount = computed(() => {
  const countModules = (mod: PlanOutlineTreeModule): number =>
    mod.childModules.reduce((sum, child) => sum + 1 + countModules(child), 0)
  return props.module.resources.length + countModules(props.module)
})

const hasExpandableItems = computed(() =>
  props.module.resources.length > 0 || props.module.childModules.length > 0,
)

function onModuleClick() {
  ctx.onModuleClick(props.module)
}

function onModuleDragOver() {
  ctx.onModuleDragOver(props.module)
}

function onModuleDragLeave() {
  ctx.onModuleDragLeave(props.module)
}

function onModuleDrop(event: DragEvent) {
  ctx.onModuleDrop(event, props.module)
}
</script>

<style scoped src="./planOutlineModule.css"></style>
