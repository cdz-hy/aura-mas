import { describe, expect, it } from 'vitest'
import {
  effectiveNoteType,
  effectiveOrganizeStatus,
  isGenericSourceLabel,
  noteGroup,
  noteListPreview,
  noteSourceDisplay,
  noteTypeLabel,
  organizeStatusLabel,
  resolveNoteSourceRoute,
  toNotePreview,
  toSourceLabel,
} from './notePresentation'

describe('notePresentation', () => {
  it('removes markdown images and annotation markers from previews', () => {
    expect(toNotePreview('## 标题\n![图](a.png)\n<<A:1|重点|解释>>正文', 20)).toBe('标题 解释 正文')
  })

  it('prefers named source metadata', () => {
    expect(toSourceLabel([{ id: 1, noteId: 2, resourceId: 3, planId: 4, moduleName: '基础', resourceTitle: '线性回归' }])).toBe('基础 · 线性回归')
    expect(toSourceLabel([])).toBeNull()
  })

  it('maps note types to stable Chinese labels with quick default for legacy', () => {
    expect(noteTypeLabel('excerpt')).toBe('摘录')
    expect(noteTypeLabel('quick')).toBe('速记')
    expect(noteTypeLabel('question')).toBe('问题')
    expect(noteTypeLabel(undefined)).toBe('速记')
    expect(noteTypeLabel(null)).toBe('速记')
    expect(effectiveNoteType(undefined)).toBe('quick')
  })

  it('maps organize statuses with pending default for legacy notes', () => {
    expect(organizeStatusLabel('pending')).toBe('待整理')
    expect(organizeStatusLabel('organizing')).toBe('整理中')
    expect(organizeStatusLabel('organized')).toBe('已整理')
    expect(organizeStatusLabel('error')).toBe('整理失败')
    expect(organizeStatusLabel(undefined)).toBe('待整理')
    expect(effectiveOrganizeStatus(undefined)).toBe('pending')
  })

  it('classifies notes into pending and organized groups', () => {
    expect(noteGroup({ organizeStatus: 'organized' })).toBe('organized')
    expect(noteGroup({ organizeStatus: 'pending' })).toBe('pending')
    expect(noteGroup({ organizeStatus: 'organizing' })).toBe('pending')
    expect(noteGroup({ organizeStatus: 'error' })).toBe('pending')
    expect(noteGroup({})).toBe('pending')
  })

  it('prefers excerpt for list preview and falls back to content', () => {
    expect(noteListPreview({ content: '用户理解', excerpt: '当 x 趋近于 a 时' })).toBe('当 x 趋近于 a 时')
    expect(noteListPreview({ content: '## 标题 正文', excerpt: '' })).toBe('标题 正文')
    expect(noteListPreview({ content: '只有内容' })).toBe('只有内容')
  })

  it('summarizes interleaved multi-excerpt notes in list preview', () => {
    const content = [
      '<<<excerpt id="a" sourceTitle="A">>>\n第一段原文内容\n<<< /excerpt >>>',
      '理解一',
      '<<<excerpt id="b">>>\n第二段\n<<< /excerpt >>>',
      '理解二',
    ].join('\n\n')
    expect(noteListPreview({ content, excerpt: '' })).toMatch(/2 段原文/)
  })

  it('collapses API error dumps into a short human preview', () => {
    const dump = '内容生成失败: MIMO API 流式调用失败(429): {"error":{"code":429,"message":"Too many requests","type":"limitation"}}'
    expect(noteListPreview({ content: dump })).toBe('内容生成失败，可重试或改写笔记')
    expect(toNotePreview(dump)).toBe('内容生成失败，可重试或改写笔记')
  })

  it('prefers sourceTitle over resource label for display', () => {
    expect(noteSourceDisplay({ sourceTitle: '极限的定义', sourceType: 'resource' }, '基础 · 资源')).toBe('极限的定义')
    expect(noteSourceDisplay({ sourceTitle: undefined, sourceType: undefined }, '基础 · 资源')).toBe('基础 · 资源')
    expect(noteSourceDisplay({ sourceTitle: undefined }, null)).toBeNull()
  })

  it('prefers real resource titles over generic 资源 #id placeholders', () => {
    expect(isGenericSourceLabel('资源 #65')).toBe(true)
    expect(isGenericSourceLabel('学习资源')).toBe(true)
    expect(isGenericSourceLabel('Spring Data Redis')).toBe(false)
    // generic sourceTitle loses to real resource label
    expect(
      noteSourceDisplay({ sourceTitle: '学习资源', sourceType: 'resource' }, '汉得HZERO平台基础服务'),
    ).toBe('汉得HZERO平台基础服务')
    // generic resource #id loses to a real title on the note
    expect(
      noteSourceDisplay({ sourceTitle: 'Spring 笔记', sourceType: 'resource' }, '资源 #65'),
    ).toBe('Spring 笔记')
  })

  it('resolves navigable routes from sourceRoute or plan/resource ids', () => {
    expect(resolveNoteSourceRoute({
      sourceRoute: '/plan/3?resource=12',
      sourceType: 'resource',
      sourceId: 12,
    })).toBe('/plan/3?resource=12')

    expect(resolveNoteSourceRoute(
      { sourceType: 'resource', sourceId: 65 },
      { planId: 9, resourceId: 65 },
    )).toBe('/plan/9?resource=65')

    expect(resolveNoteSourceRoute(
      { sourceType: 'resource', sourceId: 65 },
      null,
      9,
    )).toBe('/plan/9?resource=65')

    expect(resolveNoteSourceRoute({ sourceType: 'plan', sourceId: 4 })).toBe('/plan/4')
  })
})
