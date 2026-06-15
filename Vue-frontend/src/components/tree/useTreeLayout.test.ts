import { describe, expect, it } from 'vitest'
import type { KnowledgeNode } from '@/types/knowledgeTree'
import { buildTreeLayout, fitTreeViewport, getTreeLayoutBounds } from './useTreeLayout'

const sampleNodes: KnowledgeNode[] = [
  {
    id: 'node_root',
    treeId: 'tree_1',
    parentId: null,
    title: 'Root',
    depth: 0,
    sortOrder: 0,
  },
  {
    id: 'node_m1',
    treeId: 'tree_1',
    parentId: 'node_root',
    title: 'Main 1',
    depth: 1,
    sortOrder: 0,
  },
  {
    id: 'node_m2',
    treeId: 'tree_1',
    parentId: 'node_m1',
    title: 'Main 2',
    depth: 2,
    sortOrder: 0,
  },
  {
    id: 'node_c1',
    treeId: 'tree_1',
    parentId: 'node_m1',
    title: 'Branch Child',
    depth: 2,
    sortOrder: 1,
  },
]

describe('buildTreeLayout', () => {
  it('places root, main trunk, and alternating branch children', () => {
    const layout = buildTreeLayout(sampleNodes, 'node_root')
    expect(layout.items.find(i => i.node.id === 'node_root')?.kind).toBe('root')
    expect(layout.items.find(i => i.node.id === 'node_m1')?.kind).toBe('main')
    expect(layout.items.find(i => i.node.id === 'node_c1')?.kind).toBe('branch-right')
    expect(layout.edges.some(e => e.fromNodeId === 'node_m1' && e.toNodeId === 'node_c1')).toBe(true)
  })

  it('calculates a viewport fit that keeps the whole tree visible', () => {
    const layout = buildTreeLayout(sampleNodes, 'node_root')
    const bounds = getTreeLayoutBounds(layout.items, 236, 172)
    const fit = fitTreeViewport(bounds, 640, 480, 96, 120, 0.35, 1.6)

    expect(fit.zoom).toBeLessThanOrEqual(1)
    expect(bounds.minX * fit.zoom + fit.panX).toBeGreaterThanOrEqual(-224)
    expect((bounds.minX + bounds.width) * fit.zoom + fit.panX).toBeLessThanOrEqual(224)
    expect(bounds.minY * fit.zoom + fit.panY).toBeGreaterThanOrEqual(-120)
    expect((bounds.minY + bounds.height) * fit.zoom + fit.panY).toBeLessThanOrEqual(120)
  })

  it('hides descendants of collapsed nodes', () => {
    const nodes = sampleNodes.map(n => n.id === 'node_m1' ? { ...n, collapsed: true } : n)
    const layout = buildTreeLayout(nodes, 'node_root')
    expect(layout.items.some(i => i.node.id === 'node_c1')).toBe(false)
  })
})
