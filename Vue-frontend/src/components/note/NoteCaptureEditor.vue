<template>
  <!--
    Flex column with capped height so many 来源 rows scroll inside the body,
    while the action bar (保存) stays pinned at the bottom of the card.
  -->
  <div class="note-capture-editor mx-3 mt-2 rounded-xl border border-navy-100 bg-white overflow-hidden flex flex-col max-h-[min(58vh,32rem)]">
    <!-- Mode tabs (fixed) -->
    <div class="flex items-center gap-1 px-3 pt-3 pb-1 flex-shrink-0" role="tablist" aria-label="笔记模式">
      <div class="inline-flex p-0.5 rounded-lg bg-navy-50">
        <button
          v-for="tab in modeTabs"
          :key="tab.value"
          type="button"
          role="tab"
          class="px-2.5 py-1 text-xs rounded-md font-medium transition-colors"
          :class="mode === tab.value
            ? 'bg-white text-navy-800 shadow-sm'
            : 'text-navy-500 hover:text-navy-700'"
          :aria-selected="mode === tab.value"
          @click="emit('update:mode', tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>
      <button
        type="button"
        class="ml-auto text-xs text-navy-400 hover:text-navy-600 px-1.5 py-1 rounded-md hover:bg-navy-50 transition-colors"
        aria-label="收起编辑"
        @click="emit('collapse')"
      >
        收起
      </button>
    </div>

    <!-- Scrollable body: sources + title + content -->
    <div class="px-3 pt-2 pb-2 space-y-2.5 flex-1 min-h-0 overflow-y-auto overscroll-contain">
      <!-- Sources: compact + capped height when many -->
      <div v-if="sourceList.length > 0" class="space-y-1">
        <div class="flex items-center gap-1 px-0.5">
          <span class="text-[11px] text-navy-400">来源</span>
          <span class="text-[10px] text-navy-300">· {{ sourceList.length }} 段</span>
          <span
            v-if="sourceList.length > sourceScrollThreshold"
            class="text-[10px] text-navy-300 ml-auto"
          >
            可滚动
          </span>
        </div>
        <div
          class="space-y-1 overflow-y-auto overscroll-contain pr-0.5"
          :class="sourceListScrollClass"
          role="list"
          aria-label="笔记来源列表"
        >
          <div
            v-for="(s, idx) in sourceList"
            :key="s.key"
            role="listitem"
            class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-navy-50/80 border border-navy-100"
          >
            <span class="text-[10px] text-navy-300 flex-shrink-0 tabular-nums w-3 text-right">{{ idx + 1 }}</span>
            <div class="min-w-0 flex-1">
              <button
                v-if="s.sourceRoute"
                type="button"
                class="text-[11px] text-navy-600 truncate w-full font-medium text-left hover:text-navy-800 hover:underline underline-offset-2 leading-snug"
                :title="sourceRowTitle(s)"
                @click="emit('open-source', s.sourceRoute!)"
              >
                {{ s.sourceTitle }}
              </button>
              <span
                v-else
                class="text-[11px] text-navy-600 truncate block font-medium leading-snug"
                :title="sourceRowTitle(s)"
              >
                {{ s.sourceTitle }}
              </span>
            </div>
            <button
              v-if="sourceList.length === 1 && source && !excerptCount"
              type="button"
              class="text-[11px] text-navy-400 hover:text-navy-600 flex-shrink-0 px-1"
              aria-label="移除来源"
              @click="emit('remove-source')"
            >
              移除
            </button>
          </div>
        </div>
      </div>

      <!-- Compact optional title -->
      <div class="flex items-center gap-2 px-0.5">
        <span class="text-[11px] text-navy-400 flex-shrink-0">标题</span>
        <input
          :value="draft?.noteName ?? ''"
          class="flex-1 min-w-0 text-xs text-navy-700 bg-transparent outline-none placeholder:text-navy-300 py-0.5 border-b border-transparent focus:border-navy-200 transition-colors"
          placeholder="可选，不填则自动命名"
          @input="onTitleInput"
        />
      </div>

      <!-- Content -->
      <div class="rounded-lg bg-white border border-navy-100 focus-within:border-navy-300 transition-colors">
        <label class="block text-[11px] font-medium text-navy-400 px-3 pt-2">
          笔记正文
          <span v-if="excerptCount > 0" class="text-navy-400 font-normal">· {{ excerptCount }} 段原文</span>
        </label>
        <textarea
          ref="contentRef"
          :value="draft?.content ?? ''"
          class="w-full text-sm text-navy-600 bg-transparent outline-none resize-y leading-relaxed placeholder:text-navy-300 px-3 pb-2.5 pt-1 max-h-40"
          :class="excerptCount > 1 ? 'min-h-[7rem]' : 'min-h-[5.5rem]'"
          :placeholder="contentPlaceholder"
          @input="onContentInput"
        />
      </div>
    </div>

    <!-- Actions: always pinned at bottom of the card -->
    <div class="flex-shrink-0 px-3 py-2 border-t border-navy-50 bg-white">
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-1 min-w-0 overflow-hidden">
          <button
            v-if="draft && draft.id > 0"
            type="button"
            class="text-[11px] text-navy-500 hover:text-navy-700 px-1.5 py-1 rounded-md hover:bg-navy-50 transition-colors whitespace-nowrap truncate max-w-[5.5rem]"
            title="打开完整笔记"
            @click="emit('open-full')"
          >
            完整笔记
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap flex-shrink-0"
            :class="canOrganize
              ? 'text-navy-700 bg-navy-100 hover:bg-navy-200'
              : 'text-navy-300 bg-navy-50'"
            :disabled="!canOrganize || organizing"
            @click="emit('organize')"
          >
            <svg v-if="organizing" class="w-3 h-3 animate-spin flex-shrink-0" viewBox="0 0 24 24" fill="none">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v3a5 5 0 00-5 5H4z" />
            </svg>
            <svg v-else class="w-3 h-3 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
            </svg>
            {{ organizeButtonLabel }}
          </button>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-1 text-[11px] px-3 py-1.5 rounded-lg font-medium transition-all disabled:opacity-45 disabled:cursor-not-allowed flex-shrink-0 whitespace-nowrap"
          :class="saveButtonClass"
          :disabled="!canSave || saveStatus === 'saving'"
          :aria-label="saveButtonLabel"
          @click="onSaveClick"
        >
          <svg
            v-if="saveStatus === 'saving'"
            class="w-3 h-3 animate-spin flex-shrink-0"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v3a5 5 0 00-5 5H4z" />
          </svg>
          <svg
            v-else-if="saveStatus === 'saved'"
            class="w-3 h-3 flex-shrink-0"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
          >
            <path d="M20 6L9 17l-5-5" />
          </svg>
          {{ saveButtonLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { NoteCaptureMode, NoteCaptureSource } from '@/stores/noteCapture'
import type { NoteDraftState, NoteSaveStatus } from './useNoteDraft'
import { collectContentSources, collectExcerptTexts } from './noteBlocks'

const props = defineProps<{
  draft: NoteDraftState | null
  mode: NoteCaptureMode
  source: NoteCaptureSource | null
  excerpt: string
  saveStatus: NoteSaveStatus
  statusLabel: string
  organizing?: boolean
  organizeError?: boolean
}>()

const emit = defineEmits<{
  'update:mode': [mode: NoteCaptureMode]
  'update:fields': [patch: { noteName?: string; content?: string }]
  'remove-source': []
  'open-source': [route: string]
  collapse: []
  organize: []
  save: []
  'retry-save': []
  'open-full': []
}>()

const contentRef = ref<HTMLTextAreaElement | null>(null)

const modeTabs: { value: NoteCaptureMode; label: string }[] = [
  { value: 'excerpt', label: '摘录' },
  { value: 'quick', label: '速记' },
  { value: 'question', label: '问题' },
]

const excerptCount = computed(() => collectExcerptTexts(props.draft?.content).length)

/** Show "可滚动" and cap list height when more than this many sources. */
const sourceScrollThreshold = 3

/** One entry per 原文 fence; fall back to active capture source when no fences. */
const sourceList = computed(() => {
  const fromContent = collectContentSources(props.draft?.content)
  if (fromContent.length > 0) return fromContent
  if (!props.source?.sourceTitle) return []
  return [{
    key: `active|${props.source.sourceTitle}|${props.source.sourceRoute || ''}`,
    sourceTitle: props.source.sourceTitle,
    sourceRoute: props.source.sourceRoute || undefined,
    excerptPreview: '',
  }]
})

/** Cap source list height so it never eats the save bar. */
const sourceListScrollClass = computed(() => {
  const n = sourceList.value.length
  if (n <= 2) return 'max-h-none'
  if (n <= sourceScrollThreshold) return 'max-h-[5.5rem]'
  return 'max-h-[6.75rem]'
})

function sourceRowTitle(s: { sourceTitle: string; excerptPreview?: string }): string {
  const preview = s.excerptPreview?.trim()
  if (preview) return `${s.sourceTitle}\n${preview}`
  return s.sourceTitle
}

const contentPlaceholder = computed(() => {
  switch (props.mode) {
    case 'excerpt':
      return '原文块已插入正文；在块后继续写你的理解…'
    case 'question':
      return '在原文附近写下你的问题…'
    default:
      return '书写笔记（可与原文穿插）…'
  }
})

const canOrganize = computed(() => {
  if (!props.draft) return false
  if (props.draft.id <= 0) return false
  return Boolean(props.draft.content?.trim())
})

const organizeButtonLabel = computed(() => {
  if (props.organizing) return '整理中…'
  if (props.organizeError) return '重试整理'
  return '整理成笔记'
})

const canSave = computed(() => {
  if (!props.draft) return false
  // Allow save when dirty, errored, or brand-new draft with any content/title/excerpt
  if (props.saveStatus === 'dirty' || props.saveStatus === 'error') return true
  if (props.saveStatus === 'idle' && props.draft.id === 0) {
    return Boolean(
      props.draft.noteName?.trim()
      || props.draft.content?.trim()
      || props.excerpt?.trim()
      || props.draft.excerpt?.trim(),
    )
  }
  return false
})

const saveButtonLabel = computed(() => {
  if (props.saveStatus === 'saving') return '保存中'
  if (props.saveStatus === 'error') return '重试保存'
  if (props.saveStatus === 'saved') return '已保存'
  return '保存'
})

const saveButtonClass = computed(() => {
  if (props.saveStatus === 'error') {
    return 'text-navy-700 bg-navy-100 hover:bg-navy-200'
  }
  if (props.saveStatus === 'saved') {
    return 'text-navy-500 bg-navy-50'
  }
  if (props.saveStatus === 'saving') {
    return 'text-navy-500 bg-navy-50'
  }
  if (canSave.value) {
    return 'text-white bg-navy-700 hover:bg-navy-800'
  }
  return 'text-navy-300 bg-navy-50'
})

function onSaveClick() {
  if (props.saveStatus === 'error') {
    emit('retry-save')
    return
  }
  emit('save')
}

function onTitleInput(e: Event) {
  emit('update:fields', { noteName: (e.target as HTMLInputElement).value })
}

function onContentInput(e: Event) {
  emit('update:fields', { content: (e.target as HTMLTextAreaElement).value })
}

async function focusContent() {
  await nextTick()
  contentRef.value?.focus()
}

async function scrollContentToEnd() {
  await nextTick()
  const el = contentRef.value
  if (!el) return
  el.focus()
  el.scrollTop = el.scrollHeight
  const len = el.value.length
  el.selectionStart = len
  el.selectionEnd = len
}

watch(
  () => props.excerpt,
  (val, prev) => {
    if (val && val !== prev) void scrollContentToEnd()
  },
)

watch(
  () => props.draft?.content,
  (val, prev) => {
    // 新追加原文后滚到底，立刻看到新增 fence
    if (val && val !== prev && (val?.length || 0) > (prev?.length || 0)) {
      void scrollContentToEnd()
    }
  },
)

defineExpose({ focusContent, scrollContentToEnd })
</script>
