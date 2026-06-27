import { PYTHON_AI_BASE } from './request'

export interface TemplateInfo {
  name: string
  description: string
}

export interface TemplateDetail {
  name: string
  description: string
  slide_count: number
  layouts: {
    name: string
    template_id: number
    slide_count: number
    elements: { name: string; type: string }[]
  }[]
  functional_keys: string[]
}

/**
 * 获取所有可用 PPT 模板列表
 */
export async function fetchTemplates(): Promise<TemplateInfo[]> {
  const res = await fetch(`${PYTHON_AI_BASE}/api/ai/templates`)
  if (!res.ok) throw new Error('获取模板列表失败')
  const data = await res.json()
  return data.templates || []
}
