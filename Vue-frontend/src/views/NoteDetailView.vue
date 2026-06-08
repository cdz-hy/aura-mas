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
        <div class="flex-1 min-w-0">
          <input
            v-model="noteName"
            class="text-xl font-display font-semibold text-navy-800 bg-transparent border-none outline-none w-full placeholder:text-navy-300"
            placeholder="笔记标题"
            @blur="autoSave"
          />
          <!-- Tags -->
          <div class="flex items-center flex-wrap gap-1.5 mt-1">
            <span
              v-for="tag in noteTags"
              :key="tag"
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-navy-50 text-navy-500"
            >
              {{ tag }}
              <button class="text-navy-300 hover:text-navy-600 ml-0.5" @click="removeTag(tag)">&times;</button>
            </span>
            <input
              v-model="tagInput"
              class="text-xs bg-transparent border-none outline-none w-20 placeholder:text-navy-300 text-navy-400"
              placeholder="+ 标签"
              @keydown.enter.prevent="addTag"
              @keydown.,.prevent="addTag"
            />
          </div>
          <p class="text-xs text-navy-300 mt-0.5">
            {{ note ? `最后编辑于 ${formatDate(note.updatedAt)}` : '新建笔记' }}
            <span v-if="saving" class="ml-2 text-sage-500">保存中...</span>
            <span v-else-if="saved" class="ml-2 text-sage-500">已保存</span>
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="viewMode === 'preview' && note?.id"
          class="px-3 py-1.5 rounded-lg text-sm text-amber-600 bg-amber-50 hover:bg-amber-100 transition-colors"
          @click="openFlashcardPanel"
        >
          <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
          </svg>
          {{ dueCount > 0 ? `复习闪卡 (${dueCount})` : '闪卡' }}
        </button>
        <!-- View mode switch: edit / split / preview -->
        <div class="flex items-center bg-navy-50 rounded-lg p-0.5">
          <button
            class="px-2.5 py-1 rounded-md text-xs transition-all duration-200"
            :class="viewMode === 'edit' ? 'bg-white text-navy-700 shadow-sm' : 'text-navy-400 hover:text-navy-600'"
            @click="viewMode = 'edit'"
          >
            <svg class="w-3.5 h-3.5 inline mr-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            编辑
          </button>
          <button
            class="px-2.5 py-1 rounded-md text-xs transition-all duration-200"
            :class="viewMode === 'split' ? 'bg-white text-navy-700 shadow-sm' : 'text-navy-400 hover:text-navy-600'"
            @click="viewMode = 'split'"
          >
            <svg class="w-3.5 h-3.5 inline mr-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="3" x2="12" y2="21"/>
            </svg>
            分屏
          </button>
          <button
            class="px-2.5 py-1 rounded-md text-xs transition-all duration-200"
            :class="viewMode === 'preview' ? 'bg-white text-navy-700 shadow-sm' : 'text-navy-400 hover:text-navy-600'"
            @click="viewMode = 'preview'"
          >
            <svg class="w-3.5 h-3.5 inline mr-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" />
            </svg>
            预览
          </button>
        </div>
        <button
          v-if="viewMode !== 'preview' && content.trim().length > 0"
          class="px-3 py-1.5 rounded-lg text-sm transition-all duration-200 flex items-center gap-1.5"
          :class="formatting
            ? 'bg-indigo-50 text-indigo-600 cursor-wait'
            : 'text-indigo-600 hover:bg-indigo-50 border border-indigo-200'"
          :disabled="formatting"
          @click="handleFormat"
        >
          <svg v-if="formatting" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 11-6.219-8.56" />
          </svg>
          <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          {{ formatting ? formatStatus || '整理中...' : '整理笔记' }}
        </button>
        <button
          class="px-4 py-1.5 rounded-lg text-sm text-white bg-navy-600 hover:bg-navy-700 transition-colors"
          @click="saveNote"
        >
          保存
        </button>
      </div>
    </div>

    <!-- Source tags -->
    <div v-if="noteResources.length > 0" class="flex flex-wrap gap-2 mb-4">
      <button
        v-for="res in noteResources"
        :key="res.id"
        class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs bg-navy-50 text-navy-600 hover:bg-navy-100 transition-colors cursor-pointer"
        @click="res.planId && router.push(`/plan/${res.planId}?resource=${res.resourceId}`)"
      >
        <svg class="w-3.5 h-3.5 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
        </svg>
        <span v-if="res.moduleName" class="text-navy-400">{{ res.moduleName }} ·</span>
        {{ res.resourceTitle || `资源 #${res.resourceId}` }}
      </button>
    </div>

    <!-- Editor / Preview area -->
    <div class="card overflow-hidden flex flex-col" style="height: calc(100vh - 220px)">
      <!-- Toolbar (edit & split modes) -->
      <div v-if="viewMode !== 'preview'" class="flex items-center gap-0.5 px-4 py-2 border-b border-navy-100/50 bg-navy-50/30 shrink-0 flex-wrap">
        <button v-for="btn in toolbarButtons" :key="btn.label" class="toolbar-btn" :title="btn.label" @click="insertMarkdown(btn.prefix, btn.suffix, btn.placeholder)">
          <span class="text-xs font-medium">{{ btn.display }}</span>
        </button>
      </div>

      <!-- Edit mode -->
      <div v-if="viewMode === 'edit'" class="flex-1 min-h-0">
        <textarea
          ref="textareaRef"
          v-model="content"
          class="w-full h-full p-8 text-navy-700 leading-relaxed resize-none outline-none font-body text-base"
          placeholder="开始书写你的笔记...&#10;&#10;支持 Markdown 语法：&#10;# 标题&#10;**粗体** *斜体*&#10;- 列表&#10;> 引用&#10;`代码`"
          @input="onInput"
          @keydown.ctrl.s.prevent="saveNote"
          @keydown.meta.s.prevent="saveNote"
        ></textarea>
      </div>

      <!-- Split mode -->
      <div v-else-if="viewMode === 'split'" class="flex-1 min-h-0 flex">
        <textarea
          ref="textareaRef"
          v-model="content"
          class="flex-1 p-6 text-navy-700 leading-relaxed resize-none outline-none font-body text-base border-r border-navy-100/50"
          placeholder="开始书写你的笔记..."
          @input="onInput"
          @keydown.ctrl.s.prevent="saveNote"
          @keydown.meta.s.prevent="saveNote"
        ></textarea>
        <div class="flex-1 overflow-y-auto p-6" @mouseup="onPreviewMouseUp">
          <div class="markdown-body" v-html="renderedContent" @click="onPreviewClick"></div>
        </div>
      </div>

      <!-- Preview mode -->
      <div v-else class="flex-1 min-h-0 overflow-y-auto p-8" @mouseup="onPreviewMouseUp">
        <div class="markdown-body max-w-3xl mx-auto" v-html="renderedContent" @click="onPreviewClick"></div>
      </div>
    </div>

    <!-- Mindmap section -->
    <div v-if="viewMode === 'preview' && mindmapData" class="mt-4 card overflow-hidden" style="height: 450px">
      <MindmapPlayer :data="mindmapData" :title="noteName || '思维导图'" />
    </div>

    <!-- Format complete - flashcard prompt -->
    <transition name="fade">
      <div v-if="showFormatFlashcardPrompt" class="mt-4 p-4 rounded-xl bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-emerald-100 flex items-center justify-center">
            <svg class="w-5 h-5 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
          <div>
            <p class="text-sm font-medium text-emerald-800">笔记整理完成</p>
            <p class="text-xs text-emerald-600">是否从整理后的笔记中生成闪卡？</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="px-3 py-1.5 text-xs text-emerald-600 hover:bg-emerald-100 rounded-lg transition-colors"
            @click="showFormatFlashcardPrompt = false"
          >
            稍后再说
          </button>
          <button
            class="px-4 py-1.5 text-xs text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors"
            @click="generateFlashcardsAfterFormat"
          >
            生成闪卡
          </button>
        </div>
      </div>
    </transition>

    <!-- Selection popup -->
    <Teleport to="body">
      <div
        v-if="selectionPopup.show"
        class="selection-popup"
        :style="{ left: selectionPopup.x + 'px', top: selectionPopup.y + 'px' }"
      >
        <button class="selection-popup-btn" @click="generateFromSelection">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
          </svg>
          用选中内容生成闪卡
        </button>
      </div>
    </Teleport>

    <!-- Flashcard overlay -->
    <Teleport to="body">
      <div v-if="showFlashcardPanel" class="flashcard-overlay" @click.self="closeFlashcardPanel">
        <div class="flashcard-modal">
          <!-- Generation in progress -->
          <div v-if="generating" class="text-center py-12">
            <div class="inline-block w-8 h-8 border-2 border-amber-300 border-t-amber-600 rounded-full animate-spin mb-4" />
            <p class="text-navy-600">{{ generateStatus }}</p>
          </div>

          <!-- Player -->
          <template v-else-if="reviewCards.length > 0">
            <!-- Stale warning -->
            <div v-if="isFlashcardStale" class="stale-warning">
              <p class="text-sm text-amber-700">笔记内容已更新，闪卡可能过期</p>
              <button class="stale-regenerate-btn" @click="startGenerate">
                重新生成
              </button>
            </div>
            <FlashcardPlayer
              :cards="reviewCards"
              @close="closeFlashcardPanel"
              @reviewed="onCardReviewed"
            />
          </template>

          <!-- No cards: offer to generate -->
          <div v-else class="text-center py-12">
            <div class="text-4xl mb-4"> </div>
            <p class="text-navy-600 mb-2">还没有闪卡</p>
            <p class="text-sm text-navy-400 mb-6">从笔记内容中自动生成知识点闪卡</p>
            <button
              class="px-6 py-2.5 rounded-xl text-sm font-medium text-white bg-amber-500 hover:bg-amber-600 transition-colors"
              @click="startGenerate"
            >
              生成闪卡
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import { getNoteById, createNote, updateNote, getNoteResources } from '@/api/note'
import { getFlashcardsByNote, generateFlashcardsSSE } from '@/api/flashcard'
import { issueTicket } from '@/api/auth'
import { formatNoteSSE } from '@/api/noteAgent'
import type { Note, NoteResourceRel } from '@/types/note'
import type { Flashcard } from '@/types/flashcard'
import FlashcardPlayer from '@/components/flashcard/FlashcardPlayer.vue'
import MindmapPlayer from '@/components/resource/MindmapPlayer.vue'

