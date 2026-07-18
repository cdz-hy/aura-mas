export interface ResourceGenerationOption {
  type: string
  label: string
}

/** 左侧大纲与右侧助手共用的补充资源生成选项 */
export const resourceGenerationOptions: ResourceGenerationOption[] = [
  { type: 'text', label: '图文' },
  { type: 'quiz', label: '测验' },
  { type: 'mindmap', label: '思维导图' },
  { type: 'code', label: '代码示例' },
  { type: 'summary', label: '总结' },
  { type: 'video', label: '教学视频' },
  { type: 'animation', label: '动画' },
  { type: 'podcast', label: '播客' },
  { type: 'pptx', label: 'PPT' },
]
