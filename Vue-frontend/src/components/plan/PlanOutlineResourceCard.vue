<template>
  <article
    class="plan-outline__card plan-outline__card--resource"
    :class="{ 'plan-outline__card--active': isActive }"
    :draggable="ctx.treeDnD"
    @click.stop="ctx.selectResource(resource.resourceId)"
    @dragstart="ctx.onResourceDragStart($event, resource.resourceId, resource.title)"
  >
    <div class="plan-outline__card-head">
      <span
        class="plan-outline__index plan-outline__index--resource"
        :class="{ 'plan-outline__index--active': isActive }"
      >
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M4 2.5h6.5L13 5v8.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1Z" />
          <path d="M10 2.5V5h3" stroke-linecap="round" />
        </svg>
      </span>
      <div class="plan-outline__card-body">
        <p class="plan-outline__title" :title="resource.title">{{ resource.title }}</p>
        <div class="plan-outline__meta-row">
          <span class="plan-outline__tag" :class="ctx.tagClass(resource.resourceType)">
            {{ ctx.typeLabel(resource.resourceType) }}
          </span>
        </div>
      </div>

      <div class="plan-outline__actions">
        <span
          v-if="resource.status === 1 && ctx.stuckResourceIds?.has(resource.resourceId)"
          class="plan-outline__status plan-outline__status--failed plan-outline__status--action"
          @click.stop="ctx.retryResource(resource.resourceId)"
        >
          重试
        </span>
        <button
          v-else-if="completionStatus === 2"
          class="plan-outline__complete-btn plan-outline__complete-btn--done"
          title="点击取消完成"
          @click.stop="ctx.toggleComplete(resource.resourceId)"
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M3 8.5l3.5 3.5L13 4" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          已完成
        </button>
        <button
          v-else-if="resource.status >= 2"
          class="plan-outline__complete-btn"
          title="点击标记完成"
          @click.stop="ctx.toggleComplete(resource.resourceId)"
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <circle cx="8" cy="8" r="6" />
          </svg>
          完成
        </button>
        <span v-else class="plan-outline__status" :class="ctx.statusClass(resource.status)">
          {{ ctx.statusLabel(resource.status) }}
        </span>

        <button
          v-if="resource.status >= 2"
          class="plan-outline__delete-btn"
          title="删除资源"
          @click.stop="ctx.deleteResource(resource.resourceId)"
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <path d="M5 3V2.5A1.5 1.5 0 0 1 6.5 1h3A1.5 1.5 0 0 1 11 2.5V3m1.5 0h-9a1 1 0 0 0-1 1v.5h11V4a1 1 0 0 0-1-1ZM4.5 5.5v7a1.5 1.5 0 0 0 1.5 1.5h4a1.5 1.5 0 0 0 1.5-1.5v-7" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import type { PlanOutlineResource } from './usePlanResourceOutline'
import { OUTLINE_CONTEXT_KEY, type OutlineContext } from './planOutlineContext'

const props = defineProps<{
  resource: PlanOutlineResource
}>()

const ctx = inject(OUTLINE_CONTEXT_KEY) as OutlineContext

const isActive = computed(() => props.resource.resourceId === ctx.selectedResourceId)
const completionStatus = computed(() => ctx.progressMap?.[props.resource.resourceId] ?? 0)
</script>

<style scoped src="./planOutlineModule.css"></style>