const route = useRoute()
const router = useRouter()

const note = ref<Note | null>(null)
const noteName = ref('')
const content = ref('')
const viewMode = ref<'edit' | 'split' | 'preview'>(route.query.mode === 'preview' ? 'preview' : 'edit')
const saving = ref(false)
const saved = ref(false)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

// Tags
const noteTags = ref<string[]>([])
const tagInput = ref('')

// Toolbar
const toolbarButtons = [
  { label: '一级标题', display: 'H1', prefix: '# ', suffix: '', placeholder: '标题' },
  { label: '二级标题', display: 'H2', prefix: '## ', suffix: '', placeholder: '标题' },
  { label: '三级标题', display: 'H3', prefix: '### ', suffix: '', placeholder: '标题' },
  { label: '粗体', display: 'B', prefix: '**', suffix: '**', placeholder: '粗体文本' },
  { label: '斜体', display: 'I', prefix: '*', suffix: '*', placeholder: '斜体文本' },
  { label: '删除线', display: 'S', prefix: '~~', suffix: '~~', placeholder: '删除文本' },
  { label: '无序列表', display: '•', prefix: '- ', suffix: '', placeholder: '列表项' },
  { label: '有序列表', display: '1.', prefix: '1. ', suffix: '', placeholder: '列表项' },
  { label: '代码块', display: '<>', prefix: '```\n', suffix: '\n```', placeholder: '代码' },
  { label: '引用', display: '❝', prefix: '> ', suffix: '', placeholder: '引用内容' },
  { label: '链接', display: '🔗', prefix: '[', suffix: '](url)', placeholder: '链接文本' },
  { label: '分割线', display: '—', prefix: '\n---\n', suffix: '', placeholder: '' },
]
let saveTimer: ReturnType<typeof setTimeout> | null = null
let savedTimer: ReturnType<typeof setTimeout> | null = null

