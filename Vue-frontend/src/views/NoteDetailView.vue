<template>
  <div class="animate-fade-in-up">
    <!-- Top bar -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <button
          class="w-9 h-9 rounded-lg flex items-center justify-center text-navy-400 hover:bg-navy-50 hover:text-navy-600 transition-colors"
          @click="$router.push('/notes')"
        >
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div>
          <input
            v-model="noteName"
            class="text-xl font-display font-semibold text-navy-800 bg-transparent border-none outline-none w-full placeholder:text-navy-300"
            placeholder="笔记标题"
            @blur="autoSave"
          />
          <p class="text-xs text-navy-300 mt-0.5">
            {{ note ? `最后编辑于 ${formatDate(note.updatedAt)}` : '新建笔记' }}
            <span v-if="saving" class="ml-2 text-sage-500">保存中...</span>
            <span v-else-if="saved" class="ml-2 text-sage-500">已保存</span>
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button
          class="px-3 py-1.5 rounded-lg text-sm transition-all duration-200"
          :class="previewMode ? 'bg-navy-100 text-navy-700' : 'text-navy-400 hover:bg-navy-50 hover:text-navy-600'"
          @click="previewMode = !previewMode"
        >
          <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" />
          </svg>
          {{ previewMode ? '编辑' : '预览' }}
        </button>
        <button
          class="px-4 py-1.5 rounded-lg text-sm text-white bg-navy-600 hover:bg-navy-700 transition-colors"
          @click="saveNote"
        >
          保存
        </button>
      </div>
    </div>

    <!-- Editor / Preview area -->
    <div class="card overflow-hidden" style="height: calc(100vh - 220px)">
      <!-- Edit mode -->
      <div v-if="!previewMode" class="flex h-full">
        <textarea
          v-model="content"
          class="flex-1 p-8 text-navy-700 leading-relaxed resize-none outline-none font-body text-base"
          placeholder="开始书写你的笔记...&#10;&#10;支持 Markdown 语法：&#10;# 标题&#10;**粗体** *斜体*&#10;- 列表&#10;> 引用&#10;`代码`"
          @input="onInput"
          @keydown.ctrl.s.prevent="saveNote"
          @keydown.meta.s.prevent="saveNote"
        ></textarea>
      </div>

      <!-- Preview mode -->
      <div v-else class="h-full overflow-y-auto p-8">
        <div class="markdown-body max-w-3xl mx-auto" v-html="renderedContent"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import hljs from 'highlight.js'
import { getNotes, createNote, updateNote } from '@/api/note'
import type { Note } from '@/types/note'

const route = useRoute()
const router = useRouter()

const note = ref<Note | null>(null)
const noteName = ref('')
const content = ref('')
const previewMode = ref(false)
const saving = ref(false)
const saved = ref(false)
let saveTimer: ReturnType<typeof setTimeout> | null = null
let savedTimer: ReturnType<typeof setTimeout> | null = null

marked.setOptions({
  breaks: true,
  gfm: true,
} as any)

const renderedContent = computed(() => {
  return marked(content.value || '') as string
})

function formatDate(date: string) {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function onInput() {
  saved.value = false
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(autoSave, 3000)
}

async function autoSave() {
  if (!noteName.value.trim() && !content.value.trim()) return
  await saveNote()
}

async function saveNote() {
  if (saving.value) return
  saving.value = true
  try {
    const name = noteName.value.trim() || '无标题笔记'
    const body = content.value.trim() || ' '
    if (note.value?.id) {
      await updateNote(note.value.id, { noteName: name, content: body })
    } else {
      const res = await createNote({ noteName: name, content: body })
      // Reload to get the note with ID
      const id = (res as any)?.data?.id
      if (id) {
        router.replace(`/notes/${id}`)
      }
      await loadNote()
    }
    saved.value = true
    if (savedTimer) clearTimeout(savedTimer)
    savedTimer = setTimeout(() => { saved.value = false }, 2000)
  } catch (e) {
    console.error('Save note failed:', e)
  } finally {
    saving.value = false
  }
}

async function loadNote() {
  const id = route.params.id
  if (!id || id === 'new') {
    note.value = null
    noteName.value = ''
    content.value = ''
    return
  }
  try {
    const res = await getNotes({ page: 1, size: 100 })
    const notes = res.data?.records || []
    const found = notes.find((n: Note) => n.id === Number(id))
    if (found) {
      note.value = found
      noteName.value = found.noteName
      content.value = found.content
    } else {
      router.push('/notes')
    }
  } catch {
    router.push('/notes')
  }
}

onMounted(loadNote)

watch(() => route.params.id, (newId) => {
  if (newId) loadNote()
})
</script>
