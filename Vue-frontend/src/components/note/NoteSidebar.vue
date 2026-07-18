<template>
  <div class="note-sidebar flex flex-col h-full bg-white">
    <!-- Header -->
    <div class="px-4 py-3 border-b border-navy-100/70 flex items-center justify-between">
      <div>
        <h3 class="font-display text-[15px] font-semibold text-navy-800 leading-none">学习笔记</h3>
        <p class="text-[10px] text-navy-400 mt-1">快速捕获 · 稍后整理</p>
      </div>
      <button
        aria-label="新建笔记"
        class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-400 hover:bg-navy-50 hover:text-navy-600 transition-colors"
        @click="startNewNote"
      >
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </button>
    </div>

    <!-- Collapsed capture row -->
    <div class="px-3 pt-3">
      <button
        type="button"
        class="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-left transition-colors border-navy-100 bg-navy-50/40 hover:border-navy-200 hover:bg-navy-50/70"
        data-testid="capture-row"
        @click="expandCapture"
      >
        <span class="inline-flex items-center justify-center w-6 h-6 rounded-md bg-white border border-navy-100 text-navy-500 flex-shrink-0">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </span>
        <span class="min-w-0 flex-1">
          <span class="block text-sm text-navy-700 font-medium">
            记一条笔记
          </span>
          <span
            v-if="capture.source.value"
            class="block text-[11px] text-navy-400 truncate mt-0.5"
            :title="capture.source.value.sourceTitle"
          >
            来源 · {{ capture.source.value.sourceTitle }}
          </span>
          <span v-else class="block text-[11px] text-navy-300 mt-0.5">
            摘录 · 速记 · 提问
          </span>
        </span>
      </button>
    </div>

    <!-- Expanded capture editor -->
    <NoteCaptureEditor
      v-if="capture.expanded.value && draft"
      ref="editorRef"
      :draft="draft"
      :mode="capture.mode.value"
      :source="capture.source.value"
      :excerpt="capture.excerpt.value"
      :save-status="saveStatus"
      :status-label="statusLabel"
      :organizing="organizing"
      :organize-error="organizeError"
      @update:mode="onModeChange"
      @update:fields="onFieldInput"
      @remove-source="onRemoveSource"
      @open-source="navigateToSource"
      @collapse="collapseCapture"
      @organize="organizeCurrentNote"
      @save="manualSave"
      @retry-save="retrySave"
      @open-full="openFullEditor"
    />

    <!-- Search + filters -->
    <div class="px-3 pt-3 space-y-2">
      <div class="relative">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-navy-300 pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          v-model="keyword"
          type="text"
          placeholder="搜索笔记"
          class="w-full text-sm pl-9 pr-3 py-2 rounded-lg border border-navy-100 bg-white outline-none focus:border-navy-300 text-navy-700 placeholder:text-navy-300"
        />
      </div>
      <div class="flex items-center gap-1" role="group" aria-label="笔记筛选">
        <button
          v-for="f in filterOptions"
          :key="f.value ?? 'all'"
          type="button"
          class="px-2.5 py-1 text-[11px] rounded-md font-medium transition-colors"
          :class="capture.pendingFilter.value === f.value
            ? 'bg-navy-100 text-navy-700'
            : 'text-navy-400 hover:text-navy-600 hover:bg-navy-50'"
          @click="toggleFilter(f.value)"
        >
          {{ f.label }}
        </button>
      </div>
    </div>

    <!-- Note list (grouped) -->
    <div class="flex-1 overflow-y-auto px-3 py-3 space-y-4">
      <div v-if="listStatus === 'loading'" class="text-center py-8">
        <div class="inline-flex items-center gap-2 text-xs text-navy-400">
          加载中…
        </div>
      </div>

      <div v-else-if="listStatus === 'error'" class="text-center py-8 space-y-2">
        <p class="text-xs text-navy-500">笔记加载失败</p>
        <button class="text-xs text-navy-500 underline hover:text-navy-700" @click="() => loadNotes()">重试</button>
      </div>

      <template v-else>
        <section v-if="pendingNotes.length > 0" data-testid="group-pending">
          <h4 class="text-[11px] font-medium text-navy-400 tracking-wide mb-2 px-0.5">
            待整理
            <span class="text-navy-300 font-normal">{{ pendingNotes.length }}</span>
          </h4>
          <div class="space-y-2">
            <NoteListItem
              v-for="note in pendingNotes"
              :key="note.id"
              :note="note"
              :source-label="displaySourceLabel(note)"
              :source-route="displaySourceRoute(note)"
              @open="openNote(note)"
              @open-source="navigateToSource"
            />
          </div>
        </section>

        <section v-if="organizedNotes.length > 0" data-testid="group-organized">
          <h4 class="text-[11px] font-medium text-navy-400 tracking-wide mb-2 px-0.5">
            已整理
            <span class="text-navy-300 font-normal">{{ organizedNotes.length }}</span>
          </h4>
          <div class="space-y-2">
            <NoteListItem
              v-for="note in organizedNotes"
              :key="note.id"
              :note="note"
              :source-label="displaySourceLabel(note)"
              :source-route="displaySourceRoute(note)"
              @open="openNote(note)"
              @open-source="navigateToSource"
            />
          </div>
        </section>

        <div v-if="filteredNotes.length === 0" class="text-center py-10 px-4">
          <div class="mx-auto w-10 h-10 rounded-2xl bg-navy-50 flex items-center justify-center text-navy-300 mb-3">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <p class="text-xs text-navy-400">{{ emptyText }}</p>
          <p v-if="!keyword" class="text-[11px] text-navy-300 mt-1">在学习页选中文字，或点上方快速记一条</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  createNote as createNoteApi,
  getNoteById,
  getNoteResources,
  getNotes,
  updateNote,
} from '@/api/note'
import { getResource } from '@/api/resource'
import { formatNoteSSE } from '@/api/noteAgent'
import { issueTicket } from '@/api/auth'
import type { Note, NoteResourceRel, NoteType, OrganizeStatus } from '@/types/note'
import { useNoteCaptureStore, type NoteCaptureMode } from '@/stores/noteCapture'
import { useUiStore } from '@/stores/ui'
import { showToast } from '@/composables/useToast'
import {
  isGenericSourceLabel,
  noteGroup,
  noteSourceDisplay,
  resolveNoteSourceRoute,
  toSourceLabel,
} from './notePresentation'
import {
  appendExcerptBlock,
  buildFormatPayload,
  joinExcerptsFromContent,
  migrateLegacyToInterleaved,
  parseNoteBlocks,
  normalizeInterleavedOrder,
  preserveInterleavedStructure,
  stripFormatArtifacts,
} from './noteBlocks'
import {
  excerptInputFromSeed,
  useNoteCapture,
  type NoteCapturePendingFilter,
} from './useNoteCapture'
import { useNoteDraft } from './useNoteDraft'
import NoteCaptureEditor from './NoteCaptureEditor.vue'
import NoteListItem from './NoteListItem.vue'

