import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { NoteSourceType } from '@/types/note'
import { useUiStore } from './ui'

export type NoteCaptureMode = 'excerpt' | 'quick' | 'question'

export interface NoteCaptureSource {
  sourceType: 'plan' | 'resource' | 'knowledge-node' | 'tutor'
  sourceId?: number | string
  sourceTitle: string
  sourceRoute: string
}

/** Map UI capture source into API/draft persistence fields (knowledge-node → knowledge_tree). */
export function mapCaptureSourceToApi(source: NoteCaptureSource | null | undefined): {
  sourceType?: NoteSourceType
  sourceId?: number
  sourceTitle?: string
  sourceRoute?: string
} {
  if (!source) return {}

  const sourceType: NoteSourceType =
    source.sourceType === 'knowledge-node' ? 'knowledge_tree' : source.sourceType

  let sourceId: number | undefined
  if (typeof source.sourceId === 'number' && Number.isFinite(source.sourceId)) {
    sourceId = source.sourceId
  } else if (typeof source.sourceId === 'string' && /^\d+$/.test(source.sourceId)) {
    sourceId = Number(source.sourceId)
  }

  return {
    sourceType,
    ...(sourceId !== undefined ? { sourceId } : {}),
    sourceTitle: source.sourceTitle,
    sourceRoute: source.sourceRoute,
  }
}

export interface NoteCaptureRequest {
  mode?: NoteCaptureMode
  source?: NoteCaptureSource
  /** Source excerpt (selected passage) */
  excerpt?: string
  /** Prefill note body (笔记补充) */
  content?: string
  /** Prefill optional title */
  noteName?: string
  /** Open an existing note in the sidebar (append / continue edit) */
  openNoteId?: number
}

export type NoteCaptureRouteLike = {
  name?: string | symbol | null
  fullPath: string
  params: Record<string, unknown>
  query: Record<string, unknown>
}

export type NoteCaptureSourceContext = {
  sourceType?: NoteCaptureSource['sourceType']
  sourceId?: number | string
  title?: string
}

const LEARNING_ROUTE_NAMES = new Set(['PlanDetail', 'PlanKnowledgeTree', 'knowledge-tree'])
const BLOCKED_ROUTE_NAMES = new Set([
  'Home',
  'note-list',
  'NoteDetail',
  'UserSettings',
  'profile',
  'dashboard',
  'FlashcardReview',
])

/**
 * Resolve automatic capture source from the current route.
 * Only learning surfaces produce a source; home/settings/note-list/detail do not.
 * Tutor sources are allowed when the caller explicitly passes sourceType: 'tutor'
 * (Tutor is a panel overlay, not a dedicated route).
 */
function planIdFromRoute(route: NoteCaptureRouteLike): string | number | undefined {
  const id = route.params.id ?? route.params.planId
  if (typeof id === 'string' || typeof id === 'number') return id
  return undefined
}

/** Prefer stable deep links over opaque fullPath (e.g. always include ?resource=). */
function buildLearningSourceRoute(
  route: NoteCaptureRouteLike,
  opts?: { resourceId?: number | string; tree?: boolean },
): string {
  const planId = planIdFromRoute(route)
  if (planId != null && opts?.resourceId != null) {
    return `/plan/${planId}?resource=${opts.resourceId}`
  }
  if (planId != null && opts?.tree) {
    return `/plan/${planId}?view=tree`
  }
  if (planId != null) {
    return `/plan/${planId}`
  }
  return route.fullPath
}

export function resolveNoteCaptureSource(
  route: NoteCaptureRouteLike,
  context?: NoteCaptureSourceContext,
): NoteCaptureSource | null {
  const name = typeof route.name === 'string' ? route.name : ''

  if (context?.sourceType === 'tutor') {
    return {
      sourceType: 'tutor',
      sourceId: context.sourceId,
      sourceTitle: context.title || '智能辅导',
      sourceRoute: route.fullPath,
    }
  }

  if (BLOCKED_ROUTE_NAMES.has(name)) return null
  if (!LEARNING_ROUTE_NAMES.has(name)) return null

  const isTree =
    name === 'PlanKnowledgeTree'
    || name === 'knowledge-tree'
    || route.query.view === 'tree'

  if (isTree || context?.sourceType === 'knowledge-node') {
    return {
      sourceType: 'knowledge-node',
      sourceId: context?.sourceId,
      sourceTitle: context?.title || '知识树节点',
      sourceRoute: buildLearningSourceRoute(route, { tree: true }),
    }
  }

  if (context?.sourceType === 'plan') {
    const sourceId = context.sourceId ?? planIdFromRoute(route)
    return {
      sourceType: 'plan',
      sourceId,
      sourceTitle: context.title || '学习计划',
      sourceRoute: buildLearningSourceRoute(route),
    }
  }

  if (context?.sourceType === 'resource' || context?.sourceId != null) {
    return {
      sourceType: 'resource',
      sourceId: context?.sourceId,
      sourceTitle: context?.title || '学习资源',
      sourceRoute: buildLearningSourceRoute(route, { resourceId: context?.sourceId }),
    }
  }

  return {
    sourceType: 'plan',
    sourceId: planIdFromRoute(route),
    sourceTitle: context?.title || '学习计划',
    sourceRoute: buildLearningSourceRoute(route),
  }
}

export const useNoteCaptureStore = defineStore('noteCapture', () => {
  const pendingRequest = ref<NoteCaptureRequest | null>(null)
  /**
   * Bumped whenever the server-side note list may have changed
   * (create / update / delete). Sidebar & append pickers watch this.
   */
  const notesListEpoch = ref(0)
  /** Most recent hard-deleted note id (for optimistic UI + draft clear). */
  const lastRemovedNoteId = ref<number | null>(null)

  function requestCapture(payload: NoteCaptureRequest): void {
    pendingRequest.value = {
      mode: payload.mode,
      source: payload.source,
      excerpt: payload.excerpt,
      content: payload.content,
      noteName: payload.noteName,
      openNoteId: payload.openNoteId,
    }

    const ui = useUiStore()
    ui.tutorPanelOpen = false
    ui.notesPanelOpen = true
  }

  function peekPendingRequest(): NoteCaptureRequest | null {
    return pendingRequest.value
  }

  function takePendingRequest(): NoteCaptureRequest | null {
    const current = pendingRequest.value
    pendingRequest.value = null
    return current
  }

  /** Broadcast list invalidation to sidebars / append pickers. */
  function notifyNotesChanged(payload?: { removedId?: number }): void {
    // Always set (or clear) so consumers don't re-apply a stale delete id
    lastRemovedNoteId.value =
      payload?.removedId != null && payload.removedId > 0
        ? payload.removedId
        : null
    notesListEpoch.value += 1
  }

  return {
    pendingRequest,
    notesListEpoch,
    lastRemovedNoteId,
    requestCapture,
    peekPendingRequest,
    takePendingRequest,
    notifyNotesChanged,
  }
})
