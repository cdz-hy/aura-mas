<template>
  <div
    class="note-list-item group relative p-3 rounded-xl border border-navy-100/80 bg-white
           hover:border-navy-200 hover:bg-navy-50/40
           cursor-pointer transition-colors duration-150"
    role="button"
    tabindex="0"
    @click="emit('open')"
    @keydown.enter.prevent="emit('open')"
  >
    <div class="min-w-0">
      <div class="flex items-center gap-1.5 mb-1">
        <span class="text-[10px] font-medium px-1.5 py-0.5 rounded bg-navy-50 text-navy-500">
          {{ typeLabel }}
        </span>
        <span
          v-if="statusChip"
          class="text-[10px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-400"
        >
          {{ statusChip }}
        </span>
        <span
          v-if="isError"
          class="text-[10px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-500"
        >
          异常
        </span>
      </div>

      <p class="text-[13px] font-medium text-navy-800 truncate leading-snug">
        {{ displayTitle }}
      </p>

      <p
        v-if="preview"
        class="text-[12px] mt-1 line-clamp-2 leading-relaxed text-navy-400"
      >
        {{ preview }}
      </p>

      <div class="flex items-center gap-2 mt-2 text-[11px] text-navy-300">
        <button
          v-if="sourceLabel"
          type="button"
          class="inline-flex items-center gap-1 min-w-0 truncate max-w-[58%]
                 px-1.5 py-0.5 rounded text-left transition-colors"
          :class="sourceRoute
            ? 'text-navy-500 hover:text-navy-700 hover:bg-navy-50 cursor-pointer'
            : 'text-navy-400 cursor-default'"
          :title="sourceRoute ? `打开来源：${sourceLabel}` : sourceLabel"
          :disabled="!sourceRoute"
          @click.stop="onSourceClick"
        >
          <svg class="w-3 h-3 flex-shrink-0 opacity-60" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
          <span class="truncate">{{ sourceLabel }}</span>
        </button>
        <span v-if="flashcardCount && flashcardCount > 0" class="flex-shrink-0 text-navy-400">
          闪卡 {{ flashcardCount }}
        </span>
        <span class="ml-auto flex-shrink-0 tabular-nums">{{ updatedAtLabel }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Note } from '@/types/note'
import {
  effectiveOrganizeStatus,
  isErrorDumpContent,
  noteListPreview,
  noteTypeLabel,
  organizeStatusLabel,
} from './notePresentation'

const props = defineProps<{
  note: Note
  sourceLabel?: string | null
  sourceRoute?: string | null
  flashcardCount?: number
}>()

const emit = defineEmits<{
  open: []
  'open-source': [route: string]
}>()

const typeLabel = computed(() => noteTypeLabel(props.note.noteType))
const isError = computed(() => isErrorDumpContent(props.note.content))

const statusChip = computed(() => {
  const status = effectiveOrganizeStatus(props.note.organizeStatus)
  if (status === 'pending') return null
  return organizeStatusLabel(status)
})

const displayTitle = computed(() => {
  const name = props.note.noteName?.trim()
  if (name && name !== '无标题笔记') return name
  const preview = noteListPreview(props.note, 36)
  return preview || '无标题笔记'
})

const preview = computed(() => noteListPreview(props.note))

const updatedAtLabel = computed(() => {
  const value = props.note.updatedAt
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
})

function onSourceClick() {
  if (!props.sourceRoute) return
  emit('open-source', props.sourceRoute)
}
</script>
