<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="section-title">我的笔记</h1>
      <button class="btn-primary text-sm" @click="createNewNote">
        + 新建笔记
      </button>
    </div>

    <div v-if="notes.length === 0" class="card p-16 text-center">
      <svg class="w-16 h-16 mx-auto mb-4 text-navy-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
      </svg>
      <p class="text-navy-400 mb-4">还没有笔记，开始记录你的学习心得吧</p>
      <button class="btn-primary text-sm" @click="createNewNote">创建第一篇笔记</button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="note in notes"
        :key="note.id"
        class="card-hover p-5 cursor-pointer group"
        @click="$router.push(`/notes/${note.id}`)"
      >
        <div class="flex items-start justify-between mb-2">
          <h3 class="font-medium text-navy-800 group-hover:text-navy-600 transition-colors flex-1 mr-2 line-clamp-1">
            {{ note.noteName }}
          </h3>
          <svg class="w-4 h-4 text-navy-200 group-hover:text-navy-400 transition-colors flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </div>
        <p class="text-sm text-navy-400 line-clamp-3 mb-3">{{ note.content.substring(0, 150) }}</p>
        <div class="flex items-center justify-between text-xs text-navy-300">
          <span>{{ formatDate(note.updatedAt) }}</span>
          <button class="text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity" @click.stop="deleteNote(note.id)">
            删除
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getNotes, deleteNote as deleteNoteApi } from '@/api/note'
import type { Note } from '@/types/note'

const router = useRouter()
const notes = ref<Note[]>([])

function formatDate(date: string) {
  return new Date(date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function createNewNote() {
  router.push('/notes/new')
}

async function deleteNote(id: number) {
  try {
    await deleteNoteApi(id)
    await loadNotes()
  } catch (e) {
    console.error('Delete note failed:', e)
  }
}

async function loadNotes() {
  try {
    const res = await getNotes({ page: 1, size: 50 })
    notes.value = res.data?.records || []
  } catch {
    notes.value = []
  }
}

onMounted(loadNotes)
</script>
