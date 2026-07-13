/**
 * Interleaved note document model:
 *   [原文摘录] → [我的笔记] → [原文摘录] → [我的笔记] → ...
 *
 * Stored in Note.content using fence markers so the field stays text-compatible.
 */

export interface NoteExcerptBlock {
  type: 'excerpt'
  id: string
  text: string
  sourceTitle?: string
  sourceRoute?: string
  sourceType?: string
  sourceId?: number
}

export interface NoteTextBlock {
  type: 'note'
  /** May be empty (placeholder for user to fill after a capture). */
  text: string
}

export type NoteBlock = NoteExcerptBlock | NoteTextBlock

const OPEN_RE =
  /<<<excerpt\s+([^>]*?)>>>\r?\n?([\s\S]*?)\r?\n?<<<\s*\/excerpt\s*>>>/g

function createId(): string {
  return `ex_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
}

function escapeAttr(value: string): string {
  return value
    .replace(/\\/g, '\\\\')
    .replace(/"/g, '\\"')
    .replace(/\n/g, ' ')
}

function unescapeAttr(value: string): string {
  return value.replace(/\\"/g, '"').replace(/\\\\/g, '\\')
}

function parseAttrs(raw: string): Record<string, string> {
  const out: Record<string, string> = {}
  const re = /(\w+)="((?:\\.|[^"\\])*)"/g
  let m: RegExpExecArray | null
  while ((m = re.exec(raw)) !== null) {
    out[m[1]] = unescapeAttr(m[2])
  }
  return out
}

/** Parse interleaved blocks from note content. */
export function parseNoteBlocks(content?: string | null): NoteBlock[] {
  const raw = content ?? ''
  if (!raw.trim()) return [{ type: 'note', text: '' }]

  const blocks: NoteBlock[] = []
  let lastIndex = 0
  OPEN_RE.lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = OPEN_RE.exec(raw)) !== null) {
    const before = raw.slice(lastIndex, match.index)
    if (before.trim() || blocks.length === 0) {
      // Keep leading whitespace-only only if it's the only note so far and empty doc edge cases
      blocks.push({ type: 'note', text: before.replace(/^\n+|\n+$/g, '') })
    } else if (before.length > 0) {
      blocks.push({ type: 'note', text: before.replace(/^\n+|\n+$/g, '') })
    }

    const attrs = parseAttrs(match[1] || '')
    blocks.push({
      type: 'excerpt',
      id: attrs.id || createId(),
      text: (match[2] || '').replace(/^\n+|\n+$/g, ''),
      ...(attrs.sourceTitle ? { sourceTitle: attrs.sourceTitle } : {}),
      ...(attrs.sourceRoute ? { sourceRoute: attrs.sourceRoute } : {}),
      ...(attrs.sourceType ? { sourceType: attrs.sourceType } : {}),
      ...(attrs.sourceId && /^\d+$/.test(attrs.sourceId)
        ? { sourceId: Number(attrs.sourceId) }
        : {}),
    })
    lastIndex = match.index + match[0].length
  }

  const after = raw.slice(lastIndex)
  if (after.trim() || blocks.length === 0 || blocks[blocks.length - 1]?.type === 'excerpt') {
    blocks.push({ type: 'note', text: after.replace(/^\n+/, '') })
  }

  // Drop purely empty leading note if document starts with excerpt
  if (
    blocks.length >= 2
    && blocks[0].type === 'note'
    && !blocks[0].text.trim()
    && blocks[1].type === 'excerpt'
  ) {
    blocks.shift()
  }

  return blocks.length > 0 ? blocks : [{ type: 'note', text: '' }]
}

/** Serialize blocks back to content string. */
export function serializeNoteBlocks(blocks: NoteBlock[]): string {
  const parts: string[] = []
  for (const block of blocks) {
    if (block.type === 'note') {
      if (block.text) parts.push(block.text)
      continue
    }
    const attrs = [
      `id="${escapeAttr(block.id)}"`,
      block.sourceTitle ? `sourceTitle="${escapeAttr(block.sourceTitle)}"` : '',
      block.sourceRoute ? `sourceRoute="${escapeAttr(block.sourceRoute)}"` : '',
      block.sourceType ? `sourceType="${escapeAttr(block.sourceType)}"` : '',
      typeof block.sourceId === 'number' ? `sourceId="${block.sourceId}"` : '',
    ]
      .filter(Boolean)
      .join(' ')
    parts.push(`<<<excerpt ${attrs}>>>\n${block.text.trim()}\n<<< /excerpt >>>`)
  }
  return parts.join('\n\n').trim()
}

export function createExcerptBlock(input: {
  text: string
  sourceTitle?: string
  sourceRoute?: string
  sourceType?: string
  sourceId?: number
  id?: string
}): NoteExcerptBlock {
  return {
    type: 'excerpt',
    id: input.id || createId(),
    text: input.text.trim(),
    ...(input.sourceTitle ? { sourceTitle: input.sourceTitle } : {}),
    ...(input.sourceRoute ? { sourceRoute: input.sourceRoute } : {}),
    ...(input.sourceType ? { sourceType: input.sourceType } : {}),
    ...(typeof input.sourceId === 'number' ? { sourceId: input.sourceId } : {}),
  }
}

/**
 * Append a new excerpt + empty note slot after it (for 追加/添加 capture).
 * Ensures user can write notes right under the new excerpt.
 */
export function appendExcerptBlock(
  content: string | null | undefined,
  excerpt: {
    text: string
    sourceTitle?: string
    sourceRoute?: string
    sourceType?: string
    sourceId?: number
  },
): string {
  const blocks = parseNoteBlocks(content)
  const text = excerpt.text.trim()
  if (!text) return serializeNoteBlocks(blocks)

  // Skip if last excerpt is identical
  for (let i = blocks.length - 1; i >= 0; i--) {
    const b = blocks[i]
    if (b.type === 'excerpt') {
      if (b.text.trim() === text) return serializeNoteBlocks(blocks)
      break
    }
  }

  blocks.push(createExcerptBlock(excerpt))
  blocks.push({ type: 'note', text: '' })
  return serializeNoteBlocks(blocks)
}

/**
 * Migrate legacy notes that stored 原文 in `excerpt` field and 补充 in `content`.
 * If content has no fence markers, prepend excerpt(s) then user content.
 */
export function migrateLegacyToInterleaved(
  content: string | null | undefined,
  legacyExcerpt?: string | null,
): string {
  const raw = content ?? ''
  if (/<<<excerpt\b/.test(raw)) return raw

  // Multi-excerpt JSON from previous multi-list design
  let legacyItems: Array<{
    text: string
    sourceTitle?: string
    sourceRoute?: string
    sourceType?: string
    sourceId?: number
  }> = []

  if (legacyExcerpt?.trim()) {
    const t = legacyExcerpt.trim()
    if (t.startsWith('{') || t.startsWith('[')) {
      try {
        const parsed = JSON.parse(t) as { items?: typeof legacyItems } | typeof legacyItems
        const items = Array.isArray(parsed) ? parsed : parsed.items
        if (Array.isArray(items)) {
          legacyItems = items.filter(i => i?.text?.trim())
        }
      } catch {
        legacyItems = [{ text: t }]
      }
    } else {
      legacyItems = [{ text: t }]
    }
  }

  if (legacyItems.length === 0) return raw

  const blocks: NoteBlock[] = []
  for (const item of legacyItems) {
    blocks.push(createExcerptBlock(item))
    blocks.push({ type: 'note', text: '' })
  }
  // Put existing user content into the last note slot
  if (raw.trim()) {
    const last = blocks[blocks.length - 1]
    if (last?.type === 'note') last.text = raw
    else blocks.push({ type: 'note', text: raw })
  }
  return serializeNoteBlocks(blocks)
}

/** Collect all excerpt texts for list preview / AI context. */
export function collectExcerptTexts(content?: string | null): string[] {
  return parseNoteBlocks(content)
    .filter((b): b is NoteExcerptBlock => b.type === 'excerpt')
    .map(b => b.text)
    .filter(Boolean)
}

/**
 * One source row per 原文 excerpt block (no dedupe / no cap).
 * Same resource with 3 excerpts → 3 rows, keyed by excerpt id.
 */
export function collectContentSources(content?: string | null): Array<{
  key: string
  sourceTitle: string
  sourceRoute?: string
  sourceType?: string
  sourceId?: number
  excerptPreview: string
}> {
  const out: Array<{
    key: string
    sourceTitle: string
    sourceRoute?: string
    sourceType?: string
    sourceId?: number
    excerptPreview: string
  }> = []
  let i = 0
  for (const b of parseNoteBlocks(content)) {
    if (b.type !== 'excerpt' || !b.text.trim()) continue
    i += 1
    const title = b.sourceTitle?.trim()
    const preview = b.text.replace(/\s+/g, ' ').trim()
    out.push({
      key: b.id || `excerpt-${i}`,
      sourceTitle: title || `原文 ${i}`,
      ...(b.sourceRoute ? { sourceRoute: b.sourceRoute } : {}),
      ...(b.sourceType ? { sourceType: b.sourceType } : {}),
      ...(typeof b.sourceId === 'number' ? { sourceId: b.sourceId } : {}),
      excerptPreview: preview.length > 48 ? `${preview.slice(0, 48)}…` : preview,
    })
  }
  return out
}

export function joinExcerptsFromContent(content?: string | null): string {
  const texts = collectExcerptTexts(content)
  if (texts.length === 0) return ''
  if (texts.length === 1) return texts[0]
  return texts.map((t, i) => `【摘录 ${i + 1}】\n${t}`).join('\n\n')
}

/** Plain preview text for list cards (prefer first excerpt, else first note). */
export function interleavedPreview(content?: string | null, maxLength = 80): string {
  const blocks = parseNoteBlocks(content)
  const firstExcerpt = blocks.find((b): b is NoteExcerptBlock => b.type === 'excerpt' && !!b.text.trim())
  const firstNote = blocks.find((b): b is NoteTextBlock => b.type === 'note' && !!b.text.trim())
  const excerptCount = blocks.filter(b => b.type === 'excerpt' && b.text.trim()).length

  let base = firstExcerpt?.text || firstNote?.text || ''
  base = base.replace(/\s+/g, ' ').trim()
  if (!base) return ''

  if (excerptCount > 1 && firstExcerpt) {
    const short = base.length > maxLength - 12 ? `${base.slice(0, maxLength - 12).trim()}…` : base
    return `${excerptCount} 段原文 · ${short}`
  }
  return base.length > maxLength ? `${base.slice(0, maxLength).trim()}…` : base
}

export function updateBlockText(blocks: NoteBlock[], index: number, text: string): NoteBlock[] {
  return blocks.map((b, i) => {
    if (i !== index) return b
    if (b.type === 'excerpt') return { ...b, text }
    return { ...b, text }
  })
}

export function removeBlockAt(blocks: NoteBlock[], index: number): NoteBlock[] {
  const next = blocks.filter((_, i) => i !== index)
  // Merge adjacent note blocks
  const merged: NoteBlock[] = []
  for (const b of next) {
    const prev = merged[merged.length - 1]
    if (b.type === 'note' && prev?.type === 'note') {
      prev.text = [prev.text, b.text].filter(Boolean).join('\n\n')
    } else {
      merged.push({ ...b })
    }
  }
  if (merged.length === 0) merged.push({ type: 'note', text: '' })
  // Ensure trailing note slot after last excerpt
  if (merged[merged.length - 1]?.type === 'excerpt') {
    merged.push({ type: 'note', text: '' })
  }
  return merged
}

const NOTE_OPEN_RE =
  /<<<note\s+([^>]*?)>>>\r?\n?([\s\S]*?)\r?\n?<<<\s*\/note\s*>>>/g

/**
 * For 整理笔记: when content has 原文 fences, send each 补充 slot paired with its
 * preceding 原文 as read-only context. AI must only rewrite inside <<<note>>>;
 * client reattaches original excerpt fences after.
 */
export function buildFormatPayload(content: string): {
  contentForAi: string
  hasInterleaved: boolean
  noteCount: number
} {
  const blocks = parseNoteBlocks(content)
  const hasInterleaved = blocks.some(b => b.type === 'excerpt' && !!b.text.trim())
  if (!hasInterleaved) {
    return { contentForAi: content, hasInterleaved: false, noteCount: 0 }
  }

  const parts: string[] = []
  let noteIndex = 0
  let lastExcerptText = ''

  for (const b of blocks) {
    if (b.type === 'excerpt') {
      lastExcerptText = b.text.trim()
      continue
    }
    const idx = noteIndex++
    const userNote = b.text ?? ''
    parts.push(
      [
        `### 第 ${idx + 1} 段`,
        `【对应原文·只读·禁止写入输出·禁止改写】`,
        lastExcerptText || '（本段无对应原文）',
        '',
        `【用户补充·请整理进下方 note 块；若为空/过短/无意义，请根据上文原文写出结构化学习补充】`,
        `<<<note index="${idx}">>>`,
        userNote,
        `<<< /note >>>`,
      ].join('\n'),
    )
  }

  if (parts.length === 0) {
    parts.push(
      [
        `### 第 1 段`,
        `【对应原文·只读·禁止写入输出·禁止改写】`,
        lastExcerptText || '（无）',
        '',
        `【用户补充·请根据原文写出结构化学习补充】`,
        `<<<note index="0">>>`,
        '',
        `<<< /note >>>`,
      ].join('\n'),
    )
  }

  return {
    contentForAi: parts.join('\n\n'),
    hasInterleaved: true,
    noteCount: Math.max(noteIndex, 1),
  }
}

