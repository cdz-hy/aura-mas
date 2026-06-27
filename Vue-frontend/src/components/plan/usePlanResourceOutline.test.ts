import { describe, expect, it } from 'vitest'
import {
  buildOutlineFromLearningModules,
  buildOutlineFromTreeItems,
  buildOutlineTreeFromTreeItems,
  countOutlineModules,
  countOutlineResources,
  countOutlineTreeModules,
  deriveModuleStatus,
  moduleStatusLabel,
  nestOutlineModules,
  nestOutlineResources,
} from './usePlanResourceOutline'
import type { TreePlanOutlineItem } from '@/components/tree/useTreePlanOutline'
import type { LearningResource } from '@/types/plan'

function resource(partial: Partial<LearningResource>): LearningResource {
  return {
    id: partial.id || 1,
    planId: 42,
    parentId: null,
    moduleOrder: partial.moduleOrder || 1,
    moduleType: partial.moduleType || 'text',
    moduleData: partial.moduleData || {},
    status: partial.status ?? 0,
    storagePath: null,
    generatedByAgent: null,
    version: 1,
    createdAt: '',
    updatedAt: '',
    ...partial,
  } as LearningResource
}

describe('deriveModuleStatus', () => {
  it('returns pending when no resources', () => {
    expect(deriveModuleStatus([])).toBe('pending')
  })

  it('prioritizes failed over generating', () => {
    expect(deriveModuleStatus([
      { id: 'r:1', resourceId: 1, title: 'A', resourceType: 'text', status: 2, childResources: [] },
      { id: 'r:2', resourceId: 2, title: 'B', resourceType: 'text', status: 3, childResources: [] },
    ])).toBe('failed')
  })

  it('maps labels for UI', () => {
    expect(moduleStatusLabel('ready')).toBe('已生成')
    expect(moduleStatusLabel('generating')).toBe('生成中')
  })
})

describe('buildOutlineFromLearningModules', () => {
  it('builds card modules with stable ids and status', () => {
    const outline = buildOutlineFromLearningModules([
      {
        order: 3,
        title: '线束工程基础',
        estimatedHours: 2,
        resourceTypes: ['text'],
        resources: [
          resource({ id: 10, moduleOrder: 3, status: 2, moduleData: { title: '正文' } }),
        ],
      },
    ])

    expect(outline).toHaveLength(1)
    expect(outline[0].id).toBe('learning:3')
    expect(outline[0].displayIndex).toBe('1')
    expect(outline[0].moduleStatus).toBe('ready')
    expect(outline[0].resources[0].title).toBe('正文')
  })
})

describe('buildOutlineFromTreeItems', () => {
  it('flattens nested nodes while preserving depth and numbering', () => {
    const items: TreePlanOutlineItem[] = [
      {
        kind: 'node',
        id: 'node:root',
        nodeId: 'root',
        title: '根模块',
        summary: '摘要',
        depth: 0,
        collapsed: false,
        children: [
          {
            kind: 'resource',
            id: 'resource:1',
            resourceId: 1,
            title: '图文资源',
            resourceType: 'text',
            depth: 1,
            children: [],
          },
          {
            kind: 'node',
            id: 'node:child',
            nodeId: 'child',
            title: '子模块',
            summary: '',
            depth: 1,
            collapsed: false,
            children: [],
          },
        ],
      },
    ]

    const outline = buildOutlineFromTreeItems(items, [
      resource({ id: 1, status: 2, moduleData: { nodeId: 'root' } }),
    ])

    expect(outline.map(item => item.displayIndex)).toEqual(['1', '1.1'])
    expect(outline[0].resources).toHaveLength(1)
    expect(outline[1].depth).toBe(1)
    expect(countOutlineModules(outline)).toBe(2)
    expect(countOutlineResources(outline)).toBe(1)
  })

  it('maps ungrouped resources to group cards', () => {
    const items: TreePlanOutlineItem[] = [
      {
        kind: 'group',
        id: 'group:orphan',
        title: '未归类资源',
        depth: 0,
        children: [
          {
            kind: 'resource',
            id: 'resource:9',
            resourceId: 9,
            title: '游离资源',
            resourceType: 'quiz',
            depth: 0,
            children: [],
          },
        ],
      },
    ]

    const outline = buildOutlineFromTreeItems(items, [resource({ id: 9, moduleType: 'quiz', status: 1 })])
    expect(outline[0].kind).toBe('group')
    expect(outline[0].moduleStatus).toBe('generating')
  })

  it('builds nested tree for collapsible outline rendering', () => {
    const items: TreePlanOutlineItem[] = [
      {
        kind: 'node',
        id: 'node:parent',
        nodeId: 'parent',
        title: '父模块',
        summary: '',
        depth: 0,
        collapsed: false,
        children: [
          {
            kind: 'node',
            id: 'node:child',
            nodeId: 'child',
            title: '子模块',
            summary: '',
            depth: 1,
            collapsed: false,
            children: [],
          },
        ],
      },
    ]

    const tree = buildOutlineTreeFromTreeItems(items, [])
    expect(tree).toHaveLength(1)
    expect(tree[0].displayIndex).toBe('1')
    expect(tree[0].childModules).toHaveLength(1)
    expect(tree[0].childModules[0].displayIndex).toBe('1.1')
    expect(countOutlineTreeModules(tree)).toBe(2)
  })
})

describe('nestOutlineResources', () => {
  it('nests supplementary resources under parentId', () => {
    const tree = nestOutlineResources([
      resource({ id: 10, moduleOrder: 1, moduleType: 'text', moduleData: { title: '正文' }, status: 2 }),
      resource({ id: 11, parentId: 10, moduleOrder: 1, moduleType: 'quiz', moduleData: { title: '测验题' }, status: 2 }),
      resource({ id: 12, parentId: 10, moduleOrder: 1, moduleType: 'mindmap', moduleData: { title: '思维导图' }, status: 1 }),
    ])

    expect(tree).toHaveLength(1)
    expect(tree[0].resourceId).toBe(10)
    expect(tree[0].childResources.map(item => item.resourceId)).toEqual([11, 12])
  })
})

describe('nestOutlineModules', () => {
  it('returns empty array when modules are missing', () => {
    expect(nestOutlineModules([])).toEqual([])
  })

  it('nests flat modules by displayIndex', () => {
    const flat = buildOutlineFromTreeItems([
      {
        kind: 'node',
        id: 'node:parent',
        nodeId: 'parent',
        title: '父模块',
        summary: '',
        depth: 0,
        collapsed: false,
        children: [
          {
            kind: 'node',
            id: 'node:child',
            nodeId: 'child',
            title: '子模块',
            summary: '',
            depth: 1,
            collapsed: false,
            children: [],
          },
        ],
      },
    ], [])

    const tree = nestOutlineModules(flat)
    expect(tree).toHaveLength(1)
    expect(tree[0].childModules[0].id).toBe('node:child')
  })
})
