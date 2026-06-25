import request, { PYTHON_AI_BASE } from './request'

export interface KnowledgeGraphNode {
  id: string
  name: string
  description?: string
  resource_ids?: number[]
  mastery_level?: number
  importance?: number
}

export interface KnowledgeGraphEdge {
  id: string
  source: string
  target: string
  relationship?: string
}

export interface GraphData {
  nodes: KnowledgeGraphNode[]
  edges: KnowledgeGraphEdge[]
}

export interface UserKnowledgeDomain {
  id: number
  userId: number
  domainName: string
  graphData: GraphData
  createdAt: string
  updatedAt: string
}

export const getKnowledgeDomains = (userId: number) => {
  return request.get<UserKnowledgeDomain[]>(`/knowledge-graph/user/${userId}`)
}

export const getDomainGraph = (domainId: number) => {
  return request.get<UserKnowledgeDomain>(`/knowledge-graph/domain/${domainId}`)
}

export const patchKnowledgeNode = (domainId: number, nodeId: string, masteryLevel?: number, importance?: number) => {
  return request.patch(`/knowledge-graph/domain/${domainId}/node/${nodeId}`, {
    masteryLevel,
    importance
  })
}

export const analyzeResources = async (userId: number, resourceIds: number[]) => {
  const response = await fetch(`${PYTHON_AI_BASE}/api/ai/knowledge-graph/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, resource_ids: resourceIds })
  });
  if (!response.ok) {
    throw new Error('Failed to analyze resources');
  }
  return response.json();
}