/**
 * Remove AI/format junk that must never appear in note body:
 * empty <<>>, leftover <<<note>>> fences, orphan >> / ... lines, etc.
 * Does NOT strip valid <<A:id|type|text>> annotations or <<<excerpt>>> blocks.
 */
export function stripFormatArtifacts(text: string): string {
  if (!text) return text
  let s = text
  // leftover note-slot fences from format pipeline (keep <<<excerpt>>> intact)
  s = s.replace(/<<<\s*note\b[^>]*>>>/gi, '')
  s = s.replace(/<<<\s*\/\s*note\s*>>>/gi, '')
  // empty / broken angle-bracket tokens (<<>>, <<<>>>, << >>, etc.)
  s = s.replace(/<<\s*>>/g, '')
  s = s.replace(/<<<\s*>>>/g, '')
  // whole lines that are only < and/or > (AI fence leftovers / nested blockquote junk)
  s = s.replace(/^[ \t]*[<>]{1,}[ \t]*$/gm, '')
  // whole lines that are only ellipsis (..., …, ....)
  s = s.replace(/^[ \t]*(\.{2,}|…+)[ \t]*$/gm, '')
  // lines like ">> ..." or "> ..."
  s = s.replace(/^[ \t]*[<>]{1,}\s*(\.{2,}|…+)?[ \t]*$/gm, '')
  // trailing orphan >> glued to end of a normal sentence line
  // never touch real <<<…>>> fences or <<A:…>> annotation markers
  s = s
    .split('\n')
    .map((line) => {
      if (/<<</.test(line) || /<<A:/.test(line)) return line
      // "综合性。>>" or "综合性。>>>" → drop trailing brackets
      return line.replace(/[ \t]*>{2,}\s*$/g, '')
    })
    .join('\n')
  // collapse blank lines
  s = s.replace(/\n{3,}/g, '\n\n')
  return s.trim()
}

