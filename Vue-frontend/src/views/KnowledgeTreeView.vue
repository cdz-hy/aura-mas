<template>
  <div v-if="!hasValidPlanId" class="flex h-full min-h-0 flex-col">
    <div class="flex flex-shrink-0 items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-display font-semibold text-navy-800">知识树</h1>
        <p class="mt-1 text-xs text-navy-400">请先从学习计划进入知识树</p>
      </div>
      <button class="btn-secondary h-9 px-3 py-0 text-sm" @click="router.push('/plan/create')">
        返回学习计划
      </button>
    </div>
    <div class="mt-3 flex flex-1 items-center justify-center rounded-lg border border-navy-100 bg-white text-sm text-navy-400">
      当前页面缺少有效计划
    </div>
  </div>

  <div v-else class="flex h-full min-h-0 flex-col gap-3">
    <div class="flex flex-shrink-0 items-center justify-between gap-3">
      <div class="min-w-0">
        <h1 class="truncate text-xl font-display font-semibold text-navy-800">
          {{ store.tree?.title || '知识树' }}
        </h1>
        <p class="mt-1 truncate text-xs text-navy-400">
          {{ store.tree?.field || store.tree?.currentProblem || `计划 #${planId}` }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button
          class="h-9 rounded-lg px-3 text-sm font-medium text-navy-500 hover:bg-navy-50"
          @click="router.push(`/plan/${planId}`)"
        >
          返回计划
        </button>
        <button class="btn-secondary h-9 px-3 py-0 text-sm" :disabled="store.loading" @click="loadTree">
          刷新
        </button>
      </div>
    </div>

    <div v-if="store.error" class="flex-shrink-0 rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">
      {{ store.error }}
    </div>

    <div class="flex min-h-0 flex-1 flex-col gap-3 xl:flex-row">
      <div class="relative min-h-[360px] min-w-0 flex-1 xl:min-h-0">
        <KnowledgeTreeCanvas
          :nodes="store.nodes"
          :root-node-id="rootNodeId"
          :selected-node-id="store.currentNodeId"
          v-model:pan-x="store.panX"
          v-model:pan-y="store.panY"
          v-model:zoom="store.zoom"
          @select="store.selectNode"
          @toggle-collapse="store.toggleCollapsed"
          @subdivide="handleSubdivide"
          @first-principles="handleFirstPrinciples"
        />
        <div v-if="store.loading && !store.activeSource" class="absolute inset-0 flex items-center justify-center rounded-lg bg-white/60">
          <svg class="h-8 w-8 animate-spin text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" class="opacity-25" />
            <path d="M4 12a8 8 0 0 1 8-8" class="opacity-75" stroke-linecap="round" />
          </svg>
        </div>
      </div>

      <div class="h-[320px] flex-shrink-0 xl:h-full">
        <TreeChatPanel :selected-node="selectedNode" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import KnowledgeTreeCanvas from '@/components/tree/KnowledgeTreeCanvas.vue'
import TreeChatPanel from '@/components/tree/TreeChatPanel.vue'
import { useKnowledgeTreeStore } from '@/stores/knowledgeTree'

const props = defineProps<{
  planId?: string | number
}>()

const router = useRouter()
const store = useKnowledgeTreeStore()

const numericPlanId = computed(() => Number(props.planId))
const hasValidPlanId = computed(() => props.planId !== undefined && Number.isFinite(numericPlanId.value))
const planId = computed(() => Number.isFinite(numericPlanId.value) ? numericPlanId.value : props.planId)
const rootNodeId = computed(() => {
  const root = store.nodes.find(node => !node.parentId)
  return root?.id || store.nodes[0]?.id || null
})
const selectedNode = computed(() => store.nodes.find(node => node.id === store.currentNodeId) || null)

onMounted(loadTree)

watch(() => props.planId, () => {
  loadTree()
})

async function loadTree() {
  if (!hasValidPlanId.value) return
  await store.loadByPlan(numericPlanId.value)
}

async function handleSubdivide(nodeId: string) {
  const selected = await store.selectNode(nodeId)
  if (!selected || store.currentNodeId !== nodeId) return
  await store.subdivideCurrent('按学习顺序拆分')
}

async function handleFirstPrinciples(nodeId: string) {
  const selected = await store.selectNode(nodeId)
  if (!selected || store.currentNodeId !== nodeId) return
  await store.firstPrinciplesCurrent()
}
</script>
