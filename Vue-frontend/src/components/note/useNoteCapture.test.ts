import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useNoteCapture } from './useNoteCapture'
import { useNoteCaptureStore, type NoteCaptureSource } from '@/stores/noteCapture'

describe('useNoteCapture', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('defaults to collapsed quick mode with no source', () => {
    const capture = useNoteCapture()

    expect(capture.mode.value).toBe('quick')
    expect(capture.source.value).toBeNull()
    expect(capture.excerpt.value).toBe('')
    expect(capture.expanded.value).toBe(false)
    expect(capture.pendingFilter.value).toBeNull()
  })

  it('consumes a pending request into capture state and draft seed fields', () => {
    const store = useNoteCaptureStore()
    const source: NoteCaptureSource = {
      sourceType: 'knowledge-node',
      sourceId: 'node_1',
      sourceTitle: '极限',
      sourceRoute: '/plan/3?view=tree',
    }
    store.requestCapture({
      mode: 'excerpt',
      source,
      excerpt: '选自知识树',
    })

    const capture = useNoteCapture()
    const seed = capture.consumeRequest()

    expect(capture.mode.value).toBe('excerpt')
    expect(capture.source.value).toEqual(source)
    expect(capture.excerpt.value).toBe('选自知识树')
    expect(capture.expanded.value).toBe(true)
    expect(seed).toEqual({
      noteType: 'excerpt',
      organizeStatus: 'pending',
      excerpt: '选自知识树',
      sourceType: 'knowledge_tree',
      sourceTitle: '极限',
      sourceRoute: '/plan/3?view=tree',
    })
    expect(store.pendingRequest).toBeNull()
  })

  it('maps numeric source ids into draft seed sourceId', () => {
    const store = useNoteCaptureStore()
    store.requestCapture({
      mode: 'excerpt',
      source: {
        sourceType: 'resource',
        sourceId: 12,
        sourceTitle: '资源标题',
        sourceRoute: '/plan/1',
      },
      excerpt: '摘录',
    })

    const seed = useNoteCapture().consumeRequest()
    expect(seed).toMatchObject({
      noteType: 'excerpt',
      organizeStatus: 'pending',
      sourceType: 'resource',
      sourceId: 12,
      sourceTitle: '资源标题',
      sourceRoute: '/plan/1',
      excerpt: '摘录',
    })
  })

  it('removes source without clearing excerpt or content seed', () => {
    const capture = useNoteCapture()
    capture.openCapture({
      mode: 'excerpt',
      source: {
        sourceType: 'plan',
        sourceId: 1,
        sourceTitle: '微积分',
        sourceRoute: '/plan/1',
      },
      excerpt: '保留摘录',
    })

    capture.removeSource()

    expect(capture.source.value).toBeNull()
    expect(capture.excerpt.value).toBe('保留摘录')
    expect(capture.mode.value).toBe('excerpt')
  })

  it('returns null from consumeRequest when nothing is pending', () => {
    expect(useNoteCapture().consumeRequest()).toBeNull()
  })

  it('passes create title and append-to-note fields through consumeRequest', () => {
    const store = useNoteCaptureStore()
    store.requestCapture({
      mode: 'excerpt',
      excerpt: '正文摘录',
      noteName: '摘录 - 资源名',
      openNoteId: 99,
      appendText: '追加段落',
    })

    const seed = useNoteCapture().consumeRequest()
    expect(seed).toMatchObject({
      noteType: 'excerpt',
      excerpt: '正文摘录',
      noteName: '摘录 - 资源名',
      openNoteId: 99,
      appendText: '追加段落',
    })
  })
})
