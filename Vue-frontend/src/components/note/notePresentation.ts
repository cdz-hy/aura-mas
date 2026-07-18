import type { Note, NoteResourceRel, NoteType, OrganizeStatus } from '@/types/note'
import { interleavedPreview } from './noteBlocks'
import { parseExcerpts } from './noteExcerpts'

/** Collapse noisy error / raw JSON dumps into a short human label for list previews. */
export function sanitizeNotePreviewText(content: string): string {
  const raw = content.trim()
  if (!raw) return ''

  // MIMO / API error dumps (common when generation fails and error is saved as content)
  if (
    /内容生成失败|Too many requests|"code"\s*:\s*429|limitation/i.test(raw)
    || (/^\s*\{[\s\S]*"error"\s*:/.test(raw) && /"message"\s*:/.test(raw))
  ) {
    return '内容生成失败，可重试或改写笔记'
  }

  // Generic JSON blob
  if (/^\s*[\{\[]/.test(raw) && /"[\w]+"\s*:/.test(raw) && raw.length > 40) {
    return '结构化数据（请打开完整笔记查看）'
  }

  return raw
}

export function toNotePreview(content: string, maxLength = 80): string {
  const cleaned = sanitizeNotePreviewText(content)
  const plain = cleaned
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/<<A:[^|>]+\|[^|>]+\|([^>]+)>>/g, '$1 ')
    .replace(/[`#>*_~\[\]()]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return plain.length > maxLength ? `${plain.slice(0, maxLength).trim()}…` : plain
}

export function toSourceLabel(resources: NoteResourceRel[]): string | null {
  const source = resources[0]
  if (!source) return null
  // Prefer real title; only fall back to resource #id when nothing else exists
  if (source.resourceTitle?.trim() || source.moduleName?.trim()) {
    return [source.moduleName, source.resourceTitle].filter(Boolean).join(' · ')
  }
  if (source.resourceId) return `资源 #${source.resourceId}`
  return null
}

/** Labels that are placeholders rather than real learning titles. */
export function isGenericSourceLabel(label?: string | null): boolean {
  if (!label) return true
  const t = label.trim()
  if (!t) return true
  if (/^资源\s*#\d+$/i.test(t)) return true
  return ['学习资源', '学习来源', '学习计划', '智能辅导', '知识树节点', '知识树'].includes(t)
}

/**
 * Build a frontend route for a note's capture source.
 * Prefers persisted sourceRoute; otherwise constructs plan/resource deep links.
 */
export function resolveNoteSourceRoute(
  note: Pick<Note, 'sourceRoute' | 'sourceType' | 'sourceId'>,
  rel?: Pick<NoteResourceRel, 'planId' | 'resourceId'> | null,
  resourcePlanId?: number | null,
): string | null {
  const stored = note.sourceRoute?.trim()
  if (stored) return stored

  const planId = rel?.planId ?? resourcePlanId ?? undefined
  const resourceId =
    (note.sourceType === 'resource' && note.sourceId) ? note.sourceId : rel?.resourceId

  if (planId && resourceId) return `/plan/${planId}?resource=${resourceId}`
  if (note.sourceType === 'plan' && note.sourceId) return `/plan/${note.sourceId}`
  if (planId) return `/plan/${planId}`
  return null
}

/** Safe default for legacy notes without capture metadata. */
export function effectiveNoteType(noteType?: NoteType | string | null): NoteType {
  if (noteType === 'excerpt' || noteType === 'quick' || noteType === 'question') return noteType
  return 'quick'
}

/** Safe default for legacy notes without capture metadata. */
export function effectiveOrganizeStatus(
  status?: OrganizeStatus | string | null,
): OrganizeStatus {
  if (status === 'pending' || status === 'organizing' || status === 'organized' || status === 'error') {
    return status
  }
  return 'pending'
}

export function noteTypeLabel(noteType?: NoteType | string | null): string {
  switch (effectiveNoteType(noteType)) {
    case 'excerpt':
      return '摘录'
    case 'question':
      return '问题'
    default:
      return '速记'
  }
}

/** Minimal monochrome tones for mode badges (keep UI calm). */
export function noteTypeTone(_noteType?: NoteType | string | null): {
  badge: string
  dot: string
} {
  return {
    badge: 'bg-navy-50 text-navy-500 ring-1 ring-navy-100/80',
    dot: 'bg-navy-300',
  }
}

export function organizeStatusLabel(status?: OrganizeStatus | string | null): string {
  switch (effectiveOrganizeStatus(status)) {
    case 'organizing':
      return '整理中'
    case 'organized':
      return '已整理'
    case 'error':
      return '整理失败'
    default:
      return '待整理'
  }
}

export function organizeStatusTone(status?: OrganizeStatus | string | null): string {
  switch (effectiveOrganizeStatus(status)) {
    case 'organizing':
      return 'bg-navy-50 text-navy-500'
    case 'organized':
      return 'bg-navy-50 text-navy-600'
    case 'error':
      return 'bg-navy-50 text-navy-500 ring-1 ring-navy-200'
    default:
      return 'bg-navy-50 text-navy-500'
  }
}

/**
 * Two-group classification for the sidebar list.
 * Only fully organized notes land in 已整理; everything else is 待整理
 * (including organizing/error/legacy).
 */
export function noteGroup(
  note: Pick<Note, 'organizeStatus'> | { organizeStatus?: OrganizeStatus | string | null },
): 'pending' | 'organized' {
  return effectiveOrganizeStatus(note.organizeStatus) === 'organized' ? 'organized' : 'pending'
}

/**
 * List preview: prefer interleaved 原文/笔记 document in content;
 * fall back to legacy excerpt field, then plain content.
 */
export function noteListPreview(
  note: Pick<Note, 'content' | 'excerpt'>,
  maxLength = 80,
): string {
  // Interleaved markers in content
  if (note.content && /<<<excerpt\b/.test(note.content)) {
    const p = interleavedPreview(note.content, maxLength + 40)
    if (p) {
      // Preserve "N 段原文 · " prefix; clean the rest
      const m = p.match(/^(\d+ 段原文 · )([\s\S]*)$/)
      if (m) return m[1] + toNotePreview(m[2], maxLength - 12)
      return toNotePreview(p, maxLength)
    }
  }
  // Legacy multi/single excerpt field
  const items = parseExcerpts(note.excerpt)
  if (items.length > 1) {
    const first = toNotePreview(items[0].text, Math.max(20, maxLength - 12))
    return `${items.length} 条摘录 · ${first}`
  }
  if (items.length === 1) return toNotePreview(items[0].text, maxLength)
  return toNotePreview(note.content ?? '', maxLength)
}

/**
 * Display label for capture source.
 * Prefer non-generic titles: real sourceTitle > resource label > generic fallback.
 */
export function noteSourceDisplay(
  note: Pick<Note, 'sourceTitle' | 'sourceType'>,
  resourceLabel?: string | null,
): string | null {
  const title = note.sourceTitle?.trim() || null
  const rel = resourceLabel?.trim() || null

  if (title && !isGenericSourceLabel(title)) return title
  if (rel && !isGenericSourceLabel(rel)) return rel
  if (title) return title
  if (rel) return rel
  return null
}

/** True when content looks like a generation / API failure dump. */
export function isErrorDumpContent(content?: string | null): boolean {
  if (!content) return false
  return sanitizeNotePreviewText(content) === '内容生成失败，可重试或改写笔记'
}