// Flashcard state
const showFlashcardPanel = ref(false)
const generating = ref(false)
const generateStatus = ref('')
const reviewCards = ref<Flashcard[]>([])
const dueCount = ref(0)
const latestFlashcardAt = ref<string | null>(null)

// Note resources (source links)
const noteResources = ref<NoteResourceRel[]>([])

// Selection popup state
const selectionPopup = ref({ show: false, x: 0, y: 0, text: '' })

// Note formatting state
const formatting = ref(false)
const formatStatus = ref('')
const showFormatFlashcardPrompt = ref(false)

marked.setOptions({
  breaks: true,
  gfm: true,
} as any)

const CALLOUT_MAP: Record<string, string> = {
  '💡': 'tip',
  '⚠️': 'warning',
  '📌': 'important',
  '🌰': 'example',
  '🔑': 'key',
  '✅': 'summary',
  '📖': 'definition',
}

function classifyCallouts(html: string): string {
  return html.replace(/<blockquote>([\s\S]*?)<\/blockquote>/g, (match, inner) => {
    const text = inner.replace(/<[^>]+>/g, '').trim()
    for (const [emoji, cls] of Object.entries(CALLOUT_MAP)) {
      if (text.startsWith(emoji)) {
        return `<blockquote class="${cls}">${inner}</blockquote>`
      }
    }
    return match
  })
}

