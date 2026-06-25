import { describe, expect, it } from 'vitest'
import { buildTreePlanOutline } from './useTreePlanOutline'
import type { KnowledgeNode } from '@/types/knowledgeTree'
import type { LearningResource } from '@/types/plan'

const nodes: KnowledgeNode[] = [
  { id: 'root', treeId: 'tree_1', parentId: null, title: 'Python 基础学习', sortOrder: 0 },
  { id: 'env', treeId: 'tree_1', parentId: 'root', title: 'Python 环境搭建与初体验', sortOrder: 1 },
  { id: 'vars', treeId: 'tree_1', parentId: 'root', title: '变量、数据类型与基本操作', sortOrder: 2 },
]

function resource(partial: Partial<LearningResource>): LearningResource {
  return {
    id: partial.id || 1,
    planId: 42,
    parentId: null,
    moduleOrder: partial.moduleOrder || 1,
    moduleType: partial.moduleType || 'text',
    moduleData: partial.moduleData || {},
    status: partial.status ?? 2,
    storagePath: null,
    generatedByAgent: null,
    version: 1,
    createdAt: '',
    updatedAt: '',
    ...partial,
  } as LearningResource
}

describe('buildTreePlanOutline', () => {
  it('shows the root node and nested child nodes', () => {
    const outline = buildTreePlanOutline(nodes, [], 'root')

    expect(outline.filter(item => item.kind === 'node').map(item => item.title)).toEqual([
      'Python 环境搭建与初体验',
      '变量、数据类型与基本操作',
    ])
  })

  it('mounts resources by moduleData nodeId and node resourceId', () => {
    const outline = buildTreePlanOutline([
      ...nodes,
      { id: 'linked', treeId: 'tree_1', parentId: 'root', title: '直接关联节点', resourceId: 77, sortOrder: 3 },
    ], [
      resource({ id: 11, moduleType: 'text', moduleData: { nodeId: 'root', title: '基础练习' } }),
      resource({ id: 22, moduleType: 'animation', moduleData: { nodeId: 'vars', title: '变量演示' } }),
      resource({ id: 77, moduleType: 'quiz', moduleData: { title: '直接题目' } }),
    ], 'root')

    const vars = outline.find(item => item.kind === 'node' && item.nodeId === 'vars')
    expect(vars?.children[0]).toMatchObject({ kind: 'resource', title: '变量演示', resourceId: 22 })
    const linked = outline.find(item => item.kind === 'node' && item.nodeId === 'linked')
    expect(linked?.children[0]).toMatchObject({ kind: 'resource', title: '直接题目', resourceId: 77 })
    const rootResources = outline.find(item => item.kind === 'group' && item.title === '计划资源')
    expect(rootResources?.children[0]).toMatchObject({ kind: 'resource', title: '基础练习', resourceId: 11 })
  })

  it('falls back to title matching and unmatched resources under root', () => {
    const outline = buildTreePlanOutline(nodes, [
      resource({ id: 33, moduleType: 'text', moduleData: { module_title: 'Python 环境搭建与初体验', title: '环境搭建说明' } }),
      resource({ id: 44, moduleType: 'video', moduleData: { title: '外部补充视频' } }),
    ], 'root')

    const env = outline.find(item => item.kind === 'node' && item.nodeId === 'env')
    expect(env?.children[0]).toMatchObject({ kind: 'resource', title: '环境搭建说明', resourceId: 33 })
    const uncategorized = outline.find(item => item.kind === 'group' && item.title === '未归类资源')
    expect(uncategorized?.children[0]).toMatchObject({ kind: 'resource', title: '外部补充视频', resourceId: 44 })
  })
})
