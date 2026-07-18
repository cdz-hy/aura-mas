import { ref } from 'vue'
import type { NoteSourceType, NoteType } from '@/types/note'
import {
  mapCaptureSourceToApi,
  useNoteCaptureStore,
  type NoteCaptureMode,
  type NoteCaptureSource,
} from '@/stores/noteCapture'

export type NoteCapturePendingFilter = 'recent' | 'pinned' | 'has-source' | null

/** Draft seed produced by consumeRequest — ready for useNoteDraft.startNewNote / openNote */
export interface NoteCaptureDraftSeed {
  noteType?: NoteType
  organizeStatus?: 'pending'
  sourceType?: NoteSourceType
  sourceId?: number
  sourceTitle?: string
  sourceRoute?: string
  excerpt?: string
  content?: string
  noteName?: string
  openNoteId?: number
}

export { mapCaptureSourceToApi }

export function toCaptureDraftSeed(input: {
  mode: NoteCaptureMode
  source: NoteCaptureSource | null
  excerpt: string
  content?: string
  noteName?: string
  openNoteId?: number
}): NoteCaptureDraftSeed {
  const seed: NoteCaptureDraftSeed = {
    noteType: input.mode,
    organizeStatus: 'pending',
    ...mapCaptureSourceToApi(input.source),
  }
  if (input.excerpt) seed.excerpt = input.excerpt
  if (input.content) seed.content = input.content
  if (input.noteName) seed.noteName = input.noteName
  if (input.openNoteId != null) seed.openNoteId = input.openNoteId
  return seed
}

/** Shared excerpt fence meta from a capture seed. */
export function excerptInputFromSeed(seed: NoteCaptureDraftSeed): {
  text: string
  sourceTitle?: string
  sourceRoute?: string
  sourceType?: string
  sourceId?: number
} | null {
  const text = seed.excerpt?.trim()
  if (!text) return null
  return {
    text,
    ...(seed.sourceTitle ? { sourceTitle: seed.sourceTitle } : {}),
    ...(seed.sourceRoute ? { sourceRoute: seed.sourceRoute } : {}),
    ...(seed.sourceType ? { sourceType: seed.sourceType } : {}),
    ...(typeof seed.sourceId === 'number' ? { sourceId: seed.sourceId } : {}),
  }
}

export function useNoteCapture() {
  const store = useNoteCaptureStore()

  const mode = ref<NoteCaptureMode>('quick')
  const source = ref<NoteCaptureSource | null>(null)
  const excerpt = ref('')
  const expanded = ref(false)
  const pendingFilter = ref<NoteCapturePendingFilter>(null)

  function openCapture(opts?: {
    mode?: NoteCaptureMode
    source?: NoteCaptureSource | null
    excerpt?: string
  }) {
    if (opts?.mode) mode.value = opts.mode
    if (opts && 'source' in opts) source.value = opts.source ?? null
    if (opts && 'excerpt' in opts) excerpt.value = opts.excerpt ?? ''
    expanded.value = true
  }

  function removeSource() {
    source.value = null
  }

  function consumeRequest(): NoteCaptureDraftSeed | null {
    const request = store.takePendingRequest()
    if (!request) return null

    const nextMode = request.mode ?? (request.excerpt ? 'excerpt' : 'quick')
    mode.value = nextMode
    if ('source' in request) source.value = request.source ?? null
    if ('excerpt' in request) excerpt.value = request.excerpt ?? ''
    expanded.value = true

    return toCaptureDraftSeed({
      mode: mode.value,
      source: source.value,
      excerpt: excerpt.value,
      content: request.content,
      noteName: request.noteName,
      openNoteId: request.openNoteId,
    })
  }

  return {
    mode,
    source,
    excerpt,
    expanded,
    pendingFilter,
    openCapture,
    removeSource,
    consumeRequest,
  }
}
