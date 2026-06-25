/** 知识树拖拽 MIME 类型 */
export const TREE_NODE_DRAG_TYPE = 'application/x-aura-knowledge-node'
export const TREE_RESOURCE_DRAG_TYPE = 'application/x-aura-knowledge-resource'

export interface TreeNodeDragPayload {
  nodeId: string
  title: string
}

export interface TreeResourceDragPayload {
  resourceId: number
  title: string
}

export function setNodeDragData(event: DragEvent, payload: TreeNodeDragPayload) {
  if (!event.dataTransfer) return
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData(TREE_NODE_DRAG_TYPE, JSON.stringify(payload))
  event.dataTransfer.setData('text/plain', payload.title)
}

export function setResourceDragData(event: DragEvent, payload: TreeResourceDragPayload) {
  if (!event.dataTransfer) return
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData(TREE_RESOURCE_DRAG_TYPE, JSON.stringify(payload))
  event.dataTransfer.setData('text/plain', payload.title)
}

export function readNodeDragData(event: DragEvent): TreeNodeDragPayload | null {
  const raw = event.dataTransfer?.getData(TREE_NODE_DRAG_TYPE)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as TreeNodeDragPayload
    return parsed?.nodeId ? parsed : null
  } catch {
    return null
  }
}

export function readResourceDragData(event: DragEvent): TreeResourceDragPayload | null {
  const raw = event.dataTransfer?.getData(TREE_RESOURCE_DRAG_TYPE)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as TreeResourceDragPayload
    return parsed?.resourceId ? parsed : null
  } catch {
    return null
  }
}

export function isNodeDragEvent(event: DragEvent) {
  return Boolean(event.dataTransfer?.types.includes(TREE_NODE_DRAG_TYPE))
}

export function isResourceDragEvent(event: DragEvent) {
  return Boolean(event.dataTransfer?.types.includes(TREE_RESOURCE_DRAG_TYPE))
}