type FilterValue = NoteCapturePendingFilter

const router = useRouter()
const uiStore = useUiStore()
const noteCaptureStore = useNoteCaptureStore()
const capture = useNoteCapture()
const editorRef = ref<InstanceType<typeof NoteCaptureEditor> | null>(null)

const notes = ref<Note[]>([])
const keyword = ref('')
const sourceLabels = ref<Record<number, string | null>>({})
const sourceRoutes = ref<Record<number, string | null>>({})
const listStatus = ref<'idle' | 'loading' | 'error'>('idle')
const organizing = ref(false)
const organizeError = ref(false)
let organizeAbort: (() => void) | null = null
/** Serialize capture apply so concurrent requests don't clobber each other. */
let applyingCapture = false

const draftModel = useNoteDraft({
  createNote: createNoteApi,
  updateNote,
  storage: localStorage,
  debounceMs: 800,
  autoSave: false,
})

const draft = computed(() => draftModel.draft.value)
const saveStatus = computed(() => draftModel.saveStatus.value)
const statusLabel = computed(() => draftModel.statusLabel.value)

const filterOptions: { value: FilterValue; label: string }[] = [
  { value: 'recent', label: '最近' },
  { value: 'pinned', label: '置顶' },
  { value: 'has-source', label: '有来源' },
]

const emptyText = computed(() => (keyword.value ? '没有匹配的笔记' : '暂无笔记'))

const filteredNotes = computed(() => {
  let list = notes.value
  const filter = capture.pendingFilter.value
  if (filter === 'pinned') {
    list = list.filter(n => n.isPinned === 1)
  } else if (filter === 'has-source') {
    list = list.filter(n => Boolean(n.sourceTitle || n.sourceType || sourceLabels.value[n.id]))
  } else if (filter === 'recent') {
    list = [...list].sort((a, b) => {
      const ta = new Date(a.updatedAt).getTime() || 0
      const tb = new Date(b.updatedAt).getTime() || 0
      return tb - ta
    })
  }
  return list
})

