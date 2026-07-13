import { describe, expect, it } from 'vitest'
import {
  appendExcerptBlock,
  collectExcerptTexts,
  migrateLegacyToInterleaved,
  parseNoteBlocks,
  serializeNoteBlocks,
} from './noteBlocks'

describe('noteBlocks interleaved model', () => {
  it('round-trips excerpt + note + excerpt', () => {
    const content = appendExcerptBlock('', {
      text: '第一段原文',
      sourceTitle: '资源A',
      sourceRoute: '/plan/1?resource=1',
    })
    // user writes after first excerpt
    let blocks = parseNoteBlocks(content)
    const noteIdx = blocks.findIndex(b => b.type === 'note')
    blocks[noteIdx] = { type: 'note', text: '我对第一段的理解' }
    let saved = serializeNoteBlocks(blocks)

    saved = appendExcerptBlock(saved, { text: '第二段原文', sourceTitle: '资源B' })
    blocks = parseNoteBlocks(saved)

    const types = blocks.map(b => b.type)
    expect(types.filter(t => t === 'excerpt')).toHaveLength(2)
    expect(blocks.some(b => b.type === 'note' && b.text.includes('理解'))).toBe(true)
    expect(collectExcerptTexts(saved)).toEqual(['第一段原文', '第二段原文'])
  })

  it('migrates legacy excerpt field + content into interleaved doc', () => {
    const migrated = migrateLegacyToInterleaved('我的补充笔记', '划选的原文')
    const blocks = parseNoteBlocks(migrated)
    expect(blocks[0]).toMatchObject({ type: 'excerpt', text: '划选的原文' })
    expect(blocks.some(b => b.type === 'note' && b.text === '我的补充笔记')).toBe(true)
  })

  it('leaves already-interleaved content unchanged on migrate', () => {
    const interleaved = appendExcerptBlock('', { text: '原文' })
    expect(migrateLegacyToInterleaved(interleaved, '旧字段')).toBe(interleaved)
  })
})
