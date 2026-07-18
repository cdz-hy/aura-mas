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
  it('places first-level nodes on a vertical trunk above the root', () => {
    const layout = buildTreeLayout(sampleNodes, 'node_root')
    const root = layout.items.find(i => i.node.id === 'node_root')
    const main1 = layout.items.find(i => i.node.id === 'node_m1')
    const main2 = layout.items.find(i => i.node.id === 'node_m2')
    const branch = layout.items.find(i => i.node.id === 'node_c1')

    expect(root?.kind).toBe('root')
    expect(main1?.kind).toBe('main')
    expect(main2?.kind).toBe('branch-left')
    expect(branch?.kind).toBe('branch-right')
    expect(main1?.x).toBe(root?.x)
    expect(main1!.y).toBeLessThan(root!.y)
    expect(branch!.x).toBeGreaterThan(main1!.x)
    expect(main2!.x).toBeLessThan(main1!.x)
  })

  it('keeps root children on the same center trunk', () => {
    const nodes: KnowledgeNode[] = [
      ...sampleNodes,
      {
        id: 'node_m3',
        treeId: 'tree_1',
        parentId: 'node_root',
        title: 'Main 3',
        depth: 1,
        sortOrder: 1,
      },
    ]

    const layout = buildTreeLayout(nodes, 'node_root')
    const root = layout.items.find(i => i.node.id === 'node_root')!
    const main1 = layout.items.find(i => i.node.id === 'node_m1')!
    const main3 = layout.items.find(i => i.node.id === 'node_m3')!

    expect(main1.kind).toBe('main')
    expect(main3.kind).toBe('main')
    expect(main1.x).toBe(root.x)
    expect(main3.x).toBe(root.x)
    expect(main3.y).toBeLessThan(main1.y)
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
