export interface Note {
  id: number
  userId: number
  noteName: string
  content: string
  createdAt: string
  updatedAt: string
}

export interface NoteResourceRel {
  id: number
  noteId: number
  resourceId: number
  selectedText?: string
  positionInfo?: string
}

export interface NoteCreateRequest {
  noteName: string
  content: string
}

export interface NoteLinkRequest {
  resourceId: number
  selectedText: string
  positionInfo: string
}
