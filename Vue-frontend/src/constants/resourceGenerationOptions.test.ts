import { describe, expect, it } from 'vitest'
import { resourceGenerationOptions } from './resourceGenerationOptions'

describe('resourceGenerationOptions', () => {
  it('matches the assistant resource prompt options in order', () => {
    expect(resourceGenerationOptions).toEqual([
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
})