const pendingNotes = computed(() => filteredNotes.value.filter(n => noteGroup(n) === 'pending'))
const organizedNotes = computed(() => filteredNotes.value.filter(n => noteGroup(n) === 'organized'))

function displaySourceLabel(note: Note): string | null {
  return noteSourceDisplay(note, sourceLabels.value[note.id])
}

function displaySourceRoute(note: Note): string | null {
  const stored = note.sourceRoute?.trim()
  if (stored) return stored
  return sourceRoutes.value[note.id] ?? null
}

function navigateToSource(routePath: string) {
  if (!routePath?.trim()) return
  // Keep the notes panel open so user can return after peeking the source
  void router.push(routePath)
}

function toggleFilter(value: FilterValue) {
  capture.pendingFilter.value = capture.pendingFilter.value === value ? null : value
}

function onModeChange(mode: NoteCaptureMode) {
  capture.mode.value = mode
  if (draft.value) {
    const fields: { noteType: NoteType; organizeStatus?: OrganizeStatus } = { noteType: mode }
    if (draft.value.organizeStatus === 'organized') fields.organizeStatus = 'pending'
    draftModel.setFields(fields)
  }
}

function onFieldInput(patch: { noteName?: string; content?: string }) {
  if (!draft.value) return
  const fields = { ...patch } as Parameters<typeof draftModel.setFields>[0]
  if (draft.value.organizeStatus === 'organized') {
    fields.organizeStatus = 'pending'
  }
  draftModel.setFields(fields)
}

function onRemoveSource() {
  capture.removeSource()
  if (!draft.value) return
  // Clear source fields on draft without wiping excerpt/content
  draftModel.setFields({
    sourceType: undefined,
    sourceId: undefined,
    sourceTitle: undefined,
    sourceRoute: undefined,
    ...(draft.value.organizeStatus === 'organized' ? { organizeStatus: 'pending' as OrganizeStatus } : {}),
  })
}

function retrySave() {
  void draftModel.retrySave()
}

function manualSave() {
  void draftModel.saveNow()
}

function expandCapture() {
  if (!draft.value) {
    draftModel.startNewNote({
      mode: capture.mode.value,
      organizeStatus: 'pending',
      source: capture.source.value,
      excerpt: capture.excerpt.value || undefined,
    })
  }
  capture.expanded.value = true
  void nextTick(() => editorRef.value?.focusContent?.())
}

function collapseCapture() {
  capture.expanded.value = false
}

async function openNote(note: Note) {
  if (draft.value && draft.value.id !== note.id && draftModel.hasUnsavedChanges()) {
    const ok = await draftModel.flushIfDirty()
    if (!ok) {
      showToast('当前笔记保存失败，请先重试保存再切换', 'error', { title: '无法切换' })
      return
    }
  }
  // Open with interleaved content (migrate legacy split fields if needed)
  const migratedContent = migrateLegacyToInterleaved(note.content, note.excerpt)
  draftModel.openNote({ ...note, content: migratedContent })
  applyCaptureUiFromContent(migratedContent, note)
  capture.expanded.value = true
  organizeError.value = note.organizeStatus === 'error'
}

async function startNewNote() {
  if (draftModel.hasUnsavedChanges()) {
    const ok = await draftModel.flushIfDirty()
    if (!ok) {
      showToast('当前笔记保存失败，请先重试保存', 'error', { title: '无法新建' })
      return
    }
  }
  capture.mode.value = 'quick'
  capture.source.value = null
  capture.excerpt.value = ''
  organizeError.value = false
  draftModel.startNewNote({ mode: 'quick', organizeStatus: 'pending' })
  capture.expanded.value = true
  void nextTick(() => editorRef.value?.focusContent?.())
}

