import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createNote,
  deleteNote,
  getNoteById,
  getNoteResources,
  getNotes,
  linkNoteToResource,
  updateNote,
} from './note'

const requestMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('@/api/request', () => ({
  default: {
    get: requestMock.get,
    post: requestMock.post,
    put: requestMock.put,
    delete: requestMock.delete,
  },
}))

describe('note api contract', () => {
  beforeEach(() => {
    requestMock.get.mockReset()
    requestMock.post.mockReset()
    requestMock.put.mockReset()
    requestMock.delete.mockReset()
  })

  it('lists notes with plan/page/size/keyword params', async () => {
    requestMock.get.mockResolvedValue({ data: { records: [], total: 0 } })
    await getNotes({ page: 1, size: 20, keyword: '回归' })
    expect(requestMock.get).toHaveBeenCalledWith('/note/list', { params: { page: 1, size: 20, keyword: '回归' } })
  })

  it('fetches a single note by id', async () => {
    requestMock.get.mockResolvedValue({ data: { id: 7 } })
    await getNoteById(7)
    expect(requestMock.get).toHaveBeenCalledWith('/note/7')
  })

  it('creates a note via post', async () => {
    requestMock.post.mockResolvedValue({ data: { id: 1 } })
    await createNote({ noteName: 'n', content: 'c' })
    expect(requestMock.post).toHaveBeenCalledWith('/note', { noteName: 'n', content: 'c' })
  })

  it('sends capture metadata when creating an excerpt note', async () => {
    requestMock.post.mockResolvedValue({ data: { id: 2 } })
    await createNote({
      noteName: '无标题笔记',
      content: '我的理解',
      noteType: 'excerpt',
      organizeStatus: 'pending',
      sourceType: 'resource',
      sourceId: 12,
      sourceTitle: '极限的定义',
      sourceRoute: '/plans/1/resources/12',
      excerpt: '当 x 趋近于 a 时',
    })
    expect(requestMock.post).toHaveBeenCalledWith(
      '/note',
      expect.objectContaining({ noteType: 'excerpt', excerpt: '当 x 趋近于 a 时' }),
    )
  })

  it('sends capture metadata when updating a note', async () => {
    requestMock.put.mockResolvedValue({ data: { id: 3 } })
    await updateNote(3, {
      noteName: '整理后',
      content: '整理内容',
      organizeStatus: 'organized',
      noteType: 'question',
    })
    expect(requestMock.put).toHaveBeenCalledWith(
      '/note/3',
      expect.objectContaining({ organizeStatus: 'organized', noteType: 'question' }),
    )
  })

  it('deserializes capture metadata from list responses without transformation', async () => {
    const record = {
      id: 8,
      userId: 1,
      noteName: '摘录',
      content: '理解',
      noteType: 'excerpt',
      organizeStatus: 'pending',
      sourceType: 'resource',
      sourceId: 12,
      sourceTitle: '极限的定义',
      sourceRoute: '/plans/1/resources/12',
      excerpt: '当 x 趋近于 a 时',
      createdAt: '2026-07-12T00:00:00',
      updatedAt: '2026-07-12T00:00:00',
    }
    requestMock.get.mockResolvedValue({ data: { records: [record], total: 1 } })
    const result = await getNotes({ page: 1, size: 20 })
    expect(result.data.records[0]).toEqual(record)
  })

  it('updates a note via put', async () => {
    requestMock.put.mockResolvedValue({ data: { id: 3 } })
    await updateNote(3, { noteName: 'n2' })
    expect(requestMock.put).toHaveBeenCalledWith('/note/3', { noteName: 'n2' })
  })

  it('deletes a note', async () => {
    requestMock.delete.mockResolvedValue({ data: null })
    await deleteNote(5)
    expect(requestMock.delete).toHaveBeenCalledWith('/note/5')
  })

  it('links a note to a resource', async () => {
    requestMock.post.mockResolvedValue({ data: null })
    await linkNoteToResource(9, { resourceId: 1, selectedText: 's', positionInfo: 'p' })
    expect(requestMock.post).toHaveBeenCalledWith('/note/9/link-resource', {
      resourceId: 1,
      selectedText: 's',
      positionInfo: 'p',
    })
  })

  it('fetches note resources', async () => {
    requestMock.get.mockResolvedValue({ data: [] })
    await getNoteResources(11)
    expect(requestMock.get).toHaveBeenCalledWith('/note/11/resources')
  })
})
