<template>
  <div class="mindmap-player">
    <!-- Toolbar -->
    <div class="flex items-center justify-between mb-3">
      <div>
        <h3 class="font-display text-lg font-semibold text-navy-800">{{ title || '思维导图' }}</h3>
      </div>
      <div class="flex items-center gap-2">
        <button
          class="p-1.5 rounded-lg text-navy-400 hover:text-navy-600 hover:bg-navy-50 transition-colors"
          title="适应画布"
          @click="fitView"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
          </svg>
        </button>
        <button
          class="p-1.5 rounded-lg text-navy-400 hover:text-navy-600 hover:bg-navy-50 transition-colors"
          title="居中"
          @click="centerView"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Map container -->
    <div
      ref="mapContainer"
      class="mindmap-container rounded-xl border border-navy-100/50 bg-white overflow-hidden"
      :class="{ 'bg-navy-50/30': !ready }"
    >
      <div v-if="!ready" class="flex items-center justify-center h-full text-navy-300 text-sm">
        思维导图加载中...
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import MindElixir from 'mind-elixir'
import type { MindElixirData, MindElixirInstance, NodeObj } from 'mind-elixir'
import 'mind-elixir/style'

const props = defineProps<{
  data: MindElixirData | null
  title?: string
}>()

const mapContainer = ref<HTMLElement | null>(null)
const ready = ref(false)
let mind: MindElixirInstance | null = null

// Navy-themed palette matching the app's design system
const NAVY_THEME = {
  name: 'navy',
  type: 'light' as const,
  palette: [
    '#34508e', // navy-600 (root)
    '#4164b2', // navy-500 (level 1)
    '#6783c1', // navy-400 (level 2)
    '#8da2d1', // navy-300 (level 3)
    '#649b64', // sage-500 (accent branch)
    '#c9873b', // accent (highlight branch)
    '#83af83', // sage-400
    '#507c50', // sage-600
  ],
  cssVar: {
    '--node-gap-x': '80px',
    '--node-gap-y': '12px',
    '--main-gap-x': '100px',
    '--main-gap-y': '20px',
    '--main-color': '#273c6b',
    '--main-bgcolor': '#f0f3f9',
    '--main-bgcolor-transparent': 'rgba(240, 243, 249, 0.8)',
    '--color': '#1a2847',
    '--bgcolor': '#ffffff',
    '--selected': 'rgba(65, 100, 178, 0.15)',
    '--accent-color': '#c9873b',
    '--root-color': '#ffffff',
    '--root-bgcolor': '#34508e',
    '--root-border-color': '#273c6b',
    '--root-radius': '10px',
    '--main-radius': '8px',
    '--topic-padding': '6px 12px',
    '--panel-color': '#1a2847',
    '--panel-bgcolor': '#f0f3f9',
    '--panel-border-color': '#d9e0f0',
    '--map-padding': '20px',
  },
}

function initMindMap() {
  if (!mapContainer.value || !props.data) return

  // Destroy previous instance
  if (mind) {
    mind.destroy()
    mind = null
  }

  mind = new MindElixir({
    el: mapContainer.value,
    direction: MindElixir.SIDE,
    editable: false,
    contextMenu: false,
    toolBar: false,
    keypress: false,
    overflowHidden: false,
    theme: NAVY_THEME,
  })

  // Ensure all nodes are expanded
  const data = expandAllNodes(props.data)

  mind.init(data)
  ready.value = true

  // Auto fit after a short delay to allow rendering
  nextTick(() => {
    setTimeout(() => {
      if (mind) {
        mind.scaleFit()
        mind.toCenter()
      }
    }, 100)
  })
}

function expandAllNodes(data: MindElixirData): MindElixirData {
  const expand = (node: NodeObj): NodeObj => ({
    ...node,
    expanded: true,
    children: node.children?.map(expand),
  })
  return {
    ...data,
    nodeData: expand(data.nodeData),
  }
}

function fitView() {
  mind?.scaleFit()
}

function centerView() {
  mind?.toCenter()
}

onMounted(() => {
  if (props.data) {
    initMindMap()
  }
})

onBeforeUnmount(() => {
  if (mind) {
    mind.destroy()
    mind = null
  }
})

watch(() => props.data, (newData) => {
  if (newData) {
    nextTick(() => initMindMap())
  }
}, { deep: true })
</script>

<style scoped>
.mindmap-player {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.mindmap-container {
  flex: 1;
  min-height: 450px;
  max-height: calc(100vh - 18rem);
}

/* Override MindElixir default styles to match app theme */
.mindmap-container :deep(.map-container) {
  background: #ffffff;
}

.mindmap-container :deep(.topic) {
  border-radius: 8px;
  padding: 6px 12px;
  font-family: 'Source Sans 3', 'Noto Sans SC', system-ui, sans-serif;
  font-size: 14px;
}

/* Root node styling */
.mindmap-container :deep(.root > .topic) {
  background: linear-gradient(135deg, #34508e, #4164b2);
  color: #ffffff;
  font-weight: 600;
  font-size: 15px;
  border-radius: 10px;
  padding: 8px 16px;
  box-shadow: 0 2px 8px rgba(52, 80, 142, 0.3);
}

/* Branch connections */
.mindmap-container :deep(.lines path) {
  stroke: #b3c1e0;
  stroke-width: 2;
}

/* Selected node highlight */
.mindmap-container :deep(.selected > .topic) {
  box-shadow: 0 0 0 2px rgba(65, 100, 178, 0.4);
}
</style>