/** Sync capture mode/source/excerpt chrome from note content + meta. */
function applyCaptureUiFromContent(content: string, note?: Partial<Note>) {
  const blocks = parseNoteBlocks(content)
  const lastEx = [...blocks].reverse().find(b => b.type === 'excerpt')
  capture.excerpt.value = lastEx && lastEx.type === 'excerpt' ? lastEx.text : ''
  capture.mode.value = (note?.noteType as NoteCaptureMode) || (lastEx ? 'excerpt' : 'quick')

  const resolvedLabel = note ? displaySourceLabel(note as Note) : null
  const resolvedRoute = note ? displaySourceRoute(note as Note) : null
  if (note?.sourceTitle || note?.sourceType || resolvedLabel || resolvedRoute || lastEx) {
    const fromBlock = lastEx && lastEx.type === 'excerpt' ? lastEx : null
    capture.source.value = {
      sourceType: note?.sourceType === 'knowledge_tree'
        ? 'knowledge-node'
        : (note?.sourceType as 'plan' | 'resource' | 'tutor')
          || (fromBlock?.sourceType as 'plan' | 'resource' | 'tutor')
          || 'resource',
      sourceId: note?.sourceId ?? fromBlock?.sourceId,
      sourceTitle: resolvedLabel || note?.sourceTitle || fromBlock?.sourceTitle || '学习来源',
      sourceRoute: resolvedRoute || note?.sourceRoute || fromBlock?.sourceRoute || '',
    }
  } else {
    capture.source.value = null
  }
}

function setCaptureSourceFromSeed(seed: {
  sourceType?: string
  sourceId?: number
  sourceTitle?: string
  sourceRoute?: string
}) {
  if (!seed.sourceType && !seed.sourceTitle) return
  capture.source.value = {
    sourceType: seed.sourceType === 'knowledge_tree'
      ? 'knowledge-node'
      : (seed.sourceType as 'plan' | 'resource' | 'tutor') || 'resource',
    sourceId: seed.sourceId,
    sourceTitle: seed.sourceTitle || '学习来源',
    sourceRoute: seed.sourceRoute || '',
  }
}

function openFullEditor() {
  const note = draft.value
  if (note && note.id > 0) {
    router.push(`/notes/${note.id}`)
  }
}

