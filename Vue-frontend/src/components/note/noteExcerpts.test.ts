import { describe, expect, it } from 'vitest'
import {
  appendExcerpt,
  joinExcerptsForContext,
  parseExcerpts,
  removeExcerptItem,
  serializeExcerpts,
  updateExcerptItem,
} from './noteExcerpts'

describe('noteExcerpts', () => {
  it('parses legacy plain-text as a single item', () => {
    const items = parseExcerpts('当 x 趋近于 a 时')
    expect(items).toHaveLength(1)
    expect(items[0].text).toBe('当 x 趋近于 a 时')
  })

  it('round-trips multi excerpts as JSON', () => {
    const raw = appendExcerpt('', { text: '第一段原文', sourceTitle: '资源A' })
    const raw2 = appendExcerpt(raw, { text: '第二段原文', sourceTitle: '资源B', sourceRoute: '/plan/1?resource=2' })
    const items = parseExcerpts(raw2)
    expect(items).toHaveLength(2)
    expect(items[0].text).toBe('第一段原文')
    expect(items[1].sourceRoute).toBe('/plan/1?resource=2')
    expect(parseExcerpts(serializeExcerpts(items))).toHaveLength(2)
  })

  it('does not duplicate identical trailing excerpt on append', () => {
    const raw = appendExcerpt('', { text: '同一段' })
    const raw2 = appendExcerpt(raw, { text: '同一段' })
    expect(parseExcerpts(raw2)).toHaveLength(1)
  })

  it('updates and removes items by id', () => {
    let raw = appendExcerpt('', { text: 'A', sourceTitle: 'S1' })
    raw = appendExcerpt(raw, { text: 'B', sourceTitle: 'S2' })
    const [first, second] = parseExcerpts(raw)
    raw = updateExcerptItem(raw, first.id, { text: 'A2' })
    expect(parseExcerpts(raw)[0].text).toBe('A2')
    raw = removeExcerptItem(raw, second.id)
    expect(parseExcerpts(raw)).toHaveLength(1)
    expect(parseExcerpts(raw)[0].text).toBe('A2')
  })

  it('joins multi excerpts for AI context', () => {
    const raw = appendExcerpt(
      appendExcerpt('', { text: '甲', sourceTitle: '来源1' }),
      { text: '乙', sourceTitle: '来源2' },
    )
    const joined = joinExcerptsForContext(raw)
    expect(joined).toContain('摘录 1')
    expect(joined).toContain('甲')
    expect(joined).toContain('乙')
  })
})
