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
        @click="editNote(note)"
      >
        <h3 class="font-medium text-navy-800 mb-2 group-hover:text-navy-600 transition-colors">{{ note.noteName }}</h3>
        <p class="text-sm text-navy-400 line-clamp-3 mb-3">{{ note.content.substring(0, 150) }}</p>
        <div class="flex items-center justify-between text-xs text-navy-300">
          <span>{{ formatDate(note.updatedAt) }}</span>
          <button class="text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity" @click.stop="deleteNote(note.id)">
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- Edit modal -->
    <Teleport to="body">
      <div v-if="editingNote" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
        <div class="w-full max-w-3xl max-h-[80vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden">
          <div class="px-6 py-4 border-b border-navy-100 flex items-center justify-between">
            <input
              v-model="editingNote.noteName"
              class="text-lg font-display font-semibold text-navy-800 bg-transparent border-none outline-none w-full"
              placeholder="笔记标题"
            />
            <div class="flex gap-2 flex-shrink-0 ml-4">
              <button class="btn-ghost text-sm" @click="editingNote = null">取消</button>
              <button class="btn-primary text-sm" @click="saveNote">保存</button>
            </div>
          </div>
          <div class="flex-1 overflow-hidden">
            <textarea
              v-model="editingNote.content"
              class="w-full h-full p-6 text-navy-700 leading-relaxed resize-none outline-none font-body"
              placeholder="开始书写... (支持 Markdown)"
            ></textarea>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getNotes, createNote, updateNote, deleteNote as deleteNoteApi } from '@/api/note'
import type { Note } from '@/types/note'

const notes = ref<Note[]>([])
const editingNote = ref<Note | null>(null)

function formatDate(date: string) {
  return new Date(date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function createNewNote() {
  editingNote.value = { id: 0, userId: 0, noteName: '', content: '', createdAt: '', updatedAt: '' }
}

function editNote(note: Note) {
  editingNote.value = { ...note }
}

async function saveNote() {
  if (!editingNote.value) return
  try {
    const noteName = editingNote.value.noteName.trim() || '无标题笔记'
    const content = editingNote.value.content.trim() || ' '
    if (editingNote.value.id) {
      await updateNote(editingNote.value.id, { noteName, content })
    } else {
      await createNote({ noteName, content })
    }
    editingNote.value = null
    await loadNotes()
  } catch (e) {
    console.error('Save note failed:', e)
  }
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
