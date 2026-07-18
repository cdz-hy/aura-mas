<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="section-title">我的笔记</h1>
      <div class="flex items-center gap-3">
        <!-- 闪卡按钮 -->
        <div class="relative" ref="flashcardDropdownRef">
          <button
            class="btn-secondary text-sm flex items-center gap-2"
            @click="toggleFlashcardPanel"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
            闪卡
            <span v-if="dueCount > 0" class="px-1.5 py-0.5 bg-red-500 text-white text-xs rounded-full">{{ dueCount }}</span>
          </button>

          <!-- 闪卡下拉面板 -->
          <transition name="dropdown">
            <div
              v-if="showFlashcardPanel"
              class="absolute right-0 top-full mt-2 w-96 bg-white rounded-xl shadow-xl border border-navy-100/50 z-50 max-h-[500px] overflow-hidden flex flex-col"
            >
              <!-- 面板头部 -->
              <div class="px-4 py-3 border-b border-navy-100/50 bg-navy-50/50">
                <div class="flex items-center justify-between">
                  <h3 class="font-semibold text-navy-800">闪卡复习</h3>
                  <div class="flex items-center gap-2">
                    <span v-if="dueCount > 0" class="text-xs text-navy-500">{{ dueCount }} 张待复习</span>
                    <span v-else class="text-xs text-emerald-600">全部完成!</span>
                  </div>
                </div>
              </div>

              <!-- 闪卡列表 -->
              <div class="flex-1 overflow-y-auto custom-scrollbar">
                <!-- 加载状态 -->
                <div v-if="flashcardLoading" class="p-8 text-center">
                  <div class="animate-spin w-6 h-6 border-2 border-navy-300 border-t-transparent rounded-full mx-auto mb-2"></div>
                  <p class="text-sm text-navy-400">加载中...</p>
                </div>

                <!-- 空状态 -->
                <div v-else-if="flashcardGroups.length === 0" class="p-8 text-center">
                  <svg class="w-12 h-12 mx-auto mb-3 text-navy-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
                  </svg>
                  <p class="text-sm text-navy-400 mb-2">还没有闪卡</p>
                  <p class="text-xs text-navy-300">在笔记中生成闪卡后会显示在这里</p>
                </div>

                <!-- 按笔记分组的闪卡列表 -->
                <div v-else class="p-3 space-y-3">
                  <div
                    v-for="group in flashcardGroups"
                    :key="group.noteId"
                    class="border border-navy-100/60 rounded-lg overflow-hidden"
                  >
                    <!-- 笔记标题 -->
                    <div
                      class="flex items-center justify-between px-3 py-2 bg-navy-50/30 cursor-pointer hover:bg-navy-50/60 transition-colors"
                      @click="group.expanded = !group.expanded"
                    >
                      <div class="flex items-center gap-2 min-w-0">
                        <svg class="w-4 h-4 text-navy-400 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                        </svg>
                        <span class="text-sm font-medium text-navy-700 truncate">{{ group.noteName }}</span>
                      </div>
                      <div class="flex items-center gap-2 flex-shrink-0">
                        <span class="text-xs text-navy-400">{{ group.cards.length }} 张</span>
                        <span v-if="group.dueCount > 0" class="px-1.5 py-0.5 bg-amber-100 text-amber-700 text-xs rounded-full">{{ group.dueCount }} 待复习</span>
                        <svg
                          class="w-4 h-4 text-navy-400 transition-transform"
                          :class="{ 'rotate-180': group.expanded }"
                          viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                        >
                          <polyline points="6 9 12 15 18 9"/>
                        </svg>
                      </div>
                    </div>

                    <!-- 闪卡列表 -->
                    <transition name="expand">
                      <div v-if="group.expanded" class="divide-y divide-navy-100/40">
                        <div
                          v-for="card in group.cards"
                          :key="card.id"
                          class="px-3 py-2.5 hover:bg-navy-50/30 cursor-pointer transition-colors group/card"
                          @click="startReview(card)"
                        >
                          <div class="flex items-start justify-between gap-2">
                            <div class="min-w-0 flex-1">
                              <p class="text-sm text-navy-700 line-clamp-2">{{ card.question }}</p>
                              <div class="flex items-center gap-2 mt-1">
                                <span class="text-xs text-navy-300">
                                  复习 {{ card.reviewCount }} 次
                                </span>
                                <span v-if="card.nextReviewAt" class="text-xs" :class="isDue(card) ? 'text-amber-600' : 'text-emerald-600'">
                                  {{ isDue(card) ? '待复习' : '已掌握' }}
                                </span>
                              </div>
                            </div>
                            <button
                              class="opacity-0 group-hover/card:opacity-100 p-1.5 rounded-lg text-navy-400 hover:text-navy-600 hover:bg-navy-100 transition-all flex-shrink-0"
                              @click.stop="startReview(card)"
                              title="开始复习"
                            >
                              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polygon points="5 3 19 12 5 21 5 3"/>
                              </svg>
                            </button>
                          </div>
                        </div>
                      </div>
                    </transition>
                  </div>
                </div>
              </div>

              <!-- 底部操作 -->
              <div class="px-4 py-3 border-t border-navy-100/50 bg-navy-50/30">
                <button
                  v-if="dueCount > 0"
                  class="w-full btn-primary text-sm py-2"
                  @click="startDueReview"
                >
                  开始复习 ({{ dueCount }} 张待复习)
                </button>
                <p v-else class="text-center text-sm text-emerald-600">
                  太棒了! 所有闪卡都已掌握
                </p>
              </div>
            </div>
          </transition>
        </div>

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
        <div v-if="note.isPinned" class="absolute top-3 right-3 text-navy-400" title="已置顶">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z"/>
          </svg>
        </div>

        <!-- Capture type + organize status (与侧栏一致) -->
        <div class="flex items-center flex-wrap gap-1.5 mb-2 pr-6">
          <span class="text-[10px] font-medium px-1.5 py-0.5 rounded bg-navy-50 text-navy-500">
            {{ typeLabel(note) }}
          </span>
          <span class="text-[10px] font-medium px-1.5 py-0.5 rounded bg-navy-50 text-navy-400">
            {{ statusLabel(note) }}
          </span>
          <span
            v-if="note.sourceTitle"
            class="text-[10px] px-1.5 py-0.5 rounded bg-navy-50 text-navy-400 truncate max-w-[10rem]"
            :title="note.sourceTitle"
          >
            来源 · {{ note.sourceTitle }}
          </span>
        </div>

        <div class="flex items-start justify-between mb-2">
          <h3 class="font-medium text-navy-800 group-hover:text-navy-600 transition-colors flex-1 mr-2 line-clamp-1">
            {{ note.noteName || '无标题笔记' }}
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

        <p class="text-sm text-navy-400 line-clamp-3 mb-3">{{ previewText(note) }}</p>
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
            @click.stop="requestDeleteNote(note)"
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

    <ConfirmDialog
      :visible="showDeleteConfirm"
      title="删除笔记"
      :message="deleteConfirmMessage"
      confirm-text="确认删除"
      cancel-text="取消"
      type="danger"
      @confirm="handleDeleteConfirm"
      @cancel="handleDeleteCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getNotes, deleteNote as deleteNoteApi, updateNote } from '@/api/note'
