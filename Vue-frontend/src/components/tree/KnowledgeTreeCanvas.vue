<template>
  <div
    ref="viewportRef"
    class="tree-canvas relative h-full w-full overflow-hidden rounded-lg border border-navy-100 bg-white"
    @wheel.prevent="onWheel"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="endPan"
    @pointercancel="endPan"
    @pointerleave="endPan"
  >
    <div class="absolute bottom-4 left-1/2 z-10 flex -translate-x-1/2 items-center gap-2 rounded-lg border border-navy-100 bg-white/90 px-2 py-1 shadow-paper backdrop-blur">
      <button class="toolbar-button" title="缩小" @click="adjustZoom(-0.1)">
        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14" /></svg>
      </button>
      <span class="w-12 text-center text-xs font-semibold text-navy-500">{{ Math.round(localZoom * 100) }}%</span>
      <button class="toolbar-button" title="放大" @click="adjustZoom(0.1)">
        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14" /><path d="M5 12h14" /></svg>
      </button>
      <button class="toolbar-button" title="居中" @click="centerView">
        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3" /><path d="M12 2v3" /><path d="M12 19v3" /><path d="M2 12h3" /><path d="M19 12h3" /></svg>
      </button>
    </div>

    <div v-if="layout.items.length === 0" class="flex h-full items-center justify-center text-sm text-navy-300">
      暂无知识树节点
    </div>

    <div
      v-else
      class="absolute left-1/2 top-1/2 origin-top-left"
      :style="stageStyle"
    >
      <svg class="absolute overflow-visible" :style="svgStyle" :viewBox="svgViewBox">
        <path
          v-for="edge in edgePaths"
          :key="`${edge.fromNodeId}-${edge.toNodeId}`"
          :d="edge.d"
          fill="none"
          :stroke="edge.kind === 'main' ? '#4164b2' : '#9aa9bd'"
          :stroke-width="edge.kind === 'main' ? 2 : 1.5"
          stroke-linecap="round"
        />
      </svg>

      <KnowledgeTreeNode
        v-for="item in layout.items"
        :key="item.node.id"
        class="absolute"
        :style="nodeStyle(item)"
        :node="item.node"
        :selected="item.node.id === selectedNodeId"
        :has-children="childrenByParent.has(item.node.id)"
        @select="$emit('select', $event)"
        @toggle-collapse="$emit('toggle-collapse', $event)"
        @open-subdivide="$emit('open-subdivide', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import KnowledgeTreeNode from './KnowledgeTreeNode.vue'
import {
  buildTreeLayout,
  fitTreeViewport,
  getTreeLayoutBounds,
  type TreeLayoutItem,
} from './useTreeLayout'
import type { KnowledgeNode } from '@/types/knowledgeTree'

const NODE_WIDTH = 236
const NODE_HEIGHT = 172
const MIN_ZOOM = 0.35
const MAX_ZOOM = 1.6
const FIT_PADDING_X = 96
const FIT_PADDING_Y = 120

const props = defineProps<{
  nodes: KnowledgeNode[]
  rootNodeId: string | null
  selectedNodeId: string | null
  panX?: number
  panY?: number
  zoom?: number
}>()

const emit = defineEmits<{
  select: [nodeId: string]
  'toggle-collapse': [nodeId: string]
  'open-subdivide': [nodeId: string]
  'update:panX': [value: number]
  'update:panY': [value: number]
  'update:zoom': [value: number]
}>()

const viewportRef = ref<HTMLElement | null>(null)
const localPanX = ref(props.panX ?? 0)
const localPanY = ref(props.panY ?? 0)
const localZoom = ref(clampZoom(props.zoom ?? 1))
const panning = ref(false)
const lastPointer = ref({ x: 0, y: 0 })
let resizeObserver: ResizeObserver | null = null

const layout = computed(() => props.rootNodeId ? buildTreeLayout(props.nodes, props.rootNodeId) : { items: [], edges: [] })

const childrenByParent = computed(() => {
  const map = new Map<string, KnowledgeNode[]>()
  for (const node of props.nodes) {
    if (!node.parentId) continue
    const siblings = map.get(node.parentId) || []
    siblings.push(node)
    map.set(node.parentId, siblings)
  }
  return map
})

const itemByNodeId = computed(() => new Map(layout.value.items.map(item => [item.node.id, item])))

const contentBounds = computed(() => getTreeLayoutBounds(layout.value.items, NODE_WIDTH, NODE_HEIGHT))

const visibleLayoutKey = computed(() => layout.value.items
  .map(item => `${item.node.id}:${item.x}:${item.y}:${item.node.collapsed ? 1 : 0}`)
  .join('|'))

