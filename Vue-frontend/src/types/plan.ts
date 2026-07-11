export interface LearningPlan {
  id: number
  title: string
  learningGoal: Record<string, any> | null
  planConfig: Record<string, any> | null
  userId: number
  status: number // 0-pending, 1-generating, 2-confirming, 3-learning, 4-completed
  displayStatus?: number // 0=待规划, 1=生成中, 4=已完成 (基于资源生成状态)
  progress: number
  createdAt: string
  updatedAt: string
}

export interface PlanModule {
  id: string
  title: string
  description: string
  objectives: string[]
  estimatedHours: number
  order: number
  resourceTypes: ResourceType[]
  status: 'pending' | 'generating' | 'ready'
}

export type ResourceType = 'text' | 'document' | 'mindmap' | 'quiz' | 'code' | 'reading' | 'summary' | 'video' | 'animation' | 'podcast' | 'pptx'

export interface LearningResource {
  id: number
  planId: number
  parentId: number | null
  moduleOrder: number
  moduleType: string
  moduleData: Record<string, any>
  status: number
  storagePath: string | null
  generatedByAgent: string | null
  version: number
  createdAt: string
  updatedAt: string
}

export type AnimationExportQuality = '1080p' | '720p'
export type AnimationExportStatus = 'idle' | 'rendering' | 'ready' | 'failed'
export interface AnimationExportState {
  status: AnimationExportStatus
  url?: string | null
  error?: string | null
  startedAt?: string
  completedAt?: string | null
  resourceVersion?: number
}

export interface ResourceGenerationTask {
  id: number
  planId: number
  resourceId: number
  taskStatus: number
  agentChain: Record<string, any> | null
  retryCount: number
  createdAt: string
  finishedAt: string | null
}

export interface PlanCreateRequest {
  title: string
  learningGoal: Record<string, any>
  planConfig?: Record<string, any>
}
