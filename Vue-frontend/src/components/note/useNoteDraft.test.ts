import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NOTE_DRAFT_STORAGE_KEY, saveStatusLabel, useNoteDraft } from './useNoteDraft'
import type { Note } from '@/types/note'

function memoryStorage(initial: Record<string, string> = {}): Storage {
  const map = new Map<string, string>(Object.entries(initial))
  return {
    get length() { return map.size },
    clear: () => map.clear(),
    getItem: (key: string) => map.get(key) ?? null,
    setItem: (key: string, value: string) => { map.set(key, value) },
    removeItem: (key: string) => { map.delete(key) },
    key: (index: number) => [...map.keys()][index] ?? null,
  }
}

function note(partial: Partial<Note> = {}): Note {
  return {
    id: 10,
    userId: 1,
    noteName: '已有笔记',
    content: '原文',
    createdAt: '',
    updatedAt: '',
    ...partial,
  }
}

describe('saveStatusLabel', () => {
  it('maps autosave statuses to Chinese labels', () => {
    expect(saveStatusLabel('saving')).toBe('保存中')
    expect(saveStatusLabel('dirty')).toBe('等待保存')
    expect(saveStatusLabel('saved')).toBe('已保存')
    expect(saveStatusLabel('error')).toBe('保存失败，点击重试')
    expect(saveStatusLabel('idle')).toBe('')
  })
})