/**
 * Enforce strict 原文→笔记→原文→笔记 order.
 * Leading notes (before first excerpt) are moved under the first excerpt;
 * each excerpt gets exactly one following note slot.
 */
export function normalizeInterleavedOrder(content: string): string {
  const blocks = parseNoteBlocks(content)
  const excerpts = blocks.filter((b): b is NoteExcerptBlock => b.type === 'excerpt')
  if (excerpts.length === 0) return stripFormatArtifacts(content)

  const pairs: { excerpt: NoteExcerptBlock; notes: string[] }[] = []
  let leadingNotes: string[] = []
  let current: { excerpt: NoteExcerptBlock; notes: string[] } | null = null

  for (const b of blocks) {
    if (b.type === 'excerpt') {
      if (current) pairs.push(current)
      current = { excerpt: { ...b }, notes: [] }
      continue
    }
    const t = stripFormatArtifacts(b.text || '')
    if (!t) continue
    if (!current) leadingNotes.push(t)
    else current.notes.push(t)
  }
  if (current) pairs.push(current)

  // Attach orphan leading notes to the first excerpt's note slot
  if (pairs.length > 0 && leadingNotes.length > 0) {
    pairs[0].notes = [...leadingNotes, ...pairs[0].notes]
  }

  const rebuilt: NoteBlock[] = []
  for (const p of pairs) {
    rebuilt.push(p.excerpt)
    rebuilt.push({
      type: 'note',
      text: stripFormatArtifacts(p.notes.join('\n\n')),
    })
  }
  return serializeNoteBlocks(rebuilt)
}

