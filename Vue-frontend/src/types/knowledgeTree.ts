export interface KnowledgeTree {
  id: string
  planId: number
  userId?: number
  title: string
  field?: string | null
  currentProblem?: string | null
  learningBackground?: string | null
  currentNodeId?: string | null
  contextSummary?: string | null
  createdAt?: string
  updatedAt?: string
}

export interface KnowledgeNode {
  id: string
  treeId: string
  parentId?: string | null
  resourceId?: number | null
  title: string
  summary?: string | null
  content?: string | null
  status?: string | null
  relevance?: number | null
  importance?: number | null
  relevanceScore?: number | null
  difficulty?: number | null
  depth?: number | null
  sortOrder?: number | null
  prerequisiteIds?: string[]
  isFundamental?: boolean | null
  fpRelation?: string | null
  fpReason?: string | null
  collapsed?: boolean
  createdAt?: string
  updatedAt?: string
}

export interface TreeMessage {
  id: number
  treeId: string
  nodeId: string
  role: string
  content: string
  nextActions?: unknown[]
  searchSources?: unknown[]
  createdAt?: string
}

export interface KnowledgeTreeResponse {
  tree: KnowledgeTree
  nodes: KnowledgeNode[]
}

export interface TreeGeneratedResource {
  id: number
  type: string
  title: string
}

export interface TreeSubdivisionOption {
  angle: string
  label: string
  rationale: string
}

export type TreeSplitMode = 'Lite' | 'Medium' | 'Zen'

export interface TreeSubdivisionCaution {
  label: string
  rationale: string
}

export interface TreeSubdivisionOptionsResponse {
  tree_id?: string
  node_id: string
  options: TreeSubdivisionOption[]
  caution?: TreeSubdivisionCaution | null
  search_results?: unknown[]
}

export interface TreeFlashcard {
  question: string
  answer: string
  difficulty: number
}

export interface TreeSseHandlers {
  onProgress?: (content: string) => void
  onThinking?: (content: string) => void
  onGroupPreview?: (content: string) => void
  onChunk?: (content: string) => void
  onStreamText?: (content: string) => void
  onMessage?: (message: TreeMessage) => void
  onNodes?: (nodes: KnowledgeNode[]) => void
  onResources?: (resources: TreeGeneratedResource[]) => void
  onFlashcards?: (cards: TreeFlashcard[]) => void
  onBranchDone?: (data: { parent_id: string; parent_title: string; children: KnowledgeNode[] }) => void
  onFpLayer?: (data: { parent_id: string; parent_title: string; children: KnowledgeNode[]; reached_bottom: boolean; parent?: KnowledgeNode | null }) => void
  onAllDone?: () => void
  onCancelled?: (reason: string) => void
  onDone?: () => void
  onError?: (error: string) => void
}
