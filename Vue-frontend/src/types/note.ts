/** Capture mode for sidebar notes. Legacy notes omit this field. */
export type NoteType = 'excerpt' | 'quick' | 'question'

/** AI organization lifecycle. Legacy notes omit this field. */
export type OrganizeStatus = 'pending' | 'organizing' | 'organized' | 'error'

/** Automatic source kinds limited to learning surfaces. */
export type NoteSourceType = 'plan' | 'resource' | 'knowledge_tree' | 'tutor'

export interface Note {
  id: number
  userId: number
  noteName: string
  content: string
  tags?: string[] | string
  isPinned?: number
  noteType?: NoteType
  organizeStatus?: OrganizeStatus
  sourceType?: NoteSourceType
  sourceId?: number
  sourceTitle?: string
  sourceRoute?: string
  excerpt?: string
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
  noteType?: NoteType
  organizeStatus?: OrganizeStatus
  sourceType?: NoteSourceType
  sourceId?: number
  sourceTitle?: string
  sourceRoute?: string
  excerpt?: string
}

export interface NoteLinkRequest {
  resourceId: number
  selectedText: string
  positionInfo: string
  planId?: number
  moduleName?: string
  resourceTitle?: string
}
