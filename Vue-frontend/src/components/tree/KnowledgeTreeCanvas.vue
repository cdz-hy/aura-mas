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
        v-for="item in visibleItems"
        :key="item.node.id"
        class="absolute"
        :style="nodeStyle(item)"
        :node="item.node"
        :selected="item.node.id === selectedNodeId"
        :has-children="childrenByParent.has(item.node.id)"
        :root-node-id="rootNodeId"
        @select="$emit('select', $event)"
        @toggle-collapse="$emit('toggle-collapse', $event)"
        @open-subdivide="$emit('open-subdivide', $event)"
        @drag-start="$emit('node-drag-start', $event)"
        @drag-end="$emit('node-drag-end')"
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
  getVisibleItems,
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
  'node-drag-start': [nodeId: string]
  'node-drag-end': []
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
/**
 * 仅在“整树首次加载/切换计划”时自动 fit 一次。
 * 流式生成（subdivide / first-principles 等增量推送新节点）期间保持 false，
 * 避免用户正在 pan/zoom 时视口被强行重新居中。
 * 切换计划时 rootNodeId 变化，会重新置 true 触发一次自动 fit。
 */
const autoFitEnabled = ref(true)
let resizeFitTimer: ReturnType<typeof setTimeout> | null = null

const layout = computed(() => props.rootNodeId ? buildTreeLayout(props.nodes, props.rootNodeId) : { items: [], edges: [] })

const visibleItems = computed(() => {
  const viewport = viewportRef.value
  if (!viewport || layout.value.items.length <= 50) {
    return layout.value.items
  }
  return getVisibleItems(
    layout.value.items,
    contentBounds.value,
    { panX: localPanX.value, panY: localPanY.value, zoom: localZoom.value, width: viewport.clientWidth, height: viewport.clientHeight },
    NODE_WIDTH,
    NODE_HEIGHT,
  )
})

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

// 可见节点的 id 集合，用于连线虚拟化：大树（>50 节点）时只渲染两端均在视口内的边。
// 小树时 visibleItems 等于全部 items，不产生过滤副作用。
const visibleNodeIds = computed(() => {
  if (layout.value.items.length <= 50) return null
  return new Set(visibleItems.value.map(item => item.node.id))
})

const edgePaths = computed(() => {
  const visible = visibleNodeIds.value
  return layout.value.edges
    .map(edge => {
      const from = itemByNodeId.value.get(edge.fromNodeId)
      const to = itemByNodeId.value.get(edge.toNodeId)
      if (!from || !to) return null
      // 大树虚拟化：两端节点都不在可见集合内时跳过该边
      if (visible && !visible.has(edge.fromNodeId) && !visible.has(edge.toNodeId)) return null
      if (edge.kind === 'main') {
        const startX = from.x
        const startY = from.y - NODE_HEIGHT / 2
        const endX = to.x
        const endY = to.y + NODE_HEIGHT / 2
        const midY = endY + (startY - endY) * 0.5
        return {
          ...edge,
          d: `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`,
        }
      }

      const side = to.x >= from.x ? 1 : -1
      const startX = from.x + side * (NODE_WIDTH / 2 - 8)
      const startY = from.y
      const endX = to.x - side * (NODE_WIDTH / 2 - 8)
      const endY = to.y
      const midX = startX + (endX - startX) * 0.5
      return {
        ...edge,
        d: `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`,
      }
    })
    .filter((edge): edge is NonNullable<typeof edge> => Boolean(edge))
})

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
  // resize 回调 debounce，避免连续 resize 触发 fit 风暴；且仅在 autoFit 启用时 fit
  resizeObserver = new ResizeObserver(() => {
    if (resizeFitTimer) clearTimeout(resizeFitTimer)
    resizeFitTimer = setTimeout(() => {
      if (autoFitEnabled.value) fitView()
    }, 200)
  })
  if (viewportRef.value) {
    resizeObserver.observe(viewportRef.value)
  }
  autoFitEnabled.value = true
  fitView()
})

onBeforeUnmount(() => {
  if (resizeFitTimer) {
    clearTimeout(resizeFitTimer)
    resizeFitTimer = null
  }
  resizeObserver?.disconnect()
  resizeObserver = null
})

// 切换计划时 rootNodeId 变化 → 重新启用一次自动 fit（整树首次加载场景）。
// autoFitEnabled 在 fitView() 完成后由 loadByPlan 流程或 fit 自身置 false，
// 因此流式增量推送（rootNodeId 不变）不会再触发自动 fit。
watch(() => props.rootNodeId, () => {
  autoFitEnabled.value = true
  fitView()
})

// 布局变化时只在 autoFitEnabled 为 true（整树首次加载）时 fit；
// 流式增量、用户折叠/展开不再抢视口。
watch(visibleLayoutKey, () => {
  if (autoFitEnabled.value) {
    fitView()
  }
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

  // 完成一次 fit 后关闭自动 fit，避免后续流式增量/折叠展开抢视口。
  // 手动"居中"按钮(centerView)与切换计划(watch rootNodeId)会重新触发 fit。
  autoFitEnabled.value = false
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
