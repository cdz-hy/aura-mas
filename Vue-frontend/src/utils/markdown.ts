import { marked } from 'marked'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true,
})

export function parseMarkdown(md: string): string {
  if (!md) return ''
  // Strip incomplete image markdown during streaming to prevent layout jumps
  const cleaned = md.replace(/!\[[^\]]*\]\([^)]*$/, '')
  return marked.parse(cleaned) as string
}

// Extract draggable text segments from rendered HTML
export function extractTextSegments(html: string): Array<{ text: string; position: string }> {
  const segments: Array<{ text: string; position: string }> = []
  const div = document.createElement('div')
  div.innerHTML = html
  const elements = div.querySelectorAll('p, li, h1, h2, h3, h4, blockquote, td')
  elements.forEach((el, i) => {
    const text = el.textContent?.trim()
    if (text && text.length > 5) {
      segments.push({
        text: text.substring(0, 200),
        position: `segment-${i}`,
      })
    }
  })
  return segments
}
