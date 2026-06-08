import request from './request'

export interface KnowledgeBase {
  id: number
  docName: string
  filePath: string
  fileSize: number
  chunkCount: number | null
  parseStatus: number
  collectionName: string | null
  mineruTaskId: string | null
  uploadUserId: number
  uploadTime: string
}

export interface KBPageResult {
  total: number
  page: number
  size: number
  records: KnowledgeBase[]
}

export interface KBDetailStats {
  doc_id: number
  total_chunks: number
  type_distribution: Record<string, number>
  heading_distribution: Array<{ heading: string; count: number }>
  sample_chunks: Array<{ id: string; type: string; content_preview: string; heading: string[] }>
}

export interface CollectionStats {
  collection_name: string
  total_points: number
  status: string
}

// Java backend APIs
export function getKBList(params: { page?: number; size?: number }) {
  return request.get<any, any>('/admin/kb/list', { params })
}

export function getKBById(id: number) {
  return request.get<any, any>(`/admin/kb/${id}`)
}

export function createKB(docName: string, fileSize: number) {
  return request.post<any, any>('/admin/kb/create', { docName, fileSize })
}

export function deleteKB(id: number) {
  return request.delete(`/admin/kb/${id}`)
}

export function getKBDownloadUrl(id: number) {
  return request.get<any, any>(`/admin/kb/${id}/download`)
}

// Python backend APIs
const PYTHON_BASE = import.meta.env.VITE_PYTHON_API_URL || 'http://localhost:8002'

export async function ingestKB(docId: number, docName: string, file: File) {
  const formData = new FormData()
  formData.append('doc_id', String(docId))
  formData.append('doc_name', docName)
  formData.append('file', file)
  const resp = await fetch(`${PYTHON_BASE}/api/v1/kb/ingest`, { method: 'POST', body: formData })
  if (!resp.ok) throw new Error(`Ingest failed: ${resp.statusText}`)
  return resp.json()
}

export async function getCollectionStats(collectionName: string) {
  const resp = await fetch(`${PYTHON_BASE}/api/v1/kb/collections/${collectionName}/stats`)
  if (!resp.ok) throw new Error(`Stats fetch failed: ${resp.statusText}`)
  return resp.json()
}

export async function getDocDetail(collectionName: string, docId: number) {
  const resp = await fetch(`${PYTHON_BASE}/api/v1/kb/collections/${collectionName}/documents/${docId}/detail`)
  if (!resp.ok) throw new Error(`Detail fetch failed: ${resp.statusText}`)
  return resp.json()
}

export async function deleteDocChunks(collectionName: string, docId: number) {
  const resp = await fetch(`${PYTHON_BASE}/api/v1/kb/collections/${collectionName}/documents/${docId}`, { method: 'DELETE' })
  if (!resp.ok) throw new Error(`Delete chunks failed: ${resp.statusText}`)
  return resp.json()
}

export async function reprocessKB(docId: number, docName: string) {
  const formData = new FormData()
  formData.append('doc_name', docName)
  const resp = await fetch(`${PYTHON_BASE}/api/v1/kb/reprocess/${docId}`, { method: 'POST', body: formData })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || `Reprocess failed: ${resp.statusText}`)
  }
  return resp.json()
}
