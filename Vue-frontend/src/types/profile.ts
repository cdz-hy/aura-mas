export interface StudentProfile {
  id: number
  userId: number
  version: number
  isCurrent: number
  age: string | null
  gender: string | null
  domain: string | null
  learningBehavior: ProfileDimensions | null
  updateReason: string | null
  createdAt: string
}

export interface ProfileDimensions {
  // Felder-Silverman 四维度 (-1.0 ~ +1.0, 0.0 = 未确定)
  sensing_vs_intuitive?: number
  visual_vs_verbal?: number
  active_vs_reflective?: number
  sequential_vs_global?: number
  // 辅助维度
  knowledge_base?: string[]
  interest_tags?: string[]
  goal_orientation?: 'exam' | 'career' | 'interest' | 'research'
  weak_areas?: string[]
  preferred_resource_types?: string[]
}

export const PROFILE_DIMENSION_LABELS: Record<string, string> = {
  sensing_vs_intuitive: '感知-直觉',
  visual_vs_verbal: '视觉-言语',
  active_vs_reflective: '活跃-沉思',
  sequential_vs_global: '循序-全局',
  knowledge_base: '知识基础',
  interest_tags: '兴趣标签',
  goal_orientation: '目标导向',
  weak_areas: '薄弱环节',
  preferred_resource_types: '偏好资源',
}

export const GOAL_ORIENTATION_LABELS: Record<string, string> = {
  exam: '应试备考',
  career: '职业发展',
  interest: '兴趣爱好',
  research: '学术研究',
}

const FELDER_AXIS_LABELS: Record<string, [string, string]> = {
  sensing_vs_intuitive: ['感知型', '直觉型'],
  visual_vs_verbal: ['视觉型', '言语型'],
  active_vs_reflective: ['活跃型', '沉思型'],
  sequential_vs_global: ['循序型', '全局型'],
}

export function felderAxisLabel(axis: string, value: number): string {
  const pair = FELDER_AXIS_LABELS[axis]
  if (!pair) return ''
  if (Math.abs(value) < 0.2) return '未确定'
  return value < 0 ? pair[0] : pair[1]
}
