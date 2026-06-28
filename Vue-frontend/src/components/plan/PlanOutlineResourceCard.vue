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
          <span
            v-if="resource.status === 1 && ctx.stuckResourceIds?.has(resource.resourceId)"
            class="plan-outline__status plan-outline__status--failed plan-outline__status--action"
            @click.stop="ctx.retryResource(resource.resourceId)"
          >
            重试
          </span>
          <span v-else class="plan-outline__status" :class="ctx.statusClass(resource.status)">
            {{ ctx.statusLabel(resource.status) }}
          </span>
        </div>
      </div>
    </div>

    <div
      v-if="resource.childResources.length > 0"
      class="plan-outline__child-resources"
    >
      <PlanOutlineResourceCard
        v-for="child in resource.childResources"
        :key="child.id"
        :resource="child"
      />
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import PlanOutlineResourceCard from './PlanOutlineResourceCard.vue'
import type { PlanOutlineResource } from './usePlanResourceOutline'
import { OUTLINE_CONTEXT_KEY, type OutlineContext } from './planOutlineContext'

const props = defineProps<{
  resource: PlanOutlineResource
}>()

const ctx = inject(OUTLINE_CONTEXT_KEY) as OutlineContext

const isActive = computed(() => props.resource.resourceId === ctx.selectedResourceId)
</script>

<style scoped src="./planOutlineModule.css"></style>