const svgBounds = computed(() => {
  const padding = 180
  const bounds = getTreeLayoutBounds(layout.value.items, NODE_WIDTH, NODE_HEIGHT)
  return {
    minX: bounds.minX - padding,
    minY: bounds.minY - padding,
    width: bounds.width + padding * 2,
    height: bounds.height + padding * 2,
  }
})

const edgePaths = computed(() => layout.value.edges
  .map(edge => {
    const from = itemByNodeId.value.get(edge.fromNodeId)
    const to = itemByNodeId.value.get(edge.toNodeId)
    if (!from || !to) return null
    const startX = from.x
    const startY = from.y + NODE_HEIGHT / 2
    const endX = to.x
    const endY = to.y - NODE_HEIGHT / 2
    const midY = startY + Math.max(40, (endY - startY) * 0.45)
    return {
      ...edge,
      d: `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`,
    }
  })
  .filter((edge): edge is NonNullable<typeof edge> => Boolean(edge)))

const stageStyle = computed(() => ({
  transform: `translate(${localPanX.value}px, ${localPanY.value}px) scale(${localZoom.value})`,
}))

const svgStyle = computed(() => ({
  left: `${svgBounds.value.minX}px`,
  top: `${svgBounds.value.minY}px`,
  width: `${svgBounds.value.width}px`,
  height: `${svgBounds.value.height}px`,
}))

const svgViewBox = computed(() => `${svgBounds.value.minX} ${svgBounds.value.minY} ${svgBounds.value.width} ${svgBounds.value.height}`)

watch(() => props.panX, value => {
  if (typeof value === 'number') localPanX.value = value
})

watch(() => props.panY, value => {
  if (typeof value === 'number') localPanY.value = value
})

watch(() => props.zoom, value => {
  if (typeof value === 'number') localZoom.value = clampZoom(value)
})

onMounted(() => {
  resizeObserver = new ResizeObserver(() => fitView())
  if (viewportRef.value) {
    resizeObserver.observe(viewportRef.value)
  }
  fitView()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
})

watch(visibleLayoutKey, () => {
  fitView()
})

function nodeStyle(item: TreeLayoutItem) {
  return {
    transform: `translate(${item.x - NODE_WIDTH / 2}px, ${item.y - NODE_HEIGHT / 2}px)`,
  }
}

function onWheel(event: WheelEvent) {
  const delta = event.deltaY > 0 ? -0.08 : 0.08
  adjustZoom(delta)
}

function adjustZoom(delta: number) {
  setZoom(localZoom.value + delta)
}

function setZoom(value: number) {
  localZoom.value = clampZoom(value)
  emit('update:zoom', localZoom.value)
}

function onPointerDown(event: PointerEvent) {
  if ((event.target as HTMLElement).closest('button')) return
  panning.value = true
  lastPointer.value = { x: event.clientX, y: event.clientY }
  viewportRef.value?.setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent) {
  if (!panning.value) return
  const dx = event.clientX - lastPointer.value.x
  const dy = event.clientY - lastPointer.value.y
  lastPointer.value = { x: event.clientX, y: event.clientY }
  localPanX.value += dx
  localPanY.value += dy
  emit('update:panX', localPanX.value)
  emit('update:panY', localPanY.value)
}

function endPan(event: PointerEvent) {
  if (!panning.value) return
  panning.value = false
  if (viewportRef.value?.hasPointerCapture(event.pointerId)) {
    viewportRef.value.releasePointerCapture(event.pointerId)
  }
}

function centerView() {
  fitView()
}

async function fitView() {
  await nextTick()

  const viewport = viewportRef.value
  if (!viewport || layout.value.items.length === 0) return

  const nextFit = fitTreeViewport(
    contentBounds.value,
    viewport.clientWidth,
    viewport.clientHeight,
    FIT_PADDING_X,
    FIT_PADDING_Y,
    MIN_ZOOM,
    MAX_ZOOM,
  )

  localZoom.value = nextFit.zoom
  localPanX.value = nextFit.panX
  localPanY.value = nextFit.panY
  emit('update:panX', localPanX.value)
  emit('update:panY', localPanY.value)
  emit('update:zoom', localZoom.value)
}

function clampZoom(value: number) {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value))
}
</script>

<style scoped>
.tree-canvas {
  background-image:
    linear-gradient(rgba(26, 40, 71, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(26, 40, 71, 0.045) 1px, transparent 1px);
  background-size: 28px 28px;
}

.toolbar-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  color: rgb(71 85 105);
  transition: background-color 0.18s ease, color 0.18s ease;
}

.toolbar-button:hover {
  background: rgb(241 245 249);
  color: rgb(30 41 59);
}
</style>
