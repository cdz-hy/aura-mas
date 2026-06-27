<template>
  <div class="pptx-viewer" ref="viewerEl">
    <!-- 工具栏 -->
    <div class="pptx-toolbar">
      <span class="pptx-slide-count" v-if="slideCount">共 {{ slideCount }} 页</span>
      <div class="pptx-toolbar-right">
        <a v-if="downloadUrl" class="pptx-download-btn" :href="downloadUrl" download>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
          下载 PPT
        </a>
        <button class="pptx-btn" @click="toggleFullscreen" title="全屏">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3"/></svg>
        </button>
      </div>
    </div>
    <!-- Office Online Viewer -->
    <div class="pptx-stage">
      <iframe
        class="pptx-iframe"
        :src="viewerUrl"
        frameborder="0"
        title="PPT 预览"
      ></iframe>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  pptxUrl: string
  slideCount?: number
  downloadUrl?: string
}>()

const viewerEl = ref<HTMLElement>()

const viewerUrl = computed(() => {
  if (!props.pptxUrl) return ''
  return `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(props.pptxUrl)}`
})

function toggleFullscreen() {
  if (!viewerEl.value) return
  if (document.fullscreenElement) {
    document.exitFullscreen()
  } else {
    viewerEl.value.requestFullscreen()
  }
}
</script>

<style scoped>
.pptx-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #f8f7ff;
  border-radius: 8px;
  overflow: hidden;
}

.pptx-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #f8f7ff;
  border-bottom: 1px solid #ede9fe;
}

.pptx-toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pptx-slide-count {
  font-size: 13px;
  color: #7c3aed;
  font-weight: 600;
  background: rgba(124, 58, 237, 0.08);
  padding: 4px 12px;
  border-radius: 12px;
}

.pptx-download-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
  color: white;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.2s;
}

.pptx-download-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
}

.pptx-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #6d28d9;
  cursor: pointer;
  transition: background 0.15s;
}

.pptx-btn:hover {
  background: rgba(124, 58, 237, 0.1);
}

.pptx-stage {
  flex: 1;
  min-height: 0;
}

.pptx-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.pptx-viewer:fullscreen {
  background: #f8f7ff;
  border-radius: 0;
}

.pptx-viewer:fullscreen .pptx-iframe {
  height: calc(100vh - 49px);
}
</style>