/** Split a bare AI blob into per-excerpt note slots when possible. */
function splitBareNotesForSlots(body: string, expectedCount: number): string[] {
  const cleaned = stripFormatArtifacts(body)
  if (expectedCount <= 1) return [cleaned]

  // Prefer explicit section markers the model often emits
  const byHeader = cleaned
    .split(/(?=^#{1,3}\s+第\s*\d+\s*段)/m)
    .map(s => s.trim())
    .filter(Boolean)
  if (byHeader.length === expectedCount) {
    return byHeader.map(stripFormatArtifacts)
  }

  // Split on repeated 一句话概括 callouts (common after our format prompt)
  const bySummary = cleaned
    .split(/(?=^>\s*\*\*一句话概括\*\*)/m)
    .map(s => s.trim())
    .filter(Boolean)
  if (bySummary.length === expectedCount) {
    return bySummary.map(stripFormatArtifacts)
  }
  if (bySummary.length > 1 && bySummary.length < expectedCount) {
    const out = bySummary.map(stripFormatArtifacts)
    while (out.length < expectedCount) out.push('')
    return out
  }

  // Fallback: all in first slot (later normalize still keeps 原文 order)
  return [cleaned, ...Array.from({ length: expectedCount - 1 }, () => '')]
}

/** Parse AI output that used <<<note index="N">>> markers (or a bare blob). */
export function parseFormattedNoteSlots(formatted: string, expectedCount: number): string[] {
  const byIndex = new Map<number, string>()
  NOTE_OPEN_RE.lastIndex = 0
  let match: RegExpExecArray | null
  let order = 0
  while ((match = NOTE_OPEN_RE.exec(formatted)) !== null) {
    const attrs = parseAttrs(match[1] || '')
    const idx =
      attrs.index != null && /^\d+$/.test(attrs.index) ? Number(attrs.index) : order
    byIndex.set(idx, stripFormatArtifacts((match[2] || '').replace(/^\n+|\n+$/g, '')))
    order += 1
  }
  if (byIndex.size > 0) {
    const maxIdx = Math.max(expectedCount - 1, ...byIndex.keys(), 0)
    const notes: string[] = []
    for (let i = 0; i <= maxIdx; i++) {
      notes.push(byIndex.has(i) ? (byIndex.get(i) as string) : '')
    }
    return notes
  }

  // Strip any leftover excerpt fences from a full-doc rewrite, then split by section if possible
  const body = formatted.replace(/<<<excerpt\b[\s\S]*?<<<\s*\/excerpt\s*>>>/g, '')
  return splitBareNotesForSlots(body, expectedCount)
}

/**
 * After AI format: always keep original <<<excerpt>>> blocks (原文) in order;
 * only replace user-note slots with polished 补充; force 原文→笔记 alternating.
 */
export function preserveInterleavedStructure(
  original: string,
  formatted: string,
): string {
  // Always start from a normalized original so leading-note drift is corrected first
  const normalizedOriginal = normalizeInterleavedOrder(original)
  const origBlocks = parseNoteBlocks(normalizedOriginal)
  const hasExcerpt = origBlocks.some(b => b.type === 'excerpt' && b.text.trim())
  if (!hasExcerpt) return stripFormatArtifacts(formatted.trim() || original)

  // Only count note slots that sit after excerpts (strict alternating after normalize)
  const noteSlotCount = origBlocks.filter(b => b.type === 'note').length
  const fmtBlocks = parseNoteBlocks(formatted)

  let fmtNotes: string[]

  // Path A: AI returned full doc with excerpt fences → take only its note slots (in order)
  if (fmtBlocks.some(b => b.type === 'excerpt')) {
    // Normalize AI output too, then take notes in 原文 order
    const aiNorm = normalizeInterleavedOrder(formatted)
    const aiBlocks = parseNoteBlocks(aiNorm)
    fmtNotes = aiBlocks
      .filter((b): b is NoteTextBlock => b.type === 'note')
      .map(b => stripFormatArtifacts(b.text))
    // If AI dropped some excerpts, fall back to bare split of note-only text
    if (fmtNotes.every(n => !n.trim())) {
      fmtNotes = parseFormattedNoteSlots(formatted, noteSlotCount)
    }
  } else if (/<<<note\b/.test(formatted)) {
    // Path B: note-only markers (preferred pipeline)
    fmtNotes = parseFormattedNoteSlots(formatted, noteSlotCount)
  } else {
    // Path C: bare polished blob (AI dropped structure)
    fmtNotes = parseFormattedNoteSlots(formatted, noteSlotCount)
  }

  // Rebuild STRICTLY as excerpt → note → excerpt → note using original excerpts only
  const excerpts = origBlocks.filter((b): b is NoteExcerptBlock => b.type === 'excerpt')
  const rebuilt: NoteBlock[] = []
  for (let i = 0; i < excerpts.length; i++) {
    rebuilt.push({ ...excerpts[i] })
    const noteText = stripFormatArtifacts(fmtNotes[i] ?? '')
    // If this slot empty but we have a leftover blob only in slot 0, don't duplicate
    rebuilt.push({ type: 'note', text: noteText })
  }
  // Extra AI notes beyond excerpt count → append to last note slot (don't create trailing free notes)
  if (fmtNotes.length > excerpts.length) {
    const extra = fmtNotes
      .slice(excerpts.length)
      .map(stripFormatArtifacts)
      .filter(t => t.trim())
    if (extra.length > 0) {
      const last = rebuilt[rebuilt.length - 1]
      if (last?.type === 'note') {
        last.text = stripFormatArtifacts([last.text, ...extra].filter(Boolean).join('\n\n'))
      }
    }
  }

  return normalizeInterleavedOrder(serializeNoteBlocks(rebuilt))
}
