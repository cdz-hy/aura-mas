import { describe, expect, it } from 'vitest'
import {
  buildOutlineFromLearningModules,
  buildOutlineFromTreeItems,
  buildOutlineResources,
  buildOutlineTreeFromTreeItems,
  countOutlineModules,
  countOutlineResources,
  countOutlineTreeModules,
  deriveModuleStatus,
  moduleStatusLabel,
  nestOutlineModules,
  shouldShowModuleContextPromptForOutlineModule,
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

  it('renders source text and generated quiz at the same resource level', () => {
    const items: TreePlanOutlineItem[] = [
      {
        kind: 'node',
        id: 'node:env',
        nodeId: 'env',
        title: '环境搭建',
        summary: '',
        depth: 0,
        collapsed: false,
        children: [
          {
            kind: 'resource',
            id: 'resource:100',
            resourceId: 100,
            title: '环境搭建说明',
            resourceType: 'text',
            depth: 1,
            children: [],
          },
          {
            kind: 'resource',
            id: 'resource:101',
            resourceId: 101,
            title: '环境搭建练习测验',
            resourceType: 'quiz',
            depth: 1,
            children: [],
          },
        ],
      },
    ]

    const resources = [
      resource({ id: 100, moduleType: 'text', moduleData: { nodeId: 'env', title: '环境搭建说明' }, status: 2 }),
      resource({ id: 101, parentId: 100, moduleType: 'quiz', moduleData: { title: '环境搭建练习测验' }, status: 2 }),
    ]

    const outline = buildOutlineFromTreeItems(items, resources)
    expect(outline).toHaveLength(1)
    expect(outline[0].resources.map(r => r.resourceId)).toEqual([100, 101])
    expect(outline[0].resources.every(r => r.childResources.length === 0)).toBe(true)

    const tree = buildOutlineTreeFromTreeItems(items, resources)
    expect(tree[0].resources.map(r => r.resourceId)).toEqual([100, 101])
    expect(tree[0].resources.every(r => r.childResources.length === 0)).toBe(true)
  })
})

describe('buildOutlineResources', () => {
  it('keeps generated resources as sibling rows while preserving parent-adjacent order', () => {
    const rows = buildOutlineResources([
      resource({ id: 10, moduleOrder: 1, moduleType: 'text', moduleData: { title: '正文' }, status: 2 }),
      resource({ id: 11, parentId: 10, moduleOrder: 1, moduleType: 'quiz', moduleData: { title: '测验题' }, status: 2 }),
      resource({ id: 12, parentId: 10, moduleOrder: 1, moduleType: 'mindmap', moduleData: { title: '思维导图' }, status: 1 }),
    ])

    expect(rows.map(item => item.resourceId)).toEqual([10, 11, 12])
    expect(rows.every(item => item.childResources.length === 0)).toBe(true)
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

describe('shouldShowModuleContextPromptForOutlineModule', () => {
  it('returns true for top-level numbered modules', () => {
    expect(shouldShowModuleContextPromptForOutlineModule({
      kind: 'module',
      depth: 0,
      displayIndex: '1',
    })).toBe(true)
  })

  it('returns false for nested numbered modules', () => {
    expect(shouldShowModuleContextPromptForOutlineModule({
      kind: 'module',
      depth: 2,
      displayIndex: '1.1.1',
    })).toBe(false)
  })

  it('returns false for non-module group rows', () => {
    expect(shouldShowModuleContextPromptForOutlineModule({
      kind: 'group',
      depth: 0,
      displayIndex: '',
    })).toBe(false)
  })
})
