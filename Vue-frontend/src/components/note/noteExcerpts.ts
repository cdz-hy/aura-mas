/**
 * Multi-excerpt support for capture notes.
 * Stored in Note.excerpt as either:
 * - legacy plain string (single excerpt)
 * - JSON: { "v": 1, "items": NoteExcerptItem[] }
 */

export interface NoteExcerptItem {
  id: string
  text: string
  sourceTitle?: string
  sourceRoute?: string
  sourceType?: string
  sourceId?: number
}

const MULTI_VERSION = 1

export function createExcerptId(): string {
  return `ex_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
}

export function parseExcerpts(raw?: string | null): NoteExcerptItem[] {
  if (!raw) return []
  const trimmed = raw.trim()
  if (!trimmed) return []

  // Multi format
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      const parsed = JSON.parse(trimmed) as
        | { v?: number; items?: NoteExcerptItem[] }
        | NoteExcerptItem[]
      const items = Array.isArray(parsed) ? parsed : parsed.items
      if (Array.isArray(items)) {
        return items
          .filter(it => it && typeof it.text === 'string' && it.text.trim())
          .map(it => ({
            id: typeof it.id === 'string' && it.id ? it.id : createExcerptId(),
            text: String(it.text).trim(),
            ...(it.sourceTitle ? { sourceTitle: String(it.sourceTitle) } : {}),
            ...(it.sourceRoute ? { sourceRoute: String(it.sourceRoute) } : {}),
            ...(it.sourceType ? { sourceType: String(it.sourceType) } : {}),
            ...(typeof it.sourceId === 'number' ? { sourceId: it.sourceId } : {}),
          }))
      }
    } catch {
      // fall through to plain string
    }
  }

  // Legacy single plain-text excerpt
  return [{ id: createExcerptId(), text: trimmed }]
}

export function serializeExcerpts(items: NoteExcerptItem[]): string {
  const cleaned = items
    .filter(it => it.text?.trim())
    .map(it => ({
      id: it.id || createExcerptId(),
      text: it.text.trim(),
      ...(it.sourceTitle?.trim() ? { sourceTitle: it.sourceTitle.trim() } : {}),
      ...(it.sourceRoute?.trim() ? { sourceRoute: it.sourceRoute.trim() } : {}),
      ...(it.sourceType ? { sourceType: it.sourceType } : {}),
      ...(typeof it.sourceId === 'number' ? { sourceId: it.sourceId } : {}),
    }))

  if (cleaned.length === 0) return ''
  // Keep single plain-text for simple notes (backward-friendly)
  if (cleaned.length === 1 && !cleaned[0].sourceTitle && !cleaned[0].sourceRoute) {
    return cleaned[0].text
  }
  return JSON.stringify({ v: MULTI_VERSION, items: cleaned })
}

export function appendExcerpt(
  raw: string | null | undefined,
  item: Omit<NoteExcerptItem, 'id'> & { id?: string },
): string {
  const text = item.text?.trim()
  if (!text) return raw?.trim() || ''

  const existing = parseExcerpts(raw)
  // Dedupe exact same text at the end
  if (existing.length > 0 && existing[existing.length - 1].text === text) {
    return serializeExcerpts(existing)
  }

  existing.push({
    id: item.id || createExcerptId(),
    text,
    ...(item.sourceTitle ? { sourceTitle: item.sourceTitle } : {}),
    ...(item.sourceRoute ? { sourceRoute: item.sourceRoute } : {}),
    ...(item.sourceType ? { sourceType: item.sourceType } : {}),
    ...(typeof item.sourceId === 'number' ? { sourceId: item.sourceId } : {}),
  })
  return serializeExcerpts(existing)
}

/** Flatten excerpts for AI / single-string consumers. */
export function joinExcerptsForContext(raw?: string | null): string {
  const items = parseExcerpts(raw)
  if (items.length === 0) return ''
  if (items.length === 1) return items[0].text
  return items
    .map((it, i) => {
      const head = it.sourceTitle ? `【摘录 ${i + 1} · ${it.sourceTitle}】` : `【摘录 ${i + 1}】`
      return `${head}\n${it.text}`
    })
    .join('\n\n')
}

export function updateExcerptItem(
  raw: string | null | undefined,
  id: string,
  patch: Partial<Pick<NoteExcerptItem, 'text' | 'sourceTitle' | 'sourceRoute'>>,
): string {
  const items = parseExcerpts(raw).map(it =>
    it.id === id ? { ...it, ...patch, text: patch.text !== undefined ? patch.text : it.text } : it,
  )
  return serializeExcerpts(items)
}

export function removeExcerptItem(raw: string | null | undefined, id: string): string {
  return serializeExcerpts(parseExcerpts(raw).filter(it => it.id !== id))
}
