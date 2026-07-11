<template>
  <div 
    class="fixed top-0 w-[420px] h-full bg-white shadow-[-8px_0_32px_rgba(26,40,71,0.1)] z-40 border-l border-navy-100/50 flex flex-col transition-all duration-300"
    :style="{ right: `calc(${baseOffset}px + ${index * 420}px)` }"
  >
    <!-- Header -->
    <div class="px-5 py-4 border-b border-navy-100/50 flex flex-col gap-2 bg-navy-50/50">
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2 min-w-0 flex-1">
           <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 flex-shrink-0">
             {{ resourceTypeLabel }}
           </span>
           <h3 class="font-display text-sm font-semibold text-navy-800 truncate" :title="resourceTitle">{{ resourceTitle }}</h3>
        </div>
        <button @click="emit('close')" class="p-1 flex-shrink-0 rounded text-navy-300 hover:text-navy-600 hover:bg-navy-100 transition-colors">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
      <!-- Plan Link -->
      <div v-if="planData" class="flex items-center gap-1.5 text-xs bg-white/60 rounded-md px-2.5 py-1.5 border border-navy-100/40 mt-1">
        <svg class="w-3 h-3 text-navy-400 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
        </svg>
        <span class="text-navy-400 font-medium flex-shrink-0">所属计划:</span>
        <router-link :to="`/plan/${planData.id}`" class="text-navy-600 hover:text-indigo-600 font-semibold truncate flex-1 flex items-center gap-1 group transition-colors" :title="planData.title">
          <span class="truncate">{{ planData.title }}</span>
          <svg class="w-3 h-3 flex-shrink-0 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 12h14"></path>
            <path d="m12 5 7 7-7 7"></path>
          </svg>
        </router-link>
      </div>
      <div v-else-if="loadingPlan" class="text-[11px] text-navy-300">加载计划信息...</div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-5 custom-scrollbar relative">
      <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
        <svg class="w-8 h-8 text-navy-200 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" class="opacity-25" /><path d="M4 12a8 8 0 018-8" class="opacity-75" stroke-linecap="round" />
        </svg>
      </div>
      
      <template v-else-if="resource">
        <template v-if="resource.moduleType === 'quiz'">
           <QuizPlayer :data="quizData" v-if="quizData" />
        </template>
        <template v-else-if="resource.moduleType === 'mindmap'">
           <MindmapPlayer :data="mindmapData" :title="resourceTitle" v-if="mindmapData" />
        </template>
        <template v-else-if="resource.moduleType === 'video'">
           <div class="space-y-4">
             <VideoPlayer v-for="(v, i) in (resource.moduleData?.videos || [])" :key="i" :video="v" />
           </div>
        </template>
        <template v-else-if="resource.moduleType === 'pptx'">
           <!-- 切换按钮 -->
           <div v-if="resource.moduleData?.pptx_url && resource.moduleData?.html" class="flex items-center justify-between px-1 py-2">
             <div class="flex items-center gap-1">
               <button
                 class="px-2 py-0.5 text-[11px] rounded-l border transition-colors"
                 :class="pptxViewMode === 'office' ? 'bg-violet-600 text-white border-violet-600' : 'bg-white text-navy-500 border-navy-200 hover:bg-navy-50'"
                 @click="pptxViewMode = 'office'"
               >Office</button>
               <button
                 class="px-2 py-0.5 text-[11px] rounded-r border border-l-0 transition-colors"
                 :class="pptxViewMode === 'html' ? 'bg-violet-600 text-white border-violet-600' : 'bg-white text-navy-500 border-navy-200 hover:bg-navy-50'"
                 @click="pptxViewMode = 'html'"
               >卡片</button>
             </div>
             <a
               v-if="resource.moduleData?.pptx_filename"
               :href="pptxDownloadUrl(resource.moduleData.pptx_filename)"
               download
               class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-white text-xs font-medium"
               style="background: linear-gradient(135deg, #7c3aed, #6d28d9)"
             >
               <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
               下载
             </a>
           </div>
           <!-- Office Online Viewer 预览 -->
           <div v-if="pptxViewMode === 'office' && resource.moduleData?.pptx_url" class="flex flex-col flex-1 min-h-0">
             <iframe
               class="flex-1 w-full border-none rounded"
               :src="`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(resource.moduleData.pptx_url)}`"
               title="PPT 预览"
             ></iframe>
           </div>
           <!-- HTML 卡片预览 -->
           <div v-else-if="resource.moduleData?.html" class="prose prose-sm max-w-none text-navy-700 leading-relaxed markdown-body" v-html="resource.moduleData.html"></div>
           <!-- 无可用预览 -->
           <div v-else class="text-center py-8 space-y-4">
             <div class="text-sm text-navy-500">
               共 {{ resource.moduleData?.slide_count || 0 }} 页幻灯片
             </div>
             <a
               v-if="resource.moduleData?.pptx_filename"
               :href="pptxDownloadUrl(resource.moduleData.pptx_filename)"
               download
               class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-medium"
               style="background: linear-gradient(135deg, #7c3aed, #6d28d9)"
             >
               <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
               下载 PPT
             </a>
             <p class="text-xs text-navy-400">PPT 预览链接不可用</p>
           </div>
        </template>
        <template v-else>
           <div class="prose prose-sm max-w-none text-navy-700 leading-relaxed markdown-body" v-html="renderedMarkdown"></div>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick, onMounted } from 'vue'
