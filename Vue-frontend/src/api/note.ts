import request from './request'
import type { Note, NoteCreateRequest, NoteLinkRequest } from '@/types/note'

export function createNote(data: NoteCreateRequest) {
  return request.post<any, { data: Note }>('/note', data)
}

export function getNoteById(noteId: number) {
  return request.get<any, { data: Note }>(`/note/${noteId}`)
}

export function getNotes(params: { planId?: number; page?: number; size?: number }) {
  return request.get<any, { data: { records: Note[]; total: number } }>('/note/list', { params })
}

export function updateNote(noteId: number, data: Partial<NoteCreateRequest>) {
  return request.put<any, { data: Note }>(`/note/${noteId}`, data)
}

export function deleteNote(noteId: number) {
  return request.delete(`/note/${noteId}`)
}

export function linkNoteToResource(noteId: number, data: NoteLinkRequest) {
  return request.post(`/note/${noteId}/link-resource`, data)
}
