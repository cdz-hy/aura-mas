<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="section-title">我的笔记</h1>
      <div class="flex items-center gap-3">
        <div class="relative">
          <svg class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-navy-300 pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            v-model="keyword"
            class="input-field pl-10 w-56"
            placeholder="搜索笔记..."
            @input="onSearchInput"
          />
        </div>
        <button class="btn-primary text-sm" @click="createNewNote">
          + 新建笔记
        </button>
      </div>
    </div>

    <div v-if="notes.length === 0" class="card p-16 text-center">
      <svg class="w-16 h-16 mx-auto mb-4 text-navy-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
      </svg>
      <p class="text-navy-400 mb-4">{{ keyword ? '没有找到匹配的笔记' : '还没有笔记，开始记录你的学习心得吧' }}</p>
      <button v-if="!keyword" class="btn-primary text-sm" @click="createNewNote">创建第一篇笔记</button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="note in notes"
        :key="note.id"
        class="card-hover p-5 cursor-pointer group relative"
      >
        <!-- Pin icon -->
        <div v-if="note.isPinned" class="absolute top-3 right-3 text-amber-500" title="已置顶">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z"/>
          </svg>
        </div>

        <div class="flex items-start justify-between mb-2">
          <h3 class="font-medium text-navy-800 group-hover:text-navy-600 transition-colors flex-1 mr-2 line-clamp-1">
            {{ note.noteName }}
          </h3>
        </div>

        <!-- Tags -->
        <div v-if="parseTags(note.tags).length > 0" class="flex flex-wrap gap-1.5 mb-2">
          <span
            v-for="tag in parseTags(note.tags)"
            :key="tag"
            class="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-navy-50 text-navy-500"
          >
            {{ tag }}
          </span>
        </div>

        <p class="text-sm text-navy-400 line-clamp-3 mb-3">{{ note.content.substring(0, 150) }}</p>
        <div class="flex items-center justify-between text-xs text-navy-300">
          <span>{{ formatDate(note.updatedAt) }}</span>
        </div>

        <!-- Bottom-right actions (pin + delete) -->
        <div class="absolute bottom-2 right-2 flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            class="p-1.5 rounded-lg text-amber-500 hover:bg-amber-50 transition-colors"
            @click.stop="togglePin(note)"
            :title="note.isPinned ? '取消置顶' : '置顶'"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" :fill="note.isPinned ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
              <path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z"/>
            </svg>
          </button>
          <button
            class="p-1.5 rounded-lg text-red-400 hover:bg-red-50 transition-colors"
            @click.stop="deleteNote(note.id)"
            title="删除"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
          </button>
        </div>

        <!-- Hover overlay (view + edit only) -->
        <div class="absolute inset-0 bg-navy-900/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3 pointer-events-none">
          <button
            class="px-4 py-2 bg-white text-navy-700 text-sm font-medium rounded-lg shadow-sm hover:shadow-md hover:bg-navy-50 transition-all flex items-center gap-1.5 pointer-events-auto"
            @click.stop="$router.push(`/notes/${note.id}?mode=preview`)"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
            </svg>
            查看
          </button>
          <button
            class="px-4 py-2 bg-navy-700 text-white text-sm font-medium rounded-lg shadow-sm hover:shadow-md hover:bg-navy-800 transition-all flex items-center gap-1.5 pointer-events-auto"
            @click.stop="$router.push(`/notes/${note.id}`)"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            编辑
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getNotes, deleteNote as deleteNoteApi, updateNote } from '@/api/note'
import type { Note } from '@/types/note'

const router = useRouter()
const notes = ref<Note[]>([])
const keyword = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

function formatDate(date: string) {
  return new Date(date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function parseTags(tags: Note['tags']): string[] {
  if (!tags) return []
  if (Array.isArray(tags)) return tags
  try {
    return JSON.parse(tags as string)
  } catch {
    return []
  }
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(loadNotes, 300)
}

function createNewNote() {
  router.push('/notes/new')
}

async function togglePin(note: Note) {
  try {
    await updateNote(note.id, {
      noteName: note.noteName,
      content: note.content,
      isPinned: note.isPinned ? 0 : 1,
    })
    await loadNotes()
  } catch (e) {
    console.error('Toggle pin failed:', e)
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
    const res = await getNotes({ page: 1, size: 50, keyword: keyword.value || undefined })
    notes.value = res.data?.records || []
  } catch {
    notes.value = []
  }
}

onMounted(loadNotes)
</script>
