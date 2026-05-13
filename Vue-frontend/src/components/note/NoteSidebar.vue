<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="px-4 py-3 border-b border-navy-100/50 flex items-center justify-between">
      <h3 class="font-display text-base font-semibold text-navy-800">笔记</h3>
      <button class="w-7 h-7 rounded-lg flex items-center justify-center text-navy-400 hover:bg-navy-50 hover:text-navy-600 transition-colors" @click="createNote">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </button>
    </div>

    <!-- Drop zone -->
    <div
      class="mx-3 mt-3 p-3 border-2 border-dashed rounded-xl text-center transition-all"
      :class="isDragOver ? 'border-navy-400 bg-navy-50' : 'border-navy-200 bg-navy-50/30'"
      @dragover.prevent="isDragOver = true"
      @dragleave="isDragOver = false"
      @drop="handleDrop"
    >
      <svg class="w-5 h-5 mx-auto mb-1 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
      </svg>
      <p class="text-xs text-navy-400">{{ isDragOver ? '松开添加到笔记' : '拖拽内容到此处' }}</p>
    </div>

    <!-- Note list -->
    <div class="flex-1 overflow-y-auto px-3 py-3 space-y-2">
      <div
        v-for="note in notes"
        :key="note.id"
        class="p-3 rounded-lg border border-navy-100/50 hover:border-navy-200 cursor-pointer transition-all group"
        @click="editNote(note)"
      >
        <p class="text-sm font-medium text-navy-700 truncate">{{ note.noteName }}</p>
        <p class="text-xs text-navy-400 mt-1 line-clamp-2">{{ note.content.substring(0, 80) }}</p>
      </div>

      <div v-if="notes.length === 0" class="text-center py-8">
        <p class="text-xs text-navy-300">暂无笔记</p>
      </div>
    </div>

    <!-- Edit area -->
    <div v-if="activeNote" class="border-t border-navy-100/50">
      <div class="px-4 py-3">
        <input v-model="activeNote.noteName" class="w-full text-sm font-medium text-navy-800 bg-transparent outline-none mb-2" placeholder="笔记标题" />
        <textarea v-model="activeNote.content" class="w-full h-32 text-sm text-navy-600 bg-transparent outline-none resize-none leading-relaxed" placeholder="书写..."></textarea>
        <div class="flex justify-end gap-2 mt-2">
          <button class="text-xs text-navy-400 hover:text-navy-600" @click="activeNote = null">关闭</button>
          <button class="text-xs text-navy-600 font-medium hover:text-navy-800" @click="saveActiveNote">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getNotes, createNote as createNoteApi, updateNote } from '@/api/note'
import type { Note } from '@/types/note'

const notes = ref<Note[]>([])
const activeNote = ref<Note | null>(null)
const isDragOver = ref(false)

function editNote(note: Note) {
  activeNote.value = { ...note }
}

async function createNote() {
  activeNote.value = { id: 0, userId: 0, noteName: '', content: '', createdAt: '', updatedAt: '' }
}

async function saveActiveNote() {
  if (!activeNote.value) return
  try {
    const noteName = activeNote.value.noteName.trim() || '无标题笔记'
    const content = activeNote.value.content.trim() || ' '
    if (activeNote.value.id) {
      await updateNote(activeNote.value.id, { noteName, content })
    } else {
      await createNoteApi({ noteName, content })
    }
    activeNote.value = null
    await loadNotes()
  } catch (e) {
    console.error('Save note failed:', e)
  }
}

function handleDrop(e: DragEvent) {
  isDragOver.value = false
  const text = e.dataTransfer?.getData('text/plain')
  if (text) {
    if (!activeNote.value) {
      activeNote.value = { id: 0, userId: 0, noteName: '新笔记', content: '', createdAt: '', updatedAt: '' }
    }
    activeNote.value.content += (activeNote.value.content ? '\n\n' : '') + text
  }
}

async function loadNotes() {
  try {
    const res = await getNotes({ page: 1, size: 20 })
    notes.value = res.data?.records || []
  } catch {
    notes.value = []
  }
}

onMounted(loadNotes)
</script>