async function applyCaptureSeed() {
  // Only consume after dirty draft is safely flushed (leave pending on flush failure)
  if (!noteCaptureStore.pendingRequest) return
  if (applyingCapture) return
  applyingCapture = true

  try {
    if (draftModel.hasUnsavedChanges()) {
      const ok = await draftModel.flushIfDirty()
      if (!ok) {
        showToast('当前笔记保存失败，摘录未写入。请保存后重试', 'error', { title: '捕获中断' })
        return
      }
    }

    const seed = capture.consumeRequest()
    if (!seed) return
    organizeError.value = false

    // ── Append to existing note ──
    if (seed.openNoteId != null && seed.openNoteId > 0) {
      const targetId = seed.openNoteId
      const excerptMeta = excerptInputFromSeed(seed)

      // Prefer in-memory draft when already editing this note (keeps unsaved local edits)
      let baseContent: string
      let noteMeta: Note | null = notes.value.find(n => n.id === targetId) ?? null

      if (draft.value?.id === targetId) {
        baseContent = draft.value.content || ''
        // Keep meta for patches; draft is source of content truth
        if (!noteMeta) {
          noteMeta = {
            id: targetId,
            userId: 0,
            noteName: draft.value.noteName,
            content: draft.value.content,
            createdAt: '',
            updatedAt: '',
            noteType: draft.value.noteType,
            organizeStatus: draft.value.organizeStatus,
            sourceType: draft.value.sourceType,
            sourceId: draft.value.sourceId,
            sourceTitle: draft.value.sourceTitle,
            sourceRoute: draft.value.sourceRoute,
          }
        }
      } else {
        // Always re-fetch by id so append sees full latest body (list may be stale/empty)
        try {
          const res = await getNoteById(targetId)
          noteMeta = res.data ?? null
        } catch {
          noteMeta = null
        }
        if (!noteMeta) {
          // Drop ghost entry from sidebar list if server says gone
          notes.value = notes.value.filter(n => n.id !== targetId)
          showToast('目标笔记不存在或已删除', 'error', { title: '追加失败' })
          return
        }
        baseContent = migrateLegacyToInterleaved(noteMeta.content, noteMeta.excerpt)
      }

      const nextContent = excerptMeta
        ? appendExcerptBlock(baseContent, excerptMeta)
        : baseContent

      if (draft.value?.id === targetId) {
        const patches: Parameters<typeof draftModel.setFields>[0] = {
          content: nextContent,
          noteType: 'excerpt',
          ...(seed.excerpt ? { excerpt: seed.excerpt } : {}),
        }
        if (seed.sourceType) patches.sourceType = seed.sourceType
        if (seed.sourceId !== undefined) patches.sourceId = seed.sourceId
        if (seed.sourceTitle) patches.sourceTitle = seed.sourceTitle
        if (seed.sourceRoute) patches.sourceRoute = seed.sourceRoute
        if (draft.value.organizeStatus === 'organized') patches.organizeStatus = 'pending'
        draftModel.setFields(patches)
      } else {
        const note = noteMeta!
        draftModel.openNote({
          ...note,
          content: nextContent,
          excerpt: undefined,
          noteType: 'excerpt',
          ...(note.organizeStatus === 'organized' ? { organizeStatus: 'pending' as OrganizeStatus } : {}),
          ...(seed.sourceType ? { sourceType: seed.sourceType } : {}),
          ...(seed.sourceId !== undefined ? { sourceId: seed.sourceId } : {}),
          ...(seed.sourceTitle ? { sourceTitle: seed.sourceTitle } : {}),
          ...(seed.sourceRoute ? { sourceRoute: seed.sourceRoute } : {}),
        })
        // openNote resets dirty; re-mark content change
        draftModel.setFields({
          content: nextContent,
          noteType: 'excerpt',
          ...(note.organizeStatus === 'organized' ? { organizeStatus: 'pending' as OrganizeStatus } : {}),
          ...(seed.sourceType ? { sourceType: seed.sourceType } : {}),
          ...(seed.sourceId !== undefined ? { sourceId: seed.sourceId } : {}),
          ...(seed.sourceTitle ? { sourceTitle: seed.sourceTitle } : {}),
          ...(seed.sourceRoute ? { sourceRoute: seed.sourceRoute } : {}),
        })
      }

      if (seed.excerpt) {
        capture.excerpt.value = seed.excerpt
        capture.mode.value = 'excerpt'
      }
      setCaptureSourceFromSeed(seed)
      capture.expanded.value = true
      // 不自动保存：用户可能还要改标题/补笔记，由手动「保存」落库
      showToast('已追加原文，记得点保存', 'info', { title: '追加成功' })
      void nextTick(() => {
        editorRef.value?.scrollContentToEnd?.()
        editorRef.value?.focusContent?.()
      })
      return
    }

    // ── New capture: [原文] + empty 笔记 slot（草稿，不自动创建）──
    const excerptMeta = excerptInputFromSeed(seed)
    const initialContent = excerptMeta
      ? appendExcerptBlock(seed.content || '', excerptMeta)
      : (seed.content ?? '')

    draftModel.startNewNote({
      mode: 'excerpt',
      noteType: seed.noteType ?? 'excerpt',
      organizeStatus: seed.organizeStatus ?? 'pending',
      sourceType: seed.sourceType,
      sourceId: seed.sourceId,
      sourceTitle: seed.sourceTitle,
      sourceRoute: seed.sourceRoute,
      content: initialContent,
      noteName: seed.noteName,
      excerpt: seed.excerpt,
    })
    setCaptureSourceFromSeed(seed)
    capture.expanded.value = true
    showToast('已填入摘录，可继续编辑后保存', 'info', { title: '新建草稿' })

    void nextTick(() => {
      editorRef.value?.scrollContentToEnd?.()
      editorRef.value?.focusContent?.()
    })
  } finally {
    applyingCapture = false
    // Drain another request that arrived while we were applying
    if (noteCaptureStore.pendingRequest) {
      void applyCaptureSeed()
    }
  }
}

async function loadNotes(opts?: { soft?: boolean }) {
  const requestId = ++listRequestId
  // Soft refresh keeps the list painted (avoid flicker after delete/save)
  if (!opts?.soft || notes.value.length === 0) {
    listStatus.value = 'loading'
  }
  try {
    const res = await getNotes({ page: 1, size: 50, keyword: keyword.value || undefined })
    if (requestId !== listRequestId) return
    const data = res.data
    const records = Array.isArray(data)
      ? data
      : (Array.isArray((data as { records?: Note[] } | null)?.records)
          ? (data as { records: Note[] }).records
          : [])
    notes.value = records
    listStatus.value = 'idle'
    void loadSourceLabels(notes.value, requestId)
  } catch {
    if (requestId !== listRequestId) return
    notes.value = []
    sourceLabels.value = {}
    sourceRoutes.value = {}
    listStatus.value = 'error'
  }
}

