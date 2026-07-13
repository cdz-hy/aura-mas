import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  resolveNoteCaptureSource,
  useNoteCaptureStore,
  type NoteCaptureSource,
} from './noteCapture'
import { useUiStore } from './ui'

describe('resolveNoteCaptureSource', () => {
  it('returns resource source metadata for a plan detail route with resource context', () => {
    const source = resolveNoteCaptureSource(
      {
        name: 'PlanDetail',
        fullPath: '/plan/1?resource=12',
        params: { id: '1' },
        query: {},
      },
      {
        sourceType: 'resource',
        sourceId: 12,
        title: '极限的定义',
      },
    )

    expect(source).toEqual<NoteCaptureSource>({
      sourceType: 'resource',
      sourceId: 12,
      sourceTitle: '极限的定义',
      sourceRoute: '/plan/1?resource=12',
    })
  })

  it('returns knowledge-node source for a tree view route', () => {
    const source = resolveNoteCaptureSource(
      {
        name: 'PlanDetail',
        fullPath: '/plan/1?view=tree',
        params: { id: '1' },
        query: { view: 'tree' },
      },
      {
        sourceType: 'knowledge-node',
        sourceId: 'node_child',
        title: '导数',
      },
    )

    expect(source).toEqual({
      sourceType: 'knowledge-node',
      sourceId: 'node_child',
      sourceTitle: '导数',
      sourceRoute: '/plan/1?view=tree',
    })
  })

  it('returns tutor source when context says tutor', () => {
    const source = resolveNoteCaptureSource(
      {
        name: 'dashboard',
        fullPath: '/dashboard',
        params: {},
        query: {},
      },
      {
        sourceType: 'tutor',
        sourceId: 'tutor_session_1',
        title: '智能辅导',
      },
    )

    expect(source).toEqual({
      sourceType: 'tutor',
      sourceId: 'tutor_session_1',
      sourceTitle: '智能辅导',
      sourceRoute: '/dashboard',
    })
  })

  it('produces no source for note-list and note-detail routes', () => {
    expect(
      resolveNoteCaptureSource({
        name: 'note-list',
        fullPath: '/notes',
        params: {},
        query: {},
      }),
    ).toBeNull()

    expect(
      resolveNoteCaptureSource(
        {
          name: 'NoteDetail',
          fullPath: '/notes/9',
          params: { id: '9' },
          query: {},
        },
        { title: '我的笔记' },
      ),
    ).toBeNull()
  })

  it('produces no source for home and settings routes', () => {
    expect(
      resolveNoteCaptureSource({
        name: 'Home',
        fullPath: '/',
        params: {},
        query: {},
      }),
    ).toBeNull()

    expect(
      resolveNoteCaptureSource({
        name: 'UserSettings',
        fullPath: '/settings',
        params: {},
        query: {},
      }),
    ).toBeNull()
  })
})

describe('useNoteCaptureStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('stores a capture request and opens the notes panel', () => {
    const store = useNoteCaptureStore()
    const ui = useUiStore()
    ui.tutorPanelOpen = true
    ui.notesPanelOpen = false

    const source: NoteCaptureSource = {
      sourceType: 'resource',
      sourceId: 12,
      sourceTitle: '极限的定义',
      sourceRoute: '/plan/1',
    }

    store.requestCapture({
      mode: 'excerpt',
      source,
      excerpt: '当 x 趋近于 a 时',
    })

    expect(store.pendingRequest).toMatchObject({
      mode: 'excerpt',
      source,
      excerpt: '当 x 趋近于 a 时',
    })
    expect(ui.notesPanelOpen).toBe(true)
    expect(ui.tutorPanelOpen).toBe(false)
  })

  it('lets takePendingRequest consume the request once', () => {
    const store = useNoteCaptureStore()
    store.requestCapture({ mode: 'quick', excerpt: '速记一句' })

    expect(store.takePendingRequest()).toEqual({
      mode: 'quick',
      source: undefined,
      excerpt: '速记一句',
      content: undefined,
      noteName: undefined,
      openNoteId: undefined,
      appendText: undefined,
    })
    expect(store.takePendingRequest()).toBeNull()
    expect(store.pendingRequest).toBeNull()
  })

  it('stores create/append fields for sidebar consumption', () => {
    const store = useNoteCaptureStore()
    store.requestCapture({
      mode: 'excerpt',
      excerpt: '选中句',
      noteName: '摘录 - 资源',
      openNoteId: 12,
      appendText: '选中句',
    })
    expect(store.pendingRequest).toMatchObject({
      noteName: '摘录 - 资源',
      openNoteId: 12,
      appendText: '选中句',
      excerpt: '选中句',
    })
  })
})
