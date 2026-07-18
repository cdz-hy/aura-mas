import { computed, ref } from 'vue'
import type { Note, NoteCreateRequest, NoteSourceType, NoteType, OrganizeStatus } from '@/types/note'
import { mapCaptureSourceToApi, type NoteCaptureMode, type NoteCaptureSource } from '@/stores/noteCapture'
import { appendExcerptBlock } from './noteBlocks'

export type NoteSaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'error'

export const NOTE_DRAFT_STORAGE_KEY = 'aura.note-sidebar.new-draft.v1'
export const NOTE_AUTOSAVE_DEBOUNCE_MS = 800

export interface NoteDraftState {
  id: number
  noteName: string
  content: string
  noteType?: NoteType
  organizeStatus?: OrganizeStatus
  sourceType?: NoteSourceType
  sourceId?: number
  sourceTitle?: string
  sourceRoute?: string
  excerpt?: string
}

export interface NoteDraftSeed {
  noteName?: string
  content?: string
  noteType?: NoteType
  mode?: NoteCaptureMode
  organizeStatus?: OrganizeStatus
  sourceType?: NoteSourceType
  sourceId?: number
  sourceTitle?: string
  sourceRoute?: string
  excerpt?: string
  source?: NoteCaptureSource | null
}

export interface NoteDraftAdapters {
  createNote: (data: NoteCreateRequest) => Promise<{ data: Note }>
  updateNote: (noteId: number, data: Partial<NoteCreateRequest>) => Promise<{ data: Note }>
  storage?: Storage
  debounceMs?: number
  /** When false, edits mark dirty but only persist via saveNow / dispose / retrySave. Default true. */
  autoSave?: boolean
}

export function saveStatusLabel(status: NoteSaveStatus): string {
  switch (status) {
    case 'saving':
      return '保存中'
    case 'dirty':
      return '等待保存'
    case 'saved':
      return '已保存'
    case 'error':
      return '保存失败，点击重试'
    default:
      return ''
  }
}

function captureFieldsFromSeed(seed?: NoteDraftSeed): Partial<NoteDraftState> {
  if (!seed) return {}

  const fromSource = mapCaptureSourceToApi(seed.source ?? null)
  const noteType = seed.noteType ?? seed.mode

  return {
    ...(noteType ? { noteType } : {}),
    ...(seed.organizeStatus ? { organizeStatus: seed.organizeStatus } : {}),
    ...(seed.sourceType ? { sourceType: seed.sourceType } : fromSource.sourceType ? { sourceType: fromSource.sourceType } : {}),
    ...(seed.sourceId !== undefined ? { sourceId: seed.sourceId } : fromSource.sourceId !== undefined ? { sourceId: fromSource.sourceId } : {}),
    ...(seed.sourceTitle !== undefined ? { sourceTitle: seed.sourceTitle } : fromSource.sourceTitle ? { sourceTitle: fromSource.sourceTitle } : {}),
    ...(seed.sourceRoute !== undefined ? { sourceRoute: seed.sourceRoute } : fromSource.sourceRoute ? { sourceRoute: fromSource.sourceRoute } : {}),
    ...(seed.excerpt !== undefined ? { excerpt: seed.excerpt } : {}),
  }
}

function normalizePayload(draft: NoteDraftState): NoteCreateRequest {
  const payload: NoteCreateRequest = {
    noteName: draft.noteName.trim() || '无标题笔记',
    content: draft.content.trim() || ' ',
  }
  if (draft.noteType) payload.noteType = draft.noteType
  if (draft.organizeStatus) payload.organizeStatus = draft.organizeStatus
  if (draft.sourceType) payload.sourceType = draft.sourceType
  if (draft.sourceId !== undefined) payload.sourceId = draft.sourceId
  if (draft.sourceTitle !== undefined) payload.sourceTitle = draft.sourceTitle
  if (draft.sourceRoute !== undefined) payload.sourceRoute = draft.sourceRoute
  if (draft.excerpt !== undefined) payload.excerpt = draft.excerpt
  return payload
}

function parseRecoveredDraft(raw: string): NoteDraftState | null {
  try {
    const parsed = JSON.parse(raw) as Partial<NoteDraftState>
    if (!parsed || typeof parsed !== 'object' || parsed.id !== 0) return null
    return {
      id: 0,
      noteName: typeof parsed.noteName === 'string' ? parsed.noteName : '',
      content: typeof parsed.content === 'string' ? parsed.content : '',
      ...(typeof parsed.noteType === 'string' ? { noteType: parsed.noteType as NoteType } : {}),
      ...(typeof parsed.organizeStatus === 'string' ? { organizeStatus: parsed.organizeStatus as OrganizeStatus } : {}),
      ...(typeof parsed.sourceType === 'string' ? { sourceType: parsed.sourceType as NoteSourceType } : {}),
      ...(typeof parsed.sourceId === 'number' ? { sourceId: parsed.sourceId } : {}),
      ...(typeof parsed.sourceTitle === 'string' ? { sourceTitle: parsed.sourceTitle } : {}),
      ...(typeof parsed.sourceRoute === 'string' ? { sourceRoute: parsed.sourceRoute } : {}),
      ...(typeof parsed.excerpt === 'string' ? { excerpt: parsed.excerpt } : {}),
    }
  } catch {
    return null
  }
}

