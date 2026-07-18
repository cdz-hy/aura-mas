import { describe, expect, it } from 'vitest'
import { resourceGenerationOptions } from './resourceGenerationOptions'

describe('resourceGenerationOptions', () => {
  it('matches the assistant resource prompt options in order', () => {
    expect(resourceGenerationOptions).toEqual([
      { type: 'text', label: '正文' },
      { type: 'quiz', label: '测验' },
      { type: 'mindmap', label: '思维导图' },
      { type: 'code', label: '代码示例' },
      { type: 'summary', label: '总结' },
      { type: 'video', label: '教学视频' },
      { type: 'animation', label: '动画' },
      { type: 'podcast', label: '播客' },
      { type: 'pptx', label: 'PPT' },
    ])
  })

  it('puts 正文 first so the outline generate menu can create main content', () => {
    expect(resourceGenerationOptions[0]).toEqual({ type: 'text', label: '正文' })
  })
})