import { getFlashcardsByNote, getDueFlashcardCount } from '@/api/flashcard'
import { tracker } from '@/utils/tracker'
import { showToast } from '@/composables/useToast'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { useNoteCaptureStore } from '@/stores/noteCapture'
import type { Note } from '@/types/note'
import type { Flashcard } from '@/types/flashcard'
import {
  noteListPreview,
  noteTypeLabel,
  organizeStatusLabel,
} from '@/components/note/notePresentation'

interface FlashcardGroup {
  noteId: number
  noteName: string
  cards: Flashcard[]
  dueCount: number
  expanded: boolean
}

const router = useRouter()
const noteCaptureStore = useNoteCaptureStore()
const notes = ref<Note[]>([])
const keyword = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

// 闪卡相关状态
const showFlashcardPanel = ref(false)
const flashcardLoading = ref(false)
const dueCount = ref(0)
const flashcardGroups = ref<FlashcardGroup[]>([])
const flashcardDropdownRef = ref<HTMLElement | null>(null)

function formatDate(date: string) {
  return new Date(date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function typeLabel(note: Note) {
  return noteTypeLabel(note.noteType)
}

function statusLabel(note: Note) {
  return organizeStatusLabel(note.organizeStatus)
}

function previewText(note: Note) {
  return noteListPreview(note, 120) || '暂无预览'
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

const showDeleteConfirm = ref(false)
const deletingNoteId = ref<number | null>(null)
const deletingNoteName = ref('')
const deleteConfirmMessage = computed(() => {
  const name = deletingNoteName.value || '无标题笔记'
  return `确定要删除笔记「${name}」吗？删除后不可恢复。`
})

function requestDeleteNote(note: Note) {
  deletingNoteId.value = note.id
  deletingNoteName.value = note.noteName?.trim() || '无标题笔记'
  showDeleteConfirm.value = true
}

function handleDeleteCancel() {
  showDeleteConfirm.value = false
  deletingNoteId.value = null
  deletingNoteName.value = ''
}

async function handleDeleteConfirm() {
  const id = deletingNoteId.value
  if (id == null) {
    handleDeleteCancel()
    return
  }
  try {
    await deleteNoteApi(id)
    showDeleteConfirm.value = false
    deletingNoteId.value = null
    deletingNoteName.value = ''
    // Optimistic local remove + broadcast so sidebar / append pickers drop it too
    notes.value = notes.value.filter(n => n.id !== id)
    noteCaptureStore.notifyNotesChanged({ removedId: id })
    await loadNotes()
    showToast('笔记已删除', 'success')
  } catch (e) {
    console.error('Delete note failed:', e)
    showToast('删除失败，请稍后重试', 'error')
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

// 闪卡相关函数
function toggleFlashcardPanel() {
  showFlashcardPanel.value = !showFlashcardPanel.value
  if (showFlashcardPanel.value) {
    loadFlashcards()
  }
}

function isDue(card: Flashcard): boolean {
  if (!card.nextReviewAt) return true
  return new Date(card.nextReviewAt) <= new Date()
}

async function loadFlashcards() {
  flashcardLoading.value = true
  try {
    // 获取待复习数量
    const countRes = await getDueFlashcardCount()
    dueCount.value = countRes.data || 0

    // 获取每个笔记的闪卡
    const groups: FlashcardGroup[] = []
    for (const note of notes.value) {
      try {
        const res = await getFlashcardsByNote(note.id)
        const cards = res.data || []
        if (cards.length > 0) {
          groups.push({
            noteId: note.id,
            noteName: note.noteName,
            cards,
            dueCount: cards.filter(c => isDue(c)).length,
            expanded: false
          })
        }
      } catch {
        // 忽略单个笔记的闪卡加载失败
      }
    }
    flashcardGroups.value = groups
  } catch (e) {
    console.error('Load flashcards failed:', e)
  } finally {
    flashcardLoading.value = false
  }
}

function startReview(card: Flashcard) {
  showFlashcardPanel.value = false
  router.push(`/flashcard/review?noteId=${card.noteId}&cardId=${card.id}`)
}

function startDueReview() {
  showFlashcardPanel.value = false
  router.push('/flashcard/review')
}

// 点击外部关闭下拉面板
function handleClickOutside(event: MouseEvent) {
  if (flashcardDropdownRef.value && !flashcardDropdownRef.value.contains(event.target as Node)) {
    showFlashcardPanel.value = false
  }
}

onMounted(() => {
  loadNotes()

  // 追踪页面浏览
  tracker.trackPageView({ page: 'notes' })

  document.addEventListener('mousedown', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handleClickOutside)
})
</script>

<style scoped>
.dropdown-enter-active {
  transition: all 0.2s ease-out;
}

.dropdown-leave-active {
  transition: all 0.15s ease-in;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.95);
}

.expand-enter-active {
  transition: all 0.2s ease-out;
}

.expand-leave-active {
  transition: all 0.15s ease-in;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 500px;
}
</style>
