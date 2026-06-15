export interface Note {
  id: number
  userId: number
  noteName: string
  content: string
  tags?: string[] | string
  isPinned?: number
  createdAt: string
  updatedAt: string
}

export interface NoteResourceRel {
  id: number
  noteId: number
  resourceId: number
  selectedText?: string
  positionInfo?: string
  planId?: number
  moduleName?: string
  resourceTitle?: string
}

export interface NoteCreateRequest {
  noteName: string
  content: string
  tags?: string[]
  isPinned?: number
}

export interface NoteLinkRequest {
  resourceId: number
  selectedText: string
  positionInfo: string
  planId?: number
  moduleName?: string
  resourceTitle?: string
}