const renderedContent = computed(() => {
  const raw = content.value || ''
  // Strip ```mindmap code block before rendering markdown
  const stripped = raw.replace(/```mindmap\s*\n[\s\S]*?```/g, '').trim()
  return classifyCallouts(marked(stripped) as string)
})

const mindmapData = computed(() => {
  const raw = content.value || ''
  const match = raw.match(/```mindmap\s*\n([\s\S]*?)```/)
  if (!match) return null
  try {
    return JSON.parse(match[1].trim())
  } catch {
    return null
  }
})

const isFlashcardStale = computed(() => {
  if (!note.value?.updatedAt || !latestFlashcardAt.value) return false
  return new Date(note.value.updatedAt) > new Date(latestFlashcardAt.value)
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

function insertMarkdown(prefix: string, suffix: string, placeholder: string) {
  const ta = textareaRef.value
  if (!ta) return
  const start = ta.selectionStart
  const end = ta.selectionEnd
  const scrollTop = ta.scrollTop
  const selected = content.value.substring(start, end) || placeholder
  const before = content.value.substring(0, start)
  const after = content.value.substring(end)
  content.value = before + prefix + selected + suffix + after
  nextTick(() => {
    ta.focus()
    ta.scrollTop = scrollTop
    const cursorPos = start + prefix.length
    ta.setSelectionRange(cursorPos, cursorPos + selected.length)
  })
}

function addTag() {
  const tag = tagInput.value.trim().replace(/,/g, '')
  if (!tag || noteTags.value.includes(tag)) {
    tagInput.value = ''
    return
  }
  noteTags.value.push(tag)
  tagInput.value = ''
  autoSave()
}

function removeTag(tag: string) {
  noteTags.value = noteTags.value.filter(t => t !== tag)
  autoSave()
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
    const tags = noteTags.value.length > 0 ? noteTags.value : undefined
    if (note.value?.id) {
      await updateNote(note.value.id, { noteName: name, content: body, tags })
    } else {
      const res = await createNote({ noteName: name, content: body, tags })
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
    noteTags.value = []
    noteResources.value = []
    return
  }
  try {
    const res = await getNoteById(Number(id))
    const found = res.data
    if (found) {
      note.value = found
      noteName.value = found.noteName
      content.value = found.content
      noteTags.value = parseTags(found.tags)
      loadNoteResources(found.id)
    } else {
      router.push('/notes')
    }
  } catch {
    router.push('/notes')
  }
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

async function loadNoteResources(noteId: number) {
  try {
    const res = await getNoteResources(noteId)
    noteResources.value = res.data ?? []
  } catch {
    noteResources.value = []
  }
}

async function loadDueCount() {
  if (!note.value?.id) {
    dueCount.value = 0
    return
  }
  try {
    const res = await getFlashcardsByNote(note.value.id)
    const cards = res.data ?? []
    const now = new Date()
    dueCount.value = cards.filter(c => !c.nextReviewAt || new Date(c.nextReviewAt) <= now).length
    // Track latest flashcard creation time for stale detection
    if (cards.length > 0) {
      const sorted = [...cards].sort((a, b) =>
        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      )
      latestFlashcardAt.value = sorted[0].createdAt
    } else {
      latestFlashcardAt.value = null
    }
  } catch {
    dueCount.value = 0
    latestFlashcardAt.value = null
  }
}

async function openFlashcardPanel() {
  showFlashcardPanel.value = true
  if (!note.value?.id) return

  try {
    const res = await getFlashcardsByNote(note.value.id)
    const cards = res.data ?? []
    if (cards.length > 0) {
      const now = new Date()
      const due = cards.filter(c => !c.nextReviewAt || new Date(c.nextReviewAt) <= now)
      reviewCards.value = due.length > 0 ? due : cards
      // Track latest flashcard creation time
      const sorted = [...cards].sort((a, b) =>
        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      )
      latestFlashcardAt.value = sorted[0].createdAt
    } else {
      reviewCards.value = []
      latestFlashcardAt.value = null
    }
  } catch {
    reviewCards.value = []
  }
}

function closeFlashcardPanel() {
  showFlashcardPanel.value = false
  generating.value = false
  reviewCards.value = []
  loadDueCount()
}

async function startGenerate() {
  if (!note.value?.id) return
  showFlashcardPanel.value = true
  generating.value = true
  generateStatus.value = '正在获取认证...'

  try {
    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket

    generateStatus.value = '正在分析笔记内容...'

    generateFlashcardsSSE(ticket, note.value.id, {
      onProgress(content) {
        generateStatus.value = content
      },
      onFlashcard(index, total, question, answer, difficulty) {
        generateStatus.value = `已生成 ${index + 1}/${total} 张闪卡...`
      },
      onDone(message) {
        generating.value = false
        reviewCards.value = []
        openFlashcardPanel()
      },
      onError(error) {
        generating.value = false
        generateStatus.value = `生成失败: ${error}`
        console.error('Flashcard generation error:', error)
      },
    })
  } catch (e) {
    generating.value = false
    console.error('Failed to start flashcard generation:', e)
  }
}

// === Note formatting ===

async function handleFormat() {
  if (!content.value.trim()) return
  formatting.value = true
  formatStatus.value = ''
  showFormatFlashcardPrompt.value = false
  const originalContent = content.value

  try {
    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket

    formatStatus.value = '正在整理笔记...'
    content.value = ''

    formatNoteSSE(ticket, originalContent, {
      onProgress(message) {
        formatStatus.value = message
      },
      onChunk(chunk) {
        content.value += chunk
      },
      onDone(formatted) {
        content.value = formatted
        formatting.value = false
        formatStatus.value = ''
        saveNote()
        showFormatFlashcardPrompt.value = true
      },
      onError(error) {
        content.value = originalContent
        formatting.value = false
        formatStatus.value = ''
        console.error('Note format error:', error)
      },
    })
  } catch (e) {
    content.value = originalContent
    formatting.value = false
    formatStatus.value = ''
    console.error('Failed to start note formatting:', e)
  }
}

function generateFlashcardsAfterFormat() {
  showFormatFlashcardPrompt.value = false
  startGenerate()
}

// === Preview link navigation ===

function onPreviewClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  const anchor = target.closest('a') as HTMLAnchorElement | null
  if (!anchor) return
  const href = anchor.getAttribute('href')
  if (href && href.startsWith('/')) {
    e.preventDefault()
    router.push(href)
  }
}

// === Selection popup ===

function onPreviewMouseUp(e: MouseEvent) {
  const selection = window.getSelection()
  const text = selection?.toString().trim() || ''

  if (text.length < 10) {
    selectionPopup.value.show = false
    return
  }

  // Position popup near the end of selection
  const range = selection?.getRangeAt(0)
  if (!range) return
  const rect = range.getBoundingClientRect()
  selectionPopup.value = {
    show: true,
    x: rect.right + 8,
    y: rect.top - 10,
    text,
  }
}

function hideSelectionPopup() {
  selectionPopup.value.show = false
}

async function generateFromSelection() {
  const text = selectionPopup.value.text
  selectionPopup.value.show = false
  if (!note.value?.id || !text) return

  showFlashcardPanel.value = true
  generating.value = true
  generateStatus.value = '正在获取认证...'

  try {
    const ticketRes = await issueTicket()
    const ticket = ticketRes.data.ticket

    generateStatus.value = '正在分析选中内容...'

    generateFlashcardsSSE(ticket, note.value.id, {
      onProgress(content) {
        generateStatus.value = content
      },
      onFlashcard(index, total, question, answer, difficulty) {
        generateStatus.value = `已生成 ${index + 1}/${total} 张闪卡...`
      },
      onDone(message) {
        generating.value = false
        reviewCards.value = []
        openFlashcardPanel()
      },
      onError(error) {
        generating.value = false
        generateStatus.value = `生成失败: ${error}`
      },
    }, text)
  } catch (e) {
    generating.value = false
    console.error('Failed to generate from selection:', e)
  }
}

function onCardReviewed(_cardId: number, _quality: number) {
  // Card reviewed, player will advance automatically
}

// Hide selection popup when clicking elsewhere
function onDocumentMouseDown(e: MouseEvent) {
  const popup = document.querySelector('.selection-popup')
  if (popup && !popup.contains(e.target as Node)) {
    selectionPopup.value.show = false
  }
}

onMounted(() => {
  loadNote()
  loadDueCount()
  document.addEventListener('mousedown', onDocumentMouseDown)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onDocumentMouseDown)
})

watch(() => route.params.id, (newId) => {
  if (newId) {
    loadNote()
    loadDueCount()
  }
})
</script>

<style scoped>
.flashcard-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.2s ease;
}

.flashcard-modal {
  background: white;
  border-radius: 20px;
  padding: 32px;
  width: 90%;
  max-width: 520px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  animation: slideUp 0.25s ease;
}

.stale-warning {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  margin-bottom: 16px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 10px;
}

.stale-regenerate-btn {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  color: #92400e;
  background: #fef3c7;
  border: 1px solid #fde68a;
  border-radius: 6px;
  transition: background 0.15s;
}

.stale-regenerate-btn:hover {
  background: #fde68a;
}

.selection-popup {
  position: fixed;
  z-index: 1100;
  animation: fadeIn 0.15s ease;
}

.selection-popup-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.15s;
  cursor: pointer;
  white-space: nowrap;
}

.selection-popup-btn:hover {
  background: #fef3c7;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 28px;
  border-radius: 6px;
  color: #6b7a99;
  transition: all 0.15s;
  cursor: pointer;
  border: none;
  background: none;
}

.toolbar-btn:hover {
  background: rgba(26, 40, 71, 0.08);
  color: #1a2847;
}
</style>