import { getResource } from '@/api/resource'
import { getPlan } from '@/api/plan'
import { parseMarkdown } from '@/utils/markdown'
import { PYTHON_AI_BASE } from '@/api/request'
import type { LearningResource, LearningPlan } from '@/types/plan'
import type { QuizData } from '@/types/quiz'
import type { MindElixirData } from 'mind-elixir'

// Dynamic imports for heavy players
import QuizPlayer from './QuizPlayer.vue'
import MindmapPlayer from './MindmapPlayer.vue'
import VideoPlayer from './VideoPlayer.vue'

function pptxDownloadUrl(filename: string) {
  return `${PYTHON_AI_BASE}/api/ai/resource/pptx/download/${filename}`
}

const props = defineProps<{
  resourceId: number
  index: number
  baseOffset: number
}>()

const emit = defineEmits(['close'])

const loading = ref(true)
const resource = ref<LearningResource | null>(null)
const planData = ref<LearningPlan | null>(null)
const loadingPlan = ref(false)
const pptxViewMode = ref<'office' | 'html'>('office')

const typeLabels: Record<string, string> = {
  document: '文档', text: '正文', mindmap: '导图', quiz: '题目', code: '代码', reading: '阅读', summary: '总结', video: '视频', image: '图片', diagram: '图表', animation: '动画', podcast: '播客',
}

const resourceTypeLabel = computed(() => {
  if (!resource.value) return '学习资源'
  return typeLabels[resource.value.moduleType] || resource.value.moduleType
})

const resourceTitle = computed(() => {
  if (!resource.value) return '加载中...'
  const data = resource.value.moduleData
  if (data?.title) return data.title
  if (data?.name) return data.name
  return `学习资源 #${resource.value.id}`
})

const renderedMarkdown = computed(() => {
  if (!resource.value?.moduleData?.content) return ''
  return parseMarkdown(resource.value.moduleData.content)
})

const quizData = computed<QuizData | null>(() => {
  if (resource.value?.moduleType === 'quiz' && resource.value.moduleData?.content) {
    try {
      if (typeof resource.value.moduleData.content === 'string') {
        return JSON.parse(resource.value.moduleData.content)
      }
      return resource.value.moduleData.content
    } catch {
      return null
    }
  }
  return null
})

const mindmapData = computed<MindElixirData | null>(() => {
  if (resource.value?.moduleType === 'mindmap') {
    const data = resource.value.moduleData?.nodeData || resource.value.moduleData?.content
    try {
      return typeof data === 'string' ? JSON.parse(data) : data
    } catch {
      return null
    }
  }
  return null
})

onMounted(async () => {
  loading.value = true
  try {
    const res = await getResource(props.resourceId)
    resource.value = res.data
    normalizeResourceData(resource.value)
    if (resource.value.moduleType !== 'mindmap' && resource.value.moduleType !== 'quiz' && resource.value.moduleType !== 'video') {
       renderMermaid()
    }

    // Fetch plan details
    if (resource.value.planId) {
      loadingPlan.value = true
      getPlan(resource.value.planId).then(p => {
        planData.value = p.data
      }).catch(console.error).finally(() => loadingPlan.value = false)
    }
  } catch (e) {
    console.error('Failed to load resource preview', e)
  } finally {
    loading.value = false
  }
})

watch(() => props.resourceId, () => {
  pptxViewMode.value = 'office'
})

function normalizeResourceData(r: LearningResource) {
  if (!r) return
  if (typeof r.moduleData === 'string') {
    try {
      r.moduleData = JSON.parse(r.moduleData)
    } catch {
      r.moduleData = { content: r.moduleData }
    }
  }
}

async function renderMermaid() {
  await nextTick()
  const unrendered = document.querySelectorAll('.gv-mermaid-wrapper:not([data-rendered="true"])')
  if (unrendered.length === 0) return
  
  try {
    const mermaid = (await import('mermaid')).default
    if (!(window as any).__mermaid_initialized__) {
      mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' })
      ;(window as any).__mermaid_initialized__ = true
    }
    
    for (const el of Array.from(unrendered)) {
      const codeBase64 = el.getAttribute('data-mermaid-code')
      if (!codeBase64) continue
      try {
        const rawCode = decodeURIComponent(codeBase64).replace(/[    　]/g, ' ').replace(/[​‌‍﻿]/g, '')
        const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`
        const { svg } = await mermaid.render(id, rawCode)
        el.innerHTML = svg
        el.setAttribute('data-rendered', 'true')
      } catch {
        el.innerHTML = '<div class="text-red-500 text-sm">图表渲染失败</div>'
      }
    }
  } catch (e) {
    console.error('Mermaid render error', e)
  }
}
</script>

<style scoped>
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
}
</style>