async function resolveNoteSourceMeta(note: Note): Promise<{ id: number; label: string | null; route: string | null }> {
  let label = note.sourceTitle?.trim() || null
  let route = note.sourceRoute?.trim() || null
  let rels: NoteResourceRel[] = []

  try {
    const res = await getNoteResources(note.id)
    rels = res.data ?? []
  } catch {
    // ignore — resource links are optional enrichment
  }

  const rel = rels[0] ?? null
  const relLabel = toSourceLabel(rels)
  if (relLabel && (!label || isGenericSourceLabel(label))) {
    label = relLabel
  }

  if (!route) {
    route = resolveNoteSourceRoute(note, rel)
  }

  // Fetch the real resource title / planId when we only have an id
  const resourceId =
    (note.sourceType === 'resource' && note.sourceId) ? note.sourceId : rel?.resourceId

  if (resourceId && (isGenericSourceLabel(label) || !route)) {
    try {
      const res = await getResource(resourceId)
      const resource = res.data
      if (resource) {
        const realTitle =
          resource.moduleData?.title
          || resource.moduleData?.module_title
          || resource.moduleData?.name
        if (realTitle && isGenericSourceLabel(label)) {
          label = String(realTitle)
        }
        if (!route && resource.planId) {
          route = resolveNoteSourceRoute(note, rel, resource.planId)
        }
      }
    } catch {
      // resource may be deleted — keep fallback label
    }
  }

  if (!route) {
    route = resolveNoteSourceRoute(note, rel)
  }

  return { id: note.id, label, route }
}

async function loadSourceLabels(list: Note[], requestId: number) {
  if (list.length === 0) {
    sourceLabels.value = {}
    sourceRoutes.value = {}
    return
  }
  const results = await Promise.allSettled(list.map(note => resolveNoteSourceMeta(note)))
  const nextLabels: Record<number, string | null> = {}
  const nextRoutes: Record<number, string | null> = {}
  results.forEach((r, idx) => {
    const note = list[idx]
    if (r.status === 'fulfilled') {
      nextLabels[note.id] = r.value.label
      nextRoutes[note.id] = r.value.route
    }
  })
  if (requestId === listRequestId) {
    sourceLabels.value = nextLabels
    sourceRoutes.value = nextRoutes
  }
}

async function organizeCurrentNote() {
  const current = draft.value
  if (!current || current.id <= 0 || organizing.value) return
  if (!current.content?.trim()) return

  organizing.value = true
  organizeError.value = false
  draftModel.setFields({ organizeStatus: 'organizing' })
  await draftModel.saveNow()

  try {
    const ticketRes = await issueTicket()
    const ticket = ticketRes.data?.ticket
    if (!ticket || typeof ticket !== 'string') {
      throw new Error('无法获取认证票据')
    }

    const originalContent = current.content
    // 有原文块时只整理补充笔记，避免 AI 把穿插结构抹平成一篇文章
    const { contentForAi } = buildFormatPayload(originalContent)
    await new Promise<void>((resolve, reject) => {
      const { abort } = formatNoteSSE(
        ticket,
        contentForAi,
        {
          onDone: (formatted) => {
            // Keep 原文 blocks; only accept AI polish on user-note portions
            const merged = normalizeInterleavedOrder(
              stripFormatArtifacts(
                preserveInterleavedStructure(originalContent, formatted),
              ),
            )
            draftModel.setFields({
              content: merged,
              organizeStatus: 'organized',
            })
            // Reflect in local list immediately
            const idx = notes.value.findIndex(n => n.id === current.id)
            if (idx >= 0) {
              notes.value[idx] = {
                ...notes.value[idx],
                content: merged,
                organizeStatus: 'organized',
              }
            }
            resolve()
          },
          onError: (err) => reject(new Error(err)),
        },
        undefined,
        {
          excerpt: joinExcerptsFromContent(originalContent),
          sourceTitle: current.sourceTitle,
          noteType: current.noteType,
        },
      )
      organizeAbort = abort
    })
    await draftModel.saveNow()
  } catch {
    organizeError.value = true
    draftModel.setFields({ organizeStatus: 'error' })
    await draftModel.saveNow()
  } finally {
    organizing.value = false
    organizeAbort = null
  }
}

let listRequestId = 0
let lastPersistedDraftId = 0
let searchTimer: ReturnType<typeof setTimeout> | null = null
let collapseTimer: ReturnType<typeof setTimeout> | null = null