describe('useNoteDraft', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  it('recovers an unsaved new-note draft from storage', () => {
    const storage = memoryStorage({
      [NOTE_DRAFT_STORAGE_KEY]: JSON.stringify({ id: 0, noteName: '草稿标题', content: '草稿正文' }),
    })
    const draft = useNoteDraft({
      createNote: vi.fn(),
      updateNote: vi.fn(),
      storage,
      debounceMs: 50,
    })

    expect(draft.recoverNewDraft()).toEqual({ id: 0, noteName: '草稿标题', content: '草稿正文' })
    draft.startNewNote()
    expect(draft.draft.value).toEqual({ id: 0, noteName: '草稿标题', content: '草稿正文' })
  })

  it('persists new-note edits locally until debounced creation succeeds', async () => {
    const storage = memoryStorage()
    const createNote = vi.fn().mockResolvedValue({
      data: note({ id: 99, noteName: '新笔记', content: '内容A' }),
    })
    const updateNote = vi.fn()
    const draft = useNoteDraft({ createNote, updateNote, storage, debounceMs: 50 })

    draft.startNewNote()
    draft.setFields({ noteName: '新笔记', content: '内容A' })
    expect(JSON.parse(storage.getItem(NOTE_DRAFT_STORAGE_KEY)!)).toEqual({
      id: 0,
      noteName: '新笔记',
      content: '内容A',
    })

    await vi.advanceTimersByTimeAsync(50)

    expect(createNote).toHaveBeenCalledWith({ noteName: '新笔记', content: '内容A' })
    expect(updateNote).not.toHaveBeenCalled()
    expect(storage.getItem(NOTE_DRAFT_STORAGE_KEY)).toBeNull()
    expect(draft.draft.value?.id).toBe(99)
    expect(draft.saveStatus.value).toBe('saved')
  })

  it('keeps a new-note draft locally when creation fails', async () => {
    const storage = memoryStorage()
    const createNote = vi.fn().mockRejectedValue(new Error('network'))
    const draft = useNoteDraft({
      createNote,
      updateNote: vi.fn(),
      storage,
      debounceMs: 50,
    })

    draft.startNewNote()
    draft.setFields({ noteName: '离线草稿', content: '仍需保留' })
    await vi.advanceTimersByTimeAsync(50)

    expect(draft.saveStatus.value).toBe('error')
    expect(JSON.parse(storage.getItem(NOTE_DRAFT_STORAGE_KEY)!)).toEqual({
      id: 0,
      noteName: '离线草稿',
      content: '仍需保留',
    })
  })

  it('autosaves existing notes after debounce and serializes saves', async () => {
    const updateNote = vi.fn()
      .mockResolvedValueOnce({ data: note({ content: '一' }) })
      .mockResolvedValueOnce({ data: note({ content: '二' }) })
    const draft = useNoteDraft({
      createNote: vi.fn(),
      updateNote,
      storage: memoryStorage(),
      debounceMs: 50,
    })

    draft.openNote(note({ content: '原文' }))
    draft.setFields({ content: '一' })
    draft.setFields({ content: '二' })
    await vi.advanceTimersByTimeAsync(50)
    await Promise.resolve()
    await Promise.resolve()

    expect(updateNote).toHaveBeenCalledTimes(1)
    expect(updateNote).toHaveBeenCalledWith(10, { noteName: '已有笔记', content: '二' })
    expect(draft.saveStatus.value).toBe('saved')
  })

  it('saves edits made while an older request is still in flight', async () => {
    let resolveFirst!: (value: { data: Note }) => void
    const firstSave = new Promise<{ data: Note }>((resolve) => {
      resolveFirst = resolve
    })
    const updateNote = vi.fn()
      .mockReturnValueOnce(firstSave)
      .mockResolvedValueOnce({ data: note({ content: '较新内容' }) })
    const draft = useNoteDraft({
      createNote: vi.fn(),
      updateNote,
      storage: memoryStorage(),
      debounceMs: 50,
    })

    draft.openNote(note())
    draft.setFields({ content: '较旧内容' })
    await vi.advanceTimersByTimeAsync(50)
    expect(updateNote).toHaveBeenCalledWith(10, { noteName: '已有笔记', content: '较旧内容' })

    draft.setFields({ content: '较新内容' })
    expect(draft.saveStatus.value).toBe('dirty')
    await vi.advanceTimersByTimeAsync(50)

    resolveFirst({ data: note({ content: '较旧内容' }) })
    await vi.waitFor(() => expect(updateNote).toHaveBeenCalledTimes(2))

    expect(updateNote).toHaveBeenLastCalledWith(10, { noteName: '已有笔记', content: '较新内容' })
    expect(draft.draft.value?.content).toBe('较新内容')
    expect(draft.saveStatus.value).toBe('saved')
  })

  it('flushes a pending existing-note edit when disposed', async () => {
    const updateNote = vi.fn().mockResolvedValue({ data: note({ content: '关闭前内容' }) })
    const draft = useNoteDraft({
      createNote: vi.fn(),
      updateNote,
      storage: memoryStorage(),
      debounceMs: 800,
    })

    draft.openNote(note())
    draft.setFields({ content: '关闭前内容' })
    await draft.dispose()

    expect(updateNote).toHaveBeenCalledWith(10, { noteName: '已有笔记', content: '关闭前内容' })
    expect(draft.saveStatus.value).toBe('saved')
  })

  it('exposes error status and retries a failed save', async () => {
    const updateNote = vi.fn()
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({ data: note({ content: '修好了' }) })
    const draft = useNoteDraft({
      createNote: vi.fn(),
      updateNote,
      storage: memoryStorage(),
      debounceMs: 50,
    })

    draft.openNote(note())
    draft.setFields({ content: '修好了' })
    await vi.advanceTimersByTimeAsync(50)
    await Promise.resolve()
    await Promise.resolve()

    expect(draft.saveStatus.value).toBe('error')
    expect(draft.statusLabel.value).toBe('保存失败，点击重试')

    await draft.retrySave()
    expect(updateNote).toHaveBeenCalledTimes(2)
    expect(draft.saveStatus.value).toBe('saved')
  })

  it('clears local draft after create succeeds', async () => {
    const storage = memoryStorage()
    const createNote = vi.fn().mockResolvedValue({ data: note({ id: 99, noteName: '新笔记', content: '正文' }) })
    const draft = useNoteDraft({
      createNote,
      updateNote: vi.fn(),
      storage,
      debounceMs: 50,
    })

    draft.startNewNote()
    draft.setFields({ noteName: '新笔记', content: '正文' })
    const created = await draft.createNewNote()

    expect(created?.id).toBe(99)
    expect(draft.draft.value?.id).toBe(99)
    expect(storage.getItem(NOTE_DRAFT_STORAGE_KEY)).toBeNull()
    expect(draft.saveStatus.value).toBe('saved')
  })

  it('accepts a capture seed and serializes mode/source/excerpt into local recovery storage', async () => {
    const storage = memoryStorage()
    const createNote = vi.fn().mockResolvedValue({
      data: note({
        id: 55,
        noteName: '无标题笔记',
        content: '我的理解',
        noteType: 'excerpt',
        organizeStatus: 'pending',
        sourceType: 'resource',
        sourceId: 12,
        sourceTitle: '极限的定义',
        sourceRoute: '/plan/1',
        excerpt: '当 x 趋近于 a 时',
      }),
    })
    const draft = useNoteDraft({
      createNote,
      updateNote: vi.fn(),
      storage,
      debounceMs: 50,
    })

    draft.startNewNote({
      mode: 'excerpt',
      content: '我的理解',
      excerpt: '当 x 趋近于 a 时',
      source: {
        sourceType: 'resource',
        sourceId: 12,
        sourceTitle: '极限的定义',
        sourceRoute: '/plan/1',
      },
      organizeStatus: 'pending',
    })

    expect(draft.draft.value).toMatchObject({
      id: 0,
      content: '我的理解',
      noteType: 'excerpt',
      organizeStatus: 'pending',
      sourceType: 'resource',
      sourceId: 12,
      sourceTitle: '极限的定义',
      sourceRoute: '/plan/1',
      excerpt: '当 x 趋近于 a 时',
    })

    draft.setFields({ noteName: '摘录笔记' })
    expect(JSON.parse(storage.getItem(NOTE_DRAFT_STORAGE_KEY)!)).toMatchObject({
      id: 0,
      noteName: '摘录笔记',
      noteType: 'excerpt',
      sourceType: 'resource',
      sourceId: 12,
      excerpt: '当 x 趋近于 a 时',
    })

    await vi.advanceTimersByTimeAsync(50)
    expect(createNote).toHaveBeenCalledWith(expect.objectContaining({
      noteName: '摘录笔记',
      content: '我的理解',
      noteType: 'excerpt',
      organizeStatus: 'pending',
      sourceType: 'resource',
      sourceId: 12,
      sourceTitle: '极限的定义',
      sourceRoute: '/plan/1',
      excerpt: '当 x 趋近于 a 时',
    }))
  })

  it('does not autosave when autoSave is disabled until saveNow is called', async () => {
    const updateNote = vi.fn().mockResolvedValue({ data: note({ content: '手动' }) })
    const draft = useNoteDraft({
      createNote: vi.fn(),
      updateNote,
      storage: memoryStorage(),
      debounceMs: 50,
      autoSave: false,
    })

    draft.openNote(note())
    draft.setFields({ content: '手动' })
    await vi.advanceTimersByTimeAsync(200)
    expect(updateNote).not.toHaveBeenCalled()
    expect(draft.saveStatus.value).toBe('dirty')

    await draft.saveNow()
    expect(updateNote).toHaveBeenCalledWith(10, { noteName: '已有笔记', content: '手动' })
    expect(draft.saveStatus.value).toBe('saved')
  })

  it('saves capture-seeded new drafts that never called setFields', async () => {
    const createNote = vi.fn().mockResolvedValue({
      data: note({ id: 77, noteName: '摘录笔记', content: '<<<excerpt id="a">>>\n原文\n<<< /excerpt >>>' }),
    })
    const draft = useNoteDraft({
      createNote,
      updateNote: vi.fn(),
      storage: memoryStorage(),
      debounceMs: 50,
      autoSave: false,
    })

    draft.startNewNote({
      mode: 'excerpt',
      noteName: '摘录笔记',
      content: '<<<excerpt id="a">>>\n原文\n<<< /excerpt >>>',
      source: {
        sourceType: 'resource',
        sourceId: 1,
        sourceTitle: '资源',
        sourceRoute: '/plan/1?resource=1',
      },
    })

    // Seed fills content without setFields — previously revision stayed 0 and save no-op'd
    expect(draft.saveStatus.value).toBe('dirty')
    await draft.saveNow()
    expect(createNote).toHaveBeenCalled()
    expect(draft.draft.value?.id).toBe(77)
    expect(draft.saveStatus.value).toBe('saved')
  })

  it('maps knowledge-node capture source to knowledge_tree in the create payload', async () => {
    const storage = memoryStorage()
    const createNote = vi.fn().mockResolvedValue({ data: note({ id: 7 }) })
    const draft = useNoteDraft({
      createNote,
      updateNote: vi.fn(),
      storage,
      debounceMs: 50,
    })

    draft.startNewNote({
      mode: 'excerpt',
      content: '节点笔记',
      source: {
        sourceType: 'knowledge-node',
        sourceId: 'node_1',
        sourceTitle: '极限',
        sourceRoute: '/plan/3?view=tree',
      },
      excerpt: '树摘录',
    })
    draft.setFields({ noteName: '树笔记' })
    await vi.advanceTimersByTimeAsync(50)

    expect(createNote).toHaveBeenCalledWith(expect.objectContaining({
      sourceType: 'knowledge_tree',
      sourceTitle: '极限',
      excerpt: '树摘录',
    }))
    expect(createNote.mock.calls[0][0].sourceId).toBeUndefined()
  })
})