export function useNoteDraft(adapters: NoteDraftAdapters) {
  const storage = adapters.storage ?? localStorage
  const debounceMs = adapters.debounceMs ?? NOTE_AUTOSAVE_DEBOUNCE_MS
  const autoSave = adapters.autoSave !== false

  const draft = ref<NoteDraftState | null>(null)
  const saveStatus = ref<NoteSaveStatus>('idle')
  const statusLabel = computed(() => saveStatusLabel(saveStatus.value))

  let timer: ReturnType<typeof setTimeout> | null = null
  let saveChain: Promise<void> = Promise.resolve()
  let generation = 0
  let revision = 0
  let savedRevision = 0

  function recoverNewDraft(): NoteDraftState | null {
    const raw = storage.getItem(NOTE_DRAFT_STORAGE_KEY)
    if (!raw) return null
    return parseRecoveredDraft(raw)
  }

  function writeLocalDraft(state: NoteDraftState) {
    storage.setItem(NOTE_DRAFT_STORAGE_KEY, JSON.stringify(state))
  }

  function clearLocalDraft() {
    storage.removeItem(NOTE_DRAFT_STORAGE_KEY)
  }

  function cancelTimer() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  function openNote(note: Pick<Note, 'id' | 'noteName' | 'content'> & Partial<NoteDraftState>) {
    cancelTimer()
    generation += 1
    revision = 0
    savedRevision = 0
    draft.value = {
      id: note.id,
      noteName: note.noteName,
      content: note.content,
      ...(note.noteType ? { noteType: note.noteType } : {}),
      ...(note.organizeStatus ? { organizeStatus: note.organizeStatus } : {}),
      ...(note.sourceType ? { sourceType: note.sourceType } : {}),
      ...(note.sourceId !== undefined ? { sourceId: note.sourceId } : {}),
      ...(note.sourceTitle !== undefined ? { sourceTitle: note.sourceTitle } : {}),
      ...(note.sourceRoute !== undefined ? { sourceRoute: note.sourceRoute } : {}),
      ...(note.excerpt !== undefined ? { excerpt: note.excerpt } : {}),
    }
    saveStatus.value = 'idle'
  }

  function draftHasPersistableData(state: NoteDraftState | null | undefined): boolean {
    if (!state) return false
    return Boolean(
      state.noteName?.trim()
      || state.content?.trim()
      || state.excerpt?.trim()
      || state.sourceTitle?.trim()
      || state.sourceType
      || state.noteType,
    )
  }

  function startNewNote(seed?: NoteDraftSeed) {
    cancelTimer()
    generation += 1
    revision = 0
    savedRevision = 0
    const recovered = recoverNewDraft()
    const capture = captureFieldsFromSeed(seed)
    // Prefer an explicit capture seed (excerpt/source) over a recovered local draft.
    const preferSeed = Boolean(
      seed && (seed.excerpt || seed.source || seed.sourceType || seed.sourceTitle || seed.content),
    )

    // 有摘录但没给 content 时，立刻写入「原文块」到正文，侧栏 textarea 才能马上看到
    let content = seed?.content ?? ''
    if (!content.trim() && seed?.excerpt?.trim()) {
      const api = mapCaptureSourceToApi(seed.source ?? null)
      content = appendExcerptBlock('', {
        text: seed.excerpt,
        sourceTitle: seed.sourceTitle ?? api.sourceTitle ?? seed.source?.sourceTitle,
        sourceRoute: seed.sourceRoute ?? api.sourceRoute ?? seed.source?.sourceRoute,
        sourceType: seed.sourceType ?? api.sourceType ?? seed.source?.sourceType,
        sourceId: seed.sourceId ?? api.sourceId ?? (
          typeof seed.source?.sourceId === 'number' ? seed.source.sourceId : undefined
        ),
      })
    }

    draft.value = (!preferSeed && recovered) ? recovered : {
      id: 0,
      noteName: seed?.noteName ?? '',
      content,
      ...capture,
    }
    // Capture/recovery often fills content without setFields — mark dirty so manual save works.
    if (draftHasPersistableData(draft.value)) {
      revision = 1
      savedRevision = 0
      saveStatus.value = 'dirty'
      writeLocalDraft(draft.value)
    } else {
      saveStatus.value = 'idle'
    }
  }

  function setFields(patch: Partial<Omit<NoteDraftState, 'id'>>) {
    if (!draft.value) return
    draft.value = { ...draft.value, ...patch }
    revision += 1
    saveStatus.value = 'dirty'
    if (draft.value.id === 0) {
      writeLocalDraft(draft.value)
    }
    if (autoSave) scheduleSave()
  }

  function scheduleSave() {
    if (!autoSave) return
    cancelTimer()
    timer = setTimeout(() => {
      timer = null
      void enqueueSave()
    }, debounceMs)
  }

  /** Explicit save (manual button). Cancels pending debounce and persists immediately. */
  function saveNow(): Promise<void> {
    cancelTimer()
    // Ensure capture-seeded drafts (revision never bumped) still persist.
    if (draft.value && revision <= savedRevision && draftHasPersistableData(draft.value)) {
      revision = savedRevision + 1
      if (saveStatus.value === 'idle' || saveStatus.value === 'saved') {
        saveStatus.value = 'dirty'
      }
    }
    return enqueueSave()
  }

  function enqueueSave(): Promise<void> {
    saveChain = saveChain.then(() => persist()).catch(() => {})
    return saveChain
  }

  async function persist() {
    const current = draft.value
    if (!current || revision <= savedRevision) return

    const snapshotRevision = revision
    if (current.id === 0) {
      await createDraft()
      return
    }

    const snapshotGeneration = generation
    const snapshot = { ...current }
    saveStatus.value = 'saving'
    try {
      await adapters.updateNote(snapshot.id, normalizePayload(snapshot))
      if (snapshotGeneration !== generation) return
      savedRevision = Math.max(savedRevision, snapshotRevision)
      saveStatus.value = revision === snapshotRevision ? 'saved' : 'dirty'
    } catch {
      if (snapshotGeneration !== generation) return
      saveStatus.value = revision === snapshotRevision ? 'error' : 'dirty'
    }
  }

  async function retrySave() {
    if (!draft.value) return
    cancelTimer()
    await enqueueSave()
  }

  async function createDraft(): Promise<Note | null> {
    const current = draft.value
    if (!current || current.id !== 0) return null

    const snapshotGeneration = generation
    const snapshotRevision = revision
    saveStatus.value = 'saving'
    try {
      const { data } = await adapters.createNote(normalizePayload(current))
      if (snapshotGeneration !== generation) return data
      const hasNewerEdits = revision !== snapshotRevision
      draft.value = {
        id: data.id,
        noteName: hasNewerEdits ? draft.value?.noteName ?? data.noteName : data.noteName,
        content: hasNewerEdits ? draft.value?.content ?? data.content : data.content,
        noteType: hasNewerEdits ? draft.value?.noteType ?? data.noteType : data.noteType,
        organizeStatus: hasNewerEdits ? draft.value?.organizeStatus ?? data.organizeStatus : data.organizeStatus,
        sourceType: hasNewerEdits ? draft.value?.sourceType ?? data.sourceType : data.sourceType,
        sourceId: hasNewerEdits ? draft.value?.sourceId ?? data.sourceId : data.sourceId,
        sourceTitle: hasNewerEdits ? draft.value?.sourceTitle ?? data.sourceTitle : data.sourceTitle,
        sourceRoute: hasNewerEdits ? draft.value?.sourceRoute ?? data.sourceRoute : data.sourceRoute,
        excerpt: hasNewerEdits ? draft.value?.excerpt ?? data.excerpt : data.excerpt,
      }
      clearLocalDraft()
      savedRevision = snapshotRevision
      saveStatus.value = hasNewerEdits ? 'dirty' : 'saved'
      if (hasNewerEdits && autoSave) scheduleSave()
      return data
    } catch {
      if (snapshotGeneration === generation) {
        writeLocalDraft(current)
        saveStatus.value = 'error'
      }
      return null
    }
  }

  async function createNewNote(): Promise<Note | null> {
    cancelTimer()
    let created: Note | null = null
    saveChain = saveChain
      .then(async () => {
        created = await createDraft()
      })
      .catch(() => {})
    await saveChain
    return created
  }

  function clearDraft() {
    cancelTimer()
    generation += 1
    revision = 0
    savedRevision = 0
    draft.value = null
    saveStatus.value = 'idle'
  }

  function dispose(): Promise<void> {
    cancelTimer()
    return enqueueSave()
  }

  /** True when draft has edits not yet confirmed saved. */
  function hasUnsavedChanges(): boolean {
    return Boolean(draft.value && revision > savedRevision)
  }

  /**
   * Persist dirty draft before switching context (open another note / new capture).
   * @returns true if safe to proceed (nothing to save, or save succeeded)
   */
  async function flushIfDirty(): Promise<boolean> {
    if (!hasUnsavedChanges()) return true
    await saveNow()
    // After save chain: error means still unsaved at last snapshot
    return saveStatus.value !== 'error'
  }

  return {
    draft,
    saveStatus,
    statusLabel,
    recoverNewDraft,
    openNote,
    startNewNote,
    setFields,
    retrySave,
    saveNow,
    createNewNote,
    clearDraft,
    dispose,
    flushSave: enqueueSave,
    hasUnsavedChanges,
    flushIfDirty,
  }
}