watch(saveStatus, (status) => {
  const currentId = draft.value?.id ?? 0
  if (status === 'saved' && currentId > 0) {
    const isFirstPersist = currentId !== lastPersistedDraftId
    lastPersistedDraftId = currentId
    // Keep list previews in sync; also notify append pickers on other pages
    void loadNotes({ soft: true })
    noteCaptureStore.notifyNotesChanged()
    // Collapse only after first create so user sees "已保存"
    if (isFirstPersist) {
      if (collapseTimer) clearTimeout(collapseTimer)
      collapseTimer = setTimeout(() => {
        collapseTimer = null
        if (!organizing.value && draft.value?.id === currentId) {
          capture.expanded.value = false
        }
      }, 1200)
    }
  }
})

watch(keyword, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    searchTimer = null
    void loadNotes()
  }, 300)
})

// External create/update/delete (e.g. 我的笔记页删除) → refresh list & clear deleted draft
watch(
  () => noteCaptureStore.notesListEpoch,
  () => {
    const removedId = noteCaptureStore.lastRemovedNoteId
    if (removedId != null && removedId > 0) {
      notes.value = notes.value.filter(n => n.id !== removedId)
      if (sourceLabels.value[removedId] !== undefined) {
        const next = { ...sourceLabels.value }
        delete next[removedId]
        sourceLabels.value = next
      }
      if (sourceRoutes.value[removedId] !== undefined) {
        const next = { ...sourceRoutes.value }
        delete next[removedId]
        sourceRoutes.value = next
      }
      if (draft.value?.id === removedId) {
        draftModel.clearDraft()
        capture.expanded.value = false
        capture.source.value = null
        capture.excerpt.value = ''
        organizeError.value = false
        lastPersistedDraftId = 0
        showToast('当前笔记已删除', 'info', { title: '笔记已移除' })
      }
    }
    void loadNotes({ soft: true })
  },
)

// When async source titles/routes resolve, refresh the open editor badge
watch([sourceLabels, sourceRoutes], () => {
  const current = draft.value
  if (!current || current.id <= 0 || !capture.source.value) return
  const note = notes.value.find(n => n.id === current.id)
  if (!note) return
  const label = displaySourceLabel(note)
  const routePath = displaySourceRoute(note)
  if (!label && !routePath) return
  const prev = capture.source.value
  if (
    (label && (isGenericSourceLabel(prev.sourceTitle) || prev.sourceTitle !== label))
    || (routePath && !prev.sourceRoute)
  ) {
    capture.source.value = {
      ...prev,
      sourceTitle: label || prev.sourceTitle,
      sourceRoute: routePath || prev.sourceRoute,
    }
  }
})

// Consume when panel opens (sidebar just mounted)
watch(
  () => uiStore.notesPanelOpen,
  (open) => {
    if (open) void applyCaptureSeed()
  },
  { immediate: true },
)

// Consume when a new request arrives while the panel is already open
watch(
  () => noteCaptureStore.pendingRequest,
  (req) => {
    if (req && uiStore.notesPanelOpen) void applyCaptureSeed()
  },
)

// If capture was deferred because dirty save failed, retry after a successful save
watch(
  () => saveStatus.value,
  (s) => {
    if (s === 'saved' && noteCaptureStore.pendingRequest && uiStore.notesPanelOpen) {
      void applyCaptureSeed()
    }
  },
)

onMounted(() => {
  void loadNotes()
  const recovered = draftModel.recoverNewDraft()
  if (recovered) {
    draftModel.startNewNote()
    capture.mode.value = (recovered.noteType as NoteCaptureMode) || 'quick'
    capture.excerpt.value = recovered.excerpt || ''
    if (recovered.sourceTitle || recovered.sourceType) {
      capture.source.value = {
        sourceType: recovered.sourceType === 'knowledge_tree'
          ? 'knowledge-node'
          : (recovered.sourceType as 'plan' | 'resource' | 'tutor') || 'plan',
        sourceId: recovered.sourceId,
        sourceTitle: recovered.sourceTitle || '学习来源',
        sourceRoute: recovered.sourceRoute || '',
      }
    }
    capture.expanded.value = true
  }
  // Also try consume in case request arrived before mount
  void applyCaptureSeed()
})

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
  if (collapseTimer) clearTimeout(collapseTimer)
  if (organizeAbort) organizeAbort()
  void draftModel.dispose()
})
</script>
